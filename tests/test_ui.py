"""Controls for the window: the LM as a source, the discipline, and a live localhost smoke.

The LM path runs against a mock transport, so no key or network is needed. The disciplines
asserted: the LM is a SOURCE through the one inlet (not a separate pipe), me and the LM are
indistinguishable in tier, the window is a VIEW (no three-moves entry), the audit shows
exactly ONE proposer morphism, and the server never logs the key.
"""

from __future__ import annotations

import json
import os
import threading
import unittest
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import ui.server
from ui.current import Current, run_current
from ui.server import Handler

ROOT = Path(__file__).resolve().parents[1]

_SAVED_KEY: str | None = None


def setUpModule():
    """The window's tests must not depend on the operator's shell.

    Every test here either supplies an explicit key or exercises the NO-key path, so an
    `OPENROUTER_API_KEY` in the ambient environment both breaks the no-key assertions and
    makes the live smoke fire a real billed LM call. The continuous proposer runs the suite
    as a gate with its own key exported, which is exactly when that would bite.
    """
    global _SAVED_KEY
    _SAVED_KEY = os.environ.pop("OPENROUTER_API_KEY", None)


def tearDownModule():
    if _SAVED_KEY is not None:
        os.environ["OPENROUTER_API_KEY"] = _SAVED_KEY


def _mock_transport(_system, _body):
    """The REGION transport. Proposing is now a region completion, so a stub that returned
    the old claim-extraction JSON would be miming a mechanism that no longer exists."""
    return "", {"cost": 0.0}


class ProposingIsPerturbAndRetain(unittest.TestCase):
    """The bare propose path is DELETED. These controls describe what replaced it.

    The old control here asserted that the LM appeared as a second SOURCE at the inlet,
    beside `me`, each dropping extracted claims on the tape. That mechanism is gone: the LM
    no longer proposes claims about the typed text, it completes a region containing it, and
    what it contributes is ATTACHMENT — arrows to `[0|bias]`, retained beside the claim.
    Keeping the old assertion would have pinned the removed organ in place.
    """

    def test_the_typed_claim_is_retained_at_extraction_tier(self):
        out = run_current("The cone is positive under composition.", chart="english",
                          key="sk-or-test-key", lm_transport=_mock_transport)
        self.assertIn("me", out["proposals_by_source"])
        for p in out["proposals"]:
            self.assertEqual(p["tier"], "EXTRACTION",
                             "every source, the LM's attachments included, is proposal-tier")

    def test_the_result_reports_what_was_retained(self):
        out = run_current("The cone is positive under composition.", chart="english",
                          key="sk-or-test-key", lm_transport=_mock_transport)
        self.assertIn("retention", out)
        self.assertEqual(out["retention"]["mode"], "retain")
        self.assertTrue(out["retention"]["retained_claim"])

    def test_planted_no_model_retains_an_isolated_claim_and_says_so(self):
        """The removed organ was a raw drop treated as normal. Without a model the input
        still cannot be situated — but that is now STATED, not silently done."""
        out = run_current("The cone is positive.", chart="english")
        self.assertFalse(out["lm_available"])
        self.assertEqual(set(out["proposals_by_source"]), {"me"})
        self.assertEqual(out["retention"]["retained_arrows"], 0)
        self.assertIn("ISOLATED", out["retention"]["note"])

    def test_a_third_instance_source_uses_the_same_inlet(self):
        cur = Current()
        cur.propose_text("The cone is positive.", chart="english")
        st = cur.propose_text("The cone is positive.", chart="english", instance_id="B")
        self.assertIn("instance:B", st["proposals_by_source"])
        for p in st["proposals"]:
            self.assertEqual(p["tier"], "EXTRACTION")


class TheDiscipline(unittest.TestCase):
    def test_the_window_is_a_view_not_an_extension(self):
        from engine.three_moves import EXTENSIONS
        names = " ".join(e.name.lower() for e in EXTENSIONS)
        for w in ("window", "server", "current", "ask box", "ui"):
            self.assertNotIn(w, names, "the window is a view; it is not an extension")

    def test_exactly_one_proposer_morphism(self):
        from engine.three_moves import EXTENSIONS, ADD_MORPHISM
        inlets = [e for e in EXTENSIONS if "inlet" in e.name.lower() or "proposer" in e.name.lower()]
        self.assertEqual(len(inlets), 1, "me/LM/instance are ONE proposer morphism, not three")
        self.assertEqual(inlets[0].move, ADD_MORPHISM)
        self.assertEqual(inlets[0].status, "built")

    def test_server_never_logs_the_key(self):
        src = (ROOT / "ui" / "server.py").read_text(encoding="utf-8")
        start = src.index("def log_message")
        end = src.index("def _send", start)
        # Inspect code only (drop comment tails) — log_message must never touch the request
        # headers or body, which is where the key would be.
        code = "\n".join(line.split("#", 1)[0] for line in src[start:end].splitlines())
        for forbidden in ("self.headers", "self.rfile", ".read("):
            self.assertNotIn(forbidden, code,
                             f"log_message must not reference {forbidden!r} (key-leak vector)")


class LiveLocalhostSmoke(unittest.TestCase):
    def test_propose_and_reset_over_http(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            base = f"http://127.0.0.1:{port}"
            # GET / serves the page
            with urllib.request.urlopen(base + "/") as r:
                self.assertIn(b"One inlet", r.read())
            # POST /propose (deterministic; no key)
            body = json.dumps({"text": "The cone is positive under composition.",
                               "chart": "english"}).encode()
            req = urllib.request.Request(base + "/propose", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as r:
                state = json.load(r)
            self.assertIn("me", state["proposals_by_source"])
            self.assertEqual(state["law"], "One inlet. All proposers equal. "
                                           "Warrant conferred only at the gate.")
            # reset
            req = urllib.request.Request(base + "/reset", data=b"{}",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as r:
                self.assertTrue(json.load(r)["ok"])
        finally:
            server.shutdown()


class TheTranscriptIsPERACT(unittest.TestCase):
    """`start()` was imported and never called, so the sink accumulated forever.

    The consequence is worse than a leak: an operator opening the raw traffic would have been
    shown every call the process had served since boot, under their own question, with digests
    that all verified. A transparency surface reporting the wrong bytes is worse than none,
    because it is believed — so the boundary of one act is controlled at the HTTP layer, where
    the reset actually has to happen, rather than by reading the import.
    """

    def _serve(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server, f"http://127.0.0.1:{server.server_address[1]}"

    def _post(self, base, path, payload):
        req = urllib.request.Request(base + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            return json.load(r)

    def test_a_second_act_does_not_inherit_the_firsts_calls(self):
        from engine.transcript import CURRENT

        server, base = self._serve()
        try:
            # A DISTINCT LEFTOVER, planted on top of whatever this process already holds.
            # Asserting the sink is empty first would be a test about test ordering; the
            # property under control is that THIS string cannot survive into the next act.
            CURRENT.record("propose", "leftover system", "leftover user", "leftover reply")
            self.assertIn("leftover", json.dumps(CURRENT.as_record()))
            state = self._post(base, "/propose", {"text": "the cone is positive",
                                                  "chart": "english"})
            self.assertIn("transcript", state, "/propose must return its calls too — retain "
                                               "makes the same calls release does")
            blob = json.dumps(state["transcript"])
            self.assertNotIn("leftover", blob,
                             "the act inherited a call it did not make")
        finally:
            server.shutdown()

    def test_every_act_endpoint_returns_a_transcript_key(self):
        server, base = self._serve()
        try:
            for path, payload in (("/propose", {"text": "the cone is positive"}),
                                  ("/ask", {"question": "is the cone positive"})):
                with self.subTest(path=path):
                    out = self._post(base, path, dict(payload, chart="english"))
                    self.assertIn("transcript", out)
                    self.assertIsInstance(out["transcript"], list)
        finally:
            server.shutdown()


class TheProposerLedgerIsVisibleAndReadOnly(unittest.TestCase):
    """The window shows the daemon's own journal, and cannot promote through it."""

    def test_the_ledger_endpoint_reports_the_tier_and_the_journal(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/proposer") as r:
                payload = json.load(r)
            self.assertNotIn("error", payload, payload.get("error", ""))
            self.assertIn("EXTRACTION only", payload["tier"])
            self.assertIn("asked", payload["totals"])
            self.assertIn("calls_per_hour", payload["control"])
        finally:
            server.shutdown()

    def test_the_control_surface_writes_only_operational_fields(self):
        """PLANTED-shaped: the endpoint must not be able to set a tier, warrant, or promotion.

        Rather than trying every spelling of the attack, the control reads the AST of the
        `/proposer/control` branch and asserts the exact set of fields it writes. A new
        assignment target — of any name — fails this until it is added deliberately.
        """
        import ast

        source = Path(ui.server.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        branch = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
                    and test.left.id == "path"
                    and any(isinstance(c, ast.Constant) and c.value == "/proposer/control"
                            for c in test.comparators)):
                branch = node
        self.assertIsNotNone(branch, "the control endpoint disappeared")

        written: set[str] = set()
        # body only: `orelse` is the rest of the elif chain, which is not this endpoint
        for stmt in branch.body:
         for node in ast.walk(stmt):
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                     and node.func.id == "setattr":
                 for arg in node.args[1:2]:
                     if isinstance(arg, ast.Name):
                         written.add(f"<loop:{arg.id}>")
             elif isinstance(node, ast.Assign):
                 for target in node.targets:
                     if isinstance(target, ast.Attribute):
                         written.add(target.attr)
             if isinstance(node, ast.Constant) and isinstance(node.value, str):
                 written.add(node.value)
        allowed = {"calls_per_hour", "batch", "paused", "stop", "max_cost",
                   "/proposer/control", "<loop:field>", ""}
        self.assertEqual(written - allowed, set(),
                         "the control endpoint touches a field outside the operational set; "
                         "warrant is not a window concern")


class OpenRouterOnly(unittest.TestCase):
    """Every LM call the engine makes goes through OpenRouter. There is no Anthropic path."""

    def test_no_anthropic_endpoint_exists(self):
        import inspect

        import ui.lm as mod

        src = inspect.getsource(mod)
        self.assertNotIn("api.anthropic.com", src, "no Anthropic endpoint may exist")
        self.assertIn("openrouter.ai", src)

    def test_the_key_lookup_has_no_anthropic_fallback(self):
        import os

        from ui.lm import api_key

        old_or = os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-should-be-ignored"
        try:
            self.assertEqual(api_key(), "",
                             "an Anthropic key must NOT satisfy the key lookup")
        finally:
            os.environ.pop("ANTHROPIC_API_KEY", None)
            if old_or is not None:
                os.environ["OPENROUTER_API_KEY"] = old_or

    def test_a_non_openrouter_key_is_refused(self):
        from ui.lm import model_for

        with self.assertRaises(RuntimeError):
            model_for("sk-ant-abc")

    def test_the_model_is_the_pin_not_auto(self):
        """SUPERSEDED CONTROL. This asserted `openrouter/auto` and encoded the standing rule
        that a router picks the model. That rule cost the corpus its topology: auto served
        448 of 465 calls with a lite model that never emits `same_claim`, the only
        loop-eligible relation. The rule changed, so the control changed with it rather than
        being deleted — see `TheModelIsPinnedNotRouted` for what replaced it."""
        from ui.lm import OPENROUTER_MODEL, model_for

        self.assertEqual(model_for("sk-or-v1-whatever"), OPENROUTER_MODEL)
        self.assertNotEqual(OPENROUTER_MODEL, "openrouter/auto")


class TheWindowIsHonestAboutTheCorpus(unittest.TestCase):
    """A missing corpus must never be presented as an empty one, or as a grounded answer."""

    def test_the_header_says_whether_anything_is_loaded(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/corpus") as r:
                head = json.load(r)
            self.assertIn("loaded", head)
            self.assertIn("floor", head)
            if not head["loaded"]:
                self.assertIn("NO CORPUS LOADED", head["note"])
            else:
                self.assertGreater(head["slots"], 0)
        finally:
            server.shutdown()

    def test_an_uncoupled_question_is_never_reported_as_conditioned(self):
        """PLANTED: a question whose addresses this corpus does not carry.

        The bias joins the coupling graph with no declared arrow touching it, so nothing
        propagates and nothing moves. That must be reported as a structural fact with no
        facts emitted — never as conditioning, and never filled in by a second mechanism.
        """
        from ui.current import ask_the_corpus

        out = ask_the_corpus("zzq unlikely boundary condition 84619 that lands nowhere at all")
        self.assertFalse(out["conditioned"])
        self.assertEqual(out["moved"], 0)
        self.assertEqual(out["facts"], [])
        self.assertIn("THE FIELD DID NOT RESPOND", out["compiled"])
        self.assertNotIn("MOVED [", out["compiled"],
                         "nothing moved, so no line may carry the moved label")
        self.assertIsNone(out.get("retrieved"),
                          "the retrieval layer is deleted; a key here means it came back")

    def test_the_floor_is_never_rendered_as_a_number_when_it_is_a_gap(self):
        """A window that printed `floor: 0.0` would report agreement where there is absence."""
        from ui.current import corpus_header

        head = corpus_header()
        self.assertIsInstance(head["floor"], str)
        if head.get("loops", 0) == 0:
            self.assertIn("GAP", head["floor"])


if __name__ == "__main__":
    unittest.main()


class TheModelIsPinnedNotRouted(unittest.TestCase):
    """A model selector is a mechanism parameter, not a vendor's per-call cost decision.

    `openrouter/auto` served 448 of 465 calls with `gemini-2.5-flash-lite`, which on one
    pinned region emitted 1,789 arrow lines over 51 distinct pairs — 35 repeats each — and
    ZERO `same_claim`. Every pinned model tried had repeats-per-pair of exactly 1.0, and two
    of three emitted `same_claim`. Since `same_claim` is the only loop-eligible relation, that
    routing default is upstream of the corpus's forest topology.
    """

    def test_planted_auto_routing_is_not_the_default(self):
        from ui.lm import OPENROUTER_MODEL

        self.assertNotEqual(OPENROUTER_MODEL, "openrouter/auto",
                            "auto lets a cost heuristic choose the mechanism per call")
        self.assertIn("/", OPENROUTER_MODEL, "a pinned model names its vendor and version")

    def test_model_for_returns_the_pin(self):
        from ui.lm import OPENROUTER_MODEL, model_for

        self.assertEqual(model_for("sk-or-test"), OPENROUTER_MODEL)

    def test_a_non_openrouter_key_is_still_refused(self):
        from ui.lm import model_for

        with self.assertRaises(RuntimeError):
            model_for("sk-ant-nope")
