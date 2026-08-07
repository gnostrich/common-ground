"""THE CONSTITUTION IS CHECKED, not merely written.

B1: every OI-n resolves to real sites and real controls, or the auditor FAILS.
B2: a control that must fire and doesn't is RED — silence never reads as pass.
B5: anything not traceable to SPEC.md or an OI-n is unconstitutional by default.

These execute the registry builder and the resolver. A registry naming controls that do not
exist would be the map-not-territory failure applied to the constitution itself, and building
it caught three such entries on its first pass — one of them because the RESOLVER was wrong.
"""

import json
import unittest
from pathlib import Path

from tools.build_registry import MAP, build, resolves, statements

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "seed" / "CONSTITUTION.md"
REG = REPO / "seed" / "OI_REGISTRY.json"


class TheDocumentIsPresentAndComplete(unittest.TestCase):

    def test_the_constitution_is_in_seed(self):
        self.assertTrue(DOC.exists(), "CONSTITUTION.md is normative and must be in seed/")

    def test_every_invariant_is_numbered_contiguously_from_one(self):
        """Counted from the DOCUMENT, not pinned to 40.

        The registry grows: every operator catch appends an OI-n+1 the same day, so a control
        asserting a fixed count fails the moment the discipline it defends is followed. What
        must hold is that the numbering has no gaps — a missing OI-n means an invariant was
        deleted or never written, and both are findings.
        """
        s = statements()
        self.assertGreaterEqual(len(s), 41)
        for i in range(1, len(s) + 1):
            self.assertIn(f"OI-{i}", s, f"the registry skips OI-{i}")

    def test_every_invariant_carries_a_statement(self):
        for oi, text in statements().items():
            self.assertGreater(len(text), 40, f"{oi} has no statement")


class B1EveryEntryRESOLVES(unittest.TestCase):
    """The registry names things that exist. Checked by AST, not by plausibility."""

    def test_the_registry_builds_with_nothing_unresolvable(self):
        reg = build()
        self.assertEqual([], reg["unresolved"],
                         "an OI names a site or control that does not exist")

    def test_every_invariant_has_an_entry(self):
        reg = build()
        self.assertEqual(len(statements()), reg["count"])
        self.assertEqual(set(statements()), set(reg["entries"]))

    def test_the_committed_registry_matches_the_document(self):
        # Drift here means the JSON was written from an older constitution. Never silently
        # reconciled: the auditor reports it and the operator rules which side moved.
        self.assertTrue(REG.exists())
        self.assertEqual(json.loads(REG.read_text())["entries"], build()["entries"])

    def test_the_resolver_finds_a_class_a_function_and_an_annotated_constant(self):
        # THE RESOLVER'S OWN CONTROL. Its first version missed AnnAssign, so `BLOCKS:
        # tuple[...] = (...)` — a symbol that plainly exists — reported as unresolvable. The
        # resolver failing the resolution check it performs is the exact class this registry
        # exists to prevent.
        self.assertTrue(resolves("engine/scaffold.py:Scaffold"))
        self.assertTrue(resolves("engine/scaffold_lean.py:parse"))
        self.assertTrue(resolves("engine/grammar.py:BLOCKS"))

    def test_the_resolver_REFUSES_a_symbol_that_is_absent(self):
        self.assertFalse(resolves("engine/scaffold.py:NoSuchSymbolAnywhere"))
        self.assertFalse(resolves("engine/no_such_module.py"))

    def test_a_planted_unresolvable_entry_would_be_reported(self):
        # The registry's own RED. Without this, "0 unresolvable" could mean the check is dead.
        self.assertFalse(resolves("tests/test_constitution.py:AClassThatDoesNotExist"))


class WeakEntriesAreNAMEDNotHidden(unittest.TestCase):
    """An invariant with no control is WEAK, listed, and shrinks deliberately."""

    def test_weak_entries_are_exactly_the_process_only_ones(self):
        reg = build()
        for oi in reg["weak"]:
            self.assertEqual([], reg["entries"][oi]["controls"], f"{oi} is weak but has a control")
        for oi, entry in reg["entries"].items():
            if entry["controls"]:
                self.assertNotIn(oi, reg["weak"])

    def test_the_weak_list_is_the_work_queue_and_is_reported(self):
        reg = build()
        self.assertTrue(reg["weak"], "if nothing is weak, say so deliberately")
        self.assertLess(len(reg["weak"]), 20,
                        "more than half the constitution unmechanized is a finding")

    def test_mechanizing_a_weak_entry_removes_it_from_the_list(self):
        # The list must be able to shrink, or reporting it is decoration.
        import copy
        saved = copy.deepcopy(MAP)
        try:
            MAP["OI-40"] = {"C": ["tests/test_constitution.py:WeakEntriesAreNAMEDNotHidden"]}
            self.assertNotIn("OI-40", build()["weak"])
        finally:
            MAP.clear()
            MAP.update(saved)


class B4TheAmendmentRule(unittest.TestCase):
    """CC may propose; never merge. The section exists and stays empty until ruled."""

    def test_the_amendments_section_exists(self):
        self.assertIn("## AMENDMENTS", DOC.read_text(encoding="utf-8"))

    def test_the_amendment_rule_states_that_cc_never_merges(self):
        self.assertIn("CC may propose; never merge", DOC.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class WatchIsNotWeak(unittest.TestCase):
    """The registry must be able to say "unenforced clause" without saying "missing control".

    WEAK names an invariant with NO control — a debt somebody owes. WATCH names an unenforced
    CLAUSE inside an invariant whose other clauses are enforced, where the ruling is explicitly
    that no control is owed until the failure is OBSERVED. Filing one as the other either
    manufactures a debt nobody owes, or hides one somebody does.

    OI-45 is the first: "minimal" has no explicit check, nothing today prevents a valid but
    larger-than-needed completion, and the derivation seed for a check is a real observed
    instance rather than a hypothetical.
    """

    def setUp(self):
        import json

        self.reg = json.loads((REPO / "seed" / "OI_REGISTRY.json").read_text())

    def test_the_registry_carries_a_watch_list(self):
        self.assertIn("watch", self.reg)

    def test_a_watch_entry_is_NOT_in_the_weak_list(self):
        for oi in self.reg["watch"]:
            with self.subTest(oi=oi):
                self.assertNotIn(oi, self.reg["weak"],
                                 f"{oi} is watched, not owed — it has a control")

    def test_a_watched_entry_still_HAS_controls(self):
        """That is exactly what separates it from WEAK. If it had none it would be a debt."""
        for oi in self.reg["watch"]:
            with self.subTest(oi=oi):
                self.assertTrue(self.reg["entries"][oi]["controls"])

    def test_the_watch_reason_is_SPECIFIC_about_what_would_derive_the_check(self):
        """A watch that says only "todo" is a WEAK entry wearing a softer word."""
        for oi, why in self.reg["watch"].items():
            with self.subTest(oi=oi):
                self.assertGreater(len(why), 60, why)
                self.assertNotIn("todo", why.lower())

    def test_OI45_is_watched_and_says_why(self):
        self.assertIn("OI-45", self.reg["watch"])
        self.assertIn("minimal", self.reg["watch"]["OI-45"].lower())
