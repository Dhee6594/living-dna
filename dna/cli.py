"""dna — Living Software DNA CLI (walking skeleton).

  dna ingest <repo_path> [--db PATH] [--max-commits N]   sequence a local git repo (passes 1-4)
  dna profile <service> [--db PATH]       print a DNA profile
  dna ask "<question>" [--deep]           archaeology Q&A (graph-first; --deep uses LLM)
  dna busfactor [--person NAME]           org heatmap or departure simulation
  dna timetravel --at YYYY-MM-DD          dependency graph at a date
  dna diff --from YYYY-MM-DD [--to YYYY-MM-DD]   (--to defaults to now)
  dna mine <service> [--era N]            LLM decision mining over an era (needs API key)
  dna export [--out FILE]                 JSON dump of all nodes/edges/events (open schema)
  dna insights                            engineering-intelligence report (graph-only)
  dna connect <url> [--token T] [--branch B] [--name N]   connect + clone + build a GitHub repo
  dna sync [<repo>] [--all] [--token T]   incremental update (only new commits)
  dna repos                               list connected repositories + metadata
  dna pr [--repo N --base REV [--head REV]] | [--files ...]   PR impact prediction
  dna timeline [--repo N]                 architecture evolution over time
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
    s.add_argument("--host", default="127.0.0.1",
                   help="bind address (default: %(default)s — loopback only; "
                        "use 0.0.0.0 to expose deliberately)")
    sub.add_parser("report")
    sub.add_parser("insights")

    # --- Phase 4: GitHub connector & continuous intelligence ---------------
    s = sub.add_parser("connect"); s.add_argument("url")
    s.add_argument("--token", help="GitHub Personal Access Token (private/org repos)")
    s.add_argument("--branch"); s.add_argument("--name", help="repo name override")
    s.add_argument("--workdir", default=".dna/repos",
                   help="where working clones are stored (default: %(default)s)")
    s.add_argument("--max-commits", type=int, default=0, metavar="N")
    s = sub.add_parser("sync"); s.add_argument("repo", nargs="?")
    s.add_argument("--all", action="store_true", help="sync every connected repo")
    s.add_argument("--token")
    sub.add_parser("repos")
    s = sub.add_parser("pr")
    s.add_argument("--repo", help="connected repo name (uses its clone for the diff)")
    s.add_argument("--base", help="base revision (e.g. main, a SHA)")
    s.add_argument("--head", default="HEAD")
    s.add_argument("--files", nargs="*", help="explicit changed-file list instead of a diff")
    s = sub.add_parser("timeline"); s.add_argument("--repo")

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
        out = ops.diff(g, parse_when(a.t1), parse_when(a.t2))
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
    elif a.cmd == "insights":
        from . import insights as ins
        out = ins.insights(g)
    elif a.cmd == "connect":
        from . import github_connector as ghc
        out = ghc.connect(g, a.url, a.workdir, token=a.token, branch=a.branch,
                          repo_name=a.name, max_commits=a.max_commits)
    elif a.cmd == "sync":
        from . import github_connector as ghc
        if a.all or not a.repo:
            names = [r["repo"] for r in ghc.list_repos(g)]
            out = {n: ghc.sync_repo(g, n, token=a.token) for n in names} \
                if names else {"error": "no connected repos — run `dna connect` first"}
        else:
            out = ghc.sync_repo(g, a.repo, token=a.token)
    elif a.cmd == "repos":
        from . import github_connector as ghc
        out = ghc.list_repos(g)
    elif a.cmd == "pr":
        from . import pr_intel
        if a.files:
            files = a.files
        elif a.repo and a.base:
            from . import github_connector as ghc
            meta = ghc.repo_meta(g, a.repo)
            if not meta:
                out = {"error": f"repo '{a.repo}' not connected"}; files = None
            else:
                files = pr_intel.diff_files(meta["clone_path"], a.base, a.head)
        else:
            out = {"error": "pr needs --files ... OR --repo NAME --base REV"}; files = None
        if files is not None:
            out = pr_intel.analyze(g, files, repo=a.repo)
    elif a.cmd == "timeline":
        from . import timeline as tl
        out = tl.timeline(g, repo=a.repo)
    elif a.cmd == "serve":
        serve(a.db, a.port, a.host); return

    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
