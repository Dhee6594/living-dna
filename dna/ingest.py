"""Pass 1-3 of the sequencing pipeline, for local git repositories.

Pass 1 (Census):    enumerate services from directory layout + manifests.
Pass 2 (Structure): extract dependency edges from imports/manifests.
Pass 3 (History):   replay full git history into the canonical event log,
                    attribute changes to services, build KNOWS weights.

A "repo root" may contain several services (monorepo): any directory holding a
manifest (package.json, pyproject.toml, go.mod, requirements.txt, Cargo.toml)
or living under services/ apps/ packages/ is a service candidate.
"""
import json
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

MANIFESTS = ("package.json", "pyproject.toml", "go.mod", "requirements.txt",
             "Cargo.toml", "pom.xml", "plugin.json")  # incl. Claude plugins
SERVICE_PARENTS = ("services", "apps", "packages")
MANIFEST_DIR_ALIASES = {".claude-plugin": "parent"}  # manifest lives in a meta dir
# Directories to skip entirely during service discovery
SKIP_DIRS = frozenset({".git", "node_modules", "vendor", "dist", "build",
                       "tmp", ".tox", ".venv", "venv", "env", "__pycache__",
                       ".eggs", ".mypy_cache", ".pytest_cache"})

PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][\w.]*)", re.M)
JS_IMPORT = re.compile(r"""(?:from\s+|require\()\s*['"]([^'"]+)['"]""")

# Real-repo hardening -------------------------------------------------------
BOT_AUTHOR = re.compile(r"\[bot\]|dependabot|renovate|github-actions|snyk-bot|"
                        r"greenkeeper|pre-commit-ci|codecov|mend-bot|allcontributors|"
                        r"semantic-release|release-please|stale|mergify|sonarcloud", re.I)
NOISE_PATH = re.compile(r"(^|/)(vendor|node_modules|dist|build|\.yarn|third_party)/"
                        r"|\.(lock|min\.js|min\.css|map|svg|png|jpg|jpeg|ico|gif|pdf"
                        r"|whl|egg|pyc|pyo|class|jar|war|ear|zip|tar|gz|bz2|xz)$"
                        r"|package-lock\.json$|yarn\.lock$|pnpm-lock\.yaml$|go\.sum$"
                        r"|poetry\.lock$|Pipfile\.lock$|Gemfile\.lock$"
                        r"|\.egg-info/|\.DS_Store$")
RENAME = re.compile(r"^(?:(.*?)\{(.*?)\s*=>\s*(.*?)\}(.*)|(.*) => (.*))$")


def resolve_rename(path):
    """git numstat rename forms: 'a/{old => new}/b' or 'old => new' -> new path.

    Handles edge cases:
    - '{old => new}'   -> ('new', 'old')
    - '{=> new}'       -> ('new', '')    (added segment)
    - '{old =>}'       -> ('', 'old')   (deleted segment — treat new as '')
    - 'old => new'     -> ('new', 'old') (top-level rename)
    """
    m = RENAME.match(path)
    if not m:
        return path, None
    if m.group(2) is not None or m.group(3) is not None:
        pre  = (m.group(1) or "")
        old  = (m.group(2) or "").strip()
        new  = (m.group(3) or "").strip()
        post = (m.group(4) or "")
        new_path = (pre + new + post).replace("//", "/").strip("/") or None
        old_path = (pre + old + post).replace("//", "/").strip("/") or None
        return new_path or path, old_path
    return m.group(6).strip(), m.group(5).strip()


def _git(repo, *args):
    try:
        return subprocess.run(["git", "-C", str(repo)] + list(args),
                              capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError as exc:
        import sys
        print(f"[dna] git warning ({' '.join(args[:3])}): {exc.stderr.strip()}",
              file=sys.stderr)
        return ""  # return empty so callers degrade gracefully


# --------------------------------------------------------------- Pass 1: census
def discover_services(repo_root: Path):
    """Return {service_name: relative_dir} candidates."""
    repo_root = Path(repo_root)
    services = {}

    # Build set of sub-repo roots (dirs with their own .git); we skip these
    # so embedded fixture repos / cloned sub-projects don't pollute discovery.
    sub_repos = set()
    for git_dir in repo_root.rglob(".git"):
        if git_dir.parent != repo_root:
            sub_repos.add(git_dir.parent)

    def _in_sub_repo(p: Path) -> bool:
        for sr in sub_repos:
            try:
                p.relative_to(sr)
                return True
            except ValueError:
                pass
        return False

    for mf in MANIFESTS:
        for p in repo_root.rglob(mf):
            # Only check path components INSIDE the repo — checking the full
            # absolute path is wrong whenever the repo itself is checked out
            # under a directory that happens to be named e.g. "tmp" (common
            # in CI/sandboxes), which would wrongly skip every manifest.
            rel_parts = p.relative_to(repo_root).parts
            if any(part in SKIP_DIRS for part in rel_parts):
                continue
            if _in_sub_repo(p):
                continue
            parent = p.parent
            # manifests living in meta dirs (.claude-plugin/plugin.json) name
            # the directory ABOVE them
            if parent.name in MANIFEST_DIR_ALIASES:
                parent = parent.parent
            rel = parent.relative_to(repo_root)
            name = rel.name if str(rel) != "." else repo_root.name
            services[name] = str(rel)
    for parent in SERVICE_PARENTS:
        d = repo_root / parent
        if d.is_dir():
            for child in d.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    services.setdefault(child.name, str(child.relative_to(repo_root)))
    if not services:
        services[repo_root.name] = "."
    return services


def census(genome, repo_root: Path, repo_name: str):
    services = discover_services(repo_root)
    genome.upsert_node(f"repo:{repo_name}", "Repo", repo_name,
                       props={"path": str(repo_root)})
    for name, rel in services.items():
        langs = _langs(Path(repo_root) / rel)
        genome.upsert_node(f"svc:{name}", "Service", name,
                           props={"dir": rel, "repo": repo_name, "languages": langs},
                           provenance=[f"census:{repo_name}/{rel}"])
        genome.upsert_edge("PART_OF", f"svc:{name}", f"repo:{repo_name}")
    genome.commit()
    return services


def _langs(d: Path):
    counts = defaultdict(int)
    ext_lang = {".py": "python", ".js": "javascript", ".ts": "typescript",
                ".go": "go", ".rs": "rust", ".java": "java"}
    if d.is_dir():
        for p in d.rglob("*"):
            if p.suffix in ext_lang and ".git" not in p.parts:
                counts[ext_lang[p.suffix]] += 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1])[:3])


# ------------------------------------------------------------ Pass 2: structure
def structure(genome, repo_root: Path, services: dict, history_ts=None):
    """Dependency edges between services, from imports and manifests."""
    repo_root = Path(repo_root)
    names = set(services)
    for name, rel in services.items():
        base = repo_root / rel
        deps = set()
        evidence = defaultdict(list)
        for p in list(base.rglob("*.py"))[:400]:
            try:
                for m in PY_IMPORT.findall(p.read_text(errors="ignore")):
                    root = m.split(".")[0].replace("_", "-")
                    if root in names and root != name:
                        deps.add(root); evidence[root].append(str(p.relative_to(repo_root)))
            except OSError:
                pass
        for p in list(base.rglob("*.js")) + list(base.rglob("*.ts")):
            try:
                for m in JS_IMPORT.findall(p.read_text(errors="ignore")):
                    seg = m.strip("./").split("/")[0]
                    if seg in names and seg != name:
                        deps.add(seg); evidence[seg].append(str(p.relative_to(repo_root)))
            except OSError:
                pass
        pkg = base / "package.json"
        if pkg.exists():
            try:
                j = json.loads(pkg.read_text())
                for dep in list(j.get("dependencies", {})) + list(j.get("devDependencies", {})):
                    short = dep.split("/")[-1]
                    if short in names and short != name:
                        deps.add(short); evidence[short].append(str(pkg.relative_to(repo_root)))
            except (OSError, json.JSONDecodeError):
                pass
        # config-declared deps (our convention: dna-deps.txt — also used by fixture)
        cfg = base / "dna-deps.txt"
        if cfg.exists():
            for line in cfg.read_text().splitlines():
                line = line.strip()
                if line in names and line != name:
                    deps.add(line); evidence[line].append(str(cfg.relative_to(repo_root)))
        for d in deps:
            vf = (history_ts or {}).get((name, d))
            genome.upsert_edge("DEPENDS_ON", f"svc:{name}", f"svc:{d}",
                               props={"mechanism": "code"},
                               valid_from=vf,
                               provenance=evidence[d][:5])
    genome.commit()


# ------------------------------------------------------------- Pass 3: history
def history(genome, repo_root: Path, services: dict, repo_name: str,
            max_commits: int = 0):
    """Replay git history -> events, service attribution, KNOWS weights.

    max_commits: if > 0, only replay the N most-recent commits (useful for
    first-run on large repos like CPython/Linux kernel).
    """
    log_args = ["log", "--reverse", "--numstat", "-M",
                "--format=__C__%H|%at|%an|%ae|%s"]
    if max_commits > 0:
        # Take the N most-recent commits; --reverse shows oldest first in the
        # slice so history ordering is still chronological within the window.
        log_args = ["log", "--numstat", "-M",
                    f"-{max_commits}",
                    "--format=__C__%H|%at|%an|%ae|%s"]
    log = _git(repo_root, *log_args)
    if not log:
        return {"commits": 0, "people": 0, "services": [], "first_dep_ts": {},
                "activity": {}}
    commits, cur, renames = [], None, []
    for line in log.splitlines():
        if line.startswith("__C__"):
            parts = line[5:].split("|", 4)
            if len(parts) < 5:
                continue  # malformed line (shallow clone artifact)
            h, at, an, ae, msg = parts
            cur = {"hash": h, "at": float(at), "author": an, "email": ae,
                   "msg": msg, "files": [],
                   "bot": bool(BOT_AUTHOR.search(an) or BOT_AUTHOR.search(ae)),
                   "_seen_paths": set()}  # for merge-commit dedup
            commits.append(cur)
        elif line.strip() and cur is not None:
            parts = line.split("\t")
            if len(parts) == 3:
                add, dele, path = parts
                path, old = resolve_rename(path)
                if not path:  # rename to empty (deleted-segment edge case)
                    continue
                if old:
                    renames.append({"old": old, "new": path,
                                    "at": cur["at"], "hash": cur["hash"]})
                if NOISE_PATH.search(path):
                    continue  # vendored/lockfile noise never earns knowledge
                # Dedup: merge commits can list the same path multiple times
                if path in cur["_seen_paths"]:
                    continue
                cur["_seen_paths"].add(path)
                cur["files"].append((path,
                                     0 if add == "-" else int(add),
                                     0 if dele == "-" else int(dele)))

    # Identity resolution v0: collapse duplicate git identities before any
    # knowledge attribution (see dna/identity.py for rules).
    from .identity import resolve_identities
    aliases = resolve_identities(commits, repo_root)
    for c in commits:
        hit = aliases.get(c["email"].lower())
        if hit:
            c["email"], c["author"] = hit[0], hit[1]

    svc_dirs = sorted(services.items(), key=lambda kv: -len(kv[1]))

    def svc_of(path):
        for name, rel in svc_dirs:
            if rel == "." or path.startswith(rel.rstrip("/") + "/") or path == rel:
                return name
        return None

    knows = defaultdict(float)          # (person, service) -> raw weight
    co_change = defaultdict(int)        # (svc_a, svc_b) -> co-commit count
    co_first = {}                       # (svc_a, svc_b) -> first co-change ts
    first_seen = {}                     # service -> first commit ts
    first_dep_ts = {}                   # (svc, dep) heuristic from dna-deps.txt changes
    svc_activity = defaultdict(list)    # service -> [ts]
    people = {}
    now = time.time()
    HALF_LIFE = 365 * 24 * 3600         # 12 months

    for c in commits:
        pid = f"person:{c['email']}"
        people[pid] = c["author"]
        touched = set()
        churn = defaultdict(int)
        for path, add, dele in c["files"]:
            s = svc_of(path)
            if s:
                touched.add(s)
                churn[s] += add + dele
                if path.endswith("dna-deps.txt"):
                    base = Path(repo_root) / path
                    if base.exists():
                        for dep in base.read_text().splitlines():
                            dep = dep.strip()
                            if dep and dep in services:
                                first_dep_ts.setdefault((s, dep), c["at"])
        genome.record_event("code.commit", c["at"],
                            actors=[pid],
                            subjects=[f"svc:{s}" for s in touched],
                            payload={"hash": c["hash"], "msg": c["msg"],
                                     "churn": dict(churn)},
                            event_id=f"commit:{c['hash']}")
        decay = 0.5 ** ((now - c["at"]) / HALF_LIFE)
        for s in touched:
            first_seen.setdefault(s, c["at"])
            svc_activity[s].append(c["at"])
            if not c["bot"]:  # bots make changes; they never hold knowledge
                knows[(pid, s)] += decay * min(churn[s], 500) / 500.0
        # co-change coupling: structure signal that works even on content repos
        if not c["bot"] and 2 <= len(touched) <= 6:  # mega-commits aren't signal
            ordered = sorted(touched)
            for i, a in enumerate(ordered):
                for b in ordered[i + 1:]:
                    co_change[(a, b)] += 1
                    co_first.setdefault((a, b), c["at"])

    bot_emails = {c["email"] for c in commits if c["bot"]}
    for pid, name in people.items():
        email = pid.split(":", 1)[1]
        genome.upsert_node(pid, "Person", name,
                           props={"email": email, "bot": email in bot_emails})

    for r in renames:
        genome.record_event("code.rename", r["at"],
                            subjects=[r["old"], r["new"]],
                            payload=r, event_id=f"rename:{r['hash']}:{r['new']}")

    for (a, b), n in co_change.items():
        if n >= 2:  # coupled if they changed together more than once
            genome.upsert_edge("CO_CHANGES", f"svc:{a}", f"svc:{b}",
                               props={"count": n},
                               valid_from=co_first[(a, b)],
                               provenance=[f"co-change x{n} in git history"])

    # service birth facts
    for s, ts in first_seen.items():
        n = genome.node(f"svc:{s}")
        if n:
            props = dict(n["props"]); props["born"] = ts
            born_commit = next((c for c in commits
                                if any(svc_of(p) == s for p, _, _ in c["files"])), None)
            if born_commit:
                props["born_commit"] = born_commit["hash"]
                props["born_msg"] = born_commit["msg"]
            genome.upsert_node(f"svc:{s}", "Service", s, props=props,
                               valid_from=ts, provenance=[f"commit:{props.get('born_commit','')}"])

    # KNOWS edges, normalized per service
    by_svc = defaultdict(list)
    for (pid, s), w in knows.items():
        by_svc[s].append((pid, w))
    for s, lst in by_svc.items():
        total = sum(w for _, w in lst) or 1.0
        for pid, w in lst:
            weight = round(w / total, 4)
            if weight >= 0.01:
                genome.upsert_edge("KNOWS", pid, f"svc:{s}",
                                   props={"weight": weight},
                                   provenance=[f"git-history:{s}"])
    genome.commit()
    return {"commits": len(commits), "people": len(people),
            "services": list(first_seen), "first_dep_ts": first_dep_ts,
            "activity": {k: v for k, v in svc_activity.items()}}


# --------------------------------------------------------------- Pass 4: eras
def eras(genome, activity: dict, gap_days=21):
    """Segment each service's commit stream into eras on activity gaps."""
    out = {}
    for svc, stamps in activity.items():
        stamps = sorted(stamps)
        if not stamps:
            continue
        segs, start, prev = [], stamps[0], stamps[0]
        for t in stamps[1:]:
            if t - prev > gap_days * 86400:
                segs.append((start, prev)); start = t
            prev = t
        segs.append((start, prev))
        out[svc] = segs
        for i, (a, b) in enumerate(segs, 1):
            era_id = f"era:{svc}:{i}"
            genome.upsert_node(era_id, "Era", f"{svc} era {i}",
                               props={"start": a, "end": b, "index": i},
                               valid_from=a)
            genome.upsert_edge("HAS_ERA", f"svc:{svc}", era_id, valid_from=a)
    genome.commit()
    return out


def ingest_repo(genome, repo_root, repo_name=None, max_commits: int = 0):
    """Full pipeline passes 1-4 for one local git repo."""
    repo_root = Path(repo_root).resolve()
    repo_name = repo_name or repo_root.name
    services = census(genome, repo_root, repo_name)
    hist = history(genome, repo_root, services, repo_name,
                   max_commits=max_commits)
    structure(genome, repo_root, services, history_ts=hist["first_dep_ts"])
    era_map = eras(genome, hist["activity"])
    return {"repo": repo_name, "services": services,
            "commits": hist["commits"], "people": hist["people"],
            "eras": {k: len(v) for k, v in era_map.items()}}
