"""dna — Living Software DNA CLI (walking skeleton).

  dna ingest <repo_path> [--db PATH] [--max-commits N]   sequence a local git repo (passes 1-4)
  dna profile <service> [--db PATH]       print a DNA profile
  dna ask "<question>" [--deep]           archaeology Q&A (graph-first; --deep uses LLM)
  dna busfactor [--person NAME]           org heatmap or departure simulation
  dna timetravel --at YYYY-MM-DD          dependency graph at a date
  dna diff --from YYYY-MM-DD --to YYYY-MM-DD
  dna mine <service> [--era N]            LLM decision mining over an era (needs API key)
  dna export [--out FILE]                 JSON dump of all nodes/edges/events (open schema)
  dna serve [--port 8077]                 Genome Browser web UI + JSON API
"""
import argparse
import json
import sys

from .db import Genome
from . import genome_ops as ops
from .ingest import ingest_repo
from .server import serve, parse_when


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dna", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=".dna/genome.db")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest"); s.add_argument("repo")
    s.add_argument("--max-commits", type=int, default=0, metavar="N",
                   help="cap git history replay at N most-recent commits (0 = no cap)")
    s = sub.add_parser("profile"); s.add_argument("service")
    s = sub.add_parser("ask"); s.add_argument("question"); s.add_argument("--deep", action="store_true")
    s = sub.add_parser("busfactor"); s.add_argument("--person")
    s = sub.add_parser("timetravel"); s.add_argument("--at", required=True)
    s = sub.add_parser("diff"); s.add_argument("--from", dest="t1", required=True); s.add_argument("--to", dest="t2", default="now")
    s = sub.add_parser("mine"); s.add_argument("service"); s.add_argument("--era", type=int, default=0)
    s = sub.add_parser("export")
    s.add_argument("--out", default="", metavar="FILE",
                   help="write JSON to FILE instead of stdout")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8077)
    sub.add_parser("report")

    a = ap.parse_args(argv)
    g = Genome(a.db)
    out = None

    if a.cmd == "ingest":
        out = ingest_repo(g, a.repo, max_commits=a.max_commits)
        n = ops.materialize_profiles(g)
        out["profiles_materialized"] = n
    elif a.cmd == "profile":
        out = g.profile(f"svc:{a.service}") or {"error": f"no service {a.service}"}
    elif a.cmd == "ask":
        out = ops.ask(g, a.question)
        if a.deep:
            from . import ai
            if ai.available():
                out["deep_answer"] = ai.deep_answer(g, a.question, out)
            else:
                out["hint"] = "set ANTHROPIC_API_KEY for --deep"
    elif a.cmd == "busfactor":
        if a.person:
            people = [p for p in g.nodes(kind="Person")
                      if a.person.lower() in p["name"].lower()
                      or a.person.lower() in p["props"].get("email", "")]
            out = ops.bus_factor(g, people[0]["id"]) if people else \
                {"error": f"no person '{a.person}'"}
        else:
            out = ops.org_bus_factor(g)
    elif a.cmd == "timetravel":
        out = ops.graph_at(g, parse_when(a.at))
    elif a.cmd == "diff":
        out = ops.diff(g, parse_when(a.t1), parse_when(a.t2) or 9e12)
    elif a.cmd == "mine":
        from . import ai
        if not ai.available():
            out = {"error": "set ANTHROPIC_API_KEY to run decision mining"}
        else:
            sid = f"svc:{a.service}"
            eras = [g.node(e["dst"]) for e in g.edges_q(kind="HAS_ERA", src=sid)]
            eras = sorted([e for e in eras if e], key=lambda e: e["props"]["index"])
            if not eras:
                out = {"error": "no eras — run ingest first"}
            else:
                era = eras[a.era - 1 if a.era else -1]
                out = {"mined": ai.mine_era(g, sid, era["props"]["start"],
                                            era["props"]["end"] + 1)}
    elif a.cmd == "export":
        dump = ops.export_genome(g)
        if a.out:
            import pathlib
            pathlib.Path(a.out).write_text(json.dumps(dump, indent=1))
            out = {"exported": a.out, "stats": dump["stats"]}
        else:
            json.dump(dump, sys.stdout, indent=1)
            print()
            return
    elif a.cmd == "report":
        out = ops.quality_report(g)
    elif a.cmd == "serve":
        serve(a.db, a.port); return

    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
