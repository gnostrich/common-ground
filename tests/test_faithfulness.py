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
from engine.blocks import build_blocks, edges_from_fibers, loops_from_fibers, order_cycle
from engine.constants import decisions, shadow
from engine.extract import build_k_extractors
from engine.energy import FreeEnergy, evidence_from_deltas, lexicon_prior
from engine.linalg import normalize_simplex
from engine.meter import (
    OpenWalkError,
    anneal,
    edge_weight_map,
    holonomy,
    measured_shadow,
    path_transport_disagreement,
    verify_cycle,
)
from engine.normalize import address, classify, nu, slot_id
from engine.pipeline import build_ledger, run_meter
from engine.settle import settle
from engine.types import (
    Block,
    Clamp,
    Delta,
    Document,
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
    """Row: tree-null — **REPAIRED**, and these are the controls the ruling mandated.

    Theory: a contest graph with no cycles has a unique path between any two slots, so
    transport is path-independent and the cold floor is exactly zero — all tree contest is
    path-debt.

    Before the repair the engine returned 0.1496 on a single-edge tree and 0.4338 on an open
    three-slot walk. Both came from treating a walk as a cycle. Holonomy is now defined only
    on verified cycles, and backtracking became the measured-shadow channel.
    """

    @staticmethod
    def _states():
        return {"u": normalize_simplex([0.7, 0.1, 0.1, 0.1]),
                "v": normalize_simplex([0.1, 0.1, 0.1, 0.7]),
                "x": normalize_simplex([0.1, 0.7, 0.1, 0.1])}

    def test_a_backtrack_walk_is_refused_as_a_loop(self):
        """Control 1a: the backtracking walk is no longer holonomy."""
        weights = edge_weight_map([QEdge("u", "v", 0.9, "fiber")])
        walk = LoopSpec(id="two", kind="paraphrase", slots=("u", "v"))
        with self.assertRaises(OpenWalkError) as ctx:
            holonomy(walk, self._states(), weights)
        self.assertIn("measured-shadow channel", str(ctx.exception))

    def test_a_backtrack_walk_is_classified_shadow_and_excluded_from_floor_support(self):
        """Control 1b: it is measured, as shadow, and it is not a loop."""
        weights = edge_weight_map([QEdge("u", "v", 0.9, "fiber")])
        eps = measured_shadow("u", "v", self._states(), weights)
        self.assertGreater(eps, 0.0, "the round trip does lose something — that is shadow")
        self.assertAlmostEqual(eps, 0.14958448753462605, places=12,
                               msg="the same number the old code called holonomy")

        # And it contributes no loop, so it cannot enter the floor.
        loops = loops_from_fibers(
            [Fiber(id="f", slots=("u", "v"))], {"u": "english", "v": "english"},
            edges=[QEdge("u", "v", 0.9, "fiber")],
        )
        self.assertEqual(loops, [], "a two-member fiber yields no loop at all")

    def test_an_open_walk_raises_rather_than_being_silently_measured(self):
        """Control 2: refuse, never skip."""
        path = edge_weight_map([QEdge("u", "v", 0.9, "fiber"),
                                QEdge("v", "x", 0.9, "fiber")])
        loop = LoopSpec(id="tri", kind="paraphrase", slots=("u", "v", "x"))
        with self.assertRaises(OpenWalkError) as ctx:
            holonomy(loop, self._states(), path)
        self.assertIn("not in Q", str(ctx.exception))

        # The constructor never emits such a spec in the first place.
        self.assertEqual(
            loops_from_fibers([Fiber(id="f", slots=("u", "v", "x"))],
                              {s: "english" for s in "uvx"},
                              edges=[QEdge("u", "v", 0.9, "fiber"),
                                     QEdge("v", "x", 0.9, "fiber")]),
            [], "no cycle in Q means no loop spec",
        )

    def test_the_open_walk_quantity_survives_only_as_a_named_diagnostic(self):
        path = edge_weight_map([QEdge("u", "v", 0.9, "fiber"),
                                QEdge("v", "x", 0.9, "fiber")])
        walk = LoopSpec(id="tri", kind="paraphrase", slots=("u", "v", "x"))
        d = path_transport_disagreement(walk, self._states(), path)
        self.assertAlmostEqual(d, 0.4337950138504155, places=12,
                               msg="the identical number the old code returned as holonomy — "
                                   "the quantity is retained and renamed, not recomputed. "
                                   "What changed is that nothing reads it as a floor.")

    @staticmethod
    def _two_member_tree():
        """Two GENUINE same-claim paraphrases DECLARED as one proposition. A two-member fiber
        is a tree — one Q edge, no cycle — so no holonomy is defined on it. This is the honest
        cycle-free contest graph under exact addressing: the deleted P/not-P pair fibered only
        on string overlap; these fiber because the correspondence is DECLARED, and they still
        close no cycle because two members cannot."""
        docs = [Document("a", "english", "The kernel accepts the statement.", "repo_docs"),
                Document("b", "english", "The kernel accepts every checked statement.", "repo_docs")]
        exts = build_k_extractors(decisions(), offline=True)
        base = build_ledger(docs, exts, correspondence=frozenset())
        ids = sorted(s.id for s in base.slots)
        corr = frozenset({(ids[0], ids[1])})
        return build_ledger(docs, exts, correspondence=corr)

    def test_tree_null_passes_with_floor_zero(self):
        """Control 4: a cycle-free contest graph yields floor exactly 0."""
        ledger = self._two_member_tree()
        self.assertEqual(ledger.loops, [], "two fibered surfaces close no cycle")
        result, _, _ = run_meter(ledger, 1.0, "tree-null", shadow())
        self.assertEqual(result.mean_floor(), 0.0,
                         "all tree contest is path-debt — the floor is exactly zero")

    def test_a_cycle_free_corpus_is_flagged_no_cycle_support(self):
        """Control 5: floor 0 with a reason, never a silent zero."""
        ledger = self._two_member_tree()
        result, _, _ = run_meter(ledger, 1.0, "tree-null", shadow())
        self.assertTrue(result.no_cycle_support,
                        "a zero floor for want of a cycle must say so")
        self.assertEqual(result.measurements, [])

    def test_the_restatement_loop_is_a_genuine_triangle(self):
        """Eng_1 -> Lean -> Eng_2 -> Eng_1, as PREREG's matrix always named it."""
        chart_of = {"en1": "english", "ln": "lean", "en2": "english"}
        edges = [QEdge("en1", "ln", 0.9, "fiber"), QEdge("ln", "en2", 0.9, "fiber"),
                 QEdge("en1", "en2", 0.9, "fiber")]
        loops = loops_from_fibers([Fiber(id="f", slots=("en1", "ln", "en2"))],
                                  chart_of, edges=edges)
        self.assertEqual(len(loops), 1)
        loop = loops[0]
        self.assertEqual(loop.kind, "restatement")
        self.assertEqual(loop.slots, ("en1", "ln", "en2"),
                         "the crossing is traversed first, so the cycle reads Eng->Lean->Eng")
        self.assertEqual(loop.edges(), [("en1", "ln"), ("ln", "en2"), ("en2", "en1")])
        verify_cycle(loop, edge_weight_map(edges))


class MeasuredShadowChannel(unittest.TestCase):
    """The calibration channel the repair produced. Standard meter output."""

    @staticmethod
    def _grounded_cross_chart():
        """A GENUINE english<->lean restatement (both affirm the cone is positive) DECLARED as
        a cross-chart correspondence, with a KERNEL grounding on the english side that
        conflicts with the lean reading. The two settled states then differ, so the round-trip
        closure defect (measured shadow) on the correspondence edge is nonzero — a real
        translator drift. This replaces the deleted P/not-P triple: the drift here comes from a
        genuine grounding conflict across a true restatement, never from string overlap. The
        lean value is read off `nu(lean, surface)` = 'theorem cone_pos : IsPositive c' (cut at
        `:=`), so nothing outside the address span decides it (GATES.md sentence 8)."""
        en = Document("d", "english", "The cone is positive.", "repo_docs")
        ln = Document("l", "lean", "theorem cone_pos : IsPositive c := by simp", "lean_corpus")
        exts = build_k_extractors(decisions(), offline=True)
        base = build_ledger([en, ln], exts, correspondence=frozenset())
        en_slot = next(s.id for s in base.slots if s.chart == "english")
        ln_slot = next(s.id for s in base.slots if s.chart == "lean")
        corr = frozenset({(min(en_slot, ln_slot), max(en_slot, ln_slot))})
        clamps = [Clamp(en_slot, "F", Warrant(WarrantTier.KERNEL, "kernel:accept"))]
        ledger = build_ledger([en, ln], exts, correspondence=corr, clamps=clamps)
        result, _, _ = run_meter(ledger, 1.0, "calib", shadow())
        return result

    def test_measured_defect_is_reported_beside_the_seed_declaration(self):
        result = self._grounded_cross_chart()

        self.assertTrue(result.shadow_calibration, "every Q edge contributes a row")
        for row in result.shadow_calibration:
            self.assertGreaterEqual(row.eps_measured, 0.0)
            self.assertEqual(row.declared, 0.0, "the seed declares zero defect")
            self.assertAlmostEqual(row.drift, row.eps_measured - row.declared)

        summary = result.shadow_summary()
        self.assertIn("max_translator_drift", summary)
        self.assertEqual(summary["edges"], float(len(result.shadow_calibration)))

    def test_translator_drift_names_cross_chart_edges_only(self):
        result = self._grounded_cross_chart()
        drift_rows = result.translator_drift()
        self.assertTrue(drift_rows, "the grounded restatement must produce a measured drift")
        for row in drift_rows:
            self.assertTrue(row.crosses_charts)
            self.assertGreater(row.drift, 0.0)

    def test_the_measured_defect_never_deflates_a_floor(self):
        """It is calibration, not subtraction — a measured defect that reduced its own
        floor would be the resample-of-the-observation pattern gate 6 forbids."""
        import inspect

        import engine.meter as meter_mod

        source = inspect.getsource(meter_mod.measure).replace(" ", "")
        self.assertIn("floor=max(0.0,h_cold-sh)", source,
                      "the floor still subtracts the DECLARED shadow")
        self.assertNotIn("eps_measured", source.split("floor=")[1][:300],
                         "and never the measured one")


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
        """Drop the cross-chart edge and there is no cycle left to measure.

        Before the tree-null repair this silently returned a number for the open walk. Now
        it refuses, which is the stronger and more honest statement: the frustration was
        never a property of the three slots, it was a property of the cycle through the
        correspondence.
        """
        block = self._block()
        broken = Block("b", block.slots, tuple(e for e in block.edges
                                               if not (e.u == "en1" and e.v == "ln1")))
        flat = {s: list(FLAT) for s in block.slots}
        cold = anneal(broken, flat, flat, 1.0,
                      clamps=[Clamp("en1", "T", KERNEL), Clamp("en2", "F", KERNEL)])
        loop = LoopSpec("l", "restatement", ("en1", "ln1", "en2"))
        with self.assertRaises(OpenWalkError):
            holonomy(loop, cold.p, edge_weight_map(broken.edges))


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

    def test_no_gaps_remain_open(self):
        """Both gaps this audit opened were ruled implementation defects and repaired.

        Emptiness is a claim about the build, not a default, and it has to be re-earned
        every time. Tree-null was repaired first; the fixture change that required exposed
        extraction determinism, which was repaired in turn. Every remaining deviation is
        deliberate and cites the ruling that permits it.
        """
        from engine.faithfulness import by_design, check_faithfulness, gaps_before_p3

        self.assertEqual([g.object for g in gaps_before_p3()], [])
        self.assertTrue(all(r.deviation.ruling.strip() for r in by_design()),
                        "every by-design deviation must cite its ruling")
        self.assertTrue(check_faithfulness().ok)

    def test_a_classified_gap_would_still_be_reported_rather_than_suppressed(self):
        """The mechanism, exercised now that no real gap remains to exercise it."""
        from engine.faithfulness import GAP, Deviation, Row, check_faithfulness, gaps_before_p3
        import engine.faithfulness as mod

        original = mod.FAITHFULNESS_ROWS
        mod.FAITHFULNESS_ROWS = original + (
            Row(object="phantom", family="theory", site="engine/energy.py:FreeEnergy",
                role="-", control=original[0].control, control_claim="x",
                deviation=Deviation(kind=GAP, note="the build does not do this")),
        )
        try:
            self.assertIn("phantom", [g.object for g in gaps_before_p3()])
            self.assertTrue(check_faithfulness().ok,
                            "a classified gap is a finding, not a build failure — a finding "
                            "behind a red build is a finding nobody reads")
        finally:
            mod.FAITHFULNESS_ROWS = original


if __name__ == "__main__":
    unittest.main()


class GenerativeKeysAreContentAndSeedOnly(unittest.TestCase):
    """GATES.md sentence 7. Identity may label evidence; it may never generate it."""

    def test_a_relabelled_copy_extracts_bit_identically(self):
        """The repair's control. Was: one extra evidential identity the original never had."""
        from engine.energy import evidential_identity
        from engine.nulls import _genuine_paraphrases
        from engine.pipeline import ingest

        docs = _genuine_paraphrases("c")
        dup = [Document(f"dup::{d.doc_id}", d.chart, d.text, f"{d.source}::duplicate")
               for d in docs]
        exts = build_k_extractors(decisions(), offline=True)

        self.assertEqual(
            sorted(evidential_identity(d) for d in ingest(docs, exts)),
            sorted(evidential_identity(d) for d in ingest(dup, exts)),
            "identical text under a new doc_id and a new source label must extract "
            "bit-identically",
        )

    def test_cell_v_is_green_on_the_standard_fixture(self):
        from engine.constants import BETA_ARMS
        from engine.nulls import _genuine_paraphrases, cell_v_duplicate_source
        from engine.types import NullStatus

        cell = cell_v_duplicate_source(
            "gate7", _genuine_paraphrases("c"),
            build_k_extractors(decisions(), offline=True), BETA_ARMS[0],
        )
        self.assertIs(cell.status, NullStatus.PASS, cell.detail)
        self.assertEqual(cell.stats["residue"], 0.0, "determinism means exactly zero")

    def test_extraction_is_seeded_on_content_not_identity(self):
        import inspect

        from engine.extract import DeterministicExtractor

        source = inspect.getsource(DeterministicExtractor._spans)
        self.assertIn("doc.content_hash", source)
        self.assertNotIn("DRNG(\"extract\", self.extractor_id, self.prompt_id, doc.doc_id)",
                         source)

    def test_the_live_prompt_carries_no_document_identity(self):
        import inspect

        from engine.extract import AnthropicExtractor

        source = inspect.getsource(AnthropicExtractor._spans)
        prompt = source.split('"content": (')[1].split(")")[0]
        self.assertNotIn("doc.doc_id", prompt,
                         "a doc_id in the prompt lets the model read the label")
        self.assertIn("content_hash", prompt)

    def test_every_generative_key_is_classified_and_none_is_identity_keyed(self):
        from engine.static_checks import GENERATIVE_KEY_SITES, check_generative_keys

        result = check_generative_keys()
        self.assertTrue(result.ok, [str(v) for v in result.violations])
        self.assertGreaterEqual(result.checked_functions, 8)
        self.assertEqual([s["site"] for s in GENERATIVE_KEY_SITES
                          if s["keying"] == "identity"], [])
        for site in GENERATIVE_KEY_SITES:
            if site["keying"] == "design":
                self.assertTrue(str(site.get("ruling", "")).strip(),
                                f"{site['site']}: design keying must cite its ruling")

    def test_an_unclassified_random_stream_is_caught(self):
        """The sweep's own positive control."""
        import tempfile
        from pathlib import Path

        from engine.static_checks import check_generative_keys

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            (root / "engine" / "sneaky.py").write_text(
                "from .hashing import DRNG\n"
                "def new_stream(doc):\n"
                "    return DRNG('x', doc.doc_id)\n",
                encoding="utf-8",
            )
            result = check_generative_keys(root)
            self.assertFalse(result.ok)
            self.assertTrue(any("sneaky" in str(v) for v in result.violations))
