"""Item 4 spellcheck stage: BUILT, then DROPPED on its own controls. Recorded here.

The ruling: "Ship only on green controls (dirty-input null improves; clean-corpus verdicts
bit-identical; lexicon words never touched); else drop and record."

Three controls, applied honestly:

1. **dirty-input null improves — PASSES.** A typo folds onto its dictionary word, so the
   two share an address. The mechanism works.
2. **clean-corpus verdicts bit-identical — FAILS with the shipped dictionary.** A small
   dictionary treats every correctly-spelled word it lacks as a non-word, and edit-1
   correction then *mangles* common words (`and -> add`, `it -> is`, `we -> be`). On any
   realistic corpus this moves addresses that should not move. It would pass only with a
   comprehensive (hunspell-class) dictionary, which is a pinned artifact not available this
   round — the same shape as D8's dumps.
3. **lexicon words never touched — PASSES.** The allow-list protects domain terms.

Two of three green is not three of three, so **the stage does not ship**: `SPELLCHECK_ENABLED`
stays `false`, and this file pins control 2's failure so nobody flips it on with an
inadequate dictionary. The mechanism is retained (correct and inert when off) so that if a
comprehensive pinned dictionary lands later, enabling it is one seed-morphism away — and
control 2 becomes the gate that must pass first.
"""

from __future__ import annotations

import unittest

from engine.normalize import nu
from engine.spell import allow_list_from_seed, correct_token, spellcheck_prose


class Control1DirtyInputImproves_PASSES(unittest.TestCase):
    """The mechanism works: a typo variant folds onto the correct word's address."""

    def test_a_misspelling_folds_onto_its_dictionary_word(self):
        allow = allow_list_from_seed()
        self.assertEqual(correct_token("positvie", _dic(), allow), "positive")
        self.assertEqual(correct_token("positiv", _dic(), allow), "positive")

    def test_the_stage_would_collapse_typo_variants_to_one_address(self):
        clean, typo = "the cone is positive", "the cone is positvie"
        self.assertNotEqual(nu("english", clean), nu("english", typo))
        with _spell_on():
            self.assertEqual(nu("english", clean), nu("english", typo))

    def test_a_nonword_with_no_edit1_word_is_left_alone_not_guessed(self):
        self.assertEqual(correct_token("qwertyxyz", _dic(), allow_list_from_seed()),
                         "qwertyxyz", "the stage corrects, it does not invent")


class Control2CleanCorpusIsBitIdentical_FAILS(unittest.TestCase):
    """The blocker. A small dictionary mangles correctly-spelled common words.

    Pinned so the drop is auditable: these words are all spelled correctly, and the stage
    changes them anyway, because they are absent from the shipped dictionary and have edit-1
    neighbours that are present.
    """

    def test_correctly_spelled_common_words_are_mangled_by_a_small_dictionary(self):
        real = "the cone is positive and it remains positive whenever we compose maps"
        corrected, corrections = spellcheck_prose(real, allow=allow_list_from_seed())
        mangled = {(c.span, c.to) for c in corrections}
        self.assertIn(("and", "add"), mangled)
        self.assertNotEqual(corrected, real,
                            "a clean corpus is NOT bit-identical under the stage — control 2 "
                            "fails, so the stage does not ship")

    def test_this_is_exactly_why_the_stage_ships_off(self):
        from engine.constants import SPELLCHECK_ENABLED

        self.assertFalse(SPELLCHECK_ENABLED,
                         "control 2 is red with this dictionary, so the stage stays off")


class Control3LexiconWordsAreNeverTouched_PASSES(unittest.TestCase):
    def test_allow_listed_terms_pass_through_unchanged(self):
        allow = allow_list_from_seed()
        self.assertTrue(allow)
        for term in list(allow):
            self.assertEqual(correct_token(term, _dic(), allow), term,
                             f"allow-listed {term!r} must never be corrected")

    def test_a_domain_lemma_absent_from_the_dictionary_is_still_protected(self):
        allow, dic = allow_list_from_seed(), _dic()
        protected = sorted(t for t in allow if t not in dic and len(t) > 3)
        self.assertTrue(protected, "there must be a lexicon term outside the dictionary")
        for term in protected[:20]:
            self.assertEqual(correct_token(term, dic, allow), term)


class TheMechanismIsSoundEvenThoughItDidNotShip(unittest.TestCase):
    """The properties that would matter *if* a comprehensive dictionary landed."""

    def test_off_by_default_so_nu_is_unchanged(self):
        from engine.constants import SPELLCHECK_ENABLED

        self.assertFalse(SPELLCHECK_ENABLED)
        # With the stage off, a typo does NOT fold — the current pipeline is untouched.
        self.assertNotEqual(nu("english", "the cone is positive"),
                            nu("english", "the cone is positvie"))

    def test_correction_is_idempotent_when_on(self):
        with _spell_on():
            for s in ("the cone is positvie", "positiv under compositon"):
                once = nu("english", s)
                self.assertEqual(once, nu("english", once), f"nu(nu(x)) != nu(x) for {s!r}")

    def test_correction_is_deterministic_smallest_word(self):
        dic = frozenset({"cat", "bat", "hat"})
        self.assertEqual(correct_token("zat", dic, frozenset()), "bat")

    def test_the_diff_log_has_spans_and_counts(self):
        from engine.spell import summarize_corrections

        _, corrections = spellcheck_prose("positvie positvie positiv",
                                          allow=allow_list_from_seed())
        summary = summarize_corrections(corrections)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["distinct_spans"], 2)
        counts = {(d["span"], d["to"]): d["count"] for d in summary["diffs"]}
        self.assertEqual(counts[("positvie", "positive")], 2)
        self.assertEqual(counts[("positiv", "positive")], 1)

    def test_the_locator_points_at_the_raw_span(self):
        text = "alpha positvie beta"
        _, corrections = spellcheck_prose(text, allow=allow_list_from_seed())
        c = corrections[0]
        self.assertEqual(text[c.locator:c.locator + len(c.span)], c.span,
                         "raw bytes stay the provenance target")


def _dic():
    from engine.spell import _dictionary
    return _dictionary()


class _spell_on:
    def __enter__(self):
        import engine.normalize as nm
        self._prev = nm.SPELLCHECK_ENABLED
        nm.SPELLCHECK_ENABLED = True
        return self

    def __exit__(self, *exc):
        import engine.normalize as nm
        nm.SPELLCHECK_ENABLED = self._prev


if __name__ == "__main__":
    unittest.main()
