"""GitHub connector: connect a repository, clone/import it, run the initial
genome build, and store repository metadata for later incremental syncs.

Design:
  * Stdlib only. `git` for clone/fetch; `urllib` for the GitHub REST metadata
    call. No third-party deps (keeps the CE install a one-liner).
  * Public repos, private repos (Personal Access Token), and org repos are all
    supported. A local path is also accepted as a "remote" — handy for testing
    and air-gapped mirrors.
  * The token is NEVER written to disk or into the git remote. We clone with an
    ephemeral credential header and reset `origin` to the clean URL afterwards.
    Private-repo syncs pass the token again at sync time.
  * Repository metadata lives on the existing `repo:<name>` graph node (props),
    so it is bitemporal and exportable like every other fact.

Public entry points: connect(), sync_repo(), list_repos(), repo_meta().
"""
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import continuous
from . import genome_ops as ops
from .ingest import census, ingest_repo

GITHUB_URL = re.compile(
    r"^(?:https?://(?:www\.)?github\.com/|git@github\.com:)"
    r"(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$")
SHORTHAND = re.compile(r"^(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)$")


# ------------------------------------------------------------------- parsing
def parse_repo_url(url: str):
    """-> {'kind': 'github'|'local', 'owner', 'repo', 'clean_url'} or raises."""
    url = url.strip()
    p = Path(url).expanduser()
    if url.startswith((".", "/", "~")) or p.exists():
        name = p.name.replace(".git", "")
        return {"kind": "local", "owner": None, "repo": name,
                "clean_url": str(p.resolve() if p.exists() else p)}
    m = GITHUB_URL.match(url)
    if m:
        return {"kind": "github", "owner": m["owner"], "repo": m["repo"],
                "clean_url": f"https://github.com/{m['owner']}/{m['repo']}.git"}
    m = SHORTHAND.match(url)
    if m:
        return {"kind": "github", "owner": m["owner"], "repo": m["repo"],
                "clean_url": f"https://github.com/{m['owner']}/{m['repo']}.git"}
    raise ValueError(f"unrecognized repository reference: {url!r}")


# ----------------------------------------------------------------- git clone
def _run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def clone(clean_url, dest: Path, token=None, branch=None, kind="github"):
    """Clone `clean_url` into `dest`. For private GitHub repos an ephemeral
    Authorization header carries the token; it is never persisted to the
    remote (origin is reset to the clean URL after clone)."""
    dest = Path(dest)
    args = ["git", "clone", "--quiet"]
    if branch:
        args += ["--branch", branch]
    if token and kind == "github":
        # Basic auth header (x-access-token) applied only for this command.
        import base64
        cred = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        args += ["-c", f"http.extraHeader=Authorization: Basic {cred}"]
    args += [clean_url, str(dest)]
    r = _run(args)
    if r.returncode != 0:
        raise RuntimeError(f"git clone failed: {r.stderr.strip()}")
    # scrub any credential from the stored remote
    _run(["git", "-C", str(dest), "remote", "set-url", "origin", clean_url])
    return dest


# ------------------------------------------------------------- github metadata
def fetch_metadata(owner, repo, token=None, timeout=15):
    """GET /repos/{owner}/{repo}. Returns {} on any failure (offline, rate
    limit, private-without-token). The connector never depends on this."""
    if not owner:
        return {}
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "living-dna-connector"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.load(resp)
        owner_obj = d.get("owner") or {}
        return {
            "description": d.get("description"),
            "default_branch": d.get("default_branch"),
            "stars": d.get("stargazers_count"),
            "forks": d.get("forks_count"),
            "open_issues": d.get("open_issues_count"),
            "language": d.get("language"),
            "visibility": d.get("visibility") or ("private" if d.get("private") else "public"),
            "is_org": owner_obj.get("type") == "Organization",
            "owner_type": owner_obj.get("type"),
            "pushed_at": d.get("pushed_at"),
            "license": (d.get("license") or {}).get("spdx_id"),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError,
            TimeoutError, OSError):
        return {}


# ------------------------------------------------------------------- connect
def connect(g, url, workdir, token=None, branch=None, repo_name=None,
            max_commits=0):
    """Connect + clone/import + initial genome build + metadata store.

    workdir: directory under which the working clone is created.
    Returns a summary dict (also stored on the repo node).
    """
    t0 = time.time()
    info = parse_repo_url(url)
    name = repo_name or info["repo"]
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    clone_path = workdir / name

    if info["kind"] == "local" and Path(info["clean_url"]).exists() \
            and not clone_path.exists():
        # Import a local repo by cloning it (keeps origin for later sync).
        clone(info["clean_url"], clone_path, kind="local", branch=branch)
    elif not clone_path.exists():
        clone(info["clean_url"], clone_path, token=token, branch=branch,
              kind=info["kind"])
    # else: already cloned — reuse (idempotent connect).

    resolved_branch = branch or continuous.ingest._git(
        clone_path, "rev-parse", "--abbrev-ref", "HEAD").strip() or "main"
    meta = fetch_metadata(info["owner"], info["repo"], token=token) \
        if info["kind"] == "github" else {}

    clone_ms = round((time.time() - t0) * 1000)
    build = ingest_repo(g, clone_path, repo_name=name, max_commits=max_commits)
    n_profiles = ops.materialize_profiles(g)
    head = continuous.head_sha(clone_path)

    _store_repo_meta(g, name, {
        "provider": info["kind"],
        "remote_url": info["clean_url"],
        "owner": info["owner"],
        "is_org": bool(meta.get("is_org")),
        "branch": resolved_branch,
        "clone_path": str(clone_path),
        "head_sha": head,
        "private": meta.get("visibility") == "private",
        "connected_at": time.time(),
        "last_synced_at": time.time(),
        "github": meta,
    })
    g.commit()
    return {
        "repo": name, "provider": info["kind"], "branch": resolved_branch,
        "owner": info["owner"], "is_org": bool(meta.get("is_org")),
        "clone_ms": clone_ms,
        "build_ms": round((time.time() - t0) * 1000) - clone_ms,
        "commits": build["commits"], "people": build["people"],
        "services": list(build["services"]), "profiles": n_profiles,
        "head_sha": head, "github": meta,
    }


# ------------------------------------------------------------------- sync
def sync_repo(g, repo_name, token=None):
    """Fetch new commits and incrementally update the genome. Onboarding must
    have happened via connect() first."""
    meta = repo_meta(g, repo_name)
    if not meta:
        return {"error": f"repo '{repo_name}' not connected — run connect first"}
    clone_path = Path(meta["clone_path"])
    if not clone_path.exists():
        return {"error": f"clone path missing: {clone_path}"}
    branch = meta.get("branch") or "HEAD"
    since = meta.get("head_sha")

    # Pull new commits (fast-forward only; token re-applied for private repos).
    fetch_args = ["git", "-C", str(clone_path)]
    if token and meta.get("provider") == "github":
        import base64
        cred = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        fetch_args += ["-c", f"http.extraHeader=Authorization: Basic {cred}"]
    fetch = _run(fetch_args + ["fetch", "--quiet", "origin"])
    fetch_note = fetch.stderr.strip() if fetch.returncode != 0 else None
    if branch and branch != "HEAD":
        _run(["git", "-C", str(clone_path), "merge", "--ff-only",
              f"origin/{branch}"])

    services = census(g, clone_path, repo_name)  # re-census: new services appear
    result = continuous.sync(g, clone_path, services, repo_name, since, ref="HEAD")

    new_head = continuous.head_sha(clone_path)
    patch = dict(meta)
    patch["head_sha"] = new_head
    patch["last_synced_at"] = time.time()
    if meta.get("owner"):
        fresh = fetch_metadata(meta["owner"], repo_name.split("/")[-1], token=token)
        if fresh:
            patch["github"] = fresh
    _store_repo_meta(g, repo_name, patch)
    g.commit()
    result.update({"repo": repo_name, "head_sha": new_head,
                   "fetch_warning": fetch_note})
    return result


# ------------------------------------------------------------- metadata store
def _store_repo_meta(g, name, props):
    node = g.node(f"repo:{name}")
    merged = dict(node["props"]) if node else {}
    merged.update({k: v for k, v in props.items() if v is not None
                   or k in ("owner", "head_sha")})
    g.upsert_node(f"repo:{name}", "Repo", name, props=merged)


def repo_meta(g, repo_name):
    node = g.node(f"repo:{repo_name}")
    return node["props"] if node else None


def list_repos(g):
    out = []
    for n in g.nodes(kind="Repo"):
        p = n["props"]
        gh = p.get("github") or {}
        out.append({
            "repo": n["name"], "provider": p.get("provider", "local"),
            "branch": p.get("branch"), "owner": p.get("owner"),
            "is_org": p.get("is_org", False),
            "head_sha": (p.get("head_sha") or "")[:10],
            "connected_at": ops._date(p.get("connected_at")),
            "last_synced_at": ops._date(p.get("last_synced_at")),
            "stars": gh.get("stars"), "language": gh.get("language"),
            "visibility": gh.get("visibility"),
            "description": gh.get("description"),
        })
    return out
