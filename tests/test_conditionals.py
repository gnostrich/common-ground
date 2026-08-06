"""OI-5, MECHANIZED: a conditional in a ruling either cites a control or it is hope.

"as long as X" in a normative sentence is one of two things. If X is a gate the clause is
redundant, because the gate already refuses. If X is nothing the clause is hope wearing the
grammar of a constraint — a ruling that has not been decided yet, written so it reads as
though it has. Constraints are controls, not clauses.

THE REAL NORMATIVE TEXT IS ALREADY CLEAN, which is exactly why the planted arm carries the
weight here. A control whose only evidence is a green scan over clean files has proved nothing
about itself; every assertion below that matters runs the linter on text written to trip it.

USE VERSUS MENTION is the one real subtlety, and it is not a technicality: OI-5's own statement
contains the words "as long as X" because it quotes the phrase it forbids. A linter that could
not tell quoting from asserting would fire on the sentence defining the rule — the same
self-reference that made an earlier key-exposure control fail the moment its assertion was
written into the file it was grepping.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from engine.conditionals import TELLS, findings, mentioned, sentences

REPO = Path(__file__).resolve().parent.parent

#: The documents OI-5 governs. Rulings and specifications — not code, where a conditional is
#: ordinary description, and not INVENTORY.md, which RECORDS conditionals other people wrote.
NORMATIVE = ("seed/CONSTITUTION.md", "seed/GATES.md", "seed/DECISIONS.md", "seed/SPEC.md",
             "seed/OBJECT.md", "seed/OBJECT-AMENDED.md", "seed/DIALOGIC.md")


def normative_blobs() -> dict:
    out = {}
    for rel in NORMATIVE:
        p = REPO / rel
        if p.exists():
            out[rel] = p.read_text(encoding="utf-8")
    return out


class ThePlantedArmCarriesTheWeight(unittest.TestCase):
    """Runs on text written to trip it, because the real files are clean."""

    def test_an_uncited_conditional_is_FOUND(self):
        f = findings({"r.md": "This lands as long as the corpus is fresh."})
        self.assertEqual(len(f), 1, f)
        self.assertEqual(f[0]["tell"], "as long as")

    def test_every_tell_in_the_vocabulary_actually_fires(self):
        """A tell nobody can trigger is decoration in the list."""
        for tell in TELLS:
            with self.subTest(tell=tell):
                self.assertTrue(findings({"r.md": f"We ship {tell} the weather holds."}),
                                f"{tell!r} is in TELLS and matches nothing")

    def test_a_conditional_citing_a_GATE_is_forgiven(self):
        self.assertEqual(findings({"r.md": "This lands as long as gate 6 passes."}), [])

    def test_a_conditional_citing_an_OI_or_a_CONTROL_is_forgiven(self):
        self.assertEqual(findings({"r.md": "Retained as long as OI-41 holds."}), [])
        self.assertEqual(
            findings({"r.md": "Kept as long as tests/test_claim.py stays green."}), [])

    def test_citing_something_that_does_NOT_refuse_is_still_found(self):
        """'as long as the team agrees' points at no control. That is the whole defect."""
        self.assertTrue(findings({"r.md": "We proceed as long as everyone is comfortable."}))

    def test_the_finding_NAMES_the_sentence(self):
        """A linter that reports a count gives nobody anything to fix."""
        f = findings({"r.md": "This lands as long as the corpus is fresh."})
        self.assertIn("corpus is fresh", f[0]["sentence"])
        self.assertEqual(f[0]["path"], "r.md")


class QuotingIsNotAsserting(unittest.TestCase):
    """Use versus mention. OI-5's own statement quotes the phrase it forbids."""

    def test_a_quoted_tell_is_not_a_finding(self):
        self.assertEqual(
            findings({"r.md": 'Conditional language is a tell — "as long as X" is hope.'}), [])

    def test_a_backticked_tell_is_not_a_finding(self):
        self.assertEqual(findings({"r.md": "The phrase `as long as` is the tell."}), [])

    def test_a_tell_USED_in_the_same_sentence_as_a_quoted_one_IS_found(self):
        """The dangerous case: quote the rule, then break it in the same breath. `mentioned`
        requires EVERY occurrence to be inside quotes, so one loose use still fires."""
        s = 'The phrase "as long as" is a tell, and we ship as long as it feels right.'
        self.assertTrue(findings({"r.md": s}))
        self.assertFalse(mentioned(s, "as long as"))

    def test_mentioned_is_true_only_when_every_occurrence_is_quoted(self):
        self.assertTrue(mentioned('"as long as" and `as long as`', "as long as"))
        self.assertFalse(mentioned('as long as we like', "as long as"))


class TheREALNormativeTextIsClean(unittest.TestCase):
    """The standing arm. It passes today; the planted class is what proves it could fail."""

    def test_no_uncited_conditional_in_any_normative_document(self):
        blobs = normative_blobs()
        self.assertTrue(blobs, "NOT CHECKED: no normative documents found — that is a bug in "
                               "this control's file list, not a clean result")
        f = findings(blobs)
        self.assertEqual(f, [], "uncited conditionals in normative text: "
                                + "; ".join(f"{x['path']}: {x['sentence']}" for x in f[:4]))

    def test_the_constitution_is_actually_being_scanned(self):
        """Guards the vacuous pass: if the file list silently missed the constitution, the
        green above would mean nothing."""
        self.assertIn("seed/CONSTITUTION.md", normative_blobs())

    def test_OI5s_own_statement_survives_its_own_rule(self):
        """It quotes 'as long as X'. If the linter flagged it, the rule would forbid its own
        definition — and the temptation would be to exempt the file rather than fix the
        linter, which is how a control gets quietly defanged."""
        doc = (REPO / "seed" / "CONSTITUTION.md").read_text()
        oi5 = [s for s in sentences(doc) if "OI-5" in s or "as long as" in s.lower()]
        self.assertTrue(oi5, "OI-5's statement was not found; the file list may be wrong")
        self.assertEqual(findings({"seed/CONSTITUTION.md": doc}), [])


class ScopeIsNORMATIVETextOnly(unittest.TestCase):
    """In code a conditional is description, and running there would produce noise."""

    def test_code_is_not_in_the_scanned_set(self):
        for rel in NORMATIVE:
            self.assertFalse(rel.endswith(".py"), rel)

    def test_the_inventory_is_NOT_scanned_and_the_reason_is_stated(self):
        """INVENTORY.md records conditionals other people wrote, quoted as evidence. Scanning
        it would flag the ledger for faithfully reporting a defect."""
        self.assertNotIn("seed/INVENTORY.md", NORMATIVE)

    def test_the_residual_false_positive_is_CONFESSED_not_hidden(self):
        """Mood is not detected. A descriptive conditional in a normative document will be
        flagged, and the module says so rather than widening the exemption to hide it."""
        import engine.conditionals as m

        doc = " ".join((m.__doc__ or "").split())
        self.assertIn("false positive this module cannot remove", doc)


class TheExemptionIsANamedLineNotACategory(unittest.TestCase):
    """The linter found one real descriptive conditional on its first run over the real files.

    Dropping OBJECT-AMENDED.md from scope would have cleared it in one line and been the wrong
    fix: the document contains rulings too, and exempting a file to clear a hit in its
    narrative is how a control gets defanged by the person it inconveniences.
    """

    def test_the_allowlist_is_short_enough_to_READ(self):
        from engine.conditionals import KNOWN_DESCRIPTIVE

        self.assertLessEqual(len(KNOWN_DESCRIPTIVE), 5,
                             "past a handful this is not an allowlist, it is a scope error")

    def test_each_entry_is_a_SENTENCE_fragment_not_a_path(self):
        """A path here would be a category exemption wearing an allowlist's clothes."""
        from engine.conditionals import KNOWN_DESCRIPTIVE

        for k in KNOWN_DESCRIPTIVE:
            self.assertNotIn("/", k, f"{k!r} looks like a path, not a sentence")
            self.assertGreater(len(k), 25, f"{k!r} is short enough to match by accident")

    def test_the_exemption_does_NOT_forgive_the_same_words_used_as_a_RULING(self):
        """The allowlisted fragment is specific to its sentence. A ruling that happens to
        contain 'for as long as the' must still be caught."""
        self.assertTrue(findings({"r.md": "We keep the arrow for as long as the operator "
                                          "finds it useful."}))

    def test_OBJECT_AMENDED_is_still_IN_scope(self):
        self.assertIn("seed/OBJECT-AMENDED.md", NORMATIVE)


if __name__ == "__main__":
    unittest.main()
