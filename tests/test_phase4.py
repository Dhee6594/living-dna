"""Phase 4 tests: GitHub connector, incremental ingestion, PR intelligence,
timeline. Builds a throwaway git repo (no network), so it runs anywhere.

Run: python3 -m tests.test_phase4    (from repo root; stdlib only)
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dna.db import Genome                        # noqa: E402
from dna import genome_ops as ops                # noqa: E402
from dna import github_connector as ghc          # noqa: E402
from dna import pr_intel, timeline   # noqa: E402
from dna.ingest import ingest_repo               # noqa: E402

PASS = 0


def check(name, cond, detail=""):
    global PASS
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if cond:
        PASS += 1
    else:
        sys.exit(f"test failed: {name}")


def _git(repo, *a):
    subprocess.run(["git", "-C", str(repo)] + list(a), check=True,
                   capture_output=True)


def build_repo(path, n_commits):
    """A 2-service repo (api/, web/) with n_commits by two authors."""
    path.mkdir(parents=True)
    _git(".", "init", str(path))  # note: -C . init <path>
    _git(path, "config", "user.email", "a@x.io")
    _git(path, "config", "user.name", "Ann Dev")
    (path / "api").mkdir()
    (path / "web").mkdir()
    (path / "api" / "main.py").write_text("print('api')\n")
    (path / "web" / "app.js").write_text("console.log('web')\n")
    authors = [("Ann Dev", "a@x.io"), ("Bo Coder", "b@x.io")]
    base = time.time() - n_commits * 3600
    for i in range(n_commits):
        who = authors[i % 2]
        # Ann touches api more; Bo touches web more — asymmetric ownership.
        target = "api/main.py" if (i % 3 == 0 or who[0] == "Ann Dev") else "web/app.js"
        (path / target).write_text(f"// change {i}\n" * (i + 1))
        _git(path, "config", "user.name", who[0])
        _git(path, "config", "user.email", who[1])
        env = dict(os.environ, GIT_AUTHOR_DATE=f"{int(base + i*3600)} +0000",
                   GIT_COMMITTER_DATE=f"{int(base + i*3600)} +0000")
        subprocess.run(["git", "-C", str(path), "add", "-A"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(path), "commit", "-m", f"commit {i}"],
                       check=True, capture_output=True, env=env)


def sha(repo, ref="HEAD"):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", ref],
                          capture_output=True, text=True).stdout.strip()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "src"
        build_repo(src, 20)
        full_sha = sha(src)

        # ---- connect (initial build) at an EARLIER commit --------------------
        _git(src, "reset", "--hard", "HEAD~8")
        old_sha = sha(src)
        g = Genome(str(tmp / "g.db"))
        res = ghc.connect(g, str(src), str(tmp / "work"), repo_name="demo")
        check("connect: builds genome", res["commits"] == 12, f"{res['commits']} commits")
        check("connect: 2 services discovered",
              set(res["services"]) == {"api", "web"}, str(res["services"]))
        meta = ghc.repo_meta(g, "demo")
        check("connect: metadata stored (head_sha)", meta["head_sha"] == old_sha)
        check("connect: clone_path recorded", Path(meta["clone_path"]).exists())
        check("connect: profiles materialized", len(g.profiles_all()) == 2)

        # ---- incremental sync to the new HEAD --------------------------------
        _git(src, "reset", "--hard", full_sha)      # origin advances +8
        syn = ghc.sync_repo(g, "demo")
        check("sync: detects new commits", syn["new_commits"] == 8,
              f"{syn['new_commits']} new")
        check("sync: advances head to full", syn["head_sha"] == full_sha)
        check("sync: idempotent second run",
              ghc.sync_repo(g, "demo")["new_commits"] == 0)

        # ---- accuracy: incremental == full fresh ingest ----------------------
        g2 = Genome(str(tmp / "g2.db"))
        fresh = tmp / "fresh" / "demo"
        (tmp / "fresh").mkdir()
        subprocess.run(["git", "clone", "-q", str(src), str(fresh)], check=True)
        ingest_repo(g2, fresh, repo_name="demo")
        ops.materialize_profiles(g2)

        def knows(gg):
            return {(e["src"], e["dst"]): e["props"]["weight"]
                    for e in gg.edges_q(kind="KNOWS")}
        a, b = knows(g), knows(g2)
        maxdiff = max((abs(a.get(k, 0) - b.get(k, 0))
                       for k in set(a) | set(b)), default=0)
        check("accuracy: incremental KNOWS == full ingest (edge set)",
              set(a) == set(b), f"{len(a)} vs {len(b)} edges")
        check("accuracy: KNOWS weights match within 1e-6", maxdiff < 1e-6,
              f"maxdiff={maxdiff:.2e}")

        # bitemporal integrity: no duplicate current KNOWS edge ids
        cur = [e["id"] for e in g.edges_q(kind="KNOWS")]
        check("integrity: KNOWS edge ids unique (reconciled)",
              len(cur) == len(set(cur)), f"{len(cur)} edges")

        # ---- PR intelligence -------------------------------------------------
        pr = pr_intel.analyze(g, ["api/main.py", "docs/thing.md"], repo="demo")
        names = [x["service"] for x in pr["affected_services"]]
        check("pr: maps changed file to service", "api" in names, str(names))
        check("pr: predicts reviewers", len(pr["predicted_reviewers"]) >= 1)
        check("pr: risk band present",
              pr["architectural_risk"]["band"] in ("none", "low", "medium", "high"))
        check("pr: unmapped file surfaced",
              "docs/thing.md" in pr["unmapped_files"])

        # ---- timeline --------------------------------------------------------
        tl = timeline.timeline(g)
        types = {m["type"] for m in tl["milestones"]}
        check("timeline: has service_created milestones",
              "service_created" in types, str(types))
        check("timeline: monthly series populated", len(tl["monthly_series"]) >= 1)
        check("timeline: series has concentration_index",
              "concentration_index" in tl["monthly_series"][0])

    print(f"\nGRAND TOTAL: {PASS} CHECKS PASSED")


if __name__ == "__main__":
    main()
