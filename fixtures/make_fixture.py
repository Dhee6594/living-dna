#!/usr/bin/env python3
"""Generate the synthetic demo organization: a git repo with 2.5 years of
scripted history — services born at different times, multiple engineers,
a dependency added mid-life, a departure-shaped knowledge concentration.

Usage: python3 fixtures/make_fixture.py [target_dir]
"""
import os
import subprocess
import sys
import time
from pathlib import Path

TARGET = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures/acme-shop")

PEOPLE = {
    "lena":   ("Lena Kovacs", "lena@acme.test"),
    "marcus": ("Marcus Webb", "marcus@acme.test"),
    "aisha":  ("Aisha Rahman", "aisha@acme.test"),
    "jin":    ("Jin Park", "jin@acme.test"),
    "bot":    ("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.test"),
}

DAY = 86400
T0 = time.time() - int(2.5 * 365) * DAY  # ~2.5 years ago


def run(*args, env=None):
    subprocess.run(args, cwd=TARGET, check=True, capture_output=True, env=env)


def commit(author, msg, day, files):
    name, email = PEOPLE[author]
    ts = int(T0 + day * DAY)
    for rel, content in files.items():
        p = TARGET / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if content.startswith("+") else "w"
        with open(p, mode) as f:
            f.write(content.lstrip("+"))
    env = dict(os.environ,
               GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email,
               GIT_AUTHOR_DATE=f"{ts} +0000", GIT_COMMITTER_DATE=f"{ts} +0000")
    run("git", "add", "-A", env=env)
    run("git", "commit", "-m", msg, "--allow-empty", env=env)


def main():
    if TARGET.exists():
        import shutil; shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)
    run("git", "init", "-q", "-b", "main")

    # --- era 1: the monolith days (auth + catalog born) -------------------
    commit("lena", "Initial platform skeleton", 0,
           {"README.md": "# acme-shop\n", "services/auth/pyproject.toml": "[project]\nname='auth'\n",
            "services/auth/main.py": "def login(): pass\n"})
    commit("lena", "PAY-1 Auth: session tokens", 4,
           {"services/auth/main.py": "+def session_token(): pass\n"})
    commit("marcus", "Catalog service bootstrap (REQ-12 product browsing)", 9,
           {"services/catalog/pyproject.toml": "[project]\nname='catalog'\n",
            "services/catalog/main.py": "PRODUCTS = []\n"})
    for d in range(14, 70, 7):
        commit("marcus", f"Catalog: search improvements day{d}", d,
               {"services/catalog/main.py": f"+# search tweak {d}\n"})
        commit("lena", f"Auth: hardening day{d}", d + 1,
               {"services/auth/main.py": f"+# hardening {d}\n"})

    # --- era 2: payments is born, depends on auth --------------------------
    commit("lena", "PAY-45 Extract payments service (strangler, not rewrite)", 120,
           {"services/payments/pyproject.toml": "[project]\nname='payments'\n",
            "services/payments/main.py": "import auth\n\ndef charge(): pass\n",
            "services/payments/dna-deps.txt": "auth\n"})
    commit("lena", "PAY-51 Payments: idempotent retries after double-charge INC-310", 133,
           {"services/payments/main.py": "+IDEMPOTENT = True  # never retry blind: INC-310\n"})
    for d in range(140, 260, 9):
        commit("lena", f"Payments: gateway integration work day{d}", d,
               {"services/payments/main.py": f"+# gw {d}\n"})
    commit("jin", "Payments: observability hooks", 200,
           {"services/payments/main.py": "+METRICS = True\n"})

    # --- era 3: checkout born, depends on payments+catalog; aisha joins ----
    commit("aisha", "REQ-88 Checkout service: unified cart flow", 300,
           {"services/checkout/pyproject.toml": "[project]\nname='checkout'\n",
            "services/checkout/main.py": "import payments\nimport catalog\n",
            "services/checkout/dna-deps.txt": "payments\ncatalog\n"})
    for d in range(305, 420, 8):
        commit("aisha", f"Checkout: flow polish day{d}", d,
               {"services/checkout/main.py": f"+# flow {d}\n"})
    commit("jin", "INC-401 postmortem: checkout retries hammered payments — add backoff", 430,
           {"services/checkout/main.py": "+BACKOFF = 'exponential'  # INC-401\n"})

    # --- era 4: notifications; lena concentrates payments knowledge --------
    commit("jin", "Notifications service for order emails (REQ-130)", 520,
           {"services/notifications/pyproject.toml": "[project]\nname='notifications'\n",
            "services/notifications/main.py": "import checkout\n",
            "services/notifications/dna-deps.txt": "checkout\n"})
    for d in range(540, 760, 11):
        commit("lena", f"Payments: PCI compliance pass day{d}", d,
               {"services/payments/main.py": f"+# pci {d}\n"})
    for d in range(560, 740, 17):
        commit("aisha", f"Checkout: AB-test variants day{d}", d,
               {"services/checkout/main.py": f"+# ab {d}\n"})
    commit("marcus", "Catalog: vector search migration", 700,
           {"services/catalog/main.py": "+VECTORS = True\n"})
    commit("jin", "Notifications: digest batching", 720,
           {"services/notifications/main.py": "+BATCH = True\n"})

    # --- messy reality: bot churn, a rename, vendored noise, a plugin dir ---
    for d in range(600, 760, 25):
        commit("bot", f"Bump lodash from 4.{d}.0 to 4.{d}.1", d,
               {"services/payments/package-lock.json": f"+lock {d}\n",
                "services/payments/main.py": f"+# bump compat {d}\n"})
    commit("marcus", "Vendor: import generated client", 730,
           {"services/catalog/vendor/genclient.py": "# generated, 10k lines\n" * 50})
    name, email = PEOPLE["aisha"]
    env = dict(os.environ,
               GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email,
               GIT_AUTHOR_DATE=f"{int(T0 + 740 * DAY)} +0000",
               GIT_COMMITTER_DATE=f"{int(T0 + 740 * DAY)} +0000")
    run("git", "mv", "services/checkout/main.py", "services/checkout/core.py", env=env)
    run("git", "commit", "-m", "Checkout: rename main.py -> core.py", env=env)
    commit("jin", "Add reporting plugin (Claude-plugin style manifest)", 750,
           {"plugins/reporting/.claude-plugin/plugin.json": '{"name":"reporting"}\n',
            "plugins/reporting/skills/report.md": "# reporting skill\n"})

    n = subprocess.run(["git", "-C", str(TARGET), "rev-list", "--count", "HEAD"],
                       capture_output=True, text=True).stdout.strip()
    print(f"fixture ready: {TARGET} ({n} commits, 6 services, 4 humans + 1 bot)")


if __name__ == "__main__":
    main()
