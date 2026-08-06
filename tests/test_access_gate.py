"""The deploy gate, and what it is actually protecting.

Two things sit behind a reachable window, and only the first is obvious. The corpus is
somebody's private material — but `/ask` and `/propose` call OpenRouter with the SERVER's
key, so an ungated public URL is not merely a disclosure, it is an unmetered charge against
the operator's account by anyone who has the link. That is why `serve()` REFUSES to start a
reachable window with no token rather than warning about it: a deployer who forgets gets a
service that will not boot, which is recoverable, and the other way round is not.

Each control is planted against — the gate is exercised with a wrong token, a missing token,
and a token that shares a prefix with the real one.
"""

from __future__ import annotations

import unittest
from unittest import mock


class _Headers(dict):
    def get(self, key, default=None):        # http.client.HTTPMessage is case-insensitive
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


def _with_token(token: str):
    """Reload the module under a given COMMON_GROUND_TOKEN. The gate reads it at import."""
    import importlib
    import os

    import ui.server as server
    with mock.patch.dict(os.environ, {"COMMON_GROUND_TOKEN": token}):
        return importlib.reload(server)


class AnUngatedDeployIsRefused(unittest.TestCase):
    def test_planted_serve_refuses_to_bind_wide_with_no_token(self):
        """PLANTED: the exact oversight — deploy the window, forget the variable."""
        import os

        server = _with_token("")
        with mock.patch.dict(os.environ, {"PORT": "8080"}, clear=False):
            with self.assertRaises(SystemExit) as caught:
                server.serve()
        message = str(caught.exception)
        self.assertIn("COMMON_GROUND_TOKEN", message)
        self.assertIn("OpenRouter", message, "the refusal must name the SPEND, not just the "
                                             "corpus — the spend is the part that surprises")

    def test_open_on_purpose_is_spelled_out_not_defaulted(self):
        """Running wide open is legitimate; forgetting to decide is not. The opt-out is the
        literal string, so it cannot be reached by leaving a variable unset."""
        server = _with_token("none")
        self.assertTrue(server.OPEN_ON_PURPOSE)
        self.assertEqual(server.ACCESS_TOKEN, "")
        self.assertTrue(server._authorized("/ask", "/ask", _Headers()))

    def test_a_laptop_run_needs_no_token(self):
        server = _with_token("")
        self.assertTrue(server._authorized("/ask", "/ask", _Headers()))


class TheGateChecksEveryCostingPath(unittest.TestCase):
    def setUp(self):
        self.server = _with_token("s3cret")

    def test_the_page_shell_is_open_but_nothing_else_is(self):
        for path in ("/", "/index.html", "/healthz"):
            self.assertTrue(self.server._authorized(path, path, _Headers()),
                            f"{path} holds no corpus and spends nothing")
        for path in ("/ask", "/propose", "/corpus", "/proposer", "/proposer/control"):
            self.assertFalse(self.server._authorized(path, path, _Headers()),
                             f"{path} reads the corpus or spends the key and must be gated")

    def test_planted_a_wrong_token_is_refused(self):
        self.assertFalse(self.server._authorized("/ask", "/ask?t=wrong", _Headers()))

    def test_planted_a_prefix_of_the_token_is_refused(self):
        """A gate compared with `==` leaks its prefix to a patient caller; this one uses
        hmac.compare_digest, and the control names the reason."""
        self.assertFalse(self.server._authorized("/ask", "/ask?t=s3cre", _Headers()))
        self.assertFalse(self.server._authorized("/ask", "/ask?t=s3secret", _Headers()))

    def test_the_right_token_passes_by_query_cookie_or_header(self):
        self.assertTrue(self.server._authorized("/ask", "/ask?t=s3cret", _Headers()))
        self.assertTrue(self.server._authorized(
            "/ask", "/ask", _Headers({"Cookie": "other=1; cg_t=s3cret"})))
        self.assertTrue(self.server._authorized(
            "/ask", "/ask", _Headers({"X-Common-Ground-Token": "s3cret"})))

    def test_an_empty_supplied_token_never_matches(self):
        self.assertFalse(self.server._authorized("/ask", "/ask?t=", _Headers()))
        self.assertFalse(self.server._authorized(
            "/ask", "/ask", _Headers({"Cookie": "cg_t="})))

    def tearDown(self):
        _with_token("")     # leave the module as a laptop run found it


class ThePageCarriesTheTokenToEveryEndpoint(unittest.TestCase):
    """A gate the page cannot get through is a gate that just breaks the window."""

    def test_no_endpoint_is_fetched_without_the_token_helper(self):
        from engine.constants import REPO_ROOT

        text = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        bare = [line.strip() for line in text.splitlines()
                if "fetch('/" in line and "withToken" not in line]
        self.assertEqual(bare, [], "every call must go through withToken(), or it will 401 "
                                   "on a deployed window")

    def test_every_CONTENT_chart_is_offered_in_the_window(self):
        """PLANTED against the two that were missing: the selectors listed four charts for
        weeks after python and go were routing.

        The rule is CONTENT charts, and the refinement is not a loosening. A chart you can
        type a boundary condition into is a chart whose claims are about the world.
        `correspondence` is what arrows land in, and `medium` carries glosses — statements
        about how a model reads a word. Neither is something an operator asserts, and
        `engine/medium.py`'s CONTENT_CHARTS is the same positive list that keeps a gloss out
        of settlement, so the window and the firewall cannot disagree about which is which.
        """
        from engine.charts import chart_names
        from engine.constants import REPO_ROOT
        from engine.medium import CONTENT_CHARTS

        text = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        for name in chart_names():
            if name == "correspondence" or name not in CONTENT_CHARTS:
                continue
            self.assertIn(f"<option>{name}</option>", text,
                          f"the {name} chart exists but cannot be selected in the window")

    def test_an_INTERFACE_chart_is_NOT_offered_as_something_to_type_into(self):
        """THE FIREWALL, REACHING THE UI. A gloss is about how a medium reads a word; it is
        not a claim an operator makes about the world. Offering `medium` in the entry
        selector would let one be typed straight into content settlement, past the
        firewall — the breach coming in through the surface rather than through the engine.
        """
        from engine.charts import chart_names
        from engine.constants import REPO_ROOT
        from engine.medium import CONTENT_CHARTS, MEDIUM_CHART

        text = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        interface = [n for n in chart_names() if n not in CONTENT_CHARTS]
        self.assertIn(MEDIUM_CHART, interface, "the medium chart must be an interface chart")
        for name in interface:
            self.assertNotIn(f"<option>{name}</option>", text,
                             f"{name} is an interface chart and must not be typeable")


if __name__ == "__main__":
    unittest.main()
