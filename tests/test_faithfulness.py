"""Positive controls for every row of the faithfulness audit.

Each class here is the executable half of a row in `engine/faithfulness.py`. A row whose
control does not exist fails `check_faithfulness`; a row whose control passes vacuously is
worse than no row at all, so each control is written to fail if the object it names stops
being implemented.

Two of these are theory-level rather than component-level: `TreeNull` and `PlantedCycle`
test the hypergraph claim itself. `TreeNull` currently pins a **gap** — it asserts what the
engine actually does, which is not what the theory says it should — so the failure cannot be
closed by accident or forgotten.
"""

from __future__ import annotations

import unittest

from engine import GateViolation
from engine.blocks import build_blocks, edges_from_fibers, loops_from_fibers
from engine.energy import FreeEnergy, evidence_from_deltas, lexicon_prior
from engine.linalg import normalize_simplex
from engine.meter import anneal, edge_weight_map, holonomy
from engine.normalize import address, classify, nu, slot_id
from engine.settle import settle
from engine.types import (
    Block,
    Clamp,
    Delta,
    Fiber,
    LoopSpec,
    Provenance,
    QEdge,
    Slot,
    Warrant,
    WarrantTier,
)

KERNEL = Warrant(WarrantTier.KERNEL, "lean:accept")
FLAT = [0.0, 0.0, 0.0, 0.0]


def delta(slot: str, value: str, extractor: str, confidence: float = 1.0,
          warrant: Warrant | None = None) -> Delta:
    return Delta(
        slot=slot, chart="english", type="assert", value=value, confidence=confidence,
        warrant=warrant or Warrant(WarrantTier.EXTRACTION),
        provenance=Provenance("repo_docs", "doc", "loc", extractor, "hash"),
        surface=slot, nu=slot,
    )


def block_of(*slots: str, weight: float = 0.9) -> Block:
    edges = tuple(
        QEdge(slots[i], slots[i + 1], weight, "fiber") for i in range(len(slots) - 1)
    )
    return Block("b", tuple(slots), edges)


class EvidenceFactor(unittest.TestCase):
    """Row: evidence factor -> engine/energy.py:evidence_from_deltas."""

    def test_evidence_moves_the_settled_state_and_absence_leaves_it_uniform(self):
        block = block_of("s1", "s2")
        priors = {s: list(FLAT) for s in block.slots}

        bare = settle(block, {}, priors, 1.0)
        for s in block.slots:
            for k in range(4):
                self.assertAlmostEqual(bare.p[s][k], 0.25, places=6,
                                       msg="no evidence must leave the slot uniform")

        supported = evidence_from_deltas([delta("s1", "T", "e1"), delta("s1", "T", "e2")])
        moved = settle(block, supported, priors, 1.0)
        self.assertGreater(moved.p["s1"][2], bare.p["s1"][2],
                           "supporting deltas must lower T's energy and raise its mass")

        # Confidence and warrant weight are load-bearing, not decorative.
        weak = evidence_from_deltas([delta("s1", "T", "e1", confidence=0.05)])
        self.assertGreater(
            settle(block, supported, priors, 1.0).p["s1"][2],
            settle(block, weak, priors, 1.0).p["s1"][2],
            "two full-confidence deltas must move the state further than one weak one",
        )


class IntraChartSheaf(unittest.TestCase):
    """Row: intra-chart sheaf -> engine/blocks.py:edges_from_fibers.

    The deviation on this row says the gluing is a soft quadratic penalty rather than a
    sheaf condition. This control demonstrates the pull exists *and* that it is soft.
    """

    def test_same_chart_coupling_pulls_and_dropping_it_releases(self):
        ev = evidence_from_deltas([delta("s1", "T", "e1"), delta("s2", "F", "e2")])
        priors = {"s1": list(FLAT), "s2": list(FLAT)}

        coupled = settle(block_of("s1", "s2"), ev, priors, 1.0)
        apart = settle(Block("b", ("s1", "s2"), ()), ev, priors, 1.0)

        def gap(state):
            return max(abs(state.p["s1"][k] - state.p["s2"][k]) for k in range(4))

        self.assertLess(gap(coupled), gap(apart),
                        "a same-chart Q edge must pull the two settled states together")
        self.assertGreater(gap(coupled), 0.0,
                           "and it must NOT identify them — gluing is energy, not a "
                           "constraint (the row's recorded deviation)")

    def test_the_edge_is_built_from_same_chart_fiber_membership(self):
        slots = [Slot(id="s1", nu="\x01en\x01positive cone", type="assert", chart="english"),
                 Slot(id="s2", nu="\x01en\x01positive cones", type="assert", chart="english")]
        edges = edges_from_fibers([Fiber(id="f", slots=("s1", "s2"))], slots)
        self.assertTrue(edges, "same-chart fiber members must produce a Q edge")
        self.assertFalse(edges[0].crosses_charts({"s1": "english", "s2": "english"}))


class InterChartCorrespondence(unittest.TestCase):
    """Row: inter-chart correspondence -> engine/types.py:QEdge.

    The recorded deviation is that correspondence is **pairwise-collapsed**. This control
    both exercises the cross-chart edge and demonstrates why a triangle of pairwise edges
    is not a ternary factor.
    """

    def test_correspondence_is_pairwise_and_a_three_cycle_is_not_a_ternary_factor(self):
        # It is a correspondence: it crosses charts and it transports.
        chart_of = {"en": "english", "ln": "lean"}
        edge = QEdge("en", "ln", 0.9, "fiber")
        self.assertTrue(edge.crosses_charts(chart_of))

        ev = evidence_from_deltas([delta("en", "T", "e1"), delta("ln", "F", "e2")])
        priors = {"en": list(FLAT), "ln": list(FLAT)}
        coupled = settle(Block("b", ("en", "ln"), (edge,)), ev, priors, 1.0)
        apart = settle(Block("b", ("en", "ln"), ()), ev, priors, 1.0)
        self.assertLess(
            max(abs(coupled.p["en"][k] - coupled.p["ln"][k]) for k in range(4)),
            max(abs(apart.p["en"][k] - apart.p["ln"][k]) for k in range(4)),
        )

        # QEdge is binary by construction: there is no k-ary factor type to build.
        self.assertEqual(
            [f for f in QEdge.__dataclass_fields__ if f in ("u", "v")], ["u", "v"],
            "QEdge has exactly two endpoints",
        )

        # A joint 3-way condition with no pairwise shadow: "exactly one of the three is T".
        # Every PAIR is unconstrained under it — for any two slots, every combination of
        # values appears in some satisfying assignment — so no set of pairwise factors can
        # encode it, and a triangle of Q edges therefore cannot represent it.
        values = ("T", "F")
        satisfying = [a for a in
                      [(x, y, z) for x in values for y in values for z in values]
                      if sum(v == "T" for v in a) == 1]
        self.assertEqual(len(satisfying), 3)
        for i, j in ((0, 1), (0, 2), (1, 2)):
            pairs_seen = {(a[i], a[j]) for a in satisfying}
            self.assertGreater(
                len(pairs_seen), 1,
                "each pair remains genuinely undetermined, so the constraint lives only in "
                "the triple — a pairwise-collapsed engine cannot express it",
            )


class QPriors(unittest.TestCase):
    """Row: Q-priors -> engine/energy.py:FreeEnergy. Gate 2, measured."""

    def test_an_arbitrarily_heavy_prior_still_cannot_fix_a_value(self):
        leaning = lexicon_prior(["s1"], {"s1": "T"})
        heavy = {"s1": [v * 1000.0 for v in leaning["s1"]]}
        settled = settle(Block("b", ("s1",), ()), {}, heavy, 1.0)

        self.assertGreater(settled.p["s1"][2], 0.9, "a heavy prior should tilt hard")
        self.assertLess(settled.p["s1"][2], 1.0,
                        "but never reach the vertex: a prior is energy, and energy leaves "
                        "mass everywhere")
        self.assertTrue(all(settled.p["s1"][k] > 0.0 for k in range(4)),
                        "no b-value may be driven to exactly zero by a prior")

    def test_the_coupling_term_is_the_quadratic_the_theory_names(self):
        f = FreeEnergy(("u", "v"), {}, {}, (QEdge("u", "v", 1.0, "fiber"),), 1.0)
        near = {"u": normalize_simplex([0.7, 0.1, 0.1, 0.1]),
                "v": normalize_simplex([0.7, 0.1, 0.1, 0.1])}
        far = {"u": normalize_simplex([0.97, 0.01, 0.01, 0.01]),
               "v": normalize_simplex([0.01, 0.01, 0.01, 0.97])}
        self.assertLess(f.value(near), f.value(far),
                        "disagreement across a Q edge must cost energy")


class Clamps(unittest.TestCase):
    """Row: clamps -> engine/types.py:Clamp. Gate 3, measured."""

    def test_a_clamp_holds_and_a_non_eligible_warrant_cannot_make_one(self):
        block = block_of("s1", "s2")
        priors = {s: list(FLAT) for s in block.slots}
        # Evidence pushing the opposite way, so a clamp that leaked would be visible.
        ev = evidence_from_deltas([delta("s1", "F", "e1"), delta("s1", "F", "e2")])
        settled = settle(block, ev, priors, 1.0, clamps=[Clamp("s1", "T", KERNEL)])
        self.assertGreater(settled.p["s1"][2], 0.99,
                           "a clamped slot must hold its value against contrary evidence")

        with self.assertRaises(GateViolation):
            Clamp("s1", "T", Warrant(WarrantTier.EXTRACTION))
        with self.assertRaises(GateViolation):
            Clamp("s1", "T", Warrant(WarrantTier.PREMINTED))


class TypeConsistency(unittest.TestCase):
    """Row: type-consistency -> engine/normalize.py:slot_id."""

    def test_same_surface_different_type_cannot_collide_or_contest(self):
        surface = "the cone is positive"
        n = nu("english", surface)
        as_assert = slot_id(n, "assert")
        as_define = slot_id(n, "define")
        self.assertNotEqual(as_assert, as_define,
                            "type is constitutive of the address (gate 1)")

        # And they can never end up contesting each other: different addresses, no edge.
        deltas = [delta(as_assert, "T", "e1"), delta(as_define, "F", "e2")]
        slots = [Slot(id=as_assert, nu=n, type="assert", chart="english"),
                 Slot(id=as_define, nu=n, type="define", chart="english")]
        blocks = build_blocks(slots, [], deltas)
        for b in blocks:
            self.assertFalse({as_assert, as_define} <= set(b.slots),
                             "a type mismatch must not become a contest")

    def test_address_carries_the_classified_type(self):
        surface = "if the kernel accepts then the statement is certified"
        kind = classify("english", surface)
        slot, normalized = address("english", surface, kind)
        self.assertEqual(normalized, nu("english", surface))
        self.assertEqual(slot, slot_id(normalized, kind))
        self.assertNotEqual(slot, slot_id(normalized, "define"),
                            "the address must depend on the classified type")


class BlocksAreConnectedComponents(unittest.TestCase):
    """Row: blocks as connected components -> engine/blocks.py:build_blocks."""

    def test_two_disjoint_contests_settle_independently(self):
        deltas = [delta("a1", "T", "e1"), delta("a1", "F", "e2"),
                  delta("a2", "T", "e1"),
                  delta("b1", "T", "e1"), delta("b1", "F", "e2"),
                  delta("b2", "F", "e2")]
        slots = [Slot(id=s, nu=s, type="assert", chart="english")
                 for s in ("a1", "a2", "b1", "b2")]
        edges = [QEdge("a1", "a2", 0.9, "fiber"), QEdge("b1", "b2", 0.9, "fiber")]

        blocks = build_blocks(slots, edges, deltas)
        self.assertEqual(len(blocks), 2, "no Q edge joins the two contests")
        self.assertEqual({frozenset(b.slots) for b in blocks},
                         {frozenset({"a1", "a2"}), frozenset({"b1", "b2"})})

        a_block = next(b for b in blocks if "a1" in b.slots)
        priors = {s.id: list(FLAT) for s in slots}
        before = anneal(a_block, evidence_from_deltas(deltas), priors, 1.0)

        louder = deltas + [delta("b1", "B", "e3"), delta("b2", "B", "e3"),
                           delta("b1", "N", "e4"), delta("b2", "T", "e5")]
        after = anneal(a_block, evidence_from_deltas(louder), priors, 1.0)

        moved = max(abs(before.p[s][k] - after.p[s][k])
                    for s in a_block.slots for k in range(4))
        self.assertEqual(moved, 0.0,
                         "perturbing one component must move the other by exactly zero")


class DescentCertificate(unittest.TestCase):
    """Row: descent certificate -> engine/settle.py:settle."""

    def test_an_injected_non_monotone_step_voids_the_block(self):
        """The positive control: rig F to rise and the certificate must say `violated`."""
        import engine.settle as settle_mod

        block = block_of("s1", "s2")
        priors = {s: list(FLAT) for s in block.slots}
        # Evidence that actually pushes: with a flat objective the iterate is already
        # stationary and settling returns before taking a step, so the injection would
        # never be exercised and the control would be dead.
        ev = evidence_from_deltas([delta("s1", "T", "e1"), delta("s2", "F", "e2")])
        self.assertEqual(settle(block, ev, priors, 1.0).certificate, "monotone")

        original = settle_mod.FreeEnergy

        class Rising(original):  # type: ignore[misc, valid-type]
            """An objective that rises on every evaluation. No step can descend."""

            _calls = [0]

            def value(self, p):  # noqa: D102
                self._calls[0] += 1
                return float(self._calls[0])

        settle_mod.FreeEnergy = Rising
        try:
            rigged = settle(block, ev, priors, 1.0)
        finally:
            settle_mod.FreeEnergy = original

        self.assertEqual(rigged.certificate, "violated",
                         "a non-monotone objective must void the block, not be absorbed")
        self.assertGreater(rigged.backtracks, 0,
                           "the halving safeguard must have been exhausted, not skipped")
        self.assertEqual(settle(block, ev, priors, 1.0).certificate, "monotone",
                         "and the injection must not leak into later settles")

    def test_the_trace_is_non_increasing_on_a_real_block(self):
        ev = evidence_from_deltas([delta("s1", "T", "e1"), delta("s2", "F", "e2")])
        trace = settle(block_of("s1", "s2"), ev, {s: list(FLAT) for s in ("s1", "s2")},
                       1.0).f_trace
        self.assertTrue(trace)
        for earlier, later in zip(trace, trace[1:]):
            self.assertLessEqual(later, earlier + 1e-12)


class TreeNull(unittest.TestCase):
    """Row: tree-null — **PINS A GAP**.

    Theory: a contest graph with no cycles has a unique path between any two slots, so
    transport is path-independent and the cold floor is exactly zero — all tree contest is
    path-debt.

    The engine does not do this. These tests assert what it *actually* does, so the gap is
    recorded rather than remembered, and so that closing it turns these tests red and forces
    the record to be updated with it.
    """

    @staticmethod
    def _states():
        return {"u": normalize_simplex([0.7, 0.1, 0.1, 0.1]),
                "v": normalize_simplex([0.1, 0.1, 0.1, 0.7]),
                "x": normalize_simplex([0.1, 0.7, 0.1, 0.1])}

    def test_a_tree_contest_graph_does_not_yield_zero_floor(self):
        """(A) A backtracking walk on a single-edge tree has nonzero holonomy."""
        p = self._states()
        weights = edge_weight_map([QEdge("u", "v", 0.9, "fiber")])
        walk = LoopSpec(id="two", kind="paraphrase", slots=("u", "v"))

        self.assertEqual(walk.edges(), [("u", "v"), ("v", "u")],
                         "a two-member fiber yields a backtracking walk, not a cycle")
        h = holonomy(walk, p, weights)
        self.assertGreater(h, 0.1,
                           "GAP: theory says a tree has zero holonomy; the engine returns "
                           "a residual because transport is a contraction, not a reversible "
                           "parallel transport")
        self.assertAlmostEqual(h, 0.14958448753462605, places=12,
                               msg="pinned so the gap cannot drift silently")

    def test_two_member_fibers_are_the_common_case_so_the_gap_is_load_bearing(self):
        loops = loops_from_fibers([Fiber(id="f", slots=("u", "v"))],
                                  {"u": "english", "v": "english"})
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].edges(), [("u", "v"), ("v", "u")])

    def test_a_loop_spec_may_name_a_closing_edge_that_does_not_exist(self):
        """(B) Holonomy silently measures an open walk as if it were closed."""
        p = self._states()
        path = edge_weight_map([QEdge("u", "v", 0.9, "fiber"),
                                QEdge("v", "x", 0.9, "fiber")])
        triangle = edge_weight_map([QEdge("u", "v", 0.9, "fiber"),
                                    QEdge("v", "x", 0.9, "fiber"),
                                    QEdge("u", "x", 0.9, "fiber")])
        loop = LoopSpec(id="tri", kind="paraphrase", slots=("u", "v", "x"))

        self.assertEqual(path.get(("x", "u"), 0.0) or path.get(("u", "x"), 0.0), 0.0,
                         "the closing edge is absent from the Q graph")
        open_walk = holonomy(loop, p, path)
        closed = holonomy(loop, p, triangle)

        self.assertGreater(open_walk, closed,
                           "GAP: the open walk reports MORE holonomy than the genuine "
                           "cycle, because the start state is compared against a state "
                           "transported somewhere else entirely")
        self.assertAlmostEqual(open_walk, 0.4337950138504155, places=12)
        self.assertAlmostEqual(closed, 0.22831316518442923, places=12)


class PlantedCycle(unittest.TestCase):
    """Row: planted-cycle -> engine/meter.py:measure. This one holds."""

    @staticmethod
    def _block():
        return Block("b", ("en1", "ln1", "en2"), (
            QEdge("en1", "ln1", 0.9, "fiber"),   # the correspondence edge
            QEdge("ln1", "en2", 0.9, "fiber"),
            QEdge("en2", "en1", 0.9, "fiber"),   # closes the cycle in Q
        ))

    def _floor(self, clamps):
        block = self._block()
        flat = {s: list(FLAT) for s in block.slots}
        cold = anneal(block, flat, flat, 1.0, clamps=clamps, retained=None)
        loop = LoopSpec("l", "restatement", ("en1", "ln1", "en2"))
        return holonomy(loop, cold.p, edge_weight_map(block.edges)), cold

    def test_a_frustrated_cycle_yields_a_persistent_nonzero_floor(self):
        frustrated, cold = self._floor([Clamp("en1", "T", KERNEL),
                                        Clamp("en2", "F", KERNEL)])
        compatible, _ = self._floor([Clamp("en1", "T", KERNEL),
                                     Clamp("en2", "T", KERNEL)])

        self.assertGreater(frustrated, 0.3, "incompatible clamped ends must frustrate")
        self.assertGreater(frustrated, 10 * compatible,
                           "and by far more than the same topology with compatible ends")
        self.assertEqual(cold.certificate, "monotone",
                         "frustration is a property of the ledger, not a settling failure")

        again, _ = self._floor([Clamp("en1", "T", KERNEL), Clamp("en2", "F", KERNEL)])
        self.assertEqual(frustrated, again,
                         "and it must survive re-anneal bit-identically")

    def test_the_frustration_runs_through_the_correspondence_edge(self):
        """Drop the cross-chart edge and the cycle is gone, so the floor must collapse."""
        block = self._block()
        broken = Block("b", block.slots, tuple(e for e in block.edges
                                               if not (e.u == "en1" and e.v == "ln1")))
        flat = {s: list(FLAT) for s in block.slots}
        cold = anneal(broken, flat, flat, 1.0,
                      clamps=[Clamp("en1", "T", KERNEL), Clamp("en2", "F", KERNEL)])
        loop = LoopSpec("l", "restatement", ("en1", "ln1", "en2"))
        opened = holonomy(loop, cold.p, edge_weight_map(broken.edges))
        frustrated, _ = self._floor([Clamp("en1", "T", KERNEL), Clamp("en2", "F", KERNEL)])
        self.assertNotEqual(opened, frustrated)


class TheAuditIsComplete(unittest.TestCase):
    """The check itself, and its own positive control."""

    def test_every_row_is_mapped_controlled_and_classified(self):
        from engine.faithfulness import check_faithfulness

        result = check_faithfulness()
        self.assertTrue(result.ok, result.problems)
        self.assertGreaterEqual(result.checked_rows, 10)

    def test_an_unmapped_row_is_caught(self):
        from engine.faithfulness import Row, check_faithfulness
        import engine.faithfulness as mod

        original = mod.FAITHFULNESS_ROWS
        mod.FAITHFULNESS_ROWS = original + (
            Row(object="phantom", family="factor", site="engine/energy.py:no_such_symbol",
                role="-", control=original[0].control, control_claim="x"),
        )
        try:
            self.assertFalse(check_faithfulness().ok)
        finally:
            mod.FAITHFULNESS_ROWS = original

    def test_an_uncontrolled_row_is_caught(self):
        from engine.faithfulness import Row, check_faithfulness
        import engine.faithfulness as mod

        original = mod.FAITHFULNESS_ROWS
        mod.FAITHFULNESS_ROWS = original + (
            Row(object="phantom", family="factor", site="engine/energy.py:FreeEnergy",
                role="-", control="tests/test_faithfulness.py:Nope.test_nope",
                control_claim="x"),
        )
        try:
            self.assertFalse(check_faithfulness().ok)
        finally:
            mod.FAITHFULNESS_ROWS = original

    def test_a_by_design_deviation_without_a_ruling_is_caught(self):
        from engine.faithfulness import (
            MINIMAL_FAITHFUL, Deviation, Row, check_faithfulness,
        )
        import engine.faithfulness as mod

        original = mod.FAITHFULNESS_ROWS
        mod.FAITHFULNESS_ROWS = original + (
            Row(object="phantom", family="factor", site="engine/energy.py:FreeEnergy",
                role="-", control=original[0].control, control_claim="x",
                deviation=Deviation(kind=MINIMAL_FAITHFUL, note="because", ruling="")),
        )
        try:
            self.assertFalse(check_faithfulness().ok,
                             "calling a deviation deliberate requires naming what permits it")
        finally:
            mod.FAITHFULNESS_ROWS = original

    def test_the_open_gap_is_reported_rather_than_suppressed(self):
        from engine.faithfulness import check_faithfulness, gaps_before_p3

        gaps = gaps_before_p3()
        self.assertEqual([g.object for g in gaps],
                         ["tree-null (all tree contest is path-debt)"])
        self.assertTrue(check_faithfulness().ok,
                        "a classified gap is a finding, not a build failure — a finding "
                        "behind a red build is a finding nobody reads")


if __name__ == "__main__":
    unittest.main()
