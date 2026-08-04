"""Controls for the window: the LM as a source, the discipline, and a live localhost smoke.

The LM path runs against a mock transport, so no key or network is needed. The disciplines
asserted: the LM is a SOURCE through the one inlet (not a separate pipe), me and the LM are
indistinguishable in tier, the window is a VIEW (no three-moves entry), the audit shows
exactly ONE proposer morphism, and the server never logs the key.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from http.server import HTTPServer
from pathlib import Path

from ui.current import Current, run_current
from ui.server import Handler

ROOT = Path(__file__).resolve().parents[1]


def _mock_transport(_key, _body):
    return ('{"claims":[{"surface":"The cone is positive under composition",'
            '"type":"assert","value":"T","confidence":0.9},'
            '{"surface":"The spectral radius is the maximum modulus eigenvalue",'
            '"type":"assert","value":"T","confidence":0.8}]}')


class TheLMIsASourceThroughTheOneInlet(unittest.TestCase):
    def test_lm_proposals_enter_at_proposal_tier(self):
        out = run_current("The cone is positive under composition.", chart="english",
                          key="test-key", lm_transport=_mock_transport)
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


if __name__ == "__main__":
    unittest.main()
