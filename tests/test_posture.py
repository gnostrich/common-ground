"""THE UTTERANCE'S ACT, READ — and the inversion that makes reading safe.

Posture, retain and claim were toggles set before speaking. Read off the speaking they become
one more gated proposal: EXTRACTION tier, through the one inlet, wrong sometimes, correctable.

THE SAFETY ARGUMENT IS THE INVERSION. Everywhere else an unknown mode defaults to ASSERT,
because defaulting the other way would strip warrant from something the operator meant to
stand behind. When the machine READS rather than being told, the risk reverses: a misread that
invents a claim confers authorship nobody asserted. When unsure whether you claimed, assume
you didn't.
"""

import unittest

from engine.mode import ASSERT, BRAINSTORM
from engine.posture import (ACT_GRAMMAR, ACTS, CLAIM_ACT, CONSERVATIVE, DISCARD, EXPLORE_ACT,
                            KEEP, Reading, correct, parse, resolve_claim)


class ItReadsADeclaredTokenNeverProse(unittest.TestCase):

    def test_the_act_vocabulary_is_closed(self):
        self.assertEqual(("assert", "explore", "claim-of"), ACTS)

    def test_each_declared_act_is_read(self):
        self.assertEqual("explore", parse("ACT: explore keep-nothing").act)
        self.assertEqual("assert", parse("ACT: assert keep").act)
        self.assertEqual(7, parse("ACT: claim-of 7 keep").claim_index)

    def test_PROSE_that_sounds_like_a_claim_reads_nothing(self):
        # A reading inferred from the shape of a sentence would be a fluency judgement
        # steering warrant. The token is the only channel.
        for prose in ("that's mine, definitely keep it",
                      "yes exactly — I assert that",
                      "claim that one please"):
            r = parse(prose)
            self.assertEqual(EXPLORE_ACT, r.act, prose)
            self.assertEqual(BRAINSTORM, r.mode)

    def test_the_module_holds_no_similarity_machinery(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "posture.py").read_text()
        for banned in ("difflib", "SequenceMatcher", ".lower().split", "Counter("):
            self.assertNotIn(banned, src)


class TheConservativeDirectionINVERTS(unittest.TestCase):
    """When unsure whether you claimed, assume you didn't."""

    def test_the_conservative_reading_is_explore_keep_nothing(self):
        self.assertEqual((EXPLORE_ACT, DISCARD), CONSERVATIVE)

    def test_a_PLANTED_AMBIGUOUS_utterance_reads_conservatively_and_SAYS_SO(self):
        # The planted control: ambiguity must produce a displayed reading, not a silent guess.
        for raw in ("", "no act line at all", "ACT: assert\nACT: claim-of 3", "ACT: claim-of"):
            r = parse(raw)
            self.assertEqual(EXPLORE_ACT, r.act)
            self.assertEqual(DISCARD, r.persistence)
            self.assertTrue(r.reason, "a default nobody is told about is a reading")
            self.assertIn("reading this as", r.render())

    def test_ambiguity_never_resolves_toward_claiming(self):
        for raw in ("ACT: claim-of", "ACT: assert\nACT: explore", "garbage"):
            self.assertNotEqual(CLAIM_ACT, parse(raw).act)
            self.assertFalse(parse(raw).retains)

    def test_the_inversion_is_opposite_to_the_TOLD_default(self):
        # engine.mode: an unknown TOLD mode is ASSERT. An unread act is EXPLORE. The two
        # defaults point opposite ways on purpose, and both are the safe direction for their
        # own failure mode.
        from engine.mode import normalize
        self.assertEqual(ASSERT, normalize("garbage"))
        self.assertEqual(BRAINSTORM, parse("garbage").mode)


class MisreadsAreVISIBLE(unittest.TestCase):

    def test_every_reading_renders_a_line_for_the_top_of_the_response(self):
        for raw in ("ACT: explore keep-nothing", "ACT: assert keep", "ACT: claim-of 4 keep", ""):
            self.assertTrue(parse(raw).render().startswith("reading this as:"))

    def test_the_line_states_both_coordinates(self):
        self.assertIn("keeping nothing", parse("ACT: explore keep-nothing").render())
        self.assertIn("keeping it", parse("ACT: assert keep").render())

    def test_a_reading_always_carries_its_reason(self):
        for raw in ("ACT: assert keep", "", "ACT: claim-of"):
            self.assertTrue(parse(raw).reason)


class ClaimOfResolvesToDISPLAYEDBytesOrVOIDS(unittest.TestCase):

    def test_a_resolvable_claim_returns_the_displayed_bytes_verbatim(self):
        text = "the cone is positive under composition"
        surface, void = resolve_claim(parse("ACT: claim-of 2 keep"), {2: text})
        self.assertEqual(text, surface)
        self.assertEqual("", void)

    def test_an_unresolvable_index_VOIDS_rather_than_reconstructing(self):
        # A pullback onto a reconstruction would land on something the operator never read.
        surface, void = resolve_claim(parse("ACT: claim-of 9 keep"), {1: "a", 2: "b"})
        self.assertEqual("", surface)
        self.assertIn("VOID", void)

    def test_an_empty_displayed_sentence_VOIDS(self):
        self.assertEqual("", resolve_claim(parse("ACT: claim-of 1 keep"), {1: "  "})[0])

    def test_a_non_claim_reading_resolves_to_nothing(self):
        self.assertEqual(("", "not a claim"),
                         resolve_claim(parse("ACT: explore keep-nothing"), {1: "x"}))


class ACorrectionRestampsWithAnERATRAIL(unittest.TestCase):

    def test_the_prior_reading_is_KEPT_not_overwritten(self):
        prior = parse("ACT: explore keep-nothing", era="e1")
        fixed = correct(prior, parse("ACT: assert keep", era="e2"))
        self.assertEqual("assert", fixed.act)
        self.assertEqual(1, len(fixed.superseded))
        self.assertEqual("explore", fixed.superseded[0]["act"])

    def test_the_trail_accumulates_across_corrections(self):
        a = parse("ACT: explore keep-nothing", era="e1")
        b = correct(a, parse("ACT: assert keep", era="e2"))
        c = correct(b, parse("ACT: claim-of 3 keep", era="e3"))
        self.assertEqual(2, len(c.superseded))
        self.assertEqual(["explore", "assert"], [s["act"] for s in c.superseded])

    def test_the_correction_says_it_was_corrected(self):
        fixed = correct(parse("ACT: explore keep-nothing"), parse("ACT: assert keep"))
        self.assertIn("corrected by the operator", fixed.reason)

    def test_the_era_travels(self):
        self.assertEqual("e9", correct(parse("ACT: explore keep-nothing"),
                                       parse("ACT: assert keep", era="e9")).era)


class TheLocksAreUnchanged(unittest.TestCase):

    def test_a_read_claim_still_enters_through_the_pullback(self):
        # The reading decides how an utterance is TREATED. It confers nothing by itself: the
        # claim still needs displayed bytes and a source record.
        from engine.claim import claim
        r = parse("ACT: claim-of 1 keep")
        surface, _ = resolve_claim(r, {1: "the cone is positive"})
        c = claim(surface, "english", claimed_from="rec-3", source_mode=r.mode)
        self.assertEqual("AUTHORSHIP", c.as_record()["tier"])
        self.assertEqual("rec-3", c.claimed_from)

    def test_a_reading_cannot_manufacture_a_claim_without_bytes(self):
        from engine.claim import claim
        surface, void = resolve_claim(parse("ACT: claim-of 99 keep"), {1: "x"})
        self.assertTrue(void)
        with self.assertRaises(ValueError):
            claim(surface, "english", claimed_from="rec-3")


class TheGrammarLineIsCodomainSyntax(unittest.TestCase):
    """The razor: one sentence, stating the output syntax, no policy."""

    def test_it_states_the_form_and_nothing_else(self):
        self.assertIn("ACT:", ACT_GRAMMAR)
        for banned in ("should", "prefer", "remember", "important", "carefully"):
            self.assertNotIn(banned, ACT_GRAMMAR.lower())

    def test_it_is_one_sentence(self):
        self.assertEqual(1, ACT_GRAMMAR.count("."))


if __name__ == "__main__":
    unittest.main()


class TheGrammarIsCaseEXACT(unittest.TestCase):
    """Resolve-or-void applied to case, rather than an exemption argued for folding.

    An earlier version matched case-insensitively and folded the token to canonicalise it. The
    referee sweep refused it — folding is folding whatever it is folding — and the fix was to
    remove the fold, not to argue for it. A token in the wrong case does not match and reads
    conservatively, which is the same discipline every other resolution here follows.
    """

    def test_the_declared_lowercase_token_matches(self):
        self.assertEqual("assert", parse("ACT: assert keep").act)

    def test_a_miscased_token_reads_CONSERVATIVELY_rather_than_being_folded(self):
        for raw in ("ACT: ASSERT keep", "ACT: Claim-Of 3 keep", "ACT: Explore KEEP"):
            r = parse(raw)
            self.assertEqual(EXPLORE_ACT, r.act, raw)
            self.assertFalse(r.retains, raw)

    def test_the_module_folds_no_case_at_all(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "posture.py").read_text()
        body = src[src.index("def parse("):]
        self.assertNotIn(".lower()", body)
        self.assertNotIn(".casefold()", body)
