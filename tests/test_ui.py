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


def _mock_transport(_key, _body):
    return ('{"claims":[{"surface":"The cone is positive under composition",'
            '"type":"assert","value":"T","confidence":0.9},'
            '{"surface":"The spectral radius is the maximum modulus eigenvalue",'
            '"type":"assert","value":"T","confidence":0.8}]}')


class TheLMIsASourceThroughTheOneInlet(unittest.TestCase):
    def test_lm_proposals_enter_at_proposal_tier(self):
        out = run_current("The cone is positive under composition.", chart="english",
                          key="sk-or-test-key", lm_transport=_mock_transport)
        self.assertTrue(out["lm_available"])
        by = out["proposals_by_source"]
        self.assertIn("me", by)
        self.assertIn("lm", by)
        for p in out["proposals"]:
            self.assertEqual(p["tier"], "EXTRACTION",
                             "every source, LM included, is proposal-tier")

    def test_no_key_means_deterministic_only(self):
        out = run_current("The cone is positive.", chart="english")
        self.assertFalse(out["lm_available"])
        self.assertEqual(set(out["proposals_by_source"]), {"me"})

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

    def test_the_model_is_always_auto(self):
        from ui.lm import model_for

        self.assertEqual(model_for("sk-or-v1-whatever"), "openrouter/auto")


if __name__ == "__main__":
    unittest.main()
