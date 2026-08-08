"""THE FOURTH DOOR's surviving controls, after the doorless ruling.

WHAT WAS DELETED AND WHY THE FILE SHRANK: the nomination-offer-signature ceremony — the NAME
form, the term-candidate subclass, the informed offer, the four decidable checks that stressed
a proposed term, and the per-dialogue lexicon ledger. Vocabulary is no longer gated: an apex's
surface is DERIVED (engine/apex_surface.py, tests/test_apex_surface.py), and a term the medium
coins is ordinary testimony that enters the corpus only when the OPERATOR re-uses it. See
seed/DIALOGIC.md, THE DOORLESS SIMPLIFICATION.

WHAT SURVIVES HERE: the synthesis candidate as a RECORD (it enters nothing and never did), the
lexical-frustration residual (measurement pressure, part of settlement), and the two-mouth
law's tombstone for slots.

The original header follows.

THE FOURTH DOOR's controls, planted as the spec wrote them.

seed/DIALOGIC.md declared these before the module existed. What they are all one control for:
THE MEDIUM NOMINATES AND NEVER MINTS. Every other property here is a way for that one to fail
quietly — a slot created from medium-authored text, a term reaching an apex-name without the
operator's signature, an interrogation question generated from a reply's prose instead of from
the graph.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.synthesis import (SYNTHESIS_CANDIDATE, Candidate, apexless, collapse,
                              lexical_question, synthesis_candidates)

MODULE = Path(__file__).resolve().parents[1] / "engine" / "synthesis.py"

#: The field the surviving controls read. It outlived the class that used to own it.
_FIELD = {"compiled": "F", "citations": [
    {"n": "e3", "kind": "seated", "slot": "s1", "group": "s1"},
    {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"},
    {"n": "e9", "kind": "seated", "slot": "s3", "group": "s1"},
    {"n": "l4", "kind": "seated", "slot": "s4", "group": "s9"},
    {"n": "l5", "kind": "seated", "slot": "s5", "group": "s9"}]}


def _compiled(cites):
    return {"compiled": "FIELD", "citations": list(cites)}


class C1MintAttempt(unittest.TestCase):
    """c1. THE TWO-MOUTH LAW'S TOMBSTONE, extending the one the null surface left."""

    def test_a_synthesis_candidate_is_a_RECORD_and_enters_nothing(self):
        verdict = {"violations": [{"kind": "welded", "numbers": ["e3", "l4"],
                                   "sentence": "These jointly imply X."}]}
        got = synthesis_candidates(verdict, _compiled([
            {"n": "e3", "kind": "seated", "slot": "s1", "group": "g1"},
            {"n": "l4", "kind": "seated", "slot": "s2", "group": "g2"}]), turn=1)
        self.assertEqual(len(got), 1)
        rec = got[0].as_record()
        self.assertEqual(rec["kind"], SYNTHESIS_CANDIDATE)
        self.assertEqual(rec["record_kind"], "testimony")
        self.assertIsNone(rec["warrant"], "a nomination acquired a warrant")
        self.assertIn("nothing", rec["entered"])

    def test_NO_code_path_in_the_module_creates_a_slot_an_arrow_or_an_apex(self):
        """Read as an AST, not as prose: the module may not CALL the minting machinery.

        A promise in a docstring is not a control. What is asserted is that no name capable of
        creating corpus structure is invoked anywhere in this file.
        """
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        called = {n.func.attr if isinstance(n.func, ast.Attribute) else
                  getattr(n.func, "id", "") for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for banned in ("propose", "extract", "mint", "promote", "apex_id", "Correspondence",
                       "SlotRecord", "Delta", "commit", "clamp", "Clamp"):
            self.assertNotIn(banned, called, f"the fourth door called {banned}")

    def test_the_lane_no_longer_ADDRESSES_anything(self):
        """The informed offer needed `address` to say "this already exists as [12]". The offer
        went with the ceremony, and so did the only reason this module ever touched an
        addresser — which is the deletion being real rather than renamed."""
        src = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("from .normalize import address", src)
        self.assertNotIn("snapshot.slots[", src, "the fourth door wrote into the corpus")


class C2FluencyBlindnessHolds(unittest.TestCase):
    """c2. The lexical question comes from the GRAPH, never from a reply."""

    def test_the_interrogator_still_takes_exactly_two_parameters(self):
        import inspect

        from engine.dialogue import interrogate, next_residual

        for fn in (interrogate, next_residual):
            with self.subTest(fn=fn.__name__):
                self.assertEqual(list(inspect.signature(fn).parameters), ["compiled", "asked"],
                                 "a reply reached the question generator")

    def test_apexless_reads_citations_and_glosses_and_nothing_else(self):
        import inspect

        self.assertEqual(list(inspect.signature(apexless).parameters), ["compiled", "asked"])

    def test_the_lexical_question_is_built_from_the_CLUSTER(self):
        q = lexical_question(("e3", "e7", "e9"))
        for n in ("e3", "e7", "e9"):
            self.assertIn(f"[{n}]", q)
        self.assertNotIn("NAME", q, "the NAME ceremony survived in the question")
        self.assertIn("arrow", q, "the question must ask for what the dialogue can consume")
        self.assertIn("[∅]", q, "the question must offer its own legal exit")

    def test_a_singleton_cluster_is_NOT_a_lexical_gap(self):
        """Every claim in no fiber is its own group by construction. Asking for a name for each
        of them would ask about the whole corpus."""
        ident, members = apexless(_compiled([{"n": "e3", "kind": "seated", "slot": "s1"}]),
                                  set())
        self.assertEqual(ident, ())

    def test_a_declared_cluster_with_no_name_IS_one(self):
        ident, members = apexless(_compiled([
            {"n": "e3", "kind": "moved", "slot": "s1", "group": "s1"},
            {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"}]), set())
        self.assertEqual(ident, ("lex", "s1"))
        self.assertEqual(members, ("e3", "e7"))

    def test_an_ASKED_cluster_is_not_asked_again(self):
        field = _compiled([{"n": "e3", "kind": "moved", "slot": "s1", "group": "s1"},
                           {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"}])
        self.assertEqual(apexless(field, {("lex", "s1")})[0], ())


class C6AnchoringIsStructural(unittest.TestCase):
    """c6. The standing anti-similarity sweep extends to this module."""

    def test_no_tokenizer_no_similarity_no_case_folding(self):
        src = MODULE.read_text(encoding="utf-8")
        for banned in ("[a-z0-9]+", "[a-zA-Z]+", "\\w+", ".lower()", ".casefold()",
                       "difflib", "SequenceMatcher", "levenshtein", "jaccard"):
            self.assertNotIn(banned, src, f"a similarity mechanism reached the door: {banned}")

    def test_the_only_split_is_on_a_declared_delimiter(self):
        """`.split()` with no argument is word-splitting. Splitting a captured group on a comma
        is reading a declared serialization, which is a different act."""
        src = MODULE.read_text(encoding="utf-8")
        self.assertNotIn(".split()", src)

    def test_grouping_is_fiber_membership_and_never_word_matching(self):
        from engine.synthesis import _group_of

        got = _group_of(_compiled([
            {"n": "e3", "kind": "seated", "slot": "s1", "group": "s1"},
            {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"},
            {"n": "l9", "kind": "seated", "slot": "s3"}]))
        self.assertEqual(got, {"e3": "s1", "e7": "s1", "l9": "~l9"})


class SynthesisCandidatesAreTheWELDSeenTwice(unittest.TestCase):
    """No second detector. A weld and a synthesis candidate are one measurement."""

    def test_a_weld_verdict_becomes_a_nomination_with_the_same_footprint(self):
        verdict = {"violations": [{"kind": "welded", "numbers": ["e3", "l4"],
                                   "sentence": "These jointly imply X [e3][l4]."}]}
        got = synthesis_candidates(verdict, _FIELD, turn=1)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].footprint, ("e3", "l4"))
        self.assertEqual(got[0].kind, SYNTHESIS_CANDIDATE)
        self.assertEqual(got[0].groups, ("s1", "s9"))

    def test_other_verdicts_are_NOT_nominations(self):
        verdict = {"violations": [{"kind": "unresolved", "numbers": ["zz1"], "sentence": "x"},
                                  {"kind": "uncited", "numbers": [], "sentence": "y"}]}
        self.assertEqual(synthesis_candidates(verdict, _FIELD), [])

    def test_the_module_holds_no_second_weld_detector(self):
        """PLANTED AGAINST Q5. If this module ever computes weldedness itself there are two
        mechanisms for one job, and they will disagree the first time one is edited."""
        src = MODULE.read_text(encoding="utf-8")
        for banned in ("joined", "arrow_index", "def welded"):
            self.assertNotIn(banned, src, f"a second weld detector appeared: {banned}")


if __name__ == "__main__":
    unittest.main()
