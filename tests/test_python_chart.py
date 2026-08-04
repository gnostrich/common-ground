"""The `python` chart: additive admission through the plug-in registry.

Mirrors `tests/test_probes.py:TheChartRegistryIsAPlugInSeam`'s coverage of `tabular` (item
2), applied to `python` (repo-intake track). Three things this file exists to nail down:

1. The addition is additive — english/lean/tabular keep their tags and their addresses;
   nothing that already had a slot moved.
2. `python`'s normalizer is total and idempotent under the same adversarial fuzz null cell
   (i) already runs on every chart (asserted directly here as a fast, targeted regression;
   the null battery itself is the exhaustive check).
3. `python`'s classifier and segmenter behave sanely on real Python source, and the
   plug-in audit still reports PASS with a fourth chart registered.
"""

from __future__ import annotations

import unittest

from engine.charts import chart_names, tag_of
from engine.chart_plugin_audit import verdict
from engine.extract import _segment_python
from engine.hashing import DRNG
from engine.normalize import address, classify, nu


class TheAdditionIsAdditive(unittest.TestCase):
    """No existing chart's tag or address moved when `python` was added."""

    def test_english_and_lean_and_tabular_tags_are_unchanged(self):
        self.assertEqual(tag_of("english"), "\x01en\x01")
        self.assertEqual(tag_of("lean"), "\x01lean\x01")
        self.assertEqual(tag_of("tabular"), "\x01tab\x01")

    def test_python_gets_its_own_fresh_tag(self):
        self.assertEqual(tag_of("python"), "\x01py\x01")

    def test_an_existing_address_is_bit_identical_to_before_the_addition(self):
        """A slot id computed against english/lean is unaffected by python's presence."""
        slot, n = address("english", "Positivity is preserved under composition.", "assert")
        self.assertEqual(n, "\x01en\x01positivity is preserved under composition")
        self.assertEqual(len(slot), 64)

    def test_chart_names_lists_python_last_and_deletes_nothing(self):
        self.assertEqual(chart_names(),
                         ("english", "lean", "tabular", "conversation",
                          "correspondence", "python"),
                         "the rebase keeps every chart this branch predated")

    def test_chart_plugin_audit_still_passes_with_a_fourth_chart(self):
        v = verdict()
        self.assertTrue(v["manifest_only_possible"])
        self.assertEqual(v["blocking_sites"], [])


class PythonNormalizerIsTotalAndIdempotent(unittest.TestCase):
    """Targeted regression alongside null cell (i), which fuzzes this at n=500."""

    def test_idempotent_on_real_source(self):
        src = "def add(a, b):  # sums two numbers\n\n    return a + b\n"
        once = nu("python", src)
        self.assertEqual(once, nu("python", once))

    def test_never_raises_on_adversarial_fuzz(self):
        rng = DRNG("test-python-chart-fuzz", "fixed-seed-for-this-test")
        alphabet = "abc#@()[]{}:=\n\t \x00\x01\x1f'\"—…def class assert if"
        for _ in range(500):
            n = rng.randrange(80) + 1
            s = "".join(alphabet[rng.randrange(len(alphabet))] for _ in range(n))
            once = nu("python", s)
            self.assertEqual(once, nu("python", once), f"not idempotent on {s!r}")

    def test_comments_are_stripped(self):
        with_comment = nu("python", "x = 1  # a note")
        without = nu("python", "x = 1")
        self.assertEqual(with_comment, without)

    def test_case_is_preserved_python_is_case_sensitive(self):
        self.assertNotEqual(nu("python", "class Cone: pass"), nu("python", "class cone: pass"))

    def test_a_chart_not_in_the_manifest_is_still_rejected(self):
        with self.assertRaises(ValueError):
            nu("hieroglyphic", "anything")


class PythonClassifier(unittest.TestCase):
    def test_a_function_definition_is_define(self):
        self.assertEqual(classify("python", "def add(a, b):\n    return a + b"), "define")

    def test_a_class_definition_is_define(self):
        self.assertEqual(classify("python", "class Cone:\n    pass"), "define")

    def test_a_decorated_function_is_still_define(self):
        self.assertEqual(
            classify("python", "@staticmethod\ndef add(a, b):\n    return a + b"), "define"
        )

    def test_an_async_def_is_define(self):
        self.assertEqual(classify("python", "async def fetch():\n    pass"), "define")

    def test_a_guard_head_is_conditional(self):
        self.assertEqual(classify("python", "if x > 0:\n    return x"), "conditional")

    def test_an_unrecognised_fragment_defaults_to_assert(self):
        self.assertEqual(classify("python", "x = compute()"), "assert")


class PythonSegmenter(unittest.TestCase):
    def test_segments_top_level_defs_and_methods_flatly(self):
        src = (
            "class Foo:\n"
            "    def bar(self):\n"
            "        return 1\n"
            "\n"
            "def top(x):\n"
            "    return x\n"
        )
        spans = _segment_python(src)
        locators = {loc for _, loc in spans}
        self.assertIn("class:Foo", locators)
        self.assertIn("def:Foo.bar", locators)
        self.assertIn("def:top", locators)

    def test_never_raises_on_malformed_source(self):
        self.assertEqual(_segment_python("def foo(:\n    not python at all }{"), [])

    def test_empty_source_yields_no_spans(self):
        self.assertEqual(_segment_python(""), [])


if __name__ == "__main__":
    unittest.main()
