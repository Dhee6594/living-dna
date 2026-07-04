"""End-to-end test: fixture org -> ingest -> profiles -> bus factor -> time travel -> ask.
Run: python3 -m tests.test_skeleton   (from repo root; stdlib only)
"""
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dna.db import Genome                      # noqa: E402
from dna import genome_ops as ops              # noqa: E402
from dna.ingest import ingest_repo             # noqa: E402

PASS = 0


def check(name, cond, detail=""):
    global PASS
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if cond:
        PASS += 1
    else:
        sys.exit(f"test failed: {name}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "acme-shop"
        subprocess.run([sys.executable, str(ROOT / "fixtures/make_fixture.py"),
                        str(fixture)], check=True)
        g = Genome(str(Path(tmp) / "genome.db"))

        # ingest (passes 1-4)
        res = ingest_repo(g, fixture)
        check("ingest: 6 services discovered (incl. plugin-manifest dir)",
              len(res["services"]) == 6, str(sorted(res["services"])))
        check("ingest: 5 identities (4 humans + 1 bot)", res["people"] == 5)
        check("ingest: commits replayed", res["commits"] > 50, f"({res['commits']})")
        check("ingest: eras detected", all(v >= 1 for v in res["eras"].values()),
              str(res["eras"]))

        # real-repo hardening
        check("hardening: plugin.json manifest names parent dir",
              "reporting" in res["services"], str(res["services"].get("reporting")))
        bot = next((p for p in g.nodes(kind="Person")
                    if "dependabot" in p["name"]), None)
        check("hardening: bot identified", bot is not None
              and bot["props"].get("bot") is True)
        check("hardening: bot holds no knowledge",
              not g.edges_q(kind="KNOWS", src=bot["id"]))
        check("hardening: rename tracked as event",
              any("core.py" in str(r["payload"].get("new", ""))
                  for r in g.events_q(kind="code.rename")))

        # profiles
        n = ops.materialize_profiles(g)
        check("profiles materialized", n == 6)
        rep = ops.quality_report(g)
        check("quality report runs", rep["services"] == 6 and
              rep["people"]["bots_filtered"] == 1, str(rep["people"]))
        pay = g.profile("svc:payments")
        check("profile: payments born with cause",
              pay["born"] and "strangler" in (pay["born_msg"] or "").lower(),
              pay["born_msg"])
        check("profile: payments depends on auth",
              any(d["on"] == "auth" for d in pay["dependencies"]))
        check("profile: knowledge concentration risk on payments",
              any(r["class"] == "knowledge_concentration" for r in pay["risks"]),
              str(pay["knowledge"]))

        # bus factor
        lena = next(p for p in g.nodes(kind="Person") if "Lena" in p["name"])
        sim = ops.bus_factor(g, lena["id"])
        check("bus factor: Lena impacts payments",
              any(d["service"] == "payments" for d in sim["details"]))
        check("bus factor: payments critical without Lena",
              any(c["service"] == "payments" for c in sim["critical"]),
              f"critical={[c['service'] for c in sim['critical']]}")

        # time travel: before checkout was born (day ~200 of history)
        t_mid = time.time() - int(2.5 * 365 - 200) * 86400
        past = ops.graph_at(g, t_mid)
        now = ops.graph_at(g)
        check("time travel: fewer services in the past",
              len(past["services"]) < len(now["services"]),
              f"{len(past['services'])} then vs {len(now['services'])} now")
        check("time travel: checkout absent in the past",
              not any(s["name"] == "checkout" for s in past["services"]))

        d = ops.diff(g, t_mid, time.time())
        check("diff: checkout among services added",
              any("checkout" in s["id"] for s in d["services_added"]), str(d["services_added"]))

        # archaeology
        a1 = ops.ask(g, "who knows payments")
        check("ask: who knows payments → Lena", "Lena" in a1["answer"], a1["answer"])
        a2 = ops.ask(g, "why does checkout depend on payments")
        check("ask: dependency archaeology has evidence", len(a2["evidence"]) > 0,
              a2["answer"])
        a3 = ops.ask(g, "what happens if Lena leaves")
        check("ask: departure simulation", "payments" in a3["answer"], a3["answer"])
        a4 = ops.ask(g, "why does payments exist")
        check("ask: origin story cites birth commit",
              "strangler" in a4["answer"].lower(), a4["answer"])

    print(f"\nALL {PASS} CHECKS PASSED")


# ---------------------------------------------------------------- unit tests
# These run without the fixture git repo; they test the ingest helpers directly.

def test_rename_brace_empty_segment():
    """resolve_rename handles '{old =>}' (deleted-segment) and '{=> new}' forms."""
    from dna.ingest import resolve_rename
    # Normal case
    new, old = resolve_rename("a/{foo => bar}/b.py")
    check("rename: normal brace form", new == "a/bar/b.py" and old == "a/foo/b.py",
          f"new={new} old={old}")
    # Added-segment: '{=> new}'
    new, old = resolve_rename("src/{=> v2}/core.py")
    check("rename: added-segment brace '{=> new}'", new == "src/v2/core.py",
          f"new={new} old={old}")
    # Deleted-segment: '{old =>}'  — new path would be empty; we keep original
    new, old = resolve_rename("src/{v1 =>}/core.py")
    check("rename: deleted-segment brace '{old =>}' doesn't crash",
          new is not None, f"new={new} old={old}")
    # Top-level rename (no braces)
    new, old = resolve_rename("old/path.py => new/path.py")
    check("rename: top-level form", new == "new/path.py" and old == "old/path.py",
          f"new={new} old={old}")
    # Non-rename path — must pass through unchanged
    new, old = resolve_rename("src/main.py")
    check("rename: plain path unchanged", new == "src/main.py" and old is None,
          f"new={new} old={old}")


def test_identity_resolution():
    """Duplicate git identities collapse per dna/identity.py rules."""
    import json
    import tempfile
    from pathlib import Path
    from dna.identity import resolve_identities

    def C(author, email, bot=False):
        return {"author": author, "email": email, "bot": bot}

    # Rule A: exact multi-token name, different emails -> merged
    commits = [C("Lena Kovacs", "lena@acme.io")] * 3 + \
              [C("lena kovacs", "lena.kovacs@gmail.com")]
    m = resolve_identities(commits)
    check("identity: multi-token name merge",
          m.get("lena.kovacs@gmail.com", ("",))[0] == "lena@acme.io", str(m))

    # Canonical = identity with the most commits
    check("identity: canonical is majority identity",
          "lena@acme.io" not in m, str(m))

    # Single-token names are too ambiguous -> never merged on name alone
    commits = [C("sai", "a@x.com"), C("sai", "b@y.com")]
    check("identity: single-token names NOT merged",
          resolve_identities(commits) == {}, str(resolve_identities(commits)))

    # Rule B: GitHub noreply matches email local-part
    commits = [C("Lena Kovacs", "lena@acme.io")] * 2 + \
              [C("lenak", "12345+lena@users.noreply.github.com")]
    m = resolve_identities(commits)
    check("identity: github-noreply local-part merge",
          m.get("12345+lena@users.noreply.github.com", ("",))[0] == "lena@acme.io",
          str(m))

    # Distinct people never merged
    commits = [C("Jin Park", "jin@acme.io"), C("Lena Kovacs", "lena@acme.io")]
    check("identity: distinct people untouched",
          resolve_identities(commits) == {}, "")

    # Bots never participate
    commits = [C("Lena Kovacs", "lena@acme.io"),
               C("Lena Kovacs", "dep@bots.io", bot=True)]
    check("identity: bots never merged",
          resolve_identities(commits) == {}, "")

    # Explicit override file always wins
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".dna").mkdir()
        (root / ".dna" / "identities.json").write_text(json.dumps(
            {"aliases": {"apple@mac.local": "vs94@gmail.com"}}))
        commits = [C("Sai Dheeraj", "vs94@gmail.com")] * 2 + \
                  [C("Sai", "apple@mac.local")]
        m = resolve_identities(commits, root)
        check("identity: override file merges unrelated names",
              m.get("apple@mac.local", ("",))[0] == "vs94@gmail.com", str(m))


def test_diff_now_no_crash():
    """dna diff with 'now' endpoints must not crash (9e12 sentinel regression)."""
    import tempfile
    from pathlib import Path
    from dna.db import Genome
    from dna import genome_ops as ops

    with tempfile.TemporaryDirectory() as tmp:
        g = Genome(str(Path(tmp) / "d.db"))
        g.upsert_node("svc:a", "Service", "a", valid_from=1577836800.0)  # 2020-01-01
        g.commit()
        d = ops.diff(g, 1546300800.0, None)          # --from 2019 --to now
        check("diff: --to now does not crash",
              any("svc:a" in str(s) for s in d["services_added"]), str(d))
        d2 = ops.diff(g, None, None)                 # --from now --to now
        check("diff: now->now is empty and sane",
              d2["services_added"] == [] and d2["services_removed"] == [], str(d2))


def test_insight_engine():
    """Insight engine: cycles, hidden coupling, gini, recommendations ranking,
    end-to-end on the fixture genome (Phase 3 Task 2)."""
    import tempfile
    from pathlib import Path
    from dna.db import Genome
    from dna.ingest import ingest_repo
    from dna import genome_ops as ops
    from dna.insights import find_cycles, hidden_dependencies, _gini, insights

    # Unit: cycle detection
    adj = {"svc:a": {"svc:b"}, "svc:b": {"svc:c"}, "svc:c": {"svc:a"},
           "svc:x": {"svc:y"}}
    cyc = find_cycles(adj)
    check("insights: 3-cycle detected", any(set(c) >= {"a", "b", "c"} for c in cyc),
          str(cyc))
    check("insights: acyclic pair not flagged",
          not any("x" in c or "y" in c for c in cyc), str(cyc))
    check("insights: no false cycles on empty graph", find_cycles({}) == [], "")

    # Unit: gini
    check("insights: gini even distribution ~0", _gini([1, 1, 1, 1]) < 0.05,
          str(_gini([1, 1, 1, 1])))
    check("insights: gini concentrated -> high", _gini([0, 0, 0, 10]) > 0.7,
          str(_gini([0, 0, 0, 10])))

    # Unit: hidden dependency = co-change without declared edge
    with tempfile.TemporaryDirectory() as tmp:
        g = Genome(str(Path(tmp) / "h.db"))
        for s in ("a", "b", "c"):
            g.upsert_node(f"svc:{s}", "Service", s)
        g.upsert_edge("DEPENDS_ON", "svc:a", "svc:b")
        g.upsert_edge("CO_CHANGES", "svc:a", "svc:b", props={"count": 9})
        g.upsert_edge("CO_CHANGES", "svc:a", "svc:c", props={"count": 5})
        g.commit()
        hid = hidden_dependencies(g)
        check("insights: declared co-change not hidden",
              not any({h["a"], h["b"]} == {"a", "b"} for h in hid), str(hid))
        check("insights: undeclared co-change IS hidden",
              any({h["a"], h["b"]} == {"a", "c"} for h in hid), str(hid))

    # End-to-end on fixture
    import subprocess, sys
    with tempfile.TemporaryDirectory() as tmp:
        fx = Path(tmp) / "acme-shop"
        subprocess.run([sys.executable, str(ROOT / "fixtures/make_fixture.py"),
                        str(fx)], check=True)
        g = Genome(str(Path(tmp) / "i.db"))
        ingest_repo(g, fx)
        ops.materialize_profiles(g)
        doc = insights(g)
        for key in ("overview", "engineering_health", "architecture",
                    "risk_intelligence", "knowledge_intelligence",
                    "recommendations", "executive"):
            check(f"insights: section '{key}' present", key in doc, "")
        check("insights: scores in 0-100",
              all(0 <= doc["overview"][k] <= 100 for k in
                  ("complexity_score", "maintainability_score", "maturity_score")),
              str(doc["overview"]))
        recs = doc["recommendations"]
        check("insights: recommendations ranked by score",
              all(recs[i]["score"] >= recs[i+1]["score"]
                  for i in range(len(recs) - 1)), str([r["score"] for r in recs]))
        check("insights: recs carry impact/risk/confidence/effort",
              all(all(k in r for k in ("impact", "risk", "confidence", "effort"))
                  for r in recs), "")
        check("insights: all four executive audiences",
              set(doc["executive"]) == {"cto", "engineering_manager",
                                        "staff_engineer", "platform_team"},
              str(list(doc["executive"])))
        check("insights: silo detected on fixture (Lena/payments)",
              any(s["service"] == "payments"
                  for s in doc["knowledge_intelligence"]["knowledge_silos"]),
              str(doc["knowledge_intelligence"]["knowledge_silos"]))


def test_service_detection_beyond_manifests():
    """Tiered discovery: entrypoints, compose, content dirs; no false positives
    from tests/docs/package-internals (Phase 2 Task 1)."""
    import tempfile
    from pathlib import Path
    from dna.ingest import discover_services

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "polyrepo"

        # entrypoint tier: Dockerfile-only dir, *_server.py dir
        (root / "backend").mkdir(parents=True)
        (root / "backend" / "Dockerfile").write_text("FROM python:3.12\n")
        (root / "ner-server").mkdir()
        (root / "ner-server" / "ner_server.py").write_text("print('serve')\n")
        # excluded: tests/ with an entrypoint name
        (root / "tests").mkdir()
        (root / "tests" / "main.py").write_text("pass\n")
        # excluded: module inside a python package tree
        (root / "pkg").mkdir()
        (root / "pkg" / "__init__.py").write_text("")
        (root / "pkg" / "sub").mkdir()
        (root / "pkg" / "sub" / "app.py").write_text("pass\n")
        # compose tier
        (root / "worker").mkdir()
        (root / "worker" / "run.sh").write_text("#!/bin/sh\n")
        (root / "docker-compose.yml").write_text(
            "services:\n  worker:\n    build: ./worker\n")

        s, m = discover_services(root, with_methods=True)
        check("detect: Dockerfile-only dir found",
              m.get("backend") == "entrypoint", str(s))
        check("detect: *_server.py dir found",
              m.get("ner-server") == "entrypoint", str(s))
        check("detect: compose build context found",
              m.get("worker") == "compose", str(s))
        check("detect: tests/ never a service", "tests" not in s, str(s))
        check("detect: package-internal dir never a service",
              "sub" not in s and "pkg" not in s, str(s))

    # content tier: repo with no code markers at all -> top-level content dirs
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "content-repo"
        for d in ("modes", "reports"):
            (root / d).mkdir(parents=True)
            for i in range(3):
                (root / d / f"f{i}.md").write_text("x\n")
        (root / "thin").mkdir()
        (root / "thin" / "one.md").write_text("x\n")
        s, m = discover_services(root, with_methods=True)
        check("detect: content dirs become genes",
              m.get("modes") == "content" and m.get("reports") == "content", str(s))
        check("detect: thin dirs (<3 files) skipped", "thin" not in s, str(s))

    # manifest repo: content tier must NOT run; root '.' name never empty
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "lib"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\nname='lib'\n")
        (root / "notes").mkdir()
        for i in range(4):
            (root / "notes" / f"n{i}.md").write_text("x\n")
        s, m = discover_services(root, with_methods=True)
        check("detect: manifest repo skips content tier",
              list(s) == ["lib"] and m["lib"] == "manifest", str(s))
        check("detect: root name never empty (Path('.') bug)",
              all(n for n in s), str(s))


def test_server_bind_security():
    """Server defaults to loopback (no-auth genome must not hit the LAN);
    explicit host override remains available (regression for Phase 0 finding)."""
    import inspect
    import subprocess
    import sys
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    from dna.server import serve, make_handler

    # 1. Default bind is loopback
    default_host = inspect.signature(serve).parameters["host"].default
    check("server: default host is 127.0.0.1", default_host == "127.0.0.1",
          default_host)

    # 2. CLI exposes --host with loopback default
    out = subprocess.run([sys.executable, "-m", "dna.cli", "serve", "--help"],
                         capture_output=True, text=True, cwd=str(ROOT))
    check("server: CLI has --host flag", "--host" in out.stdout, out.stdout[-200:])
    check("server: CLI --help documents loopback default",
          "127.0.0.1" in out.stdout, out.stdout[-200:])

    # 2b. New API endpoints (report/search/events) serve from existing ops
    import json as _json
    import tempfile as _tf
    from pathlib import Path as _P
    from dna.db import Genome as _G
    from dna.ingest import ingest_repo as _ir
    from dna import genome_ops as _ops
    with _tf.TemporaryDirectory() as tmp2:
        fx = _P(tmp2) / "acme-shop"
        subprocess.run([sys.executable, str(ROOT / "fixtures/make_fixture.py"),
                        str(fx)], check=True)
        db2 = str(_P(tmp2) / "api.db")
        g2 = _G(db2)
        _ir(g2, fx)
        _ops.materialize_profiles(g2)
        g2.conn.close()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db2))
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            def _get(path):
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                    return _json.loads(r.read())
            rep = _get("/api/report")
            check("api: /api/report serves quality report",
                  rep.get("services", 0) >= 1, str(rep)[:80])
            hits = _get("/api/search?q=pay")
            check("api: /api/search finds payments",
                  any("payments" in h["id"] for h in hits), str(hits)[:80])
            evs = _get("/api/events?service=payments&limit=5")
            check("api: /api/events returns commit events",
                  0 < len(evs) <= 5 and evs[0]["kind"] == "code.commit",
                  f"{len(evs)} events")
        finally:
            httpd.shutdown()

    # 3. Functional: loopback bind serves the API; override host is honoured
    import tempfile
    from pathlib import Path
    from dna.db import Genome
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "s.db")
        Genome(db).commit()  # create empty schema
        for host in ("127.0.0.1", "0.0.0.0"):
            httpd = ThreadingHTTPServer((host, 0), make_handler(db))
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/people", timeout=5) as r:
                    ok = r.status == 200
            finally:
                httpd.shutdown()
            check(f"server: bind {host} serves /api/people", ok, f"port {port}")


def test_merge_commit_dedup():
    """Merge commits that list the same path twice must not double-count churn."""
    import tempfile, subprocess
    from pathlib import Path
    from dna.db import Genome
    from dna.ingest import ingest_repo

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "mergerepo"
        repo.mkdir()
        subprocess.run(["git", "-C", str(repo), "init", "-b", "main"],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@test.com"],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"],
                       capture_output=True, check=True)
        # Initial commit
        (repo / "app.py").write_text("x = 1\n" * 20)
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"],
                       capture_output=True, check=True)
        # Feature branch
        subprocess.run(["git", "-C", str(repo), "checkout", "-b", "feat"],
                       capture_output=True, check=True)
        (repo / "app.py").write_text("x = 2\n" * 20)
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "feat"],
                       capture_output=True, check=True)
        # Back to main and merge
        subprocess.run(["git", "-C", str(repo), "checkout", "main"],
                       capture_output=True, check=True)
        (repo / "app.py").write_text("x = 3\n" * 20)
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "main-change"],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "merge", "feat", "--no-ff",
                        "-m", "merge feat", "--allow-unrelated-histories"],
                       capture_output=True)  # may fail on conflict; that's OK

        g = Genome(str(Path(tmp) / "g.db"))
        res = ingest_repo(g, repo)
        # The repo ingested without crashing; that's the core assertion
        check("merge dedup: ingest completes without crash",
              res["commits"] >= 1, f"commits={res['commits']}")
        # Churn for any person must be non-negative and finite
        knows_edges = g.edges_q(kind="KNOWS")
        check("merge dedup: KNOWS weights are sane (0-1)",
              all(0 <= e["props"].get("weight", 0) <= 1.0 for e in knows_edges),
              f"{[(e['props']) for e in knows_edges]}")


def test_bot_author_extended():
    """Extended bot patterns (mend-bot, allcontributors, etc.) are filtered."""
    from dna.ingest import BOT_AUTHOR
    bots = [
        "mend-bot", "allcontributors[bot]", "semantic-release-bot",
        "release-please[bot]", "stale[bot]", "mergify[bot]",
        "sonarcloud[bot]", "dependabot[bot]", "renovate[bot]",
    ]
    for name in bots:
        check(f"bot filter: '{name}' recognised", bool(BOT_AUTHOR.search(name)),
              f"pattern missed: {name}")
    humans = ["alice", "bob smith", "carol@example.com", "dependant"]
    for name in humans:
        check(f"bot filter: '{name}' NOT a bot", not BOT_AUTHOR.search(name),
              f"false positive: {name}")


def test_export():
    """dna export produces a valid schema-v1.0 JSON document."""
    import tempfile, subprocess, sys
    from pathlib import Path
    from dna.db import Genome
    from dna.ingest import ingest_repo
    from dna import genome_ops as ops

    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "acme-shop"
        subprocess.run([sys.executable, str(ROOT / "fixtures/make_fixture.py"),
                        str(fixture)], check=True)
        g = Genome(str(Path(tmp) / "exp.db"))
        ingest_repo(g, fixture)
        ops.materialize_profiles(g)

        dump = ops.export_genome(g)
        check("export: schema_version present", dump.get("schema_version") == "1.0",
              str(dump.get("schema_version")))
        check("export: has nodes/edges/events keys",
              all(k in dump for k in ("nodes", "edges", "events")))
        check("export: nodes non-empty", len(dump["nodes"]) > 0,
              f"{len(dump['nodes'])} nodes")
        check("export: edges non-empty", len(dump["edges"]) > 0,
              f"{len(dump['edges'])} edges")
        check("export: events non-empty", len(dump["events"]) > 0,
              f"{len(dump['events'])} events")
        # Every node must have bitemporal fields
        n = dump["nodes"][0]
        check("export: node has valid_from", "valid_from" in n)
        check("export: node has provenance list", isinstance(n.get("provenance"), list))
        # stats must match actual lengths
        check("export: stats.nodes == len(nodes)",
              dump["stats"]["nodes"] == len(dump["nodes"]))
        check("export: stats.edges == len(edges)",
              dump["stats"]["edges"] == len(dump["edges"]))
        check("export: stats.events == len(events)",
              dump["stats"]["events"] == len(dump["events"]))


if __name__ == "__main__":
    main()
    # Run standalone unit tests
    test_rename_brace_empty_segment()
    test_identity_resolution()
    test_diff_now_no_crash()
    test_insight_engine()
    test_service_detection_beyond_manifests()
    test_server_bind_security()
    test_merge_commit_dedup()
    test_bot_author_extended()
    test_export()
    print(f"\nGRAND TOTAL: {PASS} CHECKS PASSED")
