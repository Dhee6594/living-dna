"""Identity resolution v0 (ENTERPRISE-ROADMAP Stage 0 addition).

Real repos contain the same human under several git identities
("Lena Kovacs <lena@acme.io>" vs "lena kovacs <lena@gmail.com>" vs
"12345+lena@users.noreply.github.com"). Left unmerged, KNOWS weights split
across phantom people and bus-factor results understate concentration risk.

v0 = two conservative heuristics + one explicit override file:

  A. exact full-name match (case-insensitive, >= 2 tokens — single tokens
     like "sai" are too ambiguous to merge on name alone)
  B. GitHub noreply addresses ("<id>+<user>@users.noreply.github.com")
     merge with any identity whose email local-part equals <user>

  Overrides: <repo>/.dna/identities.json
     {"aliases": {"old@host": "canonical@host", ...}}
  Overrides always win and are applied first.

Bots are never merged. The canonical identity of a merged group is the one
with the most commits. `.mailmap` support is tracked for Phase 2.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

GH_NOREPLY = re.compile(r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", re.I)


def load_overrides(repo_root) -> dict:
    p = Path(repo_root) / ".dna" / "identities.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        return {k.lower(): v for k, v in data.get("aliases", {}).items()}
    except (OSError, json.JSONDecodeError):
        return {}


def _norm_name(name: str) -> str:
    return " ".join(name.lower().split())


def resolve_identities(commits, repo_root=None):
    """Return {email_lower: (canonical_email, canonical_name)} for merged ids.

    `commits`: iterable of dicts with author/email/bot keys (ingest format).
    Identities not needing a merge are absent from the map.
    """
    overrides = load_overrides(repo_root) if repo_root else {}

    # Tally identities (skip bots entirely)
    count = Counter()
    name_of = {}
    for c in commits:
        if c.get("bot"):
            continue
        em = c["email"].lower()
        count[em] += 1
        name_of.setdefault(em, c["author"])

    # Union-find over emails
    parent = {em: em for em in count}
    for em in overrides:
        parent.setdefault(em, em)
        parent.setdefault(overrides[em].lower(), overrides[em].lower())

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Overrides first (always win)
    for alias, canon in overrides.items():
        union(alias, canon.lower())

    # Heuristic A: exact multi-token name match
    by_name = defaultdict(list)
    for em in count:
        n = _norm_name(name_of.get(em, ""))
        if len(n.split()) >= 2:
            by_name[n].append(em)
    for ems in by_name.values():
        for other in ems[1:]:
            union(ems[0], other)

    # Heuristic B: GitHub noreply <-> matching local-part
    local = defaultdict(list)
    for em in count:
        local[em.split("@", 1)[0].lower()].append(em)
    for em in count:
        m = GH_NOREPLY.match(em)
        if m:
            for other in local.get(m.group(1).lower(), []):
                if other != em:
                    union(em, other)

    # Canonical member of each group = most commits (ties: lexicographic)
    groups = defaultdict(list)
    for em in parent:
        groups[find(em)].append(em)

    alias_map = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        canon = sorted(members, key=lambda e: (-count.get(e, 0), e))[0]
        cname = name_of.get(canon) or next(
            (name_of[m] for m in members if m in name_of), canon)
        for m in members:
            if m != canon:
                alias_map[m] = (canon, cname)
    return alias_map
