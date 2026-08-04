"""The window's server: stdlib http.server, localhost only, key never logged.

One window onto one current, over a loaded corpus. `GET /` serves the page; `GET /corpus`
reports what read view is loaded; `GET /proposer` is the continuous proposer's ledger;
`POST /propose` enters a submission through the single inlet and returns the settled current
+ K's deposits; `POST /ask` compiles the question against the REAL corpus and answers from
the compiled field state; `POST /reset` clears the typed current (never the corpus). The API key is read
from the request or `OPENROUTER_API_KEY` and is never logged or written to disk. With no key
the LM source is simply absent and the page says so — every other source still flows.

Run:  OPENROUTER_API_KEY=sk-or-... python -m ui.server   (open http://127.0.0.1:8848)
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from engine.inbound import INBOUND_SYSTEM

from .current import Current, ask_the_corpus, corpus_header
from .lm import LMClient, answer, api_key, lm_available

HERE = Path(__file__).resolve().parent
INDEX = HERE / "index.html"


def _proposer_ledger() -> dict:
    """What the continuous proposer has proposed, accepted, and contradicted itself on.

    Read-only, and read off the daemon's own journal rather than any shared memory, so the
    window shows the same file the operator can `tail` — there is no second account of what
    the background process did.
    """
    from dataclasses import asdict

    from engine.continuous import CONTROL_PATH, STATUS_PATH, Control
    from engine.journal import Journal

    status_path = Path(STATUS_PATH)
    status = (json.loads(status_path.read_text(encoding="utf-8"))
              if status_path.exists() else {"note": "the continuous proposer has never run"})
    journal = Journal(Path(__file__).resolve().parents[1] / "runs" / "proposer.journal.jsonl")
    try:
        return {
            "status": status,
            "totals": journal.totals(),
            "control": asdict(Control.read(CONTROL_PATH)),
            "recent": journal.tail(25),
            "contradictions": journal.contradictions[-25:],
            "tier": "EXTRACTION only — the daemon promotes nothing and confirms nothing",
        }
    finally:
        journal.close()

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
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, INDEX.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        elif path == "/corpus":
            try:
                self._send(200, json.dumps(corpus_header()))
            except Exception as exc:
                self._send(200, json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        elif path == "/proposer":
            try:
                self._send(200, json.dumps(_proposer_ledger()))
            except Exception as exc:
                self._send(200, json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
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
            elif path == "/proposer/control":
                # The operator's hand on the background process: rate, pause, stop, cost cap.
                # It writes the control file the daemon re-reads; it cannot promote anything,
                # because there is nothing in the daemon that promotes.
                from engine.continuous import CONTROL_PATH, Control

                ctl = Control.read(CONTROL_PATH)
                for field in ("calls_per_hour", "batch"):
                    if field in b:
                        setattr(ctl, field, max(0, int(b[field])))
                for field in ("paused", "stop"):
                    if field in b:
                        setattr(ctl, field, bool(b[field]))
                if "max_cost" in b:
                    ctl.max_cost = None if b["max_cost"] in (None, "") else float(b["max_cost"])
                ctl.write(CONTROL_PATH)
                self._send(200, json.dumps(_proposer_ledger()))
            elif path == "/ask":
                question = str(b.get("question", ""))
                compiled = ask_the_corpus(question, str(b.get("chart", "english")))
                if compiled["conditioned"]:
                    # The field supplied the content; the typed text was the boundary
                    # condition. The system prompt is the inbound one, not the window's.
                    system, grounded_on = INBOUND_SYSTEM, compiled["compiled"]
                else:
                    # Nothing landed. Fall back to the typed current's own facts and SAY so —
                    # a near-passthrough reported as one is honest; one reported as a
                    # corpus-grounded answer is not.
                    state = CURRENT.state(lm_used=lm_available(key))
                    system, grounded_on = INBOUND_SYSTEM, (
                        compiled["compiled"] + "\n\nTYPED CURRENT (not the corpus):\n"
                        + _engine_facts(state, term=question))
                if lm_available(key):
                    client = LMClient(key)
                    reply = client.complete(system, grounded_on,
                                            float(b.get("temperature", 0.2)), 1200).strip()
                else:
                    reply = ("(no key — the LM is not answering. What it would have received "
                             "is below, compiled from the field.)")
                self._send(200, json.dumps({
                    "answer": reply, "grounded_on": grounded_on,
                    "lm_available": lm_available(key), "compiled": compiled,
                    "corpus_header": corpus_header()}))
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
