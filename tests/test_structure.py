"""Controls for the structure_audit: the graph IS the algebra, audited as structure.

The six structural claims, plus the mandated planted-defect control — a spurious hand-set
edge (not derivable from the fibers) must make the audit RED.
"""

from __future__ import annotations

import dataclasses
import unittest

from engine.structure_audit import (
    FAMILIES,
    STRUCTURE_CLAIMS,
    check_structure,
    classify_factors,
    fixture_ledger,
    spurious_edges,
    variable_nodes_are_fibered_only,
)
from engine.types import QEdge


class TheGraphIsTheAlgebra(unittest.TestCase):
    def setUp(self):
        self.ledger = fixture_ledger()

    def test_the_live_graph_passes(self):
        r = check_structure(self.ledger)
        self.assertTrue(r.ok, f"unclassified={r.unclassified} spurious={r.spurious}")

    def test_S1_nodes_are_fibered_not_per_slot(self):
        variables, frozen = variable_nodes_are_fibered_only(self.ledger)
        self.assertTrue(frozen, "some slots must be frozen — a node-per-slot graph fails")
        self.assertTrue(variables, "fibered slots are the variable nodes")
        # every variable is in a block that carries an edge
        edged = {s for b in self.ledger.blocks if b.edges for s in b.slots}
        self.assertEqual(variables, edged)

    def test_S2_every_factor_classifies_into_one_family(self):
        counts, unclassified = classify_factors(self.ledger)
        self.assertEqual(unclassified, [], "every factor must classify into exactly one family")
        self.assertEqual(set(counts), FAMILIES)
        self.assertGreater(sum(counts.values()), 0)

    def test_S3_correspondence_is_a_declared_fenced_gap(self):
        s3 = next(c for c in STRUCTURE_CLAIMS if c.id == "S3")
        self.assertEqual(s3.status, "declared-gap")
        self.assertIn("PAIRWISE-COLLAPSED", s3.fence)
        self.assertIn("no claim of ternary correspondence", s3.fence.lower())

    def test_S4_edge_weights_are_derived_not_free(self):
        # The live fiber edges are all reproducible from the fibers, so no free weights.
        self.assertEqual(spurious_edges(self.ledger), [])

    def test_S6_planted_spurious_edge_makes_it_red(self):
        # The mandated control: inject a hand-set edge with a weight not derivable from the
        # fibers. The audit MUST go red.
        planted = dataclasses.replace(self.ledger)
        planted.edges = list(self.ledger.edges) + [
            QEdge(u="spurious_a", v="spurious_b", weight=0.99, origin="hand-set")
        ]
        r = check_structure(planted)
        self.assertFalse(r.ok, "a spurious hand-set edge must make the audit RED")
        self.assertTrue(r.spurious)

    def test_S6_a_fiber_edge_with_a_tampered_weight_is_also_spurious(self):
        if not self.ledger.edges:
            self.skipTest("no fiber edges in the fixture")
        planted = dataclasses.replace(self.ledger)
        first = self.ledger.edges[0]
        tampered = dataclasses.replace(first, weight=first.weight + 0.5)  # hand-changed
        planted.edges = [tampered] + list(self.ledger.edges[1:])
        r = check_structure(planted)
        self.assertFalse(r.ok, "a tampered fiber-edge weight is not derivable => spurious")

    def test_S7_a_similarity_style_membership_makes_it_red(self):
        # The mandated audit-hole control: inject a fiber grouping two slots that have NO
        # declared correspondence between them — a string-overlap / similarity membership.
        # The relation does not reproduce it, so the audit MUST go RED.
        from engine.types import Fiber

        edged = {e.u for e in self.ledger.edges} | {e.v for e in self.ledger.edges}
        isolated = sorted(s.id for s in self.ledger.slots if s.id not in edged)[:2]
        self.assertEqual(len(isolated), 2, "need two isolated slots to plant a bogus fiber")
        planted = dataclasses.replace(self.ledger)
        planted.fibers = list(self.ledger.fibers) + [
            Fiber(id="planted_sim", slots=tuple(sorted(isolated)))
        ]
        r = check_structure(planted)
        self.assertFalse(r.ok, "a non-declared (similarity-style) fiber membership must be RED")
        self.assertTrue(r.membership, "the membership-is-exact check must fire")


class EveryDeclaredGapIsFenced(unittest.TestCase):
    def test_no_undeclared_deviation(self):
        # A declared gap without a citation+prohibition would be a silent re-encoding.
        for c in STRUCTURE_CLAIMS:
            if c.status == "declared-gap":
                self.assertTrue(c.fence, f"{c.id} is a gap but is not fenced")


if __name__ == "__main__":
    unittest.main()


class ACycleNeedNotSpanItsFiber(unittest.TestCase):
    """The over-strong accident, and the three cycles it hid.

    `order_cycle` demanded a Hamiltonian cycle — one through EVERY fiber member. Holonomy is
    measured around a cycle in the fundamental groupoid and nothing requires it to span its
    fiber, so the requirement was an accident rather than a definition. It cost everything:
    on the live field, eight same_claim components held a real closed english<->python cycle
    and the constructor reported zero, because each had a leaf hanging off it. Floor, K and
    every composition measurement were blocked behind a leaf.

    The three cycles below are taken verbatim from that field (runs/proposer.ledger.jsonl,
    reconstructed 2026-08-06). They are the regression: if any stops being found, the
    accident is back.
    """

    @staticmethod
    def _adj(edges):
        from engine.blocks import _adjacency

        return _adjacency(edges)

    def _graph(self, pairs, charts):
        from engine.types import QEdge

        edges = [QEdge(u=u, v=v, weight=1.0, origin="fiber") for u, v in pairs]
        return self._adj(edges), charts

    def test_a_four_cycle_with_a_leaf_hanging_off_it_is_still_found(self):
        """The exact shape of all eight: a closed 4-cycle plus one pendant vertex."""
        from engine.blocks import order_cycle

        e1, p1, e2, p2, leaf = "e1", "p1", "e2", "p2", "leaf"
        charts = {e1: "english", p1: "python", e2: "english", p2: "python",
                  leaf: "python"}
        adj, charts = self._graph(
            [(e1, p1), (p1, e2), (e2, p2), (p2, e1), (e1, leaf)], charts)
        got = order_cycle([e1, p1, e2, p2, leaf], charts, adj)
        self.assertIsNotNone(got, "a real cycle was hidden by one pendant vertex")
        self.assertEqual(len(got), 4, "the cycle is the 4-cycle, not the whole fiber")
        self.assertNotIn(leaf, got)

    def test_the_three_exhibited_field_cycles_are_found(self):
        """Verbatim from the live ledger. Each is a 4-cycle inside a 5- or 6-slot fiber."""
        from engine.blocks import order_cycle

        cases = [
            (("4f386cc9", "ebd19bf0", "14480763", "340b7d56"),
             ("python", "english", "python", "english"), ("x1",)),
            (("51e674e8", "c02e6161", "db189459", "93571a5b"),
             ("python", "english", "python", "english"), ("x1", "x2")),
            (("24cb0c8b", "24b0a96d", "abe4809f", "08344658"),
             ("english", "python", "english", "python"), ("x1", "x2")),
        ]
        for ring, kinds, leaves in cases:
            charts = dict(zip(ring, kinds))
            pairs = [(ring[i], ring[(i + 1) % 4]) for i in range(4)]
            for i, lf in enumerate(leaves):          # the pendants that hid it
                charts[lf] = "python" if kinds[0] == "english" else "english"
                pairs.append((ring[i], lf))
            adj, charts = self._graph(pairs, charts)
            got = order_cycle(list(ring) + list(leaves), charts, adj)
            self.assertIsNotNone(got, f"lost the field cycle {ring[0]}…")
            self.assertEqual(set(got), set(ring))

    def test_planted_a_tree_fiber_still_reports_no_loop(self):
        """The forest case must stay a non-answer. 359 of 367 field components are trees."""
        from engine.blocks import order_cycle

        charts = {"e": "english", "a": "python", "b": "python", "c": "go"}
        adj, charts = self._graph([("e", "a"), ("e", "b"), ("e", "c")], charts)
        self.assertIsNone(order_cycle(["e", "a", "b", "c"], charts, adj),
                          "a star has no cycle and must not produce a spec")

    def test_planted_a_figure_eight_yields_a_simple_cycle(self):
        """Two cycles meeting at a vertex is not one loop. Holonomy around a walk that
        repeats a slot is not holonomy around a loop, so `_close` refuses that shape and the
        search returns one of the two simple cycles instead."""
        from engine.blocks import order_cycle

        charts = {"a": "english", "b": "python", "c": "english",
                  "d": "python", "e": "english"}
        adj, charts = self._graph(
            [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d"), ("d", "e"), ("e", "c")],
            charts)
        got = order_cycle(["a", "b", "c", "d", "e"], charts, adj)
        self.assertIsNotNone(got)
        self.assertEqual(len(set(got)), len(got), "a slot must not repeat in a loop")
        self.assertEqual(len(got), 3, "the shortest simple cycle, not the figure-eight")

    def test_the_brute_force_cap_is_gone_not_raised(self):
        """Girth by BFS is polynomial, so no fiber is ever declined."""
        import engine.blocks as B

        self.assertFalse(hasattr(B, "CYCLE_BRUTE_MAX"))
        self.assertEqual(B.LOOPS_UNSEARCHED, 0)

    def test_a_large_fiber_no_longer_hangs(self):
        """The 43-member field fiber took an unbounded (n-1)! search before."""
        import time

        from engine.blocks import order_cycle

        n = 43
        charts = {f"s{i}": ("english" if i % 2 else "python") for i in range(n)}
        pairs = [(f"s{i}", f"s{i+1}") for i in range(n - 1)]      # a path: no cycle
        adj, charts = self._graph(pairs, charts)
        t = time.time()
        self.assertIsNone(order_cycle([f"s{i}" for i in range(n)], charts, adj))
        self.assertLess(time.time() - t, 5.0)
