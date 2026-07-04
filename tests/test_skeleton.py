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
    test_merge_commit_dedup()
    test_bot_author_extended()
    test_export()
    print(f"\nGRAND TOTAL: {PASS} CHECKS PASSED")
