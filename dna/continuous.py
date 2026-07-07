"""Continuous intelligence: incremental ingestion + refresh.

The full pipeline (dna/ingest.py) replays a repository's entire git history on
every run. That is correct but O(all commits). This module makes updates
O(new commits):

  1. detect new commits since the last sync (git rev-range),
  2. replay ONLY those into the append-only event log (idempotent),
  3. rebuild the derived aggregates (KNOWS, CO_CHANGES, service birth) from the
     FULL event log — not from git — which is fast and, crucially, produces the
     same numbers a full re-ingest would (the event log is the source of truth).

Design invariants preserved from the blueprint:
  * Append-only bitemporality — we close stale edges, never delete facts.
  * Provenance on everything — every rebuilt edge keeps its git evidence.
  * The read path never runs an LLM.

`rebuild_knowledge` mirrors the aggregate math in ingest.history() exactly; the
test suite asserts an incremental sync and a from-scratch ingest converge to the
same KNOWS weights (see tests/test_phase4.py::test_incremental_matches_full).
"""
import time
from collections import defaultdict

from . import ingest
from . import genome_ops as ops

HALF_LIFE = 365 * 24 * 3600          # 12-month knowledge half-life (== ingest)
KNOWS_MIN = 0.01                     # drop KNOWS edges below this normalized weight
CO_CHANGE_MIN = 2                    # coupling needs >1 co-change


# --------------------------------------------------------------- git helpers
def head_sha(repo_root, ref="HEAD"):
    return ingest._git(repo_root, "rev-parse", ref).strip() or None


def new_commit_count(repo_root, since_sha, ref="HEAD"):
    if not since_sha:
        return None  # unknown -> caller decides (usually: full ingest)
    out = ingest._git(repo_root, "rev-list", "--count", f"{since_sha}..{ref}")
    try:
        return int(out.strip())
    except ValueError:
        return None


# ------------------------------------------------- rebuild aggregates from log
def _commits_from_events(g):
    """Reconstruct normalized commits from the code.commit event log.

    Returns list of {at, pid, hash, msg, touched:set, churn:dict, bot:bool},
    chronologically ordered (events_q already sorts by occurred_at).
    """
    bot_pids = {p["id"] for p in g.nodes(kind="Person") if p["props"].get("bot")}
    out = []
    for ev in g.events_q(kind="code.commit"):
        if not ev["actors"]:
            continue
        pid = ev["actors"][0]
        touched = {s.split(":", 1)[1] for s in ev["subjects"] if s.startswith("svc:")}
        churn = ev["payload"].get("churn", {}) or {}
        out.append({
            "at": ev["occurred_at"], "pid": pid,
            "hash": ev["payload"].get("hash"), "msg": ev["payload"].get("msg", ""),
            "touched": touched, "churn": churn, "bot": pid in bot_pids,
        })
    return out


def rebuild_knowledge(g, services, repo_root=None, now=None):
    """Recompute KNOWS / CO_CHANGES / service-birth from the full event log and
    reconcile the graph (close edges that no longer hold). Returns the per-service
    activity map (for era recomputation)."""
    now = now if now is not None else time.time()
    commits = _commits_from_events(g)

    knows = defaultdict(float)          # (pid, svc) -> raw decayed weight
    co_change = defaultdict(int)        # (a, b) -> count
    co_first = {}                       # (a, b) -> first ts
    first_seen = {}                     # svc -> first ts
    born_commit = {}                    # svc -> (hash, msg)
    activity = defaultdict(list)        # svc -> [ts]

    for c in commits:
        touched, churn = c["touched"], c["churn"]
        decay = 0.5 ** ((now - c["at"]) / HALF_LIFE)
        for s in touched:
            if s not in first_seen:
                first_seen[s] = c["at"]
                born_commit[s] = (c["hash"], c["msg"])
            activity[s].append(c["at"])
            if not c["bot"]:
                knows[(c["pid"], s)] += decay * min(churn.get(s, 0), 500) / 500.0
        if not c["bot"] and 2 <= len(touched) <= 6:
            ordered = sorted(touched)
            for i, a in enumerate(ordered):
                for b in ordered[i + 1:]:
                    co_change[(a, b)] += 1
                    co_first.setdefault((a, b), c["at"])

    # --- service birth facts -------------------------------------------------
    for s, ts in first_seen.items():
        n = g.node(f"svc:{s}")
        if not n:
            continue
        props = dict(n["props"])
        h, msg = born_commit[s]
        if (props.get("born") != ts or props.get("born_commit") != h):
            props["born"] = ts
            props["born_commit"] = h
            props["born_msg"] = msg
            g.upsert_node(f"svc:{s}", "Service", s, props=props, valid_from=ts,
                          provenance=[f"commit:{h}"])

    # --- CO_CHANGES edges (reconcile) ---------------------------------------
    want_co = set()
    for (a, b), n in co_change.items():
        if n >= CO_CHANGE_MIN:
            eid = f"CO_CHANGES:svc:{a}->svc:{b}"
            want_co.add(eid)
            g.upsert_edge("CO_CHANGES", f"svc:{a}", f"svc:{b}",
                          props={"count": n}, valid_from=co_first[(a, b)],
                          provenance=[f"co-change x{n} in git history"],
                          edge_id=eid)
    for e in g.edges_q(kind="CO_CHANGES"):
        if e["id"] not in want_co:
            g.close_edge(e["id"])

    # --- KNOWS edges, normalized per service (reconcile) --------------------
    by_svc = defaultdict(list)
    for (pid, s), w in knows.items():
        by_svc[s].append((pid, w))
    want_knows = set()
    for s, lst in by_svc.items():
        total = sum(w for _, w in lst) or 1.0
        for pid, w in lst:
            weight = round(w / total, 4)
            if weight >= KNOWS_MIN:
                eid = f"KNOWS:{pid}->svc:{s}"
                want_knows.add(eid)
                g.upsert_edge("KNOWS", pid, f"svc:{s}", props={"weight": weight},
                              provenance=[f"git-history:{s}"], edge_id=eid)
    for e in g.edges_q(kind="KNOWS"):
        if e["id"] not in want_knows:
            g.close_edge(e["id"])

    g.commit()
    return {k: v for k, v in activity.items()}


# ------------------------------------------------------------------- refresh
def refresh(g, repo_root, services, repo_name):
    """Re-derive everything downstream of the event log + working tree:
    dependency structure, eras, materialized profiles. (Insights are computed
    on demand and read these.)"""
    activity = rebuild_knowledge(g, services, repo_root)
    ingest.structure(g, repo_root, services)
    ingest.eras(g, activity)
    ops.materialize_profiles(g)
    g.commit()
    return activity


# ------------------------------------------------------------------- sync
def sync(g, repo_root, services, repo_name, since_sha, ref="HEAD"):
    """Incrementally update the genome for a repo already ingested once.

    Returns {new_commits, from_sha, to_sha, refreshed, elapsed_ms}.
    Falls back to a full replay only if `since_sha` is unknown/unreachable.
    """
    t0 = time.time()
    to_sha = head_sha(repo_root, ref)
    if since_sha and to_sha and since_sha == to_sha:
        return {"new_commits": 0, "from_sha": since_sha, "to_sha": to_sha,
                "refreshed": False, "elapsed_ms": round((time.time() - t0) * 1000),
                "note": "already up to date"}

    n_new = new_commit_count(repo_root, since_sha, ref)
    if since_sha and n_new is not None:
        # Incremental: replay only the new range into the event log.
        ingest.history(g, repo_root, services, repo_name,
                       rev_range=f"{since_sha}..{to_sha}")
    else:
        # No usable cursor (first sync after older DB, or rewritten history):
        # replay full history — still idempotent, just slower.
        ingest.history(g, repo_root, services, repo_name)
        n_new = None

    refresh(g, repo_root, services, repo_name)
    return {"new_commits": n_new, "from_sha": since_sha, "to_sha": to_sha,
            "refreshed": True, "elapsed_ms": round((time.time() - t0) * 1000)}
