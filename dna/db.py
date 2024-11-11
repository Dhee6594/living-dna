"""Bitemporal mini-graph on SQLite.

Every node and edge carries:
  valid_from / valid_to  -> when the fact was true in the world (world time)
  recorded_at            -> when the genome learned it (knowledge time)
  confidence             -> 0..1
  provenance             -> JSON list of source artifact refs (commit hashes, file paths)

Updates never overwrite: we close valid_to and insert a successor row.
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
  row_id      INTEGER PRIMARY KEY,
  id          TEXT NOT NULL,            -- stable entity id (e.g. svc:payments)
  kind        TEXT NOT NULL,            -- Service|Person|Module|Era|Decision|Risk|Repo
  name        TEXT NOT NULL,
  props       TEXT NOT NULL DEFAULT '{}',
  valid_from  REAL NOT NULL,
  valid_to    REAL,                     -- NULL = currently true
  recorded_at REAL NOT NULL,
  confidence  REAL NOT NULL DEFAULT 1.0,
  provenance  TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_nodes_id ON nodes(id);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);

CREATE TABLE IF NOT EXISTS edges (
  row_id      INTEGER PRIMARY KEY,
  id          TEXT NOT NULL,
  kind        TEXT NOT NULL,            -- DEPENDS_ON|KNOWS|AUTHORED|MEMBER_OF|HAS_ERA|JUSTIFIES
  src         TEXT NOT NULL,
  dst         TEXT NOT NULL,
  props       TEXT NOT NULL DEFAULT '{}',
  valid_from  REAL NOT NULL,
  valid_to    REAL,
  recorded_at REAL NOT NULL,
  confidence  REAL NOT NULL DEFAULT 1.0,
  provenance  TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);

CREATE TABLE IF NOT EXISTS events (                 -- canonical event log (append-only)
  row_id      INTEGER PRIMARY KEY,
  event_id    TEXT UNIQUE NOT NULL,
  kind        TEXT NOT NULL,            -- code.commit | code.pr | genome.correction ...
  occurred_at REAL NOT NULL,
  ingested_at REAL NOT NULL,
  actors      TEXT NOT NULL DEFAULT '[]',
  subjects    TEXT NOT NULL DEFAULT '[]',
  payload     TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_at ON events(occurred_at);

CREATE TABLE IF NOT EXISTS profiles (               -- materialized DNA profiles
  entity_id   TEXT PRIMARY KEY,
  json        TEXT NOT NULL,
  updated_at  REAL NOT NULL
);
"""


class Genome:
    def __init__(self, path: str = ".dna/genome.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ----------------------------------------------------------- write path
    def upsert_node(self, id, kind, name, props=None, valid_from=None,
                    confidence=1.0, provenance=None):
        """Insert a new version of a node; closes the previous current version
        only if props actually changed (idempotent re-ingestion)."""
        now = time.time()
        valid_from = valid_from if valid_from is not None else now
        props_j = json.dumps(props or {}, sort_keys=True)
        cur = self.conn.execute(
            "SELECT row_id, props FROM nodes WHERE id=? AND valid_to IS NULL", (id,))
        row = cur.fetchone()
        if row:
            if row["props"] == props_j:
                return id  # unchanged
            self.conn.execute("UPDATE nodes SET valid_to=? WHERE row_id=?",
                              (valid_from, row["row_id"]))
        self.conn.execute(
            "INSERT INTO nodes(id,kind,name,props,valid_from,valid_to,recorded_at,confidence,provenance)"
            " VALUES(?,?,?,?,?,NULL,?,?,?)",
            (id, kind, name, props_j, valid_from, now, confidence,
             json.dumps(provenance or [])))
        return id

    def upsert_edge(self, kind, src, dst, props=None, valid_from=None,
                    confidence=1.0, provenance=None, edge_id=None):
        now = time.time()
        valid_from = valid_from if valid_from is not None else now
        edge_id = edge_id or f"{kind}:{src}->{dst}"
        props_j = json.dumps(props or {}, sort_keys=True)
        cur = self.conn.execute(
            "SELECT row_id, props FROM edges WHERE id=? AND valid_to IS NULL", (edge_id,))
        row = cur.fetchone()
        if row:
            if row["props"] == props_j:
                return edge_id
            self.conn.execute("UPDATE edges SET valid_to=? WHERE row_id=?",
                              (valid_from, row["row_id"]))
        self.conn.execute(
            "INSERT INTO edges(id,kind,src,dst,props,valid_from,valid_to,recorded_at,confidence,provenance)"
            " VALUES(?,?,?,?,?,?,NULL,?,?,?)",
            (edge_id, kind, src, dst, props_j, valid_from, now, confidence,
             json.dumps(provenance or [])))
        return edge_id

    def close_edge(self, edge_id, at=None):
        self.conn.execute(
            "UPDATE edges SET valid_to=? WHERE id=? AND valid_to IS NULL",
            (at or time.time(), edge_id))

    def record_event(self, kind, occurred_at, actors=None, subjects=None,
                     payload=None, event_id=None):
        event_id = event_id or str(uuid.uuid4())
        try:
            self.conn.execute(
                "INSERT INTO events(event_id,kind,occurred_at,ingested_at,actors,subjects,payload)"
                " VALUES(?,?,?,?,?,?,?)",
                (event_id, kind, occurred_at, time.time(),
                 json.dumps(actors or []), json.dumps(subjects or []),
                 json.dumps(payload or {})))
        except sqlite3.IntegrityError:
            pass  # idempotent
        return event_id

    def save_profile(self, entity_id, profile: dict):
        self.conn.execute(
            "INSERT INTO profiles(entity_id,json,updated_at) VALUES(?,?,?)"
            " ON CONFLICT(entity_id) DO UPDATE SET json=excluded.json, updated_at=excluded.updated_at",
            (entity_id, json.dumps(profile), time.time()))

    def commit(self):
        self.conn.commit()

    # ----------------------------------------------------------- read path
    @staticmethod
    def _at_clause(at):
        if at is None:
            return "valid_to IS NULL", ()
        return "valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)", (at, at)

    def nodes(self, kind=None, at=None):
        clause, params = self._at_clause(at)
        q = f"SELECT * FROM nodes WHERE {clause}"
        if kind:
            q += " AND kind=?"
            params = params + (kind,)
        return [self._row(r) for r in self.conn.execute(q, params)]

    def node(self, id, at=None):
        clause, params = self._at_clause(at)
        r = self.conn.execute(
            f"SELECT * FROM nodes WHERE id=? AND {clause}", (id,) + params).fetchone()
        return self._row(r) if r else None

    def edges_q(self, kind=None, src=None, dst=None, at=None):
        clause, params = self._at_clause(at)
        q = f"SELECT * FROM edges WHERE {clause}"
        for col, val in (("kind", kind), ("src", src), ("dst", dst)):
            if val:
                q += f" AND {col}=?"
                params = params + (val,)
        return [self._row(r) for r in self.conn.execute(q, params)]

    def node_history(self, id):
        return [self._row(r) for r in self.conn.execute(
            "SELECT * FROM nodes WHERE id=? ORDER BY valid_from", (id,))]

    def events_q(self, kind=None, subject=None, since=None, until=None, limit=10000):
        q, params = "SELECT * FROM events WHERE 1=1", ()
        if kind:
            q += " AND kind LIKE ?"; params += (kind + "%",)
        if since:
            q += " AND occurred_at >= ?"; params += (since,)
        if until:
            q += " AND occurred_at <= ?"; params += (until,)
        q += " ORDER BY occurred_at LIMIT ?"; params += (limit,)
        rows = [dict(r) for r in self.conn.execute(q, params)]
        for r in rows:
            for k in ("actors", "subjects", "payload"):
                r[k] = json.loads(r[k])
        if subject:
            rows = [r for r in rows if subject in r["subjects"]]
        return rows

    def profile(self, entity_id):
        r = self.conn.execute(
            "SELECT json FROM profiles WHERE entity_id=?", (entity_id,)).fetchone()
        return json.loads(r["json"]) if r else None

    def profiles_all(self):
        return [json.loads(r["json"]) for r in
                self.conn.execute("SELECT json FROM profiles")]

    @staticmethod
    def _row(r):
        d = dict(r)
        d["props"] = json.loads(d["props"])
        d["provenance"] = json.loads(d["provenance"])
        return d
