#!/usr/bin/env bash
# Living DNA — one-command demo.
# Generates a synthetic engineering org (5 services, 4 engineers, 2.5 years of
# history), sequences it into a genome, prints headline insights, and starts
# the Genome Browser. Zero dependencies beyond Python 3.10+ and git.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=${PYTHON:-python3}
DB=".dna/demo-genome.db"

command -v git >/dev/null || { echo "git is required"; exit 1; }
$PY -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
  || { echo "Python 3.10+ required (found $($PY --version))"; exit 1; }

echo "🧬 1/3 Generating demo org (fixtures/acme-shop)…"
rm -f "$DB" 2>/dev/null || true
if [ ! -d fixtures/acme-shop ]; then
  $PY fixtures/make_fixture.py >/dev/null
else
  echo "   (reusing existing fixture)"
fi

echo "🧬 2/3 Sequencing into a genome…"
$PY -m dna.cli --db "$DB" ingest fixtures/acme-shop >/dev/null

echo "🧬 3/3 Headline insights:"
$PY - "$DB" <<'EOF'
import json, sys
from dna.db import Genome
from dna.insights import insights
doc = insights(Genome(sys.argv[1]))
o = doc["overview"]
print(f"   {o['services']} services · maintainability {o['maintainability_score']}/100 "
      f"· complexity {o['complexity_score']}/100")
for s in doc["knowledge_intelligence"]["knowledge_silos"][:2]:
    print(f"   ⚠ silo: {s['holder']} holds {int(s['share']*100)}% of {s['service']}")
for r in doc["recommendations"][:3]:
    print(f"   → {r['action']}")
EOF

echo
echo "Try:  python3 -m dna.cli --db $DB ask 'who knows payments'"
echo "      python3 -m dna.cli --db $DB ask 'what happens if Lena leaves'"
echo
echo "Opening the Genome Browser at http://127.0.0.1:8077  (Ctrl-C to stop)"
exec $PY -m dna.cli --db "$DB" serve
