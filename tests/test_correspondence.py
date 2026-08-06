"""Controls for the correspondence mechanism and the proposal loop.

The mandated set, before any real-corpus run:

  * planted TRUE correspondence — forms a provisional fiber, never promotes without authorship
  * planted FALSE correspondence — the OLD ARTIFACT (a claim and its negation) is now a
    CONTROL: it must be rejected, or else visibly flagged provisional-unconfirmed, never
    silently accepted
  * reverse-arrow mismatch — an unreciprocated `same_claim` registers as OPEN, not symmetric
  * holonomy exclusion — a loop containing a `refines` arrow never enters the floor
  * one-write-path — correspondence proposals reach the tape only through `propose()`
"""

from __future__ import annotations

import unittest

from engine import EngineError
from engine.blocks import build_loop_fibers, loop_edges, loops_from_fibers, structural_edges
from engine.correspondence import (
    CORRESPONDENCE_CHART,
    Correspondence,
    asymmetries,
    correspondences_from_deltas,
    loop_pairs,
    structural_pairs,
)
from engine.holes import Hole, enumerate_holes
from engine.inlet import FastTape
from engine.propose_correspondence import (
    as_correspondence_delta,
    confirm,
    parse_answers,
    propose_over_holes,
    ProposalOutcome,
)
from engine.normalize import address
from engine.types import Slot, WarrantTier, promotable

EN = "english"
LN = "lean"


def _slot(chart: str, surface: str, type_: str = "assert") -> Slot:
    sid, nu_value = address(chart, surface, type_)
    return Slot(id=sid, nu=nu_value, type=type_, chart=chart)


def _hole(a: Slot, b: Slot) -> Hole:
    return Hole(src_chart=a.chart, src_slot=a.id, src_nu=a.nu,
                dst_chart=b.chart, dst_slot=b.id, dst_nu=b.nu,
                type=a.type, restatement=2)


class TheKindsAreConstitutional(unittest.TestCase):
    def test_there_is_no_approximates_kind(self):
        with self.assertRaises(EngineError) as cm:
            Correspondence(EN, "a", LN, "b", "approximates")
        self.assertIn("no 'approximates' kind", str(cm.exception))

    def test_intra_chart_correspondence_is_refused(self):
        # Exact addressing owns intra-chart identity; an intra-chart arrow would be
        # similarity by the back door.
        with self.assertRaises(EngineError):
            Correspondence(EN, "a", EN, "b", "same_claim")

    def test_only_same_claim_carries_holonomy(self):
        same = Correspondence(EN, "a", LN, "b", "same_claim")
        ref = Correspondence(EN, "c", LN, "d", "refines")
        inst = Correspondence(EN, "e", LN, "f", "instance_of")
        self.assertTrue(same.loop_eligible)
        self.assertFalse(ref.loop_eligible)
        self.assertFalse(inst.loop_eligible)
        self.assertEqual(loop_pairs([same, ref, inst]), {same.pair})
        self.assertEqual(structural_pairs([same, ref, inst]), {same.pair, ref.pair, inst.pair})

    def test_uncertainty_is_warrant_not_a_weaker_kind(self):
        weak = Correspondence(EN, "a", LN, "b", "same_claim", tier=WarrantTier.EXTRACTION)
        strong = Correspondence(EN, "a", LN, "b", "same_claim", tier=WarrantTier.AUTHORSHIP)
        self.assertTrue(weak.provisional, "an LM proposal is provisional")
        self.assertFalse(strong.provisional, "operator confirmation clears the floor")
        self.assertEqual(weak.kind, strong.kind, "the structure is identical; only warrant differs")


class PlantedTrueCorrespondence(unittest.TestCase):
    """A genuine english<->lean restatement, injected at extraction tier."""

    def setUp(self):
        self.en = _slot(EN, "the cone is positive under composition")
        self.ln = _slot(LN, "theorem comp_pos (f g : Cone) : IsPositive (f . g)")
        self.tape = FastTape()
        self.outcome = ProposalOutcome(_hole(self.en, self.ln), "same_claim", "both assert positivity")

    def test_it_enters_through_the_inlet_at_extraction_tier(self):
        delta = as_correspondence_delta(self.outcome, "lm", "ph")
        self.assertEqual(delta.chart, CORRESPONDENCE_CHART)
        self.assertEqual(delta.warrant.tier, WarrantTier.EXTRACTION)
        self.tape.propose(delta, "lm")
        self.assertEqual(len(self.tape.entries), 1)

    def test_it_forms_a_provisional_fiber(self):
        delta = as_correspondence_delta(self.outcome, "lm", "ph")
        self.tape.propose(delta, "lm")
        arrows = correspondences_from_deltas(self.tape.deltas())
        self.assertEqual(len(arrows), 1)
        slots = [self.en, self.ln]
        fibers = build_loop_fibers(slots, arrows)
        self.assertEqual([tuple(f.slots) for f in fibers],
                         [tuple(sorted((self.en.id, self.ln.id)))])
        self.assertTrue(arrows[0].provisional, "an extraction-tier arrow is PROVISIONAL")

    def test_it_does_not_promote_without_authorship(self):
        delta = as_correspondence_delta(self.outcome, "lm", "ph")
        self.tape.propose(delta, "lm")
        arrow = correspondences_from_deltas(self.tape.deltas())[0]
        self.assertFalse(promotable(arrow.tier), "K must not promote an extraction-tier arrow")
        # ... and the operator's confirmation is a SEPARATE claim that does clear the floor.
        confirm(arrow, self.tape, "me")
        tiers = [d.warrant.tier for d in self.tape.deltas()]
        self.assertIn(WarrantTier.AUTHORSHIP, tiers)
        confirmed = [a for a in correspondences_from_deltas(self.tape.deltas())
                     if promotable(a.tier)]
        self.assertTrue(confirmed, "after confirmation the arrow is promotable")

    def test_confirmation_collides_on_the_same_address(self):
        """The confirmation asserts the SAME arrow, so it lands on the same slot."""
        delta = as_correspondence_delta(self.outcome, "lm", "ph")
        self.tape.propose(delta, "lm")
        arrow = correspondences_from_deltas(self.tape.deltas())[0]
        conf = confirm(arrow, self.tape, "me")
        self.assertEqual(conf.delta.slot, delta.slot,
                         "confirmation is a claim about the same arrow, not a new arrow")


class PlantedFalseCorrespondence(unittest.TestCase):
    """The OLD ARTIFACT as a control: a claim and its negation are NOT the same claim."""

    def setUp(self):
        self.pos = _slot(EN, "the cone is positive")
        self.neg = _slot(LN, "theorem not_pos : not (IsPositive c)")
        self.tape = FastTape()

    def test_the_proposer_is_instructed_to_answer_none(self):
        from engine.propose_correspondence import PROPOSE_SYSTEM
        self.assertIn("NEGATION", PROPOSE_SYSTEM)
        self.assertIn("LEGAL AND EXPECTED", PROPOSE_SYSTEM)

    def test_a_none_answer_enters_nothing(self):
        raw = '{"answers":[{"i":0,"kind":"none","evidence":"one negates the other"}]}'
        holes = [_hole(self.pos, self.neg)]
        outcomes = parse_answers(raw, holes)
        self.assertEqual(len(outcomes), 1)
        self.assertFalse(outcomes[0].is_arrow)
        _, entered = propose_over_holes(holes, self.tape, lambda s, u: raw)
        self.assertEqual(entered, [], "a `none` answer must create no claim")
        self.assertEqual(self.tape.entries, (), "and must not reach the tape")

    def test_if_it_survives_it_is_visibly_provisional_never_silently_accepted(self):
        # Force the bad arrow in anyway (a proposer that got it wrong).
        bad = ProposalOutcome(_hole(self.pos, self.neg), "same_claim", "wrongly matched")
        self.tape.propose(as_correspondence_delta(bad, "lm", "ph"), "lm")
        arrows = correspondences_from_deltas(self.tape.deltas())
        self.assertTrue(arrows, "the arrow exists in the structure")
        self.assertTrue(all(a.provisional for a in arrows),
                        "a false arrow that survives MUST be visibly provisional-unconfirmed")
        self.assertFalse(any(promotable(a.tier) for a in arrows),
                         "and must never be promotable without the operator")


class ReverseArrowMismatch(unittest.TestCase):
    def test_an_unreciprocated_same_claim_is_open_not_symmetric(self):
        forward = Correspondence(EN, "a", LN, "b", "same_claim")
        self.assertEqual([a.id() for a in asymmetries([forward])], [forward.id()],
                         "the reverse was never proposed, so the arrow is OPEN")

    def test_when_both_directions_are_proposed_nothing_is_open(self):
        forward = Correspondence(EN, "a", LN, "b", "same_claim")
        self.assertEqual(asymmetries([forward, forward.reverse()]), [])

    def test_the_reverse_is_a_separate_claim_with_a_separate_address(self):
        forward = Correspondence(EN, "a", LN, "b", "same_claim")
        f_slot, _ = address(CORRESPONDENCE_CHART, forward.surface(), "assert")
        r_slot, _ = address(CORRESPONDENCE_CHART, forward.reverse().surface(), "assert")
        self.assertNotEqual(f_slot, r_slot,
                            "an arrow and its reverse must not collide, or asymmetry is invisible")


class HolonomyExclusion(unittest.TestCase):
    """A loop containing a `refines` arrow must NOT enter the floor computation."""

    def test_a_refines_arrow_never_makes_a_loop(self):
        a = _slot(EN, "alpha holds in the general case")
        b = _slot(LN, "theorem alpha_general : Alpha g")
        c = _slot("tabular", "alpha | holds")
        slots = [a, b, c]
        # A triangle whose three arrows would close a cycle — but one is `refines`.
        arrows = [
            Correspondence(EN, a.id, LN, b.id, "same_claim"),
            Correspondence(LN, b.id, "tabular", c.id, "same_claim"),
            Correspondence(EN, a.id, "tabular", c.id, "refines"),   # <- non-invertible
        ]
        chart_of = {s.id: s.chart for s in slots}
        loop_fibers = build_loop_fibers(slots, arrows)
        edges = loop_edges(slots, arrows)
        loops = loops_from_fibers(loop_fibers, chart_of,
                                  restrict_to={s.id for s in slots}, edges=edges)
        for loop in loops:
            pairs = {(u, v) if u < v else (v, u) for u, v in loop.edges()}
            refines_pair = Correspondence(EN, a.id, "tabular", c.id, "refines").pair
            self.assertNotIn(refines_pair, pairs,
                             "a loop must not traverse a non-invertible refines arrow")

    def test_refines_still_contributes_structure(self):
        a = _slot(EN, "beta holds")
        b = _slot(LN, "theorem beta : Beta")
        arrows = [Correspondence(EN, a.id, LN, b.id, "refines")]
        edges = structural_edges([a, b], arrows)
        self.assertEqual(len(edges), 1, "refines couples (gate-2 energy) even without holonomy")
        self.assertEqual(edges[0].origin, "correspondence:refines")
        self.assertEqual(build_loop_fibers([a, b], arrows), [],
                         "...but forms no loop-eligible fiber")


class HoleEnumerationIsStructural(unittest.TestCase):
    def setUp(self):
        self.slots = [_slot(EN, "gamma holds"), _slot(EN, "delta holds"),
                      _slot(LN, "theorem gamma : Gamma"), _slot(LN, "theorem delta : Delta")]
        self.support = {s.id: 2 for s in self.slots}

    def test_candidates_are_cross_chart_and_type_compatible_only(self):
        holes = enumerate_holes(self.slots, self.support, limit=50)
        self.assertTrue(holes)
        for h in holes:
            self.assertNotEqual(h.src_chart, h.dst_chart, "intra-chart is owned by addressing")
            self.assertEqual(h.type, "assert")

    def test_an_existing_arrow_is_not_a_hole(self):
        en = next(s for s in self.slots if s.chart == EN)
        ln = next(s for s in self.slots if s.chart == LN)
        existing = [Correspondence(EN, en.id, LN, ln.id, "same_claim")]
        holes = enumerate_holes(self.slots, self.support, existing=existing, limit=50)
        pair = existing[0].pair
        self.assertNotIn(pair, {(h.src_slot, h.dst_slot) if h.src_slot < h.dst_slot
                                else (h.dst_slot, h.src_slot) for h in holes})

    def test_it_is_bounded_and_ranked_by_restatement(self):
        holes = enumerate_holes(self.slots, self.support, limit=2)
        self.assertLessEqual(len(holes), 2, "the enumeration is bounded before materializing")
        counts = [h.restatement for h in holes]
        self.assertEqual(counts, sorted(counts, reverse=True), "ranked by restatement")


class TheOneWritePath(unittest.TestCase):
    def test_correspondence_proposals_reach_the_tape_only_via_propose(self):
        import ast
        import inspect

        import engine.propose_correspondence as mod

        tree = ast.parse(inspect.getsource(mod))
        appends = [n for n in ast.walk(tree)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr in ("append", "extend")
                   and isinstance(n.func.value, ast.Attribute)
                   and n.func.value.attr.startswith("_entries")]
        self.assertEqual(appends, [], "nothing here may touch the tape's entry list directly")
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "propose"]
        self.assertTrue(calls, "proposals must go through tape.propose")


if __name__ == "__main__":
    unittest.main()


class Gate8AppliesToCorrespondenceClaims(unittest.TestCase):
    """A correspondence claim's value derives from its OWN content, not surrounding text."""

    def test_the_claim_is_addressed_from_its_own_canonical_surface(self):
        arrow = Correspondence(EN, "aaa", LN, "bbb", "same_claim")
        slot, nu_value = address(CORRESPONDENCE_CHART, arrow.surface(), "assert")
        # Re-addressing the same arrow reproduces the same slot: the address is a function of
        # the arrow's own content (two exact slot addresses + the kind) and nothing else.
        again, _ = address(CORRESPONDENCE_CHART, arrow.surface(), "assert")
        self.assertEqual(slot, again)
        self.assertIn("aaa", nu_value)
        self.assertIn("bbb", nu_value)

    def test_the_static_span_check_is_green_with_the_correspondence_path_present(self):
        from engine.static_checks import check_span_discipline
        r = check_span_discipline()
        self.assertEqual(r.violations, [], f"gate 8: {r.violations}")

    def test_a_different_kind_is_a_different_claim(self):
        same = Correspondence(EN, "aaa", LN, "bbb", "same_claim")
        ref = Correspondence(EN, "aaa", LN, "bbb", "refines")
        s1, _ = address(CORRESPONDENCE_CHART, same.surface(), "assert")
        s2, _ = address(CORRESPONDENCE_CHART, ref.surface(), "assert")
        self.assertNotEqual(s1, s2, "kind is part of what the claim asserts")
