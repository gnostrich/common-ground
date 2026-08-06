"""GATE 10, APPLIED TO THE SERVED PAGE. A surface may not depict a mechanism that is gone.

Twice now the backend changed and the page did not. The candidate-list loop was deleted and
its prose stayed; the propose path was unified and its second box stayed. Both times every
check I ran was against the code in front of me rather than the bytes on the wire, and both
times the operator found it by looking at the window.

Gate 10 already refuses a DOCSTRING that claims a mechanism the call graph lacks. The page is
the same claim made to a person instead of to a reader of source, and it is the one a user
actually believes. So the same rule, on the same terms.
"""

from __future__ import annotations

import pathlib
import unittest

PAGE = pathlib.Path(__file__).resolve().parent.parent / "ui" / "index.html"


class TheSurfaceDepictsOnlyLiveMechanisms(unittest.TestCase):
    def setUp(self):
        self.body = PAGE.read_text(encoding="utf-8")

    def test_planted_the_deleted_retrieval_layer_has_no_surface(self):
        """`id="retrieved"` outlived the retrieval layer by many commits."""
        self.assertNotIn('id="retrieved"', self.body)
        self.assertNotIn("retrieved", self.body.lower().split("<script>")[0])

    def test_planted_there_is_ONE_entry_box_not_two(self):
        """Propose and ask are one act with a persistence flag. Two boxes depict two
        mechanisms, and one of them no longer exists."""
        self.assertNotIn("propose &rarr; inlet", self.body)
        self.assertEqual(self.body.count("<textarea"), 1,
                         "one act, one box")
        self.assertIn('id="retain"', self.body, "the flag must be visible as a flag")

    def test_the_candidate_list_prose_is_gone(self):
        """It described a budget-capped pairwise interrogation that was deleted."""
        for phrase in ("which corpus claims it corresponds to", "how many candidates",
                       "candidates were asked", "same three kinds"):
            self.assertNotIn(phrase, self.body,
                             f"the page still describes the deleted loop: {phrase!r}")

    def test_the_page_says_the_region_is_a_sample(self):
        """The one thing a user will otherwise infer wrongly: that these claims came back
        because they matched."""
        self.assertIn("SAMPLE", self.body)
        self.assertIn("not</b> the part of the corpus that", self.body.replace("\n", " "))

    def test_one_act_in_the_javascript_too(self):
        """A single button over two code paths would be one box depicting one mechanism while
        running two — the same defect one layer down."""
        self.assertIn("async function act()", self.body)
        self.assertNotIn("async function propose()", self.body)
        self.assertNotIn("async function ask()", self.body)


class ThePagesScriptMustPARSE(unittest.TestCase):
    """A syntax error in the inline script kills the ENTIRE page, silently.

    This shipped. One malformed template literal — a stray quote inside a backtick string —
    and the whole script failed to parse, so `corpus()` never ran (the header sat on
    "corpus: loading…" forever) and `act()` was never defined (the perturb button did
    nothing at all). Every server-side check was green; the endpoints answered in under a
    second; the suite was 887 green. Nothing in the engine could see it, because the defect
    was in a string the engine never executes.

    The page is code. It gets a compiler.
    """

    def _script(self) -> str:
        body = PAGE.read_text(encoding="utf-8")
        self.assertIn("<script>", body)
        return body.split("<script>")[1].split("</script>")[0]

    def test_the_inline_script_parses(self):
        import shutil
        import subprocess
        import tempfile

        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available to parse the page")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(self._script())
            path = fh.name
        out = subprocess.run([node, "--check", path], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0,
                         f"the page's script does not parse — the whole window is dead:\n"
                         f"{out.stderr}")

    def test_planted_a_broken_literal_is_caught(self):
        """The exact shape that shipped: a single quote closing inside a template literal."""
        import shutil
        import subprocess
        import tempfile

        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available to parse the page")
        broken = "const x = `a ${1} b '\n  + `c`;"
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(broken)
            path = fh.name
        out = subprocess.run([node, "--check", path], capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0, "the checker must reject what shipped")

    def test_every_function_the_page_calls_is_defined(self):
        """`act()` was undefined for a whole deploy and the button did nothing."""
        import re

        body = PAGE.read_text(encoding="utf-8")
        called = set(re.findall(r'onclick="(\w+)\(', body))
        script = self._script()
        for fn in sorted(called):
            self.assertTrue(
                f"function {fn}(" in script or f"async function {fn}(" in script,
                f"the page calls {fn}() but never defines it")


class TheBuildIdentifiesItself(unittest.TestCase):
    """A deploy that cannot say which commit it is cannot be caught serving a stale one."""

    def test_the_header_carries_the_served_commit(self):
        from ui.current import corpus_header

        self.assertIn("build", corpus_header())

    def test_planted_an_unstampable_build_warns_rather_than_passing(self):
        from unittest import mock

        import ui.build as B

        with mock.patch.object(B, "SERVED", ""):
            out = B.stamp()
        self.assertEqual(out["served"], "unknown")
        self.assertIn("CANNOT SAY WHICH COMMIT", out["warning"])

    def test_the_header_reports_the_SERVED_model_not_the_configured_one(self):
        """Third occurrence of code-truth != wire-truth: the HTML, the commit stamp, and an
        env var silently overriding the code pin. The deployed window ran the lite model for
        hours while the code said `google/gemini-2.5-flash`. Configured and served are
        different facts and the header now carries both."""
        from ui.current import corpus_header

        b = corpus_header()["build"]
        self.assertIn("model", b)
        self.assertIn("model_configured", b)
        self.assertIn("model_drift", b)

    def test_planted_a_pin_that_did_not_take_is_flagged(self):
        from unittest import mock

        import ui.lm as L

        with mock.patch.object(L, "OPENROUTER_MODEL", "google/gemini-2.5-flash"), \
             mock.patch.object(L, "LAST_SERVED", "google/gemini-2.5-flash-lite"):
            from ui.current import corpus_header

            self.assertTrue(corpus_header()["build"]["model_drift"],
                            "a served model differing from the pin must announce itself")

    def test_auto_routing_is_not_counted_as_drift(self):
        """`auto` means the router chooses, so a different served model is expected rather
        than a drift — the drift being flagged is a PIN that did not take."""
        from unittest import mock

        import ui.lm as L

        with mock.patch.object(L, "OPENROUTER_MODEL", "openrouter/auto"), \
             mock.patch.object(L, "LAST_SERVED", "google/gemini-2.5-flash-lite"):
            from ui.current import corpus_header

            self.assertFalse(corpus_header()["build"]["model_drift"])

    def test_the_page_renders_it(self):
        body = PAGE.read_text(encoding="utf-8")
        self.assertIn("renderBuild", body)
        self.assertIn("model served:", body)
        self.assertIn("PIN DRIFT", body)


if __name__ == "__main__":
    unittest.main()
