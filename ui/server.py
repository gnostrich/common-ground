"""The window's server: stdlib http.server, localhost only, key never logged.

One window onto one current. `GET /` serves the page; `POST /propose` enters a submission
through the single inlet and returns the settled current + K's deposits; `POST /ask` answers
grounded on the engine's actual state; `POST /reset` clears the current. The API key is read
from the request or `OPENROUTER_API_KEY` and is never logged or written to disk. With no key
the LM source is simply absent and the page says so — every other source still flows.

Run:  OPENROUTER_API_KEY=sk-or-... python -m ui.server   (open http://127.0.0.1:8848)
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .current import Current
from .lm import LMClient, answer, api_key, lm_available

HERE = Path(__file__).resolve().parent
INDEX = HERE / "index.html"

# One localhost user, one current. Module-level, so the window accumulates as you type.
CURRENT = Current()


def _engine_facts(state: dict, term: str = "") -> str:
    """A compact, authoritative digest of the current for grounding an /ask answer."""
    eng = state["engine"]
    lines = [f"charts: {eng['by_chart']}", f"contested blocks: {len(eng['contested'])}"]
    for a in eng["arms"]:
        lines.append(f"beta={a['beta']} floor={a['mean_floor']:.8f} q95={a['q95']:.8f}")
    slots = eng["slots"]
    if term:
        slots = [s for s in slots if term.casefold() in s["nu"].casefold()]
    for s in slots[:20]:
        lines.append(f"[{s['chart']}] {s['value']} :: {s['nu'][:70]}")
    lines.append(f"K promotions: {sum(1 for p in state['promotions'] if p['promoted'])} "
                 f"promoted, corpus size {len(state['corpus'])}")
    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):
    server_version = "common-ground-window/1"

    def log_message(self, fmt, *args):
        # Never echo request bodies or headers (which could carry the key). Method+path only.
        try:
            print(f"[window] {self.command} {self.path.split('?')[0]}")
        except Exception:
            pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path.split("?")[0] in ("/", "/index.html"):
            self._send(200, INDEX.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = self.path.split("?")[0]
        b = self._body()
        key = api_key(b.get("key"))          # request key or env; never logged
        try:
            if path == "/propose":
                state = CURRENT.propose_text(
                    text=str(b.get("text", "")),
                    chart=str(b.get("chart", "english")),
                    temperature=float(b.get("temperature", 0.3)),
                    key=key or None,
                    instance_id=(b.get("instance_id") or None),
                )
                self._send(200, json.dumps(state))
            elif path == "/reset":
                CURRENT.reset()
                self._send(200, json.dumps({"ok": True}))
            elif path == "/ask":
                question = str(b.get("question", ""))
                state = CURRENT.state(lm_used=lm_available(key))
                facts = _engine_facts(state, term=question)
                if lm_available(key):
                    reply = answer(LMClient(key), question, facts, float(b.get("temperature", 0.2)))
                else:
                    reply = ("(no key — the LM is not answering. Here are the engine facts the "
                             "answer would be grounded on.)")
                self._send(200, json.dumps({"answer": reply, "grounded_on": facts,
                                            "lm_available": lm_available(key)}))
            else:
                self._send(404, json.dumps({"error": "not found"}))
        except Exception as exc:   # keep the window alive; surface the error in the panel
            self._send(200, json.dumps({"error": f"{type(exc).__name__}: {exc}"}))


def serve(host: str | None = None, port: int | None = None) -> None:
    """Serve the window. Localhost by default; binds 0.0.0.0 only when a platform sets $PORT
    (Railway/Heroku/etc.) or COMMON_GROUND_BIND_ALL=1 is set explicitly — so a laptop run
    stays local while a deploy is reachable. LM-omitted unless OPENROUTER_API_KEY is set.
    """
    deploy = bool(os.environ.get("PORT") or os.environ.get("COMMON_GROUND_BIND_ALL"))
    host = host or ("0.0.0.0" if deploy else "127.0.0.1")
    port = port or int(os.environ.get("PORT", 8848))
    if host not in ("127.0.0.1", "localhost", "::1", "0.0.0.0") and not deploy:
        raise SystemExit("refusing to bind a non-localhost host; set COMMON_GROUND_BIND_ALL=1 "
                         "or $PORT to deploy")
    have = "yes" if os.environ.get("OPENROUTER_API_KEY") else "no — LM source omitted, engine runs live"
    print(f"common-ground window on http://{host}:{port}  (OPENROUTER_API_KEY set: {have})")
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
