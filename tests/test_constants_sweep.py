"""OI-4's ENFORCEMENT, executed. Every constant claims derived, swept or confessed.

The invariant existed and its control did not: the auditor invoked `tests.test_constants`, a
module that has never existed. It reported the failure as a FINDING rather than a pass — the
auditor working — but the check had never run once. An invariant with a dead control is an
invariant on paper, and this is the class the map-is-not-the-territory law names.
"""

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from engine.constants_sweep import (LEGAL, NOT_OBJECT_CONSTANTS, constants, provenance,
                                    render, unmarked)

REPO = Path(__file__).resolve().parent.parent


class TheSweepFindsThePopulation(unittest.TestCase):

    def _tree(self, body):
        d = Path(tempfile.mkdtemp())
        (d / "m.py").write_text(textwrap.dedent(body))
        return d

    def test_a_module_level_numeric_constant_is_found(self):
        got = constants(self._tree("BETA = 1.0\n"))
        self.assertEqual([("m.py", "BETA", "1.0")], got)

    def test_an_annotated_constant_is_found(self):
        self.assertEqual(1, len(constants(self._tree("CAP: int = 400\n"))))

    def test_a_computed_constant_is_found(self):
        self.assertEqual([("m.py", "WINDOW", "128")],
                         constants(self._tree("WINDOW = 2 * 64\n")))

    def test_a_LOCAL_is_not_a_constant_of_the_object(self):
        self.assertEqual([], constants(self._tree("def f():\n    x = 0.35\n    return x\n")))

    def test_a_lowercase_name_is_not_a_constant(self):
        self.assertEqual([], constants(self._tree("beta = 1.0\n")))

    def test_a_boolean_is_not_a_numeric_constant(self):
        self.assertEqual([], constants(self._tree("ENABLED = True\n")))


class EveryEngineConstantCLAIMSAProvenance(unittest.TestCase):

    def test_the_engine_is_clean(self):
        found = unmarked()
        self.assertEqual([], found, render(found))

    def test_every_engine_constant_has_an_entry(self):
        known = provenance()
        for _, name, _ in constants():
            self.assertIn(name, known, f"{name} claims no provenance")

    def test_every_provenance_is_one_of_the_three(self):
        for name, entry in provenance().items():
            self.assertIn(entry["provenance"], LEGAL, f"{name} claims {entry['provenance']!r}")

    def test_every_entry_carries_an_ARGUMENT_not_just_a_label(self):
        # A label is not a derivation. "derived" with no reason is a number wearing a word.
        for name, entry in provenance().items():
            self.assertGreater(len(entry.get("why", "")), 40, f"{name} labels without arguing")


class PlantedDefects(unittest.TestCase):
    """The sweep must FAIL on each shape it exists to catch."""

    def _with(self, mapping):
        import engine.constants_sweep as mod
        d = Path(tempfile.mkdtemp())
        (d / "m.py").write_text("PLANTED = 0.42\n")
        p = d / "prov.json"
        p.write_text(json.dumps({"constants": mapping}))
        keep = mod.PROVENANCE
        mod.PROVENANCE = p
        try:
            return mod.unmarked(d)
        finally:
            mod.PROVENANCE = keep

    def test_an_unmarked_constant_is_RED(self):
        found = self._with({})
        self.assertEqual(1, len(found))
        self.assertIn("no provenance", found[0].reason)

    def test_an_ILLEGAL_provenance_is_RED(self):
        found = self._with({"PLANTED": {"provenance": "obvious", "why": "it just is, clearly"}})
        self.assertEqual(1, len(found))
        self.assertIn("not one of", found[0].reason)

    def test_a_provenance_with_NO_ARGUMENT_is_RED(self):
        found = self._with({"PLANTED": {"provenance": "derived", "why": ""}})
        self.assertEqual(1, len(found))
        self.assertIn("a label is not a derivation", found[0].reason)

    def test_a_properly_marked_constant_passes(self):
        self.assertEqual([], self._with({"PLANTED": {
            "provenance": "confessed",
            "why": "chosen, and said to be chosen; a sweep on the battery would settle it"}}))


class TheExclusionsAreENUMERATEDNotPatterned(unittest.TestCase):
    """A pattern would quietly absorb the next real constant somebody names MAX_something."""

    def test_exclusions_are_a_named_set(self):
        self.assertIsInstance(NOT_OBJECT_CONSTANTS, frozenset)
        self.assertIn("DISPLAY_WIDTH", NOT_OBJECT_CONSTANTS)

    def test_the_physical_constants_are_NOT_excluded(self):
        for name in ("READ_BETA", "BIAS_WEIGHT", "DECLARED_WEIGHT", "BORN"):
            self.assertNotIn(name, NOT_OBJECT_CONSTANTS)


class TheOpenBetaIsCONFESSEDNotDressed(unittest.TestCase):
    """OI-4 lists beta as OPEN. Its entry must say so rather than manufacture a derivation."""

    def test_read_beta_is_confessed(self):
        entry = provenance()["READ_BETA"]
        self.assertEqual("confessed", entry["provenance"])
        self.assertIn("audit", entry["why"])

    def test_the_confession_names_what_would_settle_it(self):
        why = provenance()["READ_BETA"]["why"]
        self.assertIn("sweep", why)
        self.assertIn("stable band", why)

    def test_most_constants_are_confessed_and_that_is_reported_honestly(self):
        # 20 of 24. The point of the sweep is not to make that number small by relabelling;
        # it is to make it VISIBLE so it can be shrunk by measurement.
        kinds = [e["provenance"] for e in provenance().values()]
        self.assertGreater(kinds.count("confessed"), kinds.count("derived"))


if __name__ == "__main__":
    unittest.main()
