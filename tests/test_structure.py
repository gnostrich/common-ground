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


class EveryDeclaredGapIsFenced(unittest.TestCase):
    def test_no_undeclared_deviation(self):
        # A declared gap without a citation+prohibition would be a silent re-encoding.
        for c in STRUCTURE_CLAIMS:
            if c.status == "declared-gap":
                self.assertTrue(c.fence, f"{c.id} is a gap but is not fenced")


if __name__ == "__main__":
    unittest.main()
