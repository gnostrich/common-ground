"""THE SWEEP THAT ASKS WHETHER A CONTROL CHECKS TEXT OR BEHAVIOUR — and its own controls.

A sweep whose controls are themselves source scans would be the joke it exists to prevent, so
these execute it: they build test files on disk, run the sweep over them, and assert on what
comes back.
"""

import tempfile
import textwrap
import unittest
from pathlib import Path

from engine.control_sweep import (READERS, Control, classified_keys, render,
                                  source_reading_controls, unclassified)


def _tree(body: str) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "test_example.py").write_text(textwrap.dedent(body))
    return d


class TheSweepFindsThePopulation(unittest.TestCase):

    def test_a_getsource_control_is_found(self):
        d = _tree('''
            import inspect
            import unittest
            class C(unittest.TestCase):
                def test_it(self):
                    src = inspect.getsource(object)
                    self.assertIn("x", src)
        ''')
        got = source_reading_controls(d)
        self.assertEqual(1, len(got))
        self.assertEqual("C.test_it", got[0].test)
        self.assertEqual(("getsource",), got[0].readers)

    def test_a_read_text_control_is_found(self):
        d = _tree('''
            import unittest
            from pathlib import Path
            class C(unittest.TestCase):
                def test_it(self):
                    self.assertIn("x", Path("a").read_text())
        ''')
        self.assertEqual(("read_text",), source_reading_controls(d)[0].readers)

    def test_a_control_that_executes_is_NOT_in_the_population(self):
        d = _tree('''
            import unittest
            class C(unittest.TestCase):
                def test_it(self):
                    self.assertEqual(2, 1 + 1)
        ''')
        self.assertEqual([], source_reading_controls(d))

    def test_the_class_name_travels_so_a_control_can_be_located(self):
        d = _tree('''
            import inspect
            import unittest
            class SomeNamedClass(unittest.TestCase):
                def test_it(self):
                    inspect.getsource(object)
        ''')
        self.assertEqual("SomeNamedClass.test_it", source_reading_controls(d)[0].test)

    def test_the_reader_set_is_stated_not_incidental(self):
        # A bare `.read()` is deliberately NOT in the set: it appears on sockets, responses
        # and streams, where reading is the execution rather than a substitute for it.
        self.assertIn("getsource", READERS)
        self.assertIn("read_text", READERS)
        self.assertNotIn("read", READERS)


class NewSourceControlsCannotAppearUNCLASSIFIED(unittest.TestCase):
    """The population may grow. It may not grow silently."""

    def test_an_unruled_control_is_reported(self):
        d = _tree('''
            import inspect
            import unittest
            class C(unittest.TestCase):
                def test_it(self):
                    inspect.getsource(object)
        ''')
        with tempfile.TemporaryDirectory() as t:
            triage = Path(t) / "none.md"
            self.assertEqual(1, len(unclassified(d, triage)))

    def test_a_ruled_control_is_not_reported(self):
        d = _tree('''
            import inspect
            import unittest
            class C(unittest.TestCase):
                def test_it(self):
                    inspect.getsource(object)
        ''')
        with tempfile.TemporaryDirectory() as t:
            triage = Path(t) / "triage.md"
            triage.write_text("| 1 | `test_example.py::C.test_it` | SOURCE | reads a module |")
            self.assertEqual([], unclassified(d, triage))

    def test_a_missing_triage_file_classifies_NOTHING(self):
        # An absent document must not read as "everything is fine" — the same rule staleness
        # applies when it refuses to read `unknown` as `fresh`.
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(set(), classified_keys(Path(t) / "absent.md"))

    def test_the_render_says_clean_only_when_it_is(self):
        self.assertIn("every source-reading control is classified", render([]))
        self.assertIn("UNCLASSIFIED", render([Control("f.py", "C.t", 1, ("getsource",))]))


class TheSweepKnowsItsOwnBlindSpot(unittest.TestCase):
    """A sweep that hides its limits is worse than none.

    A control that DOES execute, with a fixture simpler than the thing it stands for, passes
    this law and fails anyway. Three in one session: a stub with no `id` attribute that took a
    fallback branch, a bound method that serialised as a method, and a source scan standing in
    for an HTTP request. The module must say so where anyone reading it will see it.
    """

    def test_the_module_states_that_executing_is_necessary_and_not_sufficient(self):
        import engine.control_sweep as mod
        doc = mod.__doc__ or ""
        self.assertIn("BLIND SPOT", doc)
        self.assertIn("necessary and not sufficient", doc)

    def test_the_law_is_in_the_ledger(self):
        from engine.constants import REPO_ROOT
        body = (REPO_ROOT / "seed" / "OBJECT-AMENDED.md").read_text(encoding="utf-8")
        self.assertIn("THE MAP IS NOT THE TERRITORY", body)


if __name__ == "__main__":
    unittest.main()
