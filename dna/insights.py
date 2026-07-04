"""Insight Engine — turns the genome into engineering intelligence.

Design rules:
  * Graph-only and deterministic: reads the genome, never git, never an LLM
    (the read path never requires inference — §2.4). `dna mine` output
    (Decision nodes) is consumed when present, never required.
  * Every score has a transparent formula documented next to it. A principal
    engineer should be able to recompute any number by hand.
  * Every insight answers one of: what should I know / fix / investigate,
    what happens next, who really owns this, where is debt accumulating.

Entry point: insights(g, repo_root=None) -> dict (JSON-safe).
"""
import time
from collections import defaultdict
from pathlib import Path

from . import genome_ops as ops

DAY = 86400.0


# ------------------------------------------------------------- graph helpers
def _dep_adjacency(g):
    adj = defaultdict(set)
    for e in g.edges_q(kind="DEPENDS_ON"):
        adj[e["src"]].add(e["dst"])
    return adj


def find_cycles(adj):
    """All elementary dependency cycles (DFS, deduped by rotation)."""
    cycles, seen = [], set()

    def dfs(node, path, visiting):
        for nxt in sorted(adj.get(node, ())):
            if nxt in path:
                cyc = path[path.index(nxt):] + [nxt]
                key = frozenset(cyc)
                if key not in seen:
                    seen.add(key)
                    cycles.append([c.split(":", 1)[1] for c in cyc])
            elif nxt not in visiting:
                visiting.add(nxt)
                dfs(nxt, path + [nxt], visiting)

    for start in sorted(adj):
        dfs(start, [start], {start})
    return cycles


def hidden_dependencies(g, min_co_changes=3):
    """Services that change together repeatedly with NO declared dependency —
    invisible on GitHub, and the classic source of surprise breakage."""
    declared = set()
    for e in g.edges_q(kind="DEPENDS_ON"):
        declared.add((e["src"], e["dst"]))
        declared.add((e["dst"], e["src"]))
    hidden = []
    for e in g.edges_q(kind="CO_CHANGES"):
        n = e["props"].get("count", 0)
        if n >= min_co_changes and (e["src"], e["dst"]) not in declared:
            hidden.append({
                "a": e["src"].split(":", 1)[1],
                "b": e["dst"].split(":", 1)[1],
                "co_changes": n,
                "since": ops._date(e["valid_from"]),
                "note": "change together with no declared dependency — "
                        "hidden coupling or a missing boundary",
            })
    hidden.sort(key=lambda h: -h["co_changes"])
    return hidden


def _gini(values):
    """0 = perfectly even, 1 = one item holds everything."""
    vals = sorted(v for v in values if v >= 0)
    n = len(vals)
    total = sum(vals)
    if n == 0 or total == 0:
        return 0.0
    cum = 0.0
    for i, v in enumerate(vals, 1):
        cum += i * v
    return round((2 * cum) / (n * total) - (n + 1) / n, 3)


# ------------------------------------------------------------------ sections
def _activity(g):
    """Per-service commit timestamps from the event log."""
    acts = defaultdict(list)
    for ev in g.events_q(kind="code.commit"):
        for s in ev["subjects"]:
            acts[s].append(ev["occurred_at"])
    return acts


def _overview(g, profiles, acts, cycles, hidden):
    all_ts = [t for ts in acts.values() for t in ts]
    now = time.time()
    age_days = (now - min(all_ts)) / DAY if all_ts else 0
    recent = [t for t in all_ts if now - t < 90 * DAY]
    langs = defaultdict(int)
    for p in profiles:
        for k, v in (p.get("languages") or {}).items():
            langs[k] += v
    dep_edges = g.edges_q(kind="DEPENDS_ON")
    n = max(1, len(profiles))
    # Complexity 0-100: edge density (40) + cycles (30) + hidden coupling (30)
    complexity = min(100, round(
        40 * min(1.0, len(dep_edges) / (2 * n))
        + 30 * min(1.0, len(cycles) / 3)
        + 30 * min(1.0, len(hidden) / 5)))
    # Maintainability 0-100: ownership breadth (50) + activity spread (30)
    #   + freedom from risk flags (20)
    eff = [p["knowledge"]["effective_owners"] for p in profiles] or [0]
    churn_gini = _gini([len(acts.get(p["id"], [])) for p in profiles])
    risky = sum(1 for p in profiles if p["risks"])
    maintainability = max(0, min(100, round(
        50 * min(1.0, (sum(eff) / len(eff)) / 3)
        + 30 * (1 - churn_gini)
        + 20 * (1 - risky / n))))
    # Maturity: age (40) + bot/CI presence (20) + multi-era share (20) + docs (20)
    bots = sum(1 for p in g.nodes(kind="Person") if p["props"].get("bot"))
    multi_era = sum(1 for p in profiles if len(p.get("eras", [])) > 1)
    documented = sum(1 for p in profiles if p.get("_has_docs"))
    maturity = min(100, round(
        40 * min(1.0, age_days / 1095)
        + 20 * (1 if bots else 0)
        + 20 * (multi_era / n)
        + 20 * (documented / n)))
    return {
        "services": len(profiles),
        "age_days": round(age_days),
        "commits_90d": len(recent),
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])[:6]),
        "complexity_score": complexity,
        "maintainability_score": maintainability,
        "maturity_score": maturity,
        "score_formulas": {
            "complexity": "40·edge_density + 30·cycles + 30·hidden_coupling",
            "maintainability": "50·avg_effective_owners/3 + 30·(1−churn_gini) + 20·(1−risky_share)",
            "maturity": "40·age/3y + 20·has_bots(CI) + 20·multi_era_share + 20·docs_share",
        },
    }


def _health(g, profiles, acts):
    now = time.time()
    weights_all = []
    hot, stable, volatile = [], [], []
    for p in profiles:
        ts = sorted(acts.get(p["id"], []))
        n90 = sum(1 for t in ts if now - t < 90 * DAY)
        life = (ts[-1] - ts[0]) / DAY if len(ts) > 1 else 0
        rate_life = len(ts) / max(life / 90, 1)      # commits per 90d, lifetime
        entry = {"service": p["entity"], "commits_90d": n90,
                 "lifetime_commits": len(ts)}
        if n90 >= max(5, 2 * rate_life):
            volatile.append({**entry, "note": "accelerating churn vs lifetime baseline"})
        elif n90 == 0 and len(ts) >= 5 and (now - ts[-1]) > 180 * DAY:
            stable.append({**entry, "dormant_days": round((now - ts[-1]) / DAY)})
        if n90 > 0:
            hot.append(entry)
        weights_all.extend(o["weight"] for o in p["knowledge"]["top"])
    hot.sort(key=lambda h: -h["commits_90d"])
    return {
        "ownership_concentration_gini": _gini(weights_all),
        "knowledge_distribution": {
            p["entity"]: p["knowledge"]["effective_owners"] for p in profiles},
        "churn_hotspots": hot[:8],
        "stable_modules": stable[:8],
        "volatile_modules": volatile[:8],
    }


def _architecture(g, profiles, cycles, hidden, acts):
    now = time.time()
    dep_edges = g.edges_q(kind="DEPENDS_ON")
    co_edges = g.edges_q(kind="CO_CHANGES")
    all_ts = [t for ts in acts.values() for t in ts]
    lifespan = (now - min(all_ts)) if all_ts else 1
    recent_cut = now - 0.2 * lifespan
    drift = [{"edge": f"{e['src'].split(':',1)[1]} -> {e['dst'].split(':',1)[1]}",
              "since": ops._date(e["valid_from"])}
             for e in dep_edges
             if e["valid_from"] and e["valid_from"] > recent_cut]
    coupling = sorted(
        ({"pair": f"{e['src'].split(':',1)[1]} <-> {e['dst'].split(':',1)[1]}",
          "co_changes": e["props"].get("count", 0),
          "declared": (e["src"], e["dst"]) in
                      {(d["src"], d["dst"]) for d in dep_edges}
                      or (e["dst"], e["src"]) in
                      {(d["src"], d["dst"]) for d in dep_edges}}
         for e in co_edges),
        key=lambda c: -c["co_changes"])[:10]
    timeline = sorted(
        ({"service": p["entity"], "born": p["born"], "eras": len(p.get("eras", [])),
          "origin": p.get("born_msg")}
         for p in profiles if p.get("born")),
        key=lambda t: t["born"] or "")
    boundary_note = None
    if profiles and co_edges:
        cross = sum(1 for c in coupling if not c["declared"])
        if cross >= max(2, len(coupling) // 2):
            boundary_note = (f"{cross} of the top {len(coupling)} coupled pairs have no "
                             "declared dependency — service boundaries may not match "
                             "how the system actually changes")
    return {
        "circular_dependencies": cycles,
        "hidden_dependencies": hidden[:10],
        "coupling": coupling,
        "architectural_drift": drift[:10],
        "evolution_timeline": timeline,
        "boundary_assessment": boundary_note
            or "declared boundaries broadly match observed change patterns",
    }


def _risk(g, profiles, acts):
    now = time.time()
    org = ops.org_bus_factor(g)
    spof = [r for r in org if r["critical_services"] > 0]
    unowned = [p["entity"] for p in profiles
               if p["knowledge"]["effective_owners"] == 0]
    scaling = []
    for p in profiles:
        n90 = sum(1 for t in acts.get(p["id"], []) if now - t < 90 * DAY)
        if len(p["dependents"]) >= 2 and n90 >= 5:
            scaling.append({
                "service": p["entity"], "dependents": len(p["dependents"]),
                "commits_90d": n90,
                "note": "high fan-in AND high recent churn — every change "
                        "here ripples outward",
            })
    frequent = sorted(
        ({"service": p["entity"],
          "commits_90d": sum(1 for t in acts.get(p["id"], []) if now - t < 90 * DAY)}
         for p in profiles),
        key=lambda x: -x["commits_90d"])[:5]
    return {
        "single_points_of_failure": spof[:8],
        "unowned_services": unowned,
        "scaling_bottlenecks": scaling,
        "frequently_changing": [f for f in frequent if f["commits_90d"] > 0],
    }


def _knowledge(g, profiles, repo_root):
    silos = []
    for p in profiles:
        top = p["knowledge"]["top"]
        if top and top[0]["weight"] >= 0.8 and len(p["dependents"]) >= 1:
            silos.append({
                "service": p["entity"], "holder": top[0]["person"],
                "share": top[0]["weight"],
                "dependents": len(p["dependents"]),
            })
    missing_docs = []
    if repo_root and Path(repo_root).is_dir():
        for p in profiles:
            d = Path(repo_root) / (p.get("dir") or ".")
            if d.is_dir() and not any(
                    (d / f).exists() for f in ("README.md", "README.rst", "README")):
                p["_has_docs"] = False
                missing_docs.append(p["entity"])
            else:
                p["_has_docs"] = True
    decisions = g.nodes(kind="Decision")
    conf = [d["confidence"] for d in decisions]
    critical = ops.org_bus_factor(g)[:3]
    context = [
        {"service": p["entity"], "born": p["born"], "origin": p.get("born_msg")}
        for p in profiles if p.get("born_msg")
    ]
    return {
        "knowledge_silos": silos,
        "missing_documentation": missing_docs,
        "critical_contributors": critical,
        "historical_context": context[:10],
        "decision_mining": {
            "decisions_mined": len(decisions),
            "avg_confidence": round(sum(conf) / len(conf), 2) if conf else None,
            "note": None if decisions else
                    "no mined decisions yet — run `dna mine <service>` with an "
                    "API key to extract decision history with citations",
        },
    }


# ------------------------------------------------------------ recommendations
EFFORT_WEEKS = {"S": 1, "M": 3, "L": 8}


def _recommendations(overview, health, arch, risk, knowledge):
    """Rule-based, ranked. score = impact·confidence − 0.5·risk_of_action.
    impact/risk_of_action: 1–5, confidence: 0–1, effort: S/M/L."""
    recs = []

    def add(action, why, impact, action_risk, confidence, effort):
        recs.append({
            "action": action, "why": why, "impact": impact,
            "risk": action_risk, "confidence": confidence, "effort": effort,
            "score": round(impact * confidence - 0.5 * action_risk, 2),
        })

    for s in knowledge["knowledge_silos"][:3]:
        add(f"Pair a second engineer with {s['holder']} on {s['service']}",
            f"{s['holder']} holds {int(s['share']*100)}% of {s['service']} knowledge "
            f"and {s['dependents']} services depend on it — one departure from "
            "recovery measured in months",
            impact=5, action_risk=1, confidence=0.9, effort="M")
    for h in arch["hidden_dependencies"][:3]:
        add(f"Declare or break the hidden coupling {h['a']} <-> {h['b']}",
            f"changed together {h['co_changes']}× with no declared dependency — "
            "invisible in code review, guaranteed surprise in refactors",
            impact=4, action_risk=2, confidence=0.8, effort="M")
    for c in arch["circular_dependencies"][:2]:
        add(f"Break the dependency cycle: {' -> '.join(c)}",
            "cycles make services undeployable independently and freeze "
            "refactoring; every architecture erodes from its first cycle",
            impact=4, action_risk=3, confidence=0.95, effort="L")
    for b in risk["scaling_bottlenecks"][:2]:
        add(f"Stabilize the interface of {b['service']}",
            f"{b['dependents']} dependents and {b['commits_90d']} changes in 90d — "
            "version its contract or extract the volatile part",
            impact=4, action_risk=2, confidence=0.75, effort="M")
    for m in knowledge["missing_documentation"][:3]:
        add(f"Add a README to {m}",
            "no entry-point documentation; onboarding cost is paid on every hire",
            impact=2, action_risk=1, confidence=0.9, effort="S")
    for u in risk["unowned_services"][:2]:
        add(f"Assign an owner to {u}",
            "zero derived knowledge edges — nobody currently 'knows' this service",
            impact=3, action_risk=1, confidence=0.85, effort="S")
    if overview["maintainability_score"] < 40:
        add("Schedule a debt-reduction iteration",
            f"maintainability {overview['maintainability_score']}/100 — churn "
            "concentration and thin ownership compound monthly",
            impact=4, action_risk=2, confidence=0.7, effort="L")
    recs.sort(key=lambda r: -r["score"])
    return recs


def _executive(overview, health, arch, risk, knowledge, recs):
    top = recs[0]["action"] if recs else "no action required"
    spof = risk["single_points_of_failure"]
    return {
        "cto": (
            f"{overview['services']} services, complexity {overview['complexity_score']}/100, "
            f"maintainability {overview['maintainability_score']}/100. "
            f"{len(spof)} people are single points of failure"
            + (f" (worst: {spof[0]['person']}, {spof[0]['critical_services']} critical services)" if spof else "")
            + f". {len(knowledge['knowledge_silos'])} knowledge silos. Priority: {top}."),
        "engineering_manager": (
            f"Knowledge gini {health['ownership_concentration_gini']} — "
            + ("concentrated; plan pairing rotations. " if health['ownership_concentration_gini'] > 0.6 else "acceptably spread. ")
            + f"{len(health['volatile_modules'])} volatile modules need review focus; "
            f"{len(knowledge['missing_documentation'])} services lack READMEs. "
            f"Succession plans exist in the bus-factor simulations."),
        "staff_engineer": (
            f"{len(arch['circular_dependencies'])} dependency cycles, "
            f"{len(arch['hidden_dependencies'])} hidden couplings (top: "
            + (f"{arch['hidden_dependencies'][0]['a']}<->{arch['hidden_dependencies'][0]['b']} "
               f"at {arch['hidden_dependencies'][0]['co_changes']}x" if arch['hidden_dependencies'] else "none")
            + f"). {arch['boundary_assessment']}. "
            f"Drift: {len(arch['architectural_drift'])} new edges in the recent window."),
        "platform_team": (
            "Scaling watchlist: "
            + (", ".join(b["service"] for b in risk["scaling_bottlenecks"]) or "clear")
            + ". Churn hotspots: "
            + (", ".join(h["service"] for h in health["churn_hotspots"][:3]) or "none")
            + ". Stable/dormant candidates for ownership archive: "
            + (", ".join(s["service"] for s in health["stable_modules"][:3]) or "none") + "."),
    }


# ----------------------------------------------------------------- entrypoint
def insights(g, repo_root=None):
    t0 = time.time()
    profiles = g.profiles_all()
    if not profiles:
        return {"error": "no profiles — run `dna ingest` first"}
    if repo_root is None:
        repos = g.nodes(kind="Repo")
        repo_root = repos[0]["props"].get("path") if repos else None
    acts = _activity(g)
    adj = _dep_adjacency(g)
    cycles = find_cycles(adj)
    hidden = hidden_dependencies(g)
    knowledge = _knowledge(g, profiles, repo_root)   # sets _has_docs, used by overview
    overview = _overview(g, profiles, acts, cycles, hidden)
    health = _health(g, profiles, acts)
    arch = _architecture(g, profiles, cycles, hidden, acts)
    risk = _risk(g, profiles, acts)
    recs = _recommendations(overview, health, arch, risk, knowledge)
    execs = _executive(overview, health, arch, risk, knowledge, recs)
    for p in profiles:
        p.pop("_has_docs", None)
    return {
        "generated_in_ms": round((time.time() - t0) * 1000),
        "overview": overview,
        "engineering_health": health,
        "architecture": arch,
        "risk_intelligence": risk,
        "knowledge_intelligence": knowledge,
        "recommendations": recs,
        "executive": execs,
    }
