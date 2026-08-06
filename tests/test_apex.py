"""APEX-STAR: the coequalizer the category already implied, made energy-bearing.

A fiber is a QUOTIENT. `edges_from_fibers` used to emit one edge per within-fiber PAIR, so an
n-member fiber contributed n(n-1)/2 couplings at full declared weight from what the
declarations record as a chain. Measured on the live corpus: one 120-member fiber carried 73%
of the entire corpus's fiber-coupling energy; the corpus-wide over-coupling factor was 5.6x.

The controls below are the ones ruled: ground-state agreement on hard equivalences, deviation
cost independent of k, contest collapse attributed to the pairs it replaces, and apexes that
are energy objects only — not slots, not addressable, not citable, not proposable.
"""

import unittest

from engine.blocks import (APEX_PREFIX, DECLARED_WEIGHT, apex_id, build_blocks,
                           edges_from_fibers, is_apex)


class _F:
    def __init__(self, members):
        self.slots = tuple(members)
        self.id = "f" + str(len(members))


class _S:
    def __init__(self, sid, chart="english"):
        self.id, self.chart = sid, chart
        self.type, self.nu = "assert", sid


class _D:
    def __init__(self, slot):
        self.slot = slot


class TheFactorizationIsAStar(unittest.TestCase):

    def test_k_members_give_k_edges_not_k_squared(self):
        for k in (2, 5, 40, 120):
            self.assertEqual(k, len(edges_from_fibers([_F([f"s{i}" for i in range(k)])])),
                             f"a {k}-member fiber must contribute {k} edges")

    def test_every_edge_touches_the_apex_and_no_two_faces_touch_directly(self):
        edges = edges_from_fibers([_F([f"s{i}" for i in range(9)])])
        for e in edges:
            self.assertTrue(is_apex(e.u) or is_apex(e.v))
            self.assertFalse(is_apex(e.u) and is_apex(e.v))

    def test_the_declared_weight_is_unchanged(self):
        # The weight was justified — a declared correspondence is asserted, not scored, and
        # there is no similarity to weight it by. Only the COUNT was ever unjustified.
        for e in edges_from_fibers([_F(["a", "b", "c"])]):
            self.assertEqual(DECLARED_WEIGHT, e.weight)

    def test_a_singleton_fiber_contributes_nothing(self):
        self.assertEqual([], edges_from_fibers([_F(["only"])]))

    def test_the_apex_id_is_derived_from_the_members_and_is_stable(self):
        a = _F(["b", "a", "c"])
        self.assertEqual(apex_id(a), apex_id(_F(["c", "b", "a"])))
        self.assertNotEqual(apex_id(a), apex_id(_F(["a", "b", "d"])))


class DeviationCostIsIndependentOfK(unittest.TestCase):
    """THE RULED CONTROL: a planted 120-member fiber must not dominate its block."""

    def test_a_members_coupling_does_not_grow_with_its_sibling_count(self):
        # One edge per member, whatever k is. Under all-pairs a member of a 120-fiber carried
        # 119 couplings and a member of a 3-fiber carried 2.
        for k in (3, 120):
            edges = edges_from_fibers([_F([f"s{i}" for i in range(k)])])
            degree = sum(1 for e in edges if "s0" in (e.u, e.v))
            self.assertEqual(1, degree, f"k={k} gave a face degree of {degree}")

    def test_a_giant_fiber_does_not_out_weigh_many_small_ones(self):
        giant = edges_from_fibers([_F([f"g{i}" for i in range(120)])])
        smalls = edges_from_fibers([_F([f"s{j}_{i}" for i in range(3)]) for j in range(40)])
        # 120 members vs 120 members. Under all-pairs: 7,140 against 120, a 59x dominance.
        self.assertEqual(len(giant), len(smalls))

    def test_the_energy_share_of_the_largest_fiber_is_its_member_share(self):
        fibers = [_F([f"g{i}" for i in range(120)])] + [
            _F([f"s{j}_{i}" for i in range(3)]) for j in range(40)]
        edges = edges_from_fibers(fibers)
        giant = sum(1 for e in edges if any(str(n).startswith("g") for n in (e.u, e.v)))
        self.assertAlmostEqual(0.5, giant / len(edges), places=2)


class AnApexIsAnEnergyObjectOnly(unittest.TestCase):
    """Not a slot, not addressable, not citable, not proposable. Planted in each position."""

    def test_an_apex_is_not_shaped_like_a_slot_address(self):
        a = apex_id(_F(["a", "b"]))
        self.assertTrue(a.startswith(APEX_PREFIX))
        self.assertTrue(is_apex(a))
        self.assertFalse(is_apex("a" * 64), "a slot address must not read as an apex")

    def test_an_apex_never_appears_in_a_BLOCKS_membership(self):
        slots = [_S("a"), _S("b"), _S("c")]
        edges = edges_from_fibers([_F(["a", "b", "c"])])
        blocks = build_blocks(slots, edges, [_D("a"), _D("b"), _D("c")])
        self.assertTrue(blocks)
        for b in blocks:
            for sid in b.slots:
                self.assertFalse(is_apex(sid), f"an apex reached block membership: {sid}")

    def test_the_faces_still_land_in_ONE_block_through_the_apex(self):
        # The star must still connect: if the apex were filtered out the quotient would stop
        # coupling and three declared-equivalent claims would settle independently.
        slots = [_S("a"), _S("b"), _S("c")]
        edges = edges_from_fibers([_F(["a", "b", "c"])])
        blocks = build_blocks(slots, edges, [_D("a"), _D("b"), _D("c")])
        self.assertEqual(1, len(blocks))
        self.assertEqual(("a", "b", "c"), blocks[0].slots)

    def test_an_apex_whose_faces_are_all_inactive_contributes_nothing(self):
        slots = [_S("a"), _S("b"), _S("z")]
        edges = edges_from_fibers([_F(["a", "b"])])
        blocks = build_blocks(slots, edges, [_D("z")])
        self.assertEqual([("z",)], [b.slots for b in blocks])

    def test_a_block_that_would_be_apex_only_is_dropped_not_emitted_empty(self):
        # An apex with no surviving face is not a block of zero claims; it is not a block.
        slots = [_S("a")]
        edges = edges_from_fibers([_F(["a", "b"])])
        blocks = build_blocks(slots, edges, [_D("a")])
        self.assertTrue(all(b.slots for b in blocks))


class GroundStateAgreementOnHardEquivalences(unittest.TestCase):
    """THE CORRECTNESS ANCHOR. The factorization changes the cost surface, not the answer.

    On a fiber whose members are declared equivalent and agree, both factorizations must put
    them in one block with the same membership: what apex-star removes is the SURPLUS coupling
    that made a large fiber rigid, never the coupling that makes a quotient a quotient.
    """

    def _all_pairs(self, fibers):
        from engine.blocks import QEdge
        out = []
        for f in fibers:
            m = sorted(f.slots)
            for i in range(len(m)):
                for j in range(i + 1, len(m)):
                    out.append(QEdge(u=m[i], v=m[j], weight=DECLARED_WEIGHT,
                                     origin="correspondence"))
        return out

    def test_block_membership_is_identical_under_both_factorizations(self):
        for k in (2, 3, 8, 40):
            fibers = [_F([f"s{i}" for i in range(k)])]
            slots = [_S(f"s{i}") for i in range(k)]
            deltas = [_D(f"s{i}") for i in range(k)]
            star = build_blocks(slots, edges_from_fibers(fibers), deltas)
            pairs = build_blocks(slots, self._all_pairs(fibers), deltas)
            self.assertEqual([b.slots for b in pairs], [b.slots for b in star],
                             f"the two factorizations disagree at k={k}")

    def test_separate_fibers_stay_separate_under_both(self):
        fibers = [_F(["a", "b"]), _F(["c", "d"])]
        slots = [_S(x) for x in ("a", "b", "c", "d")]
        deltas = [_D(x) for x in ("a", "b", "c", "d")]
        star = [b.slots for b in build_blocks(slots, edges_from_fibers(fibers), deltas)]
        pairs = [b.slots for b in build_blocks(slots, self._all_pairs(fibers), deltas)]
        self.assertEqual(pairs, star)
        self.assertEqual([("a", "b"), ("c", "d")], star)


class TheContestCollapseIsATTRIBUTED(unittest.TestCase):
    """Every pair-spray that goes away can name what it replaced."""

    def test_a_fiber_reports_the_pairs_its_star_replaces(self):
        k = 120
        f = _F([f"s{i}" for i in range(k)])
        star = len(edges_from_fibers([f]))
        allpairs = k * (k - 1) // 2
        self.assertEqual(k, star)
        self.assertEqual(7140, allpairs)
        self.assertEqual(7020, allpairs - star)

    def test_the_replacement_is_computable_from_the_fiber_alone(self):
        # Attribution must not need a stored before-image: the count of collapsed pairs is a
        # function of k, so any group can state what it replaced from its own membership.
        for k in (2, 9, 41, 120):
            f = _F([f"s{i}" for i in range(k)])
            self.assertEqual(k * (k - 1) // 2 - k,
                             k * (k - 1) // 2 - len(edges_from_fibers([f])))


if __name__ == "__main__":
    unittest.main()


class EveryConsumerReadsThroughTheONEExpansion(unittest.TestCase):
    """APEX-STAR CHANGES THE REPRESENTATION, NOT THE SEMANTICS.

    Every consumer of fiber structure must read through `expand_stars`, never re-derive
    adjacency privately. Six were found: the energy (by construction), the meter's weight map,
    the loop finder, the structure audit, the shadow calibration, and block adjacency. The
    first five were found by a downstream ZERO — a floor of exactly 0.0, an empty measurement
    list, a silent empty adjacency — and only the sixth was found by sweeping for the pattern.
    A zero is the worst possible detector: it reads as "nothing frustrates", which is a
    finding, not an error.
    """

    def _fn(self, module, name):
        import ast
        import inspect
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / module).read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.get_source_segment(src, node) or ""
        raise AssertionError(f"{module}:{name} not found")

    def test_the_known_consumers_all_route_through_it(self):
        for module, fn in (("meter.py", "edge_weight_map"),
                           ("structure_audit.py", "classify_factors"),
                           ("structure_audit.py", "spurious_edges"),
                           ("structure_audit.py", "membership_violations"),
                           ("types.py", "neighbours")):
            self.assertIn("expand_stars", self._fn(module, fn),
                          f"{module}:{fn} re-derives adjacency privately")

    def test_the_loop_finder_routes_through_it(self):
        self.assertIn("expand_stars", self._fn("blocks.py", "loops_from_fibers"))

    def test_the_expansion_is_exact_at_the_anchor(self):
        # k=2 is where freedom is zero: a two-member fiber IS one declared pair, so the
        # expansion must return exactly that pair at exactly the declared weight. Everything
        # else follows by algebra — this is the constant entering the system the only way a
        # constant may.
        from engine.blocks import expand_stars
        got = expand_stars(edges_from_fibers([_F(["a", "b"])]))
        self.assertEqual(1, len(got))
        self.assertEqual(DECLARED_WEIGHT, got[0].weight)

    def test_the_implied_weight_is_w_over_k_minus_one(self):
        from engine.blocks import expand_stars
        for k in (2, 3, 10, 120):
            got = expand_stars(edges_from_fibers([_F([f"s{i}" for i in range(k)])]))
            self.assertEqual(k * (k - 1) // 2, len(got))
            self.assertAlmostEqual(DECLARED_WEIGHT / (k - 1), got[0].weight)

    def test_a_star_and_a_declared_pair_are_indistinguishable_at_k_two(self):
        from engine.blocks import expand_stars
        from engine.types import QEdge
        star = expand_stars(edges_from_fibers([_F(["a", "b"])]))
        pair = [QEdge(u="a", v="b", weight=DECLARED_WEIGHT, origin="correspondence")]
        self.assertEqual([(e.u, e.v, e.weight, e.origin) for e in pair],
                         [(e.u, e.v, e.weight, e.origin) for e in star])


class TheApexHasNoDegreeOfFreedom(unittest.TestCase):
    """THE RULED CONTROL: p_apex is a deterministic function of its faces, nothing else.

    An apex with an initial state, a prior, an entropy term or an update rule of its own would
    be a tuned parameter in the energy core — the class this project deletes. The first
    implementation had three of those. The floor must come from face-to-face frustration
    MEDIATED through the apex, never from the apex's own settled state.
    """

    def test_no_apex_is_seeded_into_the_initial_state(self):
        from engine.blocks import build_blocks, is_apex
        from engine.settle import initial_state

        class S:
            def __init__(s, i):
                s.id, s.chart, s.type, s.nu = i, "english", "assert", i

        class D:
            def __init__(s, i):
                s.slot = i
        slots = [S("a"), S("b"), S("c")]
        blk = build_blocks(slots, edges_from_fibers([_F(["a", "b", "c"])]),
                           [D("a"), D("b"), D("c")])[0]
        state = initial_state(blk)
        self.assertEqual({"a", "b", "c"}, set(state))
        self.assertFalse(any(is_apex(k) for k in state), "an apex was given an initial state")

    def test_the_energy_has_no_latent_field(self):
        # A planted apex-with-an-independent-prior would need somewhere to live. There is
        # nowhere: FreeEnergy is over `slots`, and the consensus is recomputed per evaluation.
        import dataclasses

        from engine.energy import FreeEnergy
        names = {f.name for f in dataclasses.fields(FreeEnergy)}
        self.assertNotIn("latent", names)
        self.assertEqual({"slots", "evidence", "priors", "edges", "beta", "clamped"}, names)

    def test_the_gradient_has_no_apex_entry(self):
        from engine.energy import FreeEnergy
        from engine.blocks import is_apex
        f = FreeEnergy(slots=("a", "b", "c"), evidence={}, priors={},
                       edges=tuple(edges_from_fibers([_F(["a", "b", "c"])])), beta=1.0)
        p = {s: [0.25, 0.25, 0.25, 0.25] for s in ("a", "b", "c")}
        g = f.gradient(p)
        self.assertEqual({"a", "b", "c"}, set(g))
        self.assertFalse(any(is_apex(k) for k in g))

    def test_the_consensus_is_recomputed_from_the_faces_every_evaluation(self):
        # Move a face; the consensus must move with it. A stored apex would not.
        from engine.energy import FreeEnergy
        f = FreeEnergy(slots=("a", "b"), evidence={}, priors={},
                       edges=tuple(edges_from_fibers([_F(["a", "b"])])), beta=1.0)
        near = f.value({"a": [1.0, 0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0, 0.0]})
        far = f.value({"a": [1.0, 0.0, 0.0, 0.0], "b": [0.0, 1.0, 0.0, 0.0]})
        self.assertGreater(far, near, "the coupling did not respond to the faces moving")
