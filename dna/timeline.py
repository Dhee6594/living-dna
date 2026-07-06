"""Timeline engine: how the architecture evolved over time.

Everything here is reconstructed from bitemporal facts already in the genome —
no git, no LLM. Four views:

  * milestones      — discrete dated events: service births, dependency
                      added/removed, era starts, ownership shifts.
  * monthly_series  — rollups for charting: commits, active/cumulative
                      services, new dependencies, active contributors, and a
                      knowledge-concentration index (the risk trend).
  * ownership_shifts— per service, era-over-era change of dominant contributor.
  * dependency_evolution — full add/remove history of DEPENDS_ON edges.

The read path stays deterministic: rerun it and you get the same story.
"""
import datetime as dt
import time
from collections import defaultdict

from . import genome_ops as ops

DAY = 86400.0


def _month(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m")


# ------------------------------------------------- dependency edge history
def _dep_history(g):
    """All DEPENDS_ON edge versions (added + removed), straight from the store."""
    rows = g.conn.execute(
        "SELECT kind, src, dst, valid_from, valid_to, provenance "
        "FROM edges WHERE kind='DEPENDS_ON' ORDER BY valid_from").fetchall()
    out = []
    for r in rows:
        out.append({"src": r["src"].split(":", 1)[1], "dst": r["dst"].split(":", 1)[1],
                    "from": r["valid_from"], "to": r["valid_to"]})
    return out


# --------------------------------------------------- per-era dominant owner
def _era_windows(g):
    """svc -> [(start, end, index)] from Era nodes."""
    out = defaultdict(list)
    for e in g.edges_q(kind="HAS_ERA"):
        svc = e["src"].split(":", 1)[1]
        n = g.node(e["dst"])
        if n:
            p = n["props"]
            out[svc].append((p.get("start"), p.get("end"), p.get("index")))
    for svc in out:
        out[svc].sort(key=lambda t: t[2] or 0)
    return out


def _dominant_owner(g, sid, start, end):
    """Person with the most churn on `sid` within [start, end], from events."""
    tally = defaultdict(float)
    for ev in g.events_q(kind="code.commit", subject=sid, since=start, until=end):
        if not ev["actors"]:
            continue
        pid = ev["actors"][0]
        churn = (ev["payload"].get("churn") or {}).get(sid.split(":", 1)[1], 1)
        tally[pid] += churn or 1
    if not tally:
        return None, 0.0
    top = max(tally, key=tally.get)
    total = sum(tally.values()) or 1
    n = g.node(top)
    return (n["name"] if n else top), tally[top] / total


# ------------------------------------------------------------------- build
def timeline(g, repo=None):
    t0 = time.time()
    profiles = [p for p in g.profiles_all()
                if repo is None or p.get("repo") == repo]
    if not profiles:
        return {"error": "no profiles — run `dna ingest`/`connect` first"}

    milestones = []

    # 1) service births
    for p in profiles:
        if p.get("born"):
            milestones.append({
                "date": p["born"], "ts": _to_ts(p["born"]),
                "type": "service_created", "service": p["entity"],
                "detail": p.get("born_msg") or "",
                "evidence": f"commit:{(p.get('born_commit') or '')[:8]}"})

    # 2) dependency add / remove
    deps = _dep_history(g)
    for d in deps:
        milestones.append({
            "date": ops._date(d["from"]), "ts": d["from"],
            "type": "dependency_added", "service": d["src"],
            "detail": f"{d['src']} → {d['dst']}", "evidence": "DEPENDS_ON edge"})
        if d["to"]:
            milestones.append({
                "date": ops._date(d["to"]), "ts": d["to"],
                "type": "dependency_removed", "service": d["src"],
                "detail": f"{d['src']} ⊗ {d['dst']}", "evidence": "edge closed"})

    # 3) era starts + 4) ownership shifts
    eras = _era_windows(g)
    ownership_shifts = []
    for p in profiles:
        svc, sid = p["entity"], p["id"]
        prev_owner = None
        for (start, end, idx) in eras.get(svc, []):
            if start:
                milestones.append({
                    "date": ops._date(start), "ts": start, "type": "era_started",
                    "service": svc, "detail": f"era {idx}", "evidence": "activity segmentation"})
            owner, share = _dominant_owner(g, sid, start, (end or start) + DAY)
            if owner and prev_owner and owner != prev_owner:
                ownership_shifts.append({
                    "date": ops._date(start), "ts": start, "service": svc,
                    "from": prev_owner, "to": owner, "share": round(share, 2),
                    "era": idx})
                milestones.append({
                    "date": ops._date(start), "ts": start, "type": "ownership_shift",
                    "service": svc,
                    "detail": f"lead {prev_owner} → {owner} ({int(share*100)}%)",
                    "evidence": "dominant-churn per era"})
            if owner:
                prev_owner = owner

    milestones.sort(key=lambda m: (m["ts"] or 0))

    # 5) monthly rollups (the risk trend series)
    series = _monthly(g, profiles, deps)

    return {
        "generated_in_ms": round((time.time() - t0) * 1000),
        "span": {"from": milestones[0]["date"] if milestones else None,
                 "to": milestones[-1]["date"] if milestones else None},
        "milestones": [{k: v for k, v in m.items() if k != "ts"} for m in milestones],
        "ownership_shifts": ownership_shifts,
        "dependency_evolution": [
            {"edge": f"{d['src']} → {d['dst']}", "added": ops._date(d["from"]),
             "removed": ops._date(d["to"]) if d["to"] else None} for d in deps],
        "monthly_series": series,
    }


def _to_ts(date_str):
    try:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").replace(
            tzinfo=dt.timezone.utc).timestamp()
    except (ValueError, TypeError):
        return 0


def _monthly(g, profiles, deps):
    born_ts = sorted(_to_ts(p["born"]) for p in profiles if p.get("born"))
    commits = g.events_q(kind="code.commit")
    if not commits:
        return []
    by_month_commits = defaultdict(int)
    by_month_services = defaultdict(set)
    by_month_authors = defaultdict(set)
    by_month_concentrated = defaultdict(lambda: [0, 0])   # [concentrated, active]
    svc_month_churn = defaultdict(lambda: defaultdict(float))  # (svc,month)->pid->churn

    for ev in commits:
        m = _month(ev["occurred_at"])
        by_month_commits[m] += 1
        if ev["actors"]:
            by_month_authors[m].add(ev["actors"][0])
        churn = ev["payload"].get("churn") or {}
        for s in ev["subjects"]:
            if s.startswith("svc:"):
                by_month_services[m].add(s)
                nm = s.split(":", 1)[1]
                if ev["actors"]:
                    svc_month_churn[(s, m)][ev["actors"][0]] += churn.get(nm, 1) or 1

    # knowledge concentration per month: share of active services whose top
    # contributor did >= 70% of that month's churn on the service.
    for (_s, m), tally in svc_month_churn.items():
        by_month_concentrated[m][1] += 1
        if tally and max(tally.values()) / (sum(tally.values()) or 1) >= 0.7:
            by_month_concentrated[m][0] += 1

    new_deps_by_month = defaultdict(int)
    for d in deps:
        if d["from"]:
            new_deps_by_month[_month(d["from"])] += 1

    months = sorted(by_month_commits)
    out = []
    for m in months:
        m_end = dt.datetime.strptime(m, "%Y-%m").replace(
            tzinfo=dt.timezone.utc).timestamp() + 32 * DAY
        cum = sum(1 for b in born_ts if b <= m_end)
        conc, active = by_month_concentrated[m]
        out.append({
            "month": m,
            "commits": by_month_commits[m],
            "active_services": len(by_month_services[m]),
            "cumulative_services": cum,
            "active_contributors": len(by_month_authors[m]),
            "new_dependencies": new_deps_by_month.get(m, 0),
            "concentration_index": round(conc / active, 2) if active else 0.0,
        })
    return out
