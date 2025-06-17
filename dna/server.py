"""Genome Browser API + UI server. Pure stdlib (http.server)."""
import datetime as dt
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .db import Genome
from . import genome_ops as ops

WEB = Path(__file__).parent.parent / "web"


def parse_when(s):
    if not s or s == "now":
        return None
    return dt.datetime.strptime(s, "%Y-%m-%d").replace(
        tzinfo=dt.timezone.utc).timestamp()


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj, indent=1).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            g = Genome(db_path)
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            p = u.path
            try:
                if p == "/" or p == "/index.html":
                    body = (WEB / "index.html").read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif p == "/api/profiles":
                    self._json(g.profiles_all())
                elif p.startswith("/api/profile/"):
                    prof = g.profile("svc:" + p.rsplit("/", 1)[1])
                    self._json(prof or {"error": "not found"},
                               200 if prof else 404)
                elif p == "/api/graph":
                    self._json(ops.graph_at(g, parse_when(qs.get("at", [None])[0])))
                elif p == "/api/diff":
                    self._json(ops.diff(g, parse_when(qs["from"][0]),
                                        parse_when(qs["to"][0]) or 9e12))
                elif p == "/api/busfactor":
                    who = qs.get("person", [None])[0]
                    if who:
                        people = [x for x in g.nodes(kind="Person")
                                  if who.lower() in x["name"].lower()
                                  or who.lower() in x["props"].get("email", "")]
                        self._json(ops.bus_factor(g, people[0]["id"])
                                   if people else {"error": f"no person '{who}'"})
                    else:
                        self._json(ops.org_bus_factor(g))
                elif p == "/api/ask":
                    self._json(ops.ask(g, qs.get("q", [""])[0]))
                elif p == "/api/people":
                    self._json([{"id": n["id"], "name": n["name"]}
                                for n in g.nodes(kind="Person")])
                elif p == "/api/decisions":
                    self._json([{"id": n["id"], "statement": n["props"].get("statement"),
                                 "rationale": n["props"].get("rationale"),
                                 "confidence": n["confidence"],
                                 "provenance": n["provenance"]}
                                for n in g.nodes(kind="Decision")])
                else:
                    self._json({"error": "not found"}, 404)
            except Exception as exc:  # noqa: BLE001 — v0 surface
                self._json({"error": str(exc)}, 500)
            finally:
                g.conn.close()

    return Handler


def serve(db_path=".dna/genome.db", port=8077):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), make_handler(db_path))
    print(f"Genome Browser: http://localhost:{port}  (db: {db_path})")
    httpd.serve_forever()
