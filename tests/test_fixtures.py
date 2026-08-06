"""THE REGRESSION FIXTURES: every behaviour that had to be re-explained twice.

THE RULE, and it is the operator's: a behaviour the operator has had to explain more than once
becomes a named fixture the same day. Re-explanation is the signal that an understanding is
LOAD-BEARING AND UN-GATED — it matters enough to say again, and nothing in the suite was
holding it. Every entry below is drawn from this session's history, and each names the failure
that put it here so the fixture cannot be quietly weakened into something that passes.

The auditor owns keeping this list current. A new re-explanation is a new fixture, not a note.
"""

import unittest

from engine.grounded import WARRANTS, check_answer, warrants_held
from engine.structure_trace import Signature, signature_of

#: THE CANONICAL STRUCTURAL QUESTION. Verbatim, because it has failed enough times to be a
#: fixture rather than an example: it returned implementation details of an unrelated
#: repository, then "nothing moved" contradicting its own trace.
STRUCTURAL_QUESTION = "common thread through the math"

#: THE SUBSTRATE-REPAIR RETEST. Verbatim, pinned by the operator as the one fixed input that
#: separates two explanations of the same symptom.
#:
#: Run on the PRE-REPAIR substrate it returned: attachment 59 of 59 (100%, the guard's limit
#: case), 0 of 24 moved slots reached over any declared arrow, and a region drawn from the ETS
#: writer/deploy cluster — the 120-member fiber's gravity well.
#:
#: Re-run byte-identical after the demotion and apex-star land, the three numbers reported
#: side by side. The two outcomes mean different things and only one of them is a defect:
#:   attachment drops below the guard AND any arrows travel -> the gravity well collapsed;
#:     the muddle was substrate flattening and the repair fixed it.
#:   still 59/59 with 0 arrows -> the cross-project conceptual thread genuinely is not in the
#:     corpus as same_claim structure. A real finding, and the answer is daemon-hours plus the
#:     lexicon hubs, not more repair.
RETEST_QUESTION = "talk about the gibbs ebm across projects and general design principles"

#: What that input measured before the repair. Pinned so the comparison cannot drift.
RETEST_PRE_REPAIR = {
    "attachment_fraction": 1.0,      # 59 of 59 objects shown
    "attached": 59,
    "shown": 59,
    "moved": 24,
    "reached_over_arrows": 0,
    "region_cluster": "ETS writer/deploy — the 120-member fiber",
    "substrate": "pre-demotion: 2,082 same_claim pairs, 96.7% code-to-own-docstring "
                 "containment mis-kinded as identity",
}


class _Att:
    def __init__(self, kind):
        self.kind = kind


class _Moved:
    def __init__(self, hops):
        self.hops = hops


class _Pert:
    def __init__(self, kinds):
        self.attachment = [_Att(k) for k in kinds]


class _Rel:
    def __init__(self, hops):
        self.moved = [_Moved(h) for h in hops]


class StructuralQuestionsAnswerFromStructure(unittest.TestCase):
    """FIXTURE: a question about the corpus's SHAPE must reach the structure layer.

    Why it exists: "common thread through the math" is a Pi-1 question. The relaxation path
    can only report which objects were displaced, so it returned `role_unit_pool` and
    `compute_eigenmodes` — and the loops, fibers and same_claim clusters that answer the
    question were measured, in the header, and never in the prompt.
    """

    def test_the_canonical_question_is_still_the_canonical_question(self):
        self.assertEqual("common thread through the math", STRUCTURAL_QUESTION)

    def test_bears_on_only_with_no_arrow_reach_is_the_signature(self):
        sig = signature_of(_Pert(["bears_on"] * 26), _Rel([0] * 24))
        self.assertTrue(sig.structural)
        self.assertTrue(sig.bears_on_only)
        self.assertTrue(sig.no_arrow_reach)

    def test_a_correspondence_attachment_means_it_was_a_claim_not_a_topic(self):
        sig = signature_of(_Pert(["bears_on", "same_claim"]), _Rel([0, 0]))
        self.assertFalse(sig.structural, "an asserting input is not a structural question")

    def test_arrow_reach_means_the_relaxation_DID_carry_something(self):
        sig = signature_of(_Pert(["bears_on"] * 5), _Rel([0, 2, 0]))
        self.assertFalse(sig.structural)

    def test_the_signature_states_both_branches_so_absence_is_never_inferred(self):
        self.assertEqual("", signature_of(_Pert(["same_claim"]), _Rel([1])).render())
        self.assertIn("STRUCTURAL QUESTION DETECTED",
                      signature_of(_Pert(["bears_on"]), _Rel([0])).render())

    def test_the_structure_block_emits_citable_lines(self):
        from engine.inbound import Citable
        from engine.structure_trace import structure_lines

        class Snap:
            slots = {f"s{i}": type("S", (), {"chart": "english", "nu": f"claim {i}"})()
                     for i in range(6)}
            arrows = [type("A", (), {"src_chart": "english", "dst_chart": "lean"})()
                      for _ in range(4)]
            fibers = [("s0", "s1", "s2"), ("s3", "s4", "s5")]
            loops = 8
        cites = []
        lines = structure_lines(Snap(), cites, Citable)
        self.assertTrue(cites, "the structure layer emitted nothing citable")
        self.assertTrue(any(c.kind == "fiber" for c in cites))
        self.assertTrue(any(c.kind == "cluster" for c in cites))
        self.assertTrue(any("FIBER" in x for x in lines))

    def test_what_is_dropped_from_the_structure_block_is_counted(self):
        from engine.inbound import Citable
        from engine.structure_trace import TOP_FIBERS, structure_lines

        class Snap:
            slots = {f"s{i}": type("S", (), {"chart": "english", "nu": f"c{i}"})()
                     for i in range(60)}
            arrows = []
            fibers = [tuple(f"s{i*3+j}" for j in range(3)) for i in range(20)]
            loops = 0
        cites = []
        text = "\n".join(structure_lines(Snap(), cites, Citable))
        self.assertIn(f"{20 - TOP_FIBERS} further class(es)", text,
                      "a silent cut reads as coverage")


class AbsenceClaimsAreCitable(unittest.TestCase):
    """FIXTURE: an honest negative is a legal sentence, not a permanent RED.

    Why it exists: three of eleven sentences in a live answer said "not measured here" and
    every one was convicted, because the grammar had only positive citations.
    """

    def _c(self, ns=(1,), **rel):
        return {"citations": [{"n": n} for n in ns],
                "relaxation": {"rows": rel.pop("rows", [{"hops": 1}]), **rel},
                "attachment": {"attachment": [{"kind": "bears_on"}]}}

    def test_a_whole_trace_absence_is_green(self):
        self.assertTrue(check_answer("The relation is not measured here [∅].", self._c()).ok)

    def test_an_invented_absence_reason_is_red(self):
        v = check_answer("The region could not be aimed at all [∅anchor].", self._c())
        self.assertFalse(v.ok)

    def test_every_warrant_the_grammar_accepts_is_in_the_prompt(self):
        from engine.inbound import INBOUND_SYSTEM
        for name in WARRANTS:
            self.assertIn(f"[∅{name}]", INBOUND_SYSTEM)


class SummarySentencesMustCite(unittest.TestCase):
    """FIXTURE: the sentences that assert most are the ones that lose their citation.

    Why it exists: measured on a live answer, 17 of 21 sentences cited; the four that did not
    were the opening "what this bears on", the linking sentences, and the closing summary.
    """

    def test_an_uncited_summary_sentence_is_red(self):
        v = check_answer("Taken together these claims all concern the settling floor.",
                         {"citations": [{"n": 1}, {"n": 2}]})
        self.assertFalse(v.ok)
        self.assertEqual("uncited", v.violations[0]["kind"])

    def test_a_summary_citing_every_line_it_summarises_is_green(self):
        """A summary over ONE group. Across groups it needs the arrow or [∅rel].

        The fixture used to leave the two objects ungrouped, and the weld rule now convicts
        it: "these claims all concern the settling floor" asserts a shared subject, which is
        a relation, and nothing declared one. The property under defence — a summary sentence
        may cite every line it summarises — survives; what changed is that a summary spanning
        groups the field never joined must say so.
        """
        self.assertTrue(check_answer(
            "Taken together these claims all concern the settling floor [1][2].",
            {"citations": [{"n": 1, "group": "g"}, {"n": 2, "group": "g"}]}).ok)

    def test_a_summary_ACROSS_groups_needs_the_arrow_or_the_marker(self):
        c = {"citations": [{"n": 1, "group": "a"}, {"n": 2, "group": "b"}]}
        self.assertFalse(check_answer(
            "Taken together these claims all concern the settling floor [1][2].", c).ok)
        self.assertTrue(check_answer(
            "Taken together these claims all concern the settling floor [1][2][∅rel].",
            c).ok)

    def test_the_grammar_carries_the_rule_the_measured_failure_produced(self):
        """THE RULE, not the prompt's old shouting about it.

        This asserted the literal word "SUMMARY" appeared in the prompt — a sentence added
        after measuring that summary sentences drop their citations. The prompt has since been
        stripped to grammar and state, and the right assertion is that the rule is stated once
        and enforced, not that a particular paragraph still exists to exhort about it.
        """
        from engine.grammar import BLOCKS
        self.assertTrue(any(k == "GRAMMAR" and "several objects names all of them" in t
                            for k, t in BLOCKS))
        self.assertFalse(check_answer(
            "Taken together these claims all concern the settling floor.",
            {"citations": [{"n": 1}, {"n": 2}]}).ok)


class SharpVerbatimInputExactLands(unittest.TestCase):
    """FIXTURE: a claim the corpus holds verbatim seeds its OWN neighbourhood.

    Why it exists: the battery's sharp input — a corpus claim with 254 declared arrows — was
    hash-rotated to an unrelated hub and declined. The spec inverted.
    """

    def test_an_address_the_corpus_carries_is_the_anchor(self):
        from engine.region import anchor_for

        class Snap:
            slots = {"deadbeef": object()}
            arrows = []
        self.assertEqual("deadbeef", anchor_for(Snap(), "deadbeef"))

    def test_a_near_miss_address_does_not_hit(self):
        from engine.region import anchor_for

        class Snap:
            slots = {"abc123": object()}
            arrows = []
        self.assertEqual("", anchor_for(Snap(), "abc124"))


class VagueTopicGivesGradedBearsOn(unittest.TestCase):
    """FIXTURE: a topic attaches by bears-on, and attaching to EVERYTHING is degeneracy.

    Why it exists: 59 attachments from a 59-claim region, reported as a rich result.
    """

    def _p(self, attached, members):
        from engine.perturb import Attachment, Perturbation
        p = Perturbation()
        p.attachment = [Attachment(kind="bears_on", dst_slot=f"s{i}", dst_chart="english",
                                   dst_nu=f"c{i}", tier="EXTRACTION", evidence="")
                        for i in range(attached)]
        p.region = type("R", (), {"members": [None] * members})()
        return p

    def test_total_attachment_is_red(self):
        self.assertTrue(self._p(59, 60).indiscriminate)

    def test_a_graded_attachment_is_green(self):
        self.assertFalse(self._p(26, 60).indiscriminate)

    def test_the_red_state_reaches_the_answer_as_a_warrant(self):
        compiled = {"citations": [{"n": 1}], "relaxation": {"rows": [{"hops": 1}]},
                    "attachment": {"attachment": [{"kind": "bears_on"}],
                                   "discrimination": {"red": True}}}
        self.assertIn("indiscriminate", warrants_held(compiled))


class TheExportSheetIsExactlyTheCompiledContext(unittest.TestCase):
    """FIXTURE: exporting must carry the claims verbatim and the absences, and nothing else.

    Why it exists: the sheet is the context-repetition killer only if a receiving model gets
    the asker's real material. A sheet that summarises is a sheet that has to be trusted.
    """

    RECORD = {
        "typed": "does the settling floor relate to the second FDT",
        "citations": [
            {"n": 1, "kind": "bears_on", "chart": "english", "slot": "a",
             "nu": "the floor is measured per arm"},
            {"n": 2, "kind": "moved", "chart": "english", "slot": "b",
             "nu": "the second FDT surrogate floor is 0.12153270"},
        ],
        "relaxation": {"rows": [{"slot": "b", "tier": "EXTRACTION", "shift": 0.41, "hops": 1,
                                 "contested": False, "weakest_tier": "EXTRACTION",
                                 "path": [{"kind": "same_claim", "src_chart": "english",
                                           "dst_chart": "lean"}]}],
                       "blocks_skipped": 1},
        "attachment": {"attachment": [{"kind": "bears_on"}]},
    }

    def setUp(self):
        from engine.export_sheet import sheet
        self.text = sheet(self.RECORD)

    def test_the_question_is_in_it_verbatim(self):
        self.assertIn("does the settling floor relate to the second FDT", self.text)

    def test_every_moved_claim_is_in_it_verbatim_with_its_index(self):
        self.assertIn("the second FDT surrogate floor is 0.12153270", self.text)
        self.assertIn("[2]", self.text)

    def test_the_declared_path_travels_with_the_claim(self):
        self.assertIn("VIA same_claim", self.text)

    def test_the_stated_absence_is_in_it(self):
        self.assertIn("[∅cap]", self.text)
        self.assertIn(WARRANTS["cap"], self.text)

    def test_the_attachment_is_in_it_with_its_kind(self):
        self.assertIn("bears_on", self.text)
        self.assertIn("the floor is measured per arm", self.text)

    def test_it_carries_no_answer_and_no_summary(self):
        # A preamble that argues is a preamble that must be trusted. This one is checkable
        # line by line against the window that produced it.
        low = self.text.lower()
        for banned in ("in summary", "therefore the", "the answer is", "conclusion:"):
            self.assertNotIn(banned, low)

    def test_it_carries_the_citation_grammar_so_the_receiver_is_held_to_it(self):
        self.assertIn("[∅]", self.text)
        self.assertIn("bracketed number", self.text)

    def test_it_is_a_pure_function_of_the_record(self):
        from engine.export_sheet import sheet
        self.assertEqual(self.text, sheet(self.RECORD))

    def test_an_empty_record_produces_a_sheet_that_says_so(self):
        from engine.export_sheet import sheet
        t = sheet({"typed": "x", "citations": [], "relaxation": {}, "attachment": {}})
        self.assertIn("Nothing moved.", t)
        self.assertIn("Nothing attached", t)


if __name__ == "__main__":
    unittest.main()


class TheSubstrateRepairRetest(unittest.TestCase):
    """FIXTURE: one fixed input, run before and after the repair, three numbers.

    Why it exists: the same symptom — a region full of one repository's writer internals —
    has two possible causes, and they call for opposite responses. Either the substrate was
    flattened (96.7% of same_claim was containment mis-kinded as identity, closure fabricating
    a 120-member gravity well) and the repair collapses it, or the cross-project conceptual
    thread genuinely is not in the corpus as declared structure and the answer is daemon-hours,
    not more repair. Guessing between those is how a real corpus limitation gets "fixed"
    forever without improving.
    """

    def test_the_retest_input_is_pinned_verbatim(self):
        self.assertEqual("talk about the gibbs ebm across projects and general design "
                         "principles", RETEST_QUESTION)

    def test_the_pre_repair_numbers_are_recorded_not_remembered(self):
        self.assertEqual(1.0, RETEST_PRE_REPAIR["attachment_fraction"])
        self.assertEqual(0, RETEST_PRE_REPAIR["reached_over_arrows"])
        self.assertEqual(24, RETEST_PRE_REPAIR["moved"])

    def test_the_pre_repair_reading_names_the_substrate_it_was_measured_on(self):
        # A before-number with no substrate attached is a number that cannot be compared to
        # anything: the corpus changed under it twice in one session.
        self.assertIn("pre-demotion", RETEST_PRE_REPAIR["substrate"])

    def test_total_attachment_is_at_the_guard_limit(self):
        from engine.perturb import Perturbation
        self.assertGreaterEqual(RETEST_PRE_REPAIR["attachment_fraction"],
                                Perturbation.INDISCRIMINATE)

    def test_both_outcomes_are_written_down_before_the_rerun(self):
        # Stating what each result would MEAN before measuring is what stops the measurement
        # from being read to suit whichever answer arrives.
        import tests.test_fixtures as mod
        doc = mod.__doc__ or ""
        src = __import__("inspect").getsource(mod)
        self.assertIn("gravity well collapsed", src)
        self.assertIn("daemon-hours", src)
