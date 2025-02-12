"""Genome operations: DNA profiles, bus factor, time travel, archaeology answers."""
import datetime as dt
import re
import time
from collections import defaultdict

EXPORT_SCHEMA_VERSION = "1.0"


def export_genome(g) -> dict:
    """Full JSON dump of all current nodes, edges, and events.

    Fulfils the open-schema promise (§2.4 law 7).  The output is:
    - Deterministic: sorted by id so diffs are readable.
    - Bitemporal: every row keeps valid_from/valid_to/recorded_at/provenance.
    - Complete: includes historical (closed) rows, not just current ones.
    """
    def _node(r):
        return {
            "id": r["id"], "kind": r["kind"], "name": r["name"],
            "props": r["props"],
            "valid_from": r["valid_from"], "valid_to": r["valid_to"],
            "recorded_at": r["recorded_at"], "confidence": r["confidence"],
            "provenance": r["provenance"],
        }

    def _edge(r):
        return {
            "id": r["id"], "kind": r["kind"],
            "src": r["src"], "dst": r["dst"],
            "props": r["props"],
            "valid_from": r["valid_from"], "valid_to": r["valid_to"],
            "recorded_at": r["recorded_at"], "confidence": r["confidence"],
            "provenance": r["provenance"],
        }

    def _event(r):
        return {
            "event_id": r["event_id"], "kind": r["kind"],
            "occurred_at": r["occurred_at"], "ingested_at": r["ingested_at"],
            "actors": r["actors"], "subjects": r["subjects"],
            "payload": r["payload"],
        }

    # Pull all rows (including historical closed ones) via direct queries
    import json as _json
    conn = g.conn

    raw_nodes = [dict(r) for r in conn.execute(
        "SELECT * FROM nodes ORDER BY id, valid_from")]
    raw_edges = [dict(r) for r in conn.execute(
        "SELECT * FROM edges ORDER BY id, valid_from")]
    raw_events = [dict(r) for r in conn.execute(
        "SELECT * FROM events ORDER BY occurred_at")]

    for r in raw_nodes:
        r["props"] = _json.loads(r["props"])
        r["provenance"] = _json.loads(r["provenance"])
    for r in raw_edges:
        r["props"] = _json.loads(r["props"])
        r["provenance"] = _json.loads(r["provenance"])
    for r in raw_events:
        for k in ("actors", "subjects", "payload"):
            r[k] = _json.loads(r[k])

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": dt.datetime.utcnow().isoformat() + "Z",
        "stats": {
            "nodes": len(raw_nodes),
            "edges": len(raw_edges),
            "events": len(raw_events),
        },
        "nodes": [_node(r) for r in raw_nodes],
        "edges": [_edge(r) for r in raw_edges],
        "events": [_event(r) for r in raw_events],
    }




def _date(ts):
    return dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if ts else None


# ------------------------------------------------------------------ profiles
def materialize_profiles(g):
    """Build/refresh a DNA profile per service from the graph + event log."""
    services = g.nodes(kind="Service")
    for svc in services:
        sid = svc["id"]
        deps = [{"on": e["dst"].split(":", 1)[1],
                 "mechanism": e["props"].get("mechanism"),
                 "since": _date(e["valid_from"]),
                 "evidence": e["provenance"]}
                for e in g.edges_q(kind="DEPENDS_ON", src=sid)]
        dependents = [e["src"].split(":", 1)[1]
                      for e in g.edges_q(kind="DEPENDS_ON", dst=sid)]
        coupled = sorted(
            ([(e["dst"] if e["src"] == sid else e["src"]).split(":", 1)[1],
              e["props"].get("count", 0)]
             for e in g.edges_q(kind="CO_CHANGES", src=sid)
             + g.edges_q(kind="CO_CHANGES", dst=sid)),
            key=lambda t: -t[1])[:5]
        owners = sorted(
            ({"person": g.node(e["src"])["name"] if g.node(e["src"]) else e["src"],
              "person_id": e["src"],
              "weight": e["props"].get("weight", 0)}
             for e in g.edges_q(kind="KNOWS", dst=sid)),
            key=lambda o: -o["weight"])
        eff = effective_owners([o["weight"] for o in owners])
        eras = sorted(
            ({"label": n["name"], "start": _date(n["props"].get("start")),
              "end": _date(n["props"].get("end")), "index": n["props"].get("index")}
             for n in (g.node(e["dst"]) for e in g.edges_q(kind="HAS_ERA", src=sid))
             if n),
            key=lambda e: e["index"] or 0)
        commits = g.events_q(kind="code.commit", subject=sid)
        risks = []
        if eff < 1.6 and owners:
            risks.append({
                "class": "knowledge_concentration",
                "score": round(min(1.0, owners[0]["weight"] + (1.6 - eff) / 1.6), 2),
                "note": f"effective owners {eff} — top contributor holds "
                        f"{int(owners[0]['weight']*100)}% of derived knowledge",
                "evidence": [f"KNOWS edges for {sid}"]})
        if len(dependents) >= 2 and len(commits) >= 10:
            risks.append({
                "class": "bottleneck",
                "score": round(min(1.0, 0.3 + 0.15 * len(dependents)), 2),
                "note": f"{len(dependents)} services depend on this; "
                        f"{len(commits)} lifetime changes",
                "evidence": [f"DEPENDS_ON -> {sid}"]})
        profile = {
            "entity": svc["name"], "id": sid, "kind": "Service",
            "repo": svc["props"].get("repo"), "dir": svc["props"].get("dir"),
            "languages": svc["props"].get("languages", {}),
            "born": _date(svc["props"].get("born")),
            "born_commit": svc["props"].get("born_commit"),
            "born_msg": svc["props"].get("born_msg"),
            "eras": eras,
            "dependencies": deps,
            "dependents": dependents,
            "co_changes_with": [{"service": s, "times": n} for s, n in coupled],
            "knowledge": {"effective_owners": eff, "top": owners[:5]},
            "risks": risks,
            "stats": {"lifetime_commits": len(commits)},
        }
        g.save_profile(sid, profile)
    g.commit()
    return len(services)


def effective_owners(weights):
    """exp(entropy) of the contribution distribution — 'how many people really know this'."""
    import math
    ws = [w for w in weights if w > 0]
    total = sum(ws)
    if not ws or total == 0:
        return 0.0
    ent = -sum((w / total) * math.log(w / total) for w in ws)
    return round(math.exp(ent), 2)


# ----------------------------------------------------------------- bus factor
def bus_factor(g, person_id, threshold=0.5):
    """Simulate a departure: which services lose too much knowledge."""
    person = g.node(person_id)
    impacted = []
    for e in g.edges_q(kind="KNOWS", src=person_id):
        sid = e["dst"]
        all_edges = g.edges_q(kind="KNOWS", dst=sid)
        leaving = e["props"].get("weight", 0)
        remaining = [x["props"].get("weight", 0) for x in all_edges
                     if x["src"] != person_id]
        rem_total = sum(remaining)
        rem_eff = effective_owners(remaining)
        if leaving >= 0.15:
            successors = sorted(
                ((g.node(x["src"])["name"], x["props"].get("weight", 0))
                 for x in all_edges if x["src"] != person_id and g.node(x["src"])),
                key=lambda t: -t[1])
            impacted.append({
                "service": sid.split(":", 1)[1],
                "knowledge_lost": round(leaving, 3),
                "knowledge_remaining": round(rem_total, 3),
                "effective_owners_after": rem_eff,
                "critical": rem_total < threshold,
                "recovery_estimate_weeks": max(2, int(leaving * 26)),
                "succession": [{"pair_with": n, "current_weight": round(w, 3)}
                               for n, w in successors[:2]],
            })
    impacted.sort(key=lambda x: -x["knowledge_lost"])
    return {"person": person["name"] if person else person_id,
            "person_id": person_id,
            "services_impacted": len(impacted),
            "critical": [i for i in impacted if i["critical"]],
            "details": impacted}


def org_bus_factor(g):
    """Org-wide heatmap: every person x their departure blast."""
    out = []
    for p in g.nodes(kind="Person"):
        sim = bus_factor(g, p["id"])
        out.append({"person": p["name"], "person_id": p["id"],
                    "critical_services": len(sim["critical"]),
                    "services_impacted": sim["services_impacted"]})
    out.sort(key=lambda x: (-x["critical_services"], -x["services_impacted"]))
    return out


# ---------------------------------------------------------------- time travel
def graph_at(g, at=None):
    """Dependency graph (+ service set) at timestamp `at` (None = now)."""
    nodes = [{"id": n["id"], "name": n["name"], "kind": n["kind"],
              "born": _date(n["props"].get("born"))}
             for n in g.nodes(kind="Service", at=at)]
    ids = {n["id"] for n in nodes}
    edges = [{"src": e["src"], "dst": e["dst"], "since": _date(e["valid_from"])}
             for e in g.edges_q(kind="DEPENDS_ON", at=at)
             if e["src"] in ids and e["dst"] in ids]
    return {"at": _date(at) if at else "now", "services": nodes, "dependencies": edges}


def diff(g, t1, t2):
    g1, g2 = graph_at(g, t1), graph_at(g, t2)
    s1 = {n["id"] for n in g1["services"]}; s2 = {n["id"] for n in g2["services"]}
    e1 = {(e["src"], e["dst"]) for e in g1["dependencies"]}
    e2 = {(e["src"], e["dst"]) for e in g2["dependencies"]}
    def cause(svc_id, after_ts, before_ts):
        evs = g.events_q(kind="code.commit", subject=svc_id,
                         since=min(after_ts, before_ts), until=max(after_ts, before_ts))
        return evs[0]["payload"].get("msg") if evs else None
    return {
        "from": g1["at"], "to": g2["at"],
        "services_added": [{"id": s, "cause": cause(s, t1, t2)} for s in s2 - s1],
        "services_removed": sorted(s1 - s2),
        "dependencies_added": sorted([f"{a}->{b}" for a, b in e2 - e1]),
        "dependencies_removed": sorted([f"{a}->{b}" for a, b in e1 - e2]),
    }


# ------------------------------------------------------------- quality report
def quality_report(g):
    """Genome quality report — the validation artifact for real-repo runs.
    Surfaces what to inspect and what probably went wrong."""
    profiles = g.profiles_all()
    people = g.nodes(kind="Person")
    bots = [p for p in people if p["props"].get("bot")]
    commits = g.events_q(kind="code.commit")
    renames = g.events_q(kind="code.rename")
    dep_edges = g.edges_q(kind="DEPENDS_ON")
    co_edges = g.edges_q(kind="CO_CHANGES")
    flags = []
    by_repo = {}
    for p in profiles:
        by_repo.setdefault(p.get("repo") or "?", []).append(p["entity"])
        is_content = not p.get("languages")  # no code files: docs/config/plugin dir
        if (not p["dependencies"] and not p["dependents"]
                and not p.get("co_changes_with") and not is_content):
            flags.append(f"ISOLATED: {p['entity']} has no dependency or co-change "
                         "edges — import detection may have missed its language/layout")
        if p["stats"]["lifetime_commits"] < 3:
            flags.append(f"THIN: {p['entity']} has <3 commits — "
                         "possibly a misdetected service (stray manifest?)")
        if p["knowledge"]["effective_owners"] == 0:
            flags.append(f"NO-OWNER: {p['entity']} has no knowledge edges")
    if len(by_repo) > 1:
        flags.append("MULTI-REPO DB: this genome contains several repos "
                     "(see by_repo). Intentional for org genomes; use --db "
                     "for separate ones.")
    if len(profiles) == 1:
        flags.append("SINGLE-SERVICE: whole repo collapsed to one service — "
                     "fine for libraries; for monorepos check SERVICE_PARENTS dirs")
    return {
        "services": len(profiles),
        "by_repo": {k: sorted(v) for k, v in sorted(by_repo.items())},
        "content_only_services": sum(1 for p in profiles if not p.get("languages")),
        "co_change_edges": len(co_edges),
        "people": {"humans": len(people) - len(bots), "bots_filtered": len(bots)},
        "commits": len(commits),
        "renames_tracked": len(renames),
        "dependency_edges": len(dep_edges),
        "explained_edges": sum(1 for e in dep_edges if e["provenance"]),
        "risks_derived": sum(len(p["risks"]) for p in profiles),
        "coverage": {
            "services_with_born": sum(1 for p in profiles if p["born"]),
            "services_with_eras": sum(1 for p in profiles if p["eras"]),
            "services_with_owners": sum(1 for p in profiles
                                        if p["knowledge"]["top"]),
        },
        "inspect": flags or ["no anomalies flagged — spot-check 3 profiles by hand"],
    }


# ---------------------------------------------------------------- archaeology
def ask(g, question: str):
    """Graph-first archaeology. Pattern-matches common question shapes and
    answers from the genome with evidence. (LLM synthesis plugs in via ai.py.)"""
    q = question.lower()

    m = re.search(r"who knows (?:about )?([\w-]+)", q)
    if m:
        sid = f"svc:{m.group(1)}"
        prof = g.profile(sid)
        if not prof:
            return {"answer": f"No service '{m.group(1)}' in the genome.", "evidence": []}
        top = prof["knowledge"]["top"]
        return {"answer": f"{prof['entity']}: " + ", ".join(
                    f"{o['person']} ({int(o['weight']*100)}%)" for o in top[:3])
                    + f". Effective owners: {prof['knowledge']['effective_owners']}.",
                "evidence": [f"KNOWS edges derived from git history for {sid}"]}

    m = re.search(r"why (?:does|is) ([\w-]+).{0,30}?(?:depend(?:s)? on|call|use[s]?) ([\w-]+)", q)
    if m:
        a, b = m.group(1), m.group(2)
        edges = g.edges_q(kind="DEPENDS_ON", src=f"svc:{a}", dst=f"svc:{b}")
        if not edges:
            return {"answer": f"No dependency {a} -> {b} found in the genome.",
                    "evidence": []}
        e = edges[0]
        since = _date(e["valid_from"])
        evs = g.events_q(kind="code.commit", subject=f"svc:{a}",
                         since=e["valid_from"] - 7 * 86400,
                         until=e["valid_from"] + 7 * 86400)
        commit_ctx = [f"{ev['payload']['hash'][:8]} — {ev['payload']['msg']}"
                      for ev in evs[:4]]
        return {"answer": f"{a} has depended on {b} since {since} "
                          f"(mechanism: {e['props'].get('mechanism')}). "
                          f"Commits around the edge's creation suggest the context below.",
                "evidence": e["provenance"] + commit_ctx,
                "hint": "Connect an LLM key (dna ask --deep) for narrative synthesis."}

    m = re.search(r"\bif\s+([\w .@-]+?)\s+(?:leaves|left|quits)", q)
    if m:
        name = m.group(1).strip()
        people = [p for p in g.nodes(kind="Person")
                  if name.lower() in p["name"].lower()
                  or name.lower() in p["props"].get("email", "").lower()]
        if not people:
            return {"answer": f"No person matching '{name}' in the genome.", "evidence": []}
        sim = bus_factor(g, people[0]["id"])
        crit = ", ".join(c["service"] for c in sim["critical"]) or "none"
        return {"answer": f"If {sim['person']} leaves: {sim['services_impacted']} services "
                          f"impacted, critical: {crit}.",
                "evidence": [f"bus-factor simulation over KNOWS edges"],
                "detail": sim}

    m = re.search(r"why (?:does|do) ([\w-]+) exist", q)
    if m:
        prof = g.profile(f"svc:{m.group(1)}")
        if prof:
            return {"answer": f"{prof['entity']} was born {prof['born']} "
                              f"(commit {str(prof.get('born_commit'))[:8]}: "
                              f"\"{prof.get('born_msg')}\"). "
                              f"{len(prof['dependents'])} services now depend on it.",
                    "evidence": [f"commit:{prof.get('born_commit')}"]}

    return {"answer": "I can answer (graph-only v0): 'who knows <service>', "
                      "'why does <a> depend on <b>', 'why does <svc> exist', "
                      "'what happens if <person> leaves'.",
            "evidence": []}
