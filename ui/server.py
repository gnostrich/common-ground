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
import hmac
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from engine.export_sheet import sheet
from engine.corpus_state import SNAPSHOT_PATH
from engine.grounded import check_answer
from engine.dialogue import (TURN_BUDGET, Turn, arrows_from, converse,
                             render_prompt as dialogue_prompt, slot_of)
from engine.transcript import CURRENT as TRANSCRIPT, start as start_transcript
from engine.inbound import INBOUND_SYSTEM

from .current import Current, ask_the_corpus, corpus_header
from . import lm as _lm
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

#: THE DATA CHANNEL. The corpus is DATA, not code: it must never enter a git tree, public or
#: private, and never ship inside an image. `seed_runs/` is gitignored for exactly that reason,
#: which is also why Railway skipped it and `ui/boot.seed_state` — correct code — has never
#: executed on any deploy. So the material arrives over the wire, straight onto the volume.
#:
#: THE ENDPOINT DOES NOT EXIST unless this variable is set. Not "returns 403": a 404, the same
#: as any unrouted path, so a deploy with the variable unset is a deploy with no upload surface
#: to find. Setting it is the operator's act; unsetting it afterwards is the removal.
SEED_UPLOAD_ENV = "CG_SEED_UPLOAD_TOKEN"

#: Files the channel will write. A fixed list, not a caller-supplied path: an upload endpoint
#: that takes a filename is an arbitrary-write endpoint wearing a narrower name.
UPLOADABLE = {"corpus.snapshot", "proposer.journal.jsonl"}

#: Largest upload accepted. The snapshot is ~25MB; the journal ~30MB. Stated so a truncated
#: transfer fails loudly rather than landing a short file that loads as a smaller corpus.
MAX_UPLOAD = 256 * 1024 * 1024


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

    def _seed(self):
        """THE DATA CHANNEL. The corpus arrives here or not at all.

        It may not enter a git tree, public or private, and may not ship inside an image —
        which is precisely why `ui/boot.seed_state` has never executed on any deploy: the
        staging directory is gitignored for publication reasons and Railway skips gitignored
        paths. So the material goes straight onto the volume, over the wire.

        THE ENDPOINT DOES NOT EXIST unless `CG_SEED_UPLOAD_TOKEN` is set — a 404, the same as
        any unrouted path, not a 403 that advertises what is behind it. Setting the variable
        is the operator's act; unsetting it afterwards is the removal.

        ATOMIC AND VERIFIED. Bytes land in a temp file beside the target, are hashed, are
        compared against the digest the caller declared, and only then renamed into place. A
        truncated transfer that loaded as a smaller corpus would be indistinguishable from a
        smaller corpus, which is the one failure this must not be able to have.
        """
        import hashlib
        import tempfile

        token = os.environ.get(SEED_UPLOAD_ENV, "")
        if not token:
            return self._send(404, json.dumps({"error": "not found"}))
        if not hmac.compare_digest(self.headers.get("X-Seed-Token", ""), token):
            return self._send(401, json.dumps({"error": "bad seed token"}))
        name = self.headers.get("X-Seed-Name", "")
        if name not in UPLOADABLE:
            return self._send(400, json.dumps({
                "error": f"{name!r} is not an uploadable name",
                "why": ("the channel writes a FIXED set of names. An endpoint that takes a "
                        "caller-supplied path is an arbitrary-write endpoint wearing a "
                        "narrower name."),
                "uploadable": sorted(UPLOADABLE)}))
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_UPLOAD:
            return self._send(400, json.dumps({
                "error": f"content-length {length} outside 1..{MAX_UPLOAD}"}))
        declared = (self.headers.get("X-Seed-Sha256") or "").strip()
        if not declared:
            return self._send(400, json.dumps({
                "error": "X-Seed-Sha256 is required",
                "why": ("an unverified upload that truncates lands a short file that loads "
                        "as a smaller corpus, and nothing downstream could tell the "
                        "difference")}))

        target = Path(SNAPSHOT_PATH).parent / name
        target.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        got = 0
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=f".{name}.")
        try:
            with os.fdopen(fd, "wb") as out:
                while got < length:
                    chunk = self.rfile.read(min(1 << 20, length - got))
                    if not chunk:
                        break
                    out.write(chunk)
                    h.update(chunk)
                    got += len(chunk)
            if got != length:
                os.unlink(tmp)
                return self._send(400, json.dumps({
                    "error": f"short transfer: {got} of {length} bytes"}))
            if h.hexdigest() != declared:
                os.unlink(tmp)
                return self._send(400, json.dumps({
                    "error": "sha256 mismatch — the bytes that arrived are not the bytes "
                             "that were sent",
                    "declared": declared, "received": h.hexdigest()}))
            was = target.stat().st_size if target.exists() else 0
            os.replace(tmp, target)
        except Exception as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return self._send(500, json.dumps({"error": f"{type(exc).__name__}: {exc}"}))

        # The window holds a snapshot in memory; a replaced substrate that nothing rereads is
        # a replaced substrate nobody is using.
        try:
            corpus_snapshot(reload=True)
        except Exception:
            pass
        return self._send(200, json.dumps({
            "ok": True, "name": name, "bytes": got, "sha256": h.hexdigest(),
            "replaced_bytes": was,
            "note": ("written atomically and verified against the declared digest. The "
                     "journal is never overwritten by this channel — see UPLOADABLE.")}))

    def do_POST(self):
        path = self.path.split("?")[0]
        if not self._gate(path):
            return
        if path == "/seed":
            # HANDLED BEFORE `_body()`. The corpus is tens of megabytes of pickle; running it
            # through a JSON parser would fail on the first byte, and reading it twice is not
            # possible on a socket. So the raw stream is taken here and nowhere else.
            return self._seed()
        b = self._body()
        key = api_key(b.get("key"))          # request key or env; never logged
        # THE TRANSCRIPT IS PER-ACT, and this line is what makes it so. It was imported and
        # never called, so `CURRENT.calls` accumulated across every request the process had
        # ever served: the operator would have been shown somebody else's traffic under their
        # own question, growing without bound. A transparency surface that reports the wrong
        # bytes is worse than none, because it is believed.
        start_transcript()
        try:
            if path == "/propose":
                # NO MODE. The lock that lived here guarded a brainstorm/assert selector
                # that no longer exists: every utterance enters the tape as an authored
                # record, and K is the only door to slow weight. There is nothing left to
                # launder through, because there is no second channel to launder from.
                state = CURRENT.propose_text(
                    text=str(b.get("text", "")),
                    chart=str(b.get("chart", "english")),
                    temperature=float(b.get("temperature", 0.3)),
                    key=key or None,
                    instance_id=(b.get("instance_id") or None),
                )
                state["transcript"] = TRANSCRIPT.as_record()
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
            elif path == "/intake":
                # THE INTAKE SURFACE. One door for material arriving from outside, and lineage
                # is a thing an arrival may DECLARE about itself rather than a second path.
                # Material with no manifest travels the identical route.
                #
                # BEHIND THE SEED-UPLOAD TOKEN, not the read token. This WRITES to the corpus,
                # and the read token gates disclosure and spend — a different question. The
                # endpoint does not exist when the variable is unset, the same 404 as any
                # unrouted path, so a deploy with no upload token has no intake surface to
                # find.
                seed_token = os.environ.get(SEED_UPLOAD_ENV, "")
                if not seed_token:
                    return self._send(404, json.dumps({"error": "not found"}))
                if not hmac.compare_digest(self.headers.get("X-Seed-Token", ""), seed_token):
                    return self._send(401, json.dumps({"error": "bad seed token"}))
                from engine.corpus_state import SNAPSHOT_PATH
                from engine.intake import intake
                from engine.lineage import Export

                snap = corpus_snapshot()
                export = None
                if b.get("export"):
                    # VERIFIED, NOT TRUSTED. The id is a hash of the question and the
                    # addresses, so a forged stub is refused here rather than becoming
                    # lineage nobody declared.
                    export = Export.read(b["export"])
                arrival = intake(b.get("documents") or [], snap,
                                 manifest=b.get("manifest"), export=export)
                # PERSISTED, or the merge lives only until the next reload. Saved AFTER the
                # arrival is complete, so a failed intake leaves the corpus as it was.
                if arrival.slots_new or arrival.edges:
                    snap.save(SNAPSHOT_PATH)
                    corpus_snapshot(reload=True)
                self._send(200, json.dumps({"arrival": arrival.as_record(),
                                            "corpus_header": corpus_header()}))
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
                # ─── THE DIALOGUE ─────────────────────────────────────────────────────
                # ONE CONVERSATION, and its last turn is the answer. The render call that
                # used to live here is DELETED: the two-port split was an artifact of the
                # mute-coordinates era, when the medium was not allowed to write words on the
                # extraction port and a second port had to exist for the words. Once it
                # answers in cited prose the two are one act, and a render call standing
                # beside a dialogue that already produced prose is a second mechanism for
                # one job.
                _phase("answering")
                grounded_on = compiled["compiled"]
                system = dialogue_prompt()
                if lm_available(key):
                    client = LMClient(key)

                    def _turn(sys_text: str, user_text: str):
                        # EVERY TURN IS RECORDED, both directions, by turn number rather than
                        # by port — there are no ports any more. The engine's interrogations
                        # are recorded separately, because attributing machine-authored text
                        # to the medium would misattribute authorship in the one panel whose
                        # whole job is to prove it.
                        _t = time.time()
                        out = client.complete(sys_text, user_text,
                                              float(b.get("temperature", 0.2)), 1200).strip()
                        TRANSCRIPT.record(f"turn {len(TRANSCRIPT.calls) + 1}",
                                          sys_text, user_text, out,
                                          model=str(_lm.LAST_SERVED or ""),
                                          seconds=time.time() - _t)
                        return out, {}

                    # TURN 1 IS ALREADY DONE — it is the attachment call, made inside
                    # ask_the_corpus with the dialogue's own prompt. Seeding it here is what
                    # makes this ONE conversation: its prose and its arrows enter the record
                    # as turn 1, and the loop continues from turn 2 against the field those
                    # arrows moved. Re-asking would spend a call to obtain what we already
                    # hold, and would ask it of a smaller field.
                    att = (compiled.get("attachment") or {})
                    first = None
                    if att.get("prose"):
                        # THE CITABLE SET FOR A TURN IS WHAT THAT TURN WAS SHOWN. Turn 1 saw
                        # the whole region; the compiled citations are only what attached or
                        # moved. Resolving turn 1 against the compiled set voided every arrow
                        # to an object that did not itself move — 10 records, 0 resolved on
                        # column C's first run.
                        first = Turn(n=1, ask=question, prose=att["prose"],
                                     proposals=arrows_from(
                                         att["prose"],
                                         set(att.get("labels") or ()) | set(slot_of(compiled)),
                                         turn=1),
                                     moved=int(((compiled.get("relaxation") or {})
                                                .get("moved")) or 0))
                    dlg = converse(question, compiled, _turn,
                                   budget=int(b.get("turns", TURN_BUDGET)), system=system,
                                   first_turn=first)
                    reply = dlg.answer
                    dialogue_record = dlg.as_record()
                else:
                    reply = ("(no key — the LM is not answering. What it would have received "
                             "is below, compiled from the field.)")
                    dialogue_record = None
                # THE GATE THAT PUTS THE ANSWER FIRST. Unchanged by the collapse: the last
                # turn is prose in the same grammar the render call produced, so the same
                # checker judges it. Checked here, on the way out, so the verdict travels
                # with the prose it judges and the page cannot show one without the other.
                _phase("checking")
                verdict = check_answer(reply, compiled).as_record()
                self._send(200, json.dumps({
                    "answer": reply, "grounded_on": grounded_on, "faithful": verdict,
                    # EVERY CALL, BOTH CHANNELS, RAW — including the attachment call, which
                    # decides what the answer can be about. With digests, so the displayed
                    # bytes can be verified to be the sent bytes.
                    "transcript": TRANSCRIPT.as_record(),
                    # THE PORTABLE SHEET. A VIEW over the record this request already made —
                    # it is returned WITH the answer rather than behind a second endpoint, so
                    # exporting cannot re-run a perturbation or produce a sheet describing a
                    # different one than the operator is looking at.
                    # THE DIALOGUE ITSELF, turn by turn: what was asked, who asked it, what
                    # arrows each turn yielded, and what moved between them.
                    "dialogue": dialogue_record,
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
