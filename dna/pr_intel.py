"""Pull-Request intelligence.

Given the files a PR touches, predict — from the genome, before the code is
merged — the things a human reviewer usually discovers too late:

  * affected services         (which genes this PR mutates)
  * knowledge owners          (who should review, by derived KNOWS weight)
  * architectural risk        (fan-in blast radius, cycles, churn)
  * hidden dependency impact  (services that historically change together with
                               the touched ones but aren't in this PR)
  * documentation impact      (undocumented or high-dependent services changed
                               without a docs/README touch)

Pure graph reads — deterministic, no LLM, evidence attached to every claim.
Input is a list of changed file paths; helpers derive that from a local diff or
(when reachable) the GitHub PR files API.
"""
import subprocess
import time
from collections import defaultdict

from . import insights as ins
from .ingest import svc_of_fn

DAY = 86400.0
DOC_HINT = ("readme", "docs/", "doc/", ".md", ".rst", "changelog")


# --------------------------------------------------------------- file sources
def diff_files(repo_path, base, head="HEAD"):
    """Changed file paths between two revisions of a local clone."""
    r = subprocess.run(["git", "-C", str(repo_path), "diff", "--name-only",
                        f"{base}..{head}"], capture_output=True, text=True)
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def pr_files_via_api(owner, repo, number, token=None, timeout=15):
    """Changed paths for a GitHub PR. Returns [] if unreachable."""
    import json
    import urllib.error
    import urllib.request
    files, page = [], 1
    while True:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files"
            f"?per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "living-dna-connector"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                batch = json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError,
                TimeoutError, OSError):
            break
        if not batch:
            break
        files += [f["filename"] for f in batch]
        if len(batch) < 100:
            break
        page += 1
    return files


# ----------------------------------------------------------------- internals
def _services_map(g, repo=None):
    return {n["name"]: n["props"].get("dir", ".")
            for n in g.nodes(kind="Service")
            if repo is None or n["props"].get("repo") == repo}


def _recent_commits(g, sid, days=90):
    now = time.time()
    return sum(1 for ev in g.events_q(kind="code.commit", subject=sid)
               if now - ev["occurred_at"] < days * DAY)


# ------------------------------------------------------------------- analyze
def analyze(g, files, repo=None):
    """Core PR predictor. `files`: list of changed paths."""
    t0 = time.time()
    services = _services_map(g, repo)
    svc_of = svc_of_fn(services)

    touched = defaultdict(list)          # svc -> [files]
    for f in files:
        s = svc_of(f)
        if s:
            touched[f"svc:{s}"].append(f)
    touched_ids = set(touched)
    doc_touch = any(any(h in f.lower() for h in DOC_HINT) for f in files)

    # dependency + co-change adjacency (once)
    dependents = defaultdict(set)
    depends_on = defaultdict(set)
    for e in g.edges_q(kind="DEPENDS_ON"):
        dependents[e["dst"]].add(e["src"])
        depends_on[e["src"]].add(e["dst"])
    co_adj = defaultdict(dict)
    for e in g.edges_q(kind="CO_CHANGES"):
        co_adj[e["src"]][e["dst"]] = e["props"].get("count", 0)
        co_adj[e["dst"]][e["src"]] = e["props"].get("count", 0)

    affected, owners_agg = [], defaultdict(float)
    hidden_hits, doc_flags = [], []
    for sid, fs in sorted(touched.items()):
        prof = g.profile(sid) or {}
        name = sid.split(":", 1)[1]
        fan_in = sorted(x.split(":", 1)[1] for x in dependents.get(sid, ()))
        churn90 = _recent_commits(g, sid)
        top = (prof.get("knowledge") or {}).get("top", [])
        for o in top:
            owners_agg[(o["person"], o["person_id"])] += o["weight"]
        affected.append({
            "service": name, "files_changed": len(fs),
            "dependents": fan_in, "fan_in": len(fan_in),
            "depends_on": sorted(x.split(":", 1)[1] for x in depends_on.get(sid, ())),
            "commits_90d": churn90,
            "effective_owners": (prof.get("knowledge") or {}).get("effective_owners"),
            "top_owners": [{"person": o["person"], "weight": o["weight"]}
                           for o in top[:3]],
            "existing_risks": [r["class"] for r in prof.get("risks", [])],
        })
        # hidden coupling: strong co-change partners NOT in this PR
        for other, cnt in co_adj.get(sid, {}).items():
            if other not in touched_ids and cnt >= 3 and \
                    other not in {h["with"] for h in hidden_hits if h["from"] == name}:
                hidden_hits.append({
                    "from": name, "with": other.split(":", 1)[1], "co_changes": cnt,
                    "note": "changes with the touched service but is absent from "
                            "this PR — likely needs a coordinated change or a test"})
        # documentation impact
        if not doc_touch and (len(fan_in) >= 1 or churn90 >= 5):
            doc_flags.append({
                "service": name,
                "reason": f"{len(fan_in)} dependents / {churn90} recent changes and "
                          "no docs touched in this PR"})

    # suggested reviewers = highest aggregated KNOWS across touched services
    reviewers = sorted(({"person": p, "person_id": pid, "knowledge_score": round(w, 3)}
                        for (p, pid), w in owners_agg.items()),
                       key=lambda r: -r["knowledge_score"])[:5]

    # cycles this PR participates in
    adj = ins._dep_adjacency(g)
    cycles = [c for c in ins.find_cycles(adj)
              if any(f"svc:{n}" in touched_ids for n in c)]

    risk = _risk_level(affected, hidden_hits, cycles)
    return {
        "generated_in_ms": round((time.time() - t0) * 1000),
        "files_analyzed": len(files),
        "affected_services": affected,
        "unmapped_files": [f for f in files if not svc_of(f)][:20],
        "predicted_reviewers": reviewers,
        "architectural_risk": risk,
        "hidden_dependency_impact": sorted(hidden_hits,
                                           key=lambda h: -h["co_changes"]),
        "cycles_touched": cycles,
        "documentation_impact": doc_flags,
    }


def _risk_level(affected, hidden, cycles):
    """Transparent 0-100 risk score + band. Formula documented inline."""
    if not affected:
        return {"score": 0, "band": "none",
                "note": "no known services touched (new or unmapped paths)"}
    max_fan_in = max((a["fan_in"] for a in affected), default=0)
    total_churn = sum(a["commits_90d"] for a in affected)
    spof = sum(1 for a in affected
               if "knowledge_concentration" in a["existing_risks"])
    # 35·fan-in + 25·cycles + 20·hidden coupling + 20·concentrated ownership
    score = min(100, round(
        35 * min(1.0, max_fan_in / 4)
        + 25 * min(1.0, len(cycles))
        + 20 * min(1.0, len(hidden) / 3)
        + 20 * min(1.0, spof / max(1, len(affected)))))
    band = "high" if score >= 60 else "medium" if score >= 30 else "low"
    return {
        "score": score, "band": band, "max_fan_in": max_fan_in,
        "total_recent_churn": total_churn, "cycles_touched": len(cycles),
        "hidden_couplings": len(hidden),
        "formula": "35·fan_in/4 + 25·in_cycle + 20·hidden/3 + 20·spof_share",
    }
