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
                    self._json(ops.diff(g, parse_when(qs.get("from", ["now"])[0]),
                                        parse_when(qs.get("to", ["now"])[0])))
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
                elif p == "/api/report":
                    self._json(ops.quality_report(g))
                elif p == "/api/insights":
                    from . import insights as ins
                    self._json(ins.insights(g))
                elif p == "/api/repos":
                    from . import github_connector as ghc
                    self._json(ghc.list_repos(g))
                elif p == "/api/timeline":
                    from . import timeline as tl
                    self._json(tl.timeline(g, repo=qs.get("repo", [None])[0]))
                elif p == "/api/search":
                    q = qs.get("q", [""])[0].lower()
                    if not q:
                        self._json([])
                    else:
                        hits = [{"id": n["id"], "kind": n["kind"],
                                 "name": n["name"]}
                                for n in g.nodes()
                                if q in n["name"].lower() or q in n["id"].lower()]
                        self._json(hits[:50])
                elif p == "/api/events":
                    svc = qs.get("service", [None])[0]
                    kind = qs.get("kind", ["code."])[0]
                    limit = int(qs.get("limit", ["200"])[0])
                    evs = g.events_q(kind=kind,
                                     subject=f"svc:{svc}" if svc else None)
                    self._json(evs[-limit:])
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

        def do_POST(self):
            g = Genome(db_path)
            u = urllib.parse.urlparse(self.path)
            length = int(self.headers.get("Content-Length", 0) or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, TypeError):
                body = {}
            workdir = str(Path(db_path).parent / "repos")
            try:
                if u.path == "/api/connect":
                    from . import github_connector as ghc
                    self._json(ghc.connect(
                        g, body["url"], workdir, token=body.get("token"),
                        branch=body.get("branch"), repo_name=body.get("name")))
                elif u.path == "/api/sync":
                    from . import github_connector as ghc
                    self._json(ghc.sync_repo(g, body["repo"], token=body.get("token")))
                elif u.path == "/api/pr":
                    from . import pr_intel
                    if body.get("files"):
                        files = body["files"]
                    else:
                        meta = _repo_meta(g, body.get("repo"))
                        files = (pr_intel.diff_files(meta["clone_path"], body["base"],
                                                     body.get("head", "HEAD"))
                                 if meta else [])
                    self._json(pr_intel.analyze(g, files, repo=body.get("repo")))
                else:
                    self._json({"error": "not found"}, 404)
            except Exception as exc:  # noqa: BLE001 — v0 surface
                self._json({"error": str(exc)}, 500)
            finally:
                g.conn.close()

    return Handler


def _repo_meta(g, name):
    from . import github_connector as ghc
    return ghc.repo_meta(g, name) if name else None


def serve(db_path=".dna/genome.db", port=8077, host="127.0.0.1"):
    # Default to loopback: the genome contains person-level knowledge data and
    # this v0 server has no auth. Use --host 0.0.0.0 to expose deliberately.
    httpd = ThreadingHTTPServer((host, port), make_handler(db_path))
    print(f"Genome Browser: http://{host}:{port}  (db: {db_path})")
    httpd.serve_forever()
