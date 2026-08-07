"""THE FOURTH DOOR's controls, c1-c6, planted as the spec wrote them.

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

from engine.synthesis import (COLLISION, COVERAGE, RESIDUE, SPLIT, SYNTHESIS_CANDIDATE,
                              TERM_CANDIDATE, Candidate, apexless, collapse, inform,
                              lexical_question, stress, synthesis_candidates, terms_from)

MODULE = Path(__file__).resolve().parents[1] / "engine" / "synthesis.py"


def _compiled(cites):
    return {"compiled": "FIELD", "citations": list(cites)}


class C1MintAttempt(unittest.TestCase):
    """c1. THE TWO-MOUTH LAW'S TOMBSTONE, extending the one the null surface left."""

    def test_a_nomination_naming_an_unshown_label_yields_NOTHING(self):
        got = terms_from('NAME [e3][e999] AS "mode-splitting"', {"e3", "e7"}, turn=2)
        self.assertEqual(got, [], "a label the field never showed was accepted into a term")

    def test_a_nomination_over_shown_labels_is_a_RECORD_and_enters_nothing(self):
        got = terms_from('NAME [e3][e7] AS "mode-splitting"', {"e3", "e7"}, turn=2)
        self.assertEqual(len(got), 1)
        rec = got[0].as_record()
        self.assertEqual(rec["kind"], TERM_CANDIDATE)
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

    def test_address_is_used_for_IDENTITY_only_and_never_to_write(self):
        """`address` IS called — the informed offer needs it to say "this already exists". What
        must not happen is a write, which the test above covers, so this pins the read."""
        src = MODULE.read_text(encoding="utf-8")
        self.assertIn("from .normalize import address", src)
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
        self.assertIn("NAME", q)
        self.assertIn("[∅]", q, "the question must offer its own legal exit")

    def test_a_singleton_cluster_is_NOT_a_lexical_gap(self):
        """Every claim in no fiber is its own group by construction. Asking for a name for each
        of them would ask about the whole corpus."""
        ident, members = apexless(_compiled([{"n": "e3", "kind": "seated", "slot": "s1"}]),
                                  set())
        self.assertEqual(ident, ())

    def test_a_declared_cluster_with_no_name_IS_one(self):
        ident, members = apexless(_compiled([
            {"n": "e3", "kind": "seated", "slot": "s1", "group": "s1"},
            {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"}]), set())
        self.assertEqual(ident, ("lex", "s1"))
        self.assertEqual(members, ("e3", "e7"))

    def test_an_ASKED_cluster_is_not_asked_again(self):
        field = _compiled([{"n": "e3", "kind": "seated", "slot": "s1", "group": "s1"},
                           {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"}])
        self.assertEqual(apexless(field, {("lex", "s1")})[0], ())


class C3OneNominationPerFootprint(unittest.TestCase):
    """c3. The footprint is the identity; words are candidate surfaces for it."""

    def test_two_terms_over_the_same_objects_collapse_to_one_with_alternatives(self):
        got = collapse([
            Candidate(kind=TERM_CANDIDATE, footprint=("e3", "e7"), turn=2, surfaces=("alpha",)),
            Candidate(kind=TERM_CANDIDATE, footprint=("e7", "e3"), turn=4, surfaces=("beta",)),
        ])
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].surfaces, ("alpha", "beta"))
        self.assertEqual(got[0].turn, 2, "the nomination happened at the earlier turn")

    def test_different_footprints_do_not_collapse(self):
        got = collapse([
            Candidate(kind=TERM_CANDIDATE, footprint=("e3", "e7"), turn=2, surfaces=("a",)),
            Candidate(kind=TERM_CANDIDATE, footprint=("e3", "e9"), turn=2, surfaces=("b",)),
        ])
        self.assertEqual(len(got), 2)

    def test_a_restated_nomination_is_one_claim_and_the_record_says_so(self):
        """The records-versus-pairs law, at the level of vocabulary."""
        said = 'NAME [e3][e7] AS "alpha"\nNAME [e3][e7] AS "alpha"\nNAME [e3][e7] AS "beta"'
        got = terms_from(said, {"e3", "e7"}, turn=2)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].surfaces, ("alpha", "beta"))


class C4SignatureOnlyEntry(unittest.TestCase):
    """c4. An enthusiastic transcript changes nothing about tier or vocabulary."""

    def test_an_enthusiastic_dialogue_leaves_the_field_untouched(self):
        from engine.dialogue import Turn, converse

        field = _compiled([{"n": "e3", "kind": "attached", "slot": "s1", "group": "s1"},
                           {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"}])
        before = [dict(c) for c in field["citations"]]

        def transport(system, user):
            return ('This is clearly one idea and it should be adopted at once.\n'
                    'NAME [e3][e7] AS "mode-splitting"\n'
                    'The work establishes it [e3].'), {}

        d = converse("q", field, transport, budget=3,
                     first_turn=Turn(n=1, ask="q", prose="The work establishes it [e3]."))
        self.assertEqual(field["citations"], before, "the dialogue mutated the field")
        rec = d.as_record()["lexicon"]
        self.assertIsNotNone(rec, "a lexical residual ran and recorded nothing")
        for c in rec["nominations"]:
            self.assertIsNone(c["warrant"])
            self.assertEqual(c["record_kind"], "testimony")

    def test_a_surviving_nomination_is_still_only_a_record(self):
        c = Candidate(kind=TERM_CANDIDATE, footprint=("e3", "e7"), turn=2, surfaces=("x",))
        self.assertEqual(stress(c, _compiled([
            {"n": "e3", "kind": "seated", "slot": "s1", "group": "s1"},
            {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"}]), ("e3", "e7")), [],
            "fixture must be a clean nomination")
        self.assertIsNone(c.as_record()["warrant"])


class C5InformedOfferIdentity(unittest.TestCase):
    """c5. What the field already holds, named — exactly, never by resemblance."""

    def test_a_candidate_whose_nu_EXISTS_is_told_where(self):
        from engine.corpus_state import CorpusSnapshot, SlotRecord
        from engine.normalize import address

        text = "The cone is positive under composition."
        slot, nu = address("english", text, "assert")
        snap = CorpusSnapshot(slots={slot: SlotRecord(
            slot=slot, chart="english", type="assert", nu=nu, value="true",
            confidence=1.0, tier="EXTRACTION", docs=())}, arrows=())
        compiled = _compiled([{"n": "e5", "kind": "seated", "slot": slot}])
        c = Candidate(kind=SYNTHESIS_CANDIDATE, footprint=("e3", "e7"), turn=2, text=text)
        offer = inform(c, compiled, snap)
        self.assertIn("[e5]", offer)
        self.assertIn("adds an event, not a slot", offer)

    def test_a_footprint_inside_ONE_fiber_is_told_which(self):
        c = Candidate(kind=SYNTHESIS_CANDIDATE, footprint=("e3", "e7"), turn=2,
                      groups=("s1abcdef",))
        offer = inform(c, _compiled([]), None)
        self.assertIn("one declared proposition already", offer)
        self.assertIn("s1abcdef"[:12], offer)

    def test_a_genuine_gap_offers_NOTHING_and_says_so_by_being_empty(self):
        c = Candidate(kind=SYNTHESIS_CANDIDATE, footprint=("e3", "e7"), turn=2,
                      groups=("~e3", "~e7"))
        self.assertEqual(inform(c, _compiled([]), None), "")


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


class TheFourDecidableChecks(unittest.TestCase):
    """The stress table, each failure planted at the shape the spec names."""

    FIELD = {"compiled": "F", "citations": [
        {"n": "e3", "kind": "seated", "slot": "s1", "group": "s1"},
        {"n": "e7", "kind": "seated", "slot": "s2", "group": "s1"},
        {"n": "e9", "kind": "seated", "slot": "s3", "group": "s1"},
        {"n": "l4", "kind": "seated", "slot": "s4", "group": "s9"},
        {"n": "l5", "kind": "seated", "slot": "s5", "group": "s9"}]}

    def _checks(self, foot, cluster=()):
        c = Candidate(kind=TERM_CANDIDATE, footprint=foot, turn=2, surfaces=("x",))
        return {f["check"] for f in stress(c, self.FIELD, cluster)}

    def test_COVERAGE_fails_when_the_name_claims_an_object_the_field_lacks(self):
        self.assertIn(COVERAGE, self._checks(("e3", "e7", "e9", "zz1")))

    def test_SPLIT_fails_when_the_citations_span_two_clusters(self):
        self.assertIn(SPLIT, self._checks(("e3", "l4")))

    def test_RESIDUE_fails_when_the_name_leaves_measured_structure_uncovered(self):
        got = self._checks(("e3", "e7"), cluster=("e3", "e7", "e9"))
        self.assertIn(RESIDUE, got)

    def test_a_name_covering_its_whole_cluster_passes_every_check(self):
        self.assertEqual(self._checks(("e3", "e7", "e9"), cluster=("e3", "e7", "e9")), set())

    def test_COLLISION_fails_when_the_fiber_already_has_a_name(self):
        import engine.synthesis as syn

        saved = syn.named
        try:
            syn.named = lambda g: "existing-name" if g == "s1" else ""
            self.assertIn(COLLISION, self._checks(("e3", "e7", "e9"), ("e3", "e7", "e9")))
        finally:
            syn.named = saved


class SynthesisCandidatesAreTheWELDSeenTwice(unittest.TestCase):
    """No second detector. A weld and a synthesis candidate are one measurement."""

    def test_a_weld_verdict_becomes_a_nomination_with_the_same_footprint(self):
        verdict = {"violations": [{"kind": "welded", "numbers": ["e3", "l4"],
                                   "sentence": "These jointly imply X [e3][l4]."}]}
        got = synthesis_candidates(verdict, TheFourDecidableChecks.FIELD, turn=1)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].footprint, ("e3", "l4"))
        self.assertEqual(got[0].kind, SYNTHESIS_CANDIDATE)
        self.assertEqual(got[0].groups, ("s1", "s9"))

    def test_other_verdicts_are_NOT_nominations(self):
        verdict = {"violations": [{"kind": "unresolved", "numbers": ["zz1"], "sentence": "x"},
                                  {"kind": "uncited", "numbers": [], "sentence": "y"}]}
        self.assertEqual(synthesis_candidates(verdict, TheFourDecidableChecks.FIELD), [])

    def test_the_module_holds_no_second_weld_detector(self):
        """PLANTED AGAINST Q5. If this module ever computes weldedness itself there are two
        mechanisms for one job, and they will disagree the first time one is edited."""
        src = MODULE.read_text(encoding="utf-8")
        for banned in ("joined", "arrow_index", "def welded"):
            self.assertNotIn(banned, src, f"a second weld detector appeared: {banned}")


if __name__ == "__main__":
    unittest.main()
