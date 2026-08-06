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
import time
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from engine.export_sheet import sheet
from engine.grounded import check_answer
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


#: When set, every request must carry this token. Unset on a laptop; REQUIRED for a deploy,
#: enforced in `serve()` below rather than left to whoever runs it. The literal string
#: `none` is the deliberate opt-out — spelling it is an act, forgetting the variable is not.
_RAW_TOKEN = os.environ.get("COMMON_GROUND_TOKEN", "").strip()
OPEN_ON_PURPOSE = _RAW_TOKEN == "none"
ACCESS_TOKEN = "" if OPEN_ON_PURPOSE else _RAW_TOKEN

#: Paths served without a token. Only the page shell, which holds no corpus and spends
#: nothing — everything it then asks for is gated.
OPEN_PATHS = frozenset({"/", "/index.html", "/healthz"})


def _authorized(path: str, raw_path: str, headers) -> bool:
    """Two things are behind this gate, and the second is the one that costs money.

    The corpus is somebody's private material. But `/ask` and `/propose` call OpenRouter with
    the SERVER's key, so an open deploy is not merely a disclosure — it is an unmetered spend
    against the operator's account by anyone who has the URL. A deploy therefore refuses to
    start without a token (see `serve`), rather than trusting the deployer to remember.
    """
    if not ACCESS_TOKEN or path in OPEN_PATHS:
        return True
    from urllib.parse import parse_qs, urlparse

    supplied = (parse_qs(urlparse(raw_path).query).get("t") or [""])[0]
    if not supplied:
        cookie = headers.get("Cookie") or ""
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "cg_t":
                supplied = value
                break
    if not supplied:
        supplied = (headers.get("X-Common-Ground-Token") or "").strip()
    # Constant-time: a token checked with `==` leaks its prefix to a patient caller.
    import hmac

    return hmac.compare_digest(supplied, ACCESS_TOKEN)


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

    def _gate(self, path: str) -> bool:
        if _authorized(path, self.path, self.headers):
            return True
        self._send(401, json.dumps({
            "error": "this window is token-gated",
            "how": "open the URL with ?t=<token> once; the page stores it for the session.",
            "why": ("/ask and /propose spend the operator's OpenRouter credits and read a "
                    "private corpus, so an ungated deploy is an open tab on both."),
        }))
        return False

    def do_GET(self):
        path = self.path.split("?")[0]
        if not self._gate(path):
            return
        if path == "/healthz":
            self._send(200, json.dumps({"ok": True, "gated": bool(ACCESS_TOKEN)}))
        elif path in ("/", "/index.html"):
            body = INDEX.read_text(encoding="utf-8")
            self._send(200, body, "text/html; charset=utf-8")
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
        if not self._gate(path):
            return
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
                # PHASES ARE RECORDED, NOT STREAMED — and that is a retreat, recorded as one.
                # Streaming NDJSON worked under curl and HUNG THE BROWSER: the handler speaks
                # HTTP/1.0 with no Content-Length, so the response is close-delimited, and
                # behind a keep-alive proxy `fetch().body.getReader()` never sees `done`. The
                # operator waited five minutes on a request that completed in twenty-four
                # seconds. A progress channel that can hang the thing it reports on is worse
                # than no progress channel, so this is buffered again until chunked framing is
                # done properly and verified in a browser rather than in curl.
                phases: list[dict] = []

                def _phase(name: str) -> None:
                    phases.append({"stage": name, "at": round(time.time() - _t_req, 3)})

                _t_req = time.time()
                compiled = ask_the_corpus(question, str(b.get("chart", "english")), key=key,
                                          on_stage=_phase)
                # No branch on whether anything "landed". The compiled input already IS
                # the field's response — the moved region with the declared path to each
                # moved slot, or an explicit statement that nothing moved and why. There is
                # nothing to fall back TO: the empty typed current that used to be stapled
                # on here reported `charts: {}` and `corpus size 0`, which read as a fact
                # about the corpus and was a fact about an unrelated object.
                system, grounded_on = INBOUND_SYSTEM, compiled["compiled"]
                _phase("answering")
                if lm_available(key):
                    client = LMClient(key)
                    reply = client.complete(system, grounded_on,
                                            float(b.get("temperature", 0.2)), 1200).strip()
                else:
                    reply = ("(no key — the LM is not answering. What it would have received "
                             "is below, compiled from the field.)")
                # THE GATE THAT PUTS THE ANSWER FIRST. Checked here, on the way out, so the
                # verdict travels with the prose it judges and the page cannot show one
                # without the other. Green licenses the answer-first hierarchy; a violation
                # is displayed ON the answer, not filed in the scope.
                _phase("checking")
                verdict = check_answer(reply, compiled).as_record()
                self._send(200, json.dumps({
                    "answer": reply, "grounded_on": grounded_on, "faithful": verdict,
                    # THE PORTABLE SHEET. A VIEW over the record this request already made —
                    # it is returned WITH the answer rather than behind a second endpoint, so
                    # exporting cannot re-run a perturbation or produce a sheet describing a
                    # different one than the operator is looking at.
                    "sheet": sheet(compiled),
                    "lm_available": lm_available(key), "compiled": compiled,
                    "phases": phases, "corpus_header": corpus_header()}))
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
    if deploy and not ACCESS_TOKEN and not OPEN_ON_PURPOSE:
        # Refused here rather than warned about, because the thing being protected is not
        # only a private corpus: /ask and /propose spend the operator's OpenRouter credits,
        # and an ungated public URL is an unmetered charge against their account. A deployer
        # who forgets gets a service that will not start, which is recoverable; the other
        # way round is not.
        raise SystemExit(
            "refusing to serve a reachable window with no COMMON_GROUND_TOKEN.\n"
            "This binds 0.0.0.0 and serves a loaded corpus, and /ask spends the operator's\n"
            "OpenRouter credits on every request. Set COMMON_GROUND_TOKEN to a secret and\n"
            "open the URL once with ?t=<that secret>. To run wide open on purpose, set\n"
            "COMMON_GROUND_TOKEN to the literal string 'none'.")
    have = "yes" if os.environ.get("OPENROUTER_API_KEY") else "no — LM source omitted, engine runs live"
    print(f"common-ground window on http://{host}:{port}  (OPENROUTER_API_KEY set: {have})")

    # A deploy carries its state in the image and reads it from a volume; seeding is
    # copy-if-absent, so a redeploy never rolls the live journal back to upload time.
    from .boot import seed_state, start_proposer_if_asked

    if deploy:
        print(f"[boot] state: {seed_state()}", flush=True)
    if start_proposer_if_asked() is not None:
        print("[boot] continuous proposer running in-process; pause/stop/rate/cap in the "
              "window control it exactly as they control a local one.", flush=True)

    # THREADED, and the reason is not throughput. `/ask` builds the arrow read view over the
    # whole corpus on its first call, which takes minutes; on a single-threaded server that
    # one request blocks EVERY other request, so the window went completely dead — the page
    # would not even load — and it read as a broken deploy rather than as a slow query.
    #
    # The read view is also WARMED here, off-thread, so that first slow call happens before
    # anyone types rather than inside their first question.
    import threading

    def _warm() -> None:
        try:
            from .current import corpus_snapshot

            t0 = time.time()
            snap = corpus_snapshot()
            print(f"[boot] read view warm: {len(snap.slots):,} slots, "
                  f"{len(snap.arrows):,} arrows in {time.time() - t0:.0f}s", flush=True)
        except Exception as exc:                  # a cold window still serves; it is just slow
            print(f"[boot] read view could not be warmed: {type(exc).__name__}: {exc}",
                  flush=True)

    threading.Thread(target=_warm, daemon=True).start()
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
