"""NOMINATION: it selects a neighbourhood and decides nothing.

The defect it answers, measured: region seeding drew from the arrow-richest slots, that set
was 71% one repository holding 15% of the material, and a question about certified positivity
could draw 2 of 512 eligible slots from that provenance. Arrow density is self-reinforcing, so
the walk's own history answered every topic regardless of what was asked.

The line these controls defend is the one that makes it legal at all: a phrase the corpus
literally contains is a declared fact about that claim's TEXT. It nominates. It never relates.
"""

import unittest

from engine.nominate import MAX_NOMINATED, MIN_PHRASE, nominate, phrases


class _Rec:
    def __init__(self, nu, chart="english"):
        self.nu, self.chart, self.type = nu, chart, "assert"
        self.docs = ()


class _Snap:
    def __init__(self, mapping):
        self.slots = {k: _Rec(v) for k, v in mapping.items()}


class ItNominatesWhereThePhraseLITERALLYIs(unittest.TestCase):

    def test_a_phrase_the_corpus_holds_nominates_its_carriers(self):
        snap = _Snap({"a": "certified positivity is established here",
                      "b": "unrelated material about pad models",
                      "c": "more on certified positivity and its bounds"})
        n = nominate(snap, "what does the certified positivity work establish")
        self.assertEqual(("a", "c"), n["slots"])
        self.assertEqual("certified positivity", n["phrase"])

    def test_it_prefers_the_LONGER_LITERAL_STRING_not_the_longer_word_run(self):
        # THE DEFECT THIS REPLACED: ranking by word count picked "what does the" — three
        # function words — over "certified positivity", so a real question landed in the
        # wrong corpus for a purely grammatical reason. Character length needs no stopword
        # list, which matters because a stopword list is a vocabulary judgement this module
        # is not allowed to make.
        snap = _Snap({"fn": "what does the pad model do",
                      "topic": "certified positivity bounds the spectrum"})
        self.assertEqual("certified positivity",
                         nominate(snap, "what does the certified positivity work")["phrase"])

    def test_a_phrase_absent_from_the_corpus_nominates_nothing_and_says_so(self):
        n = nominate(_Snap({"a": "pad models and track roles"}), "holonomy of the connection")
        self.assertEqual((), n["slots"])
        self.assertIn("does not occur", n["reason"].replace("no phrase of the typed text "
                                                            "occurs", "does not occur"))

    def test_a_phrase_carried_by_too_much_of_the_corpus_FALLS_BACK_and_says_so(self):
        # A nomination selecting most of the corpus is the same as no nomination while
        # looking like a result. It must not return an arbitrary slice.
        snap = _Snap({f"s{i}": "the settled state of the field" for i in range(MAX_NOMINATED + 5)})
        n = nominate(snap, "what is the settled state of the field")
        self.assertEqual((), n["slots"])
        self.assertIn("too broad", n["reason"])
        self.assertGreater(n["occurrences"], MAX_NOMINATED)

    def test_short_fragments_are_not_nominated_on(self):
        self.assertTrue(all(len(p) >= MIN_PHRASE for p in phrases("a b c the of and")))


class ItDECIDESNothing(unittest.TestCase):
    """The whole legality of this module. It returns addresses and only addresses."""

    def test_the_result_carries_no_score_weight_kind_or_verdict(self):
        snap = _Snap({"a": "certified positivity holds", "b": "other"})
        n = nominate(snap, "certified positivity here")
        for banned in ("score", "weight", "kind", "relation", "arrow", "rank",
                       "similarity", "confidence"):
            self.assertNotIn(banned, n, f"a nominator returned a {banned}")

    def test_every_carrier_is_nominated_EQUALLY(self):
        # No ranking among carriers: a slot carries the phrase or it does not. Ordering the
        # carriers by anything would be the resemblance judgement this must not make.
        snap = _Snap({"a": "certified positivity",
                      "b": "certified positivity certified positivity certified positivity"})
        self.assertEqual(("a", "b"), nominate(snap, "certified positivity")["slots"])

    def test_it_holds_no_word_bag_and_no_case_folding(self):
        # engine/referee_sweep enforces this repository-wide; asserted here too because this
        # module is the one most likely to grow one back.
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "nominate.py").read_text()
        for banned in (".lower()", ".casefold()", "set(_words", "Counter("):
            self.assertNotIn(banned, src, f"a word bag is back: {banned}")

    def test_it_is_registered_in_the_referee_sweep_with_its_reasoning(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "referee_sweep.py").read_text()
        self.assertIn("nominate.py", src)
        self.assertIn("decides nothing", src)


class TheSeederUsesItBeforeTheArrowRichCore(unittest.TestCase):

    def test_a_nominated_slot_becomes_the_anchor(self):
        from engine.region import anchor_for

        class S:
            slots = {"topic": _Rec("certified positivity is established"),
                     "hub": _Rec("an unrelated hub claim")}
            arrows = []
        self.assertEqual("topic", anchor_for(S(), "seed", text="certified positivity"))

    def test_exact_address_landing_still_comes_FIRST(self):
        # Gate 1 is identity, not resemblance, and it outranks a nomination.
        from engine.region import anchor_for

        class S:
            slots = {"exact": _Rec("certified positivity"), "other": _Rec("certified positivity")}
            arrows = []
        self.assertEqual("exact", anchor_for(S(), "exact", text="certified positivity"))

    def test_with_no_text_the_old_path_is_unchanged(self):
        from engine.region import anchor_for

        class S:
            slots = {"a": _Rec("x"), "b": _Rec("y")}
            arrows = []
        self.assertEqual("", anchor_for(S(), "seed"))


if __name__ == "__main__":
    unittest.main()
