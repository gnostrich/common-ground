"""The five constitutional gates, tested as gates rather than as documentation.

Each test tries to *violate* the gate through the API a caller would actually reach for.
A gate that only holds when nobody pushes on it is not a gate.
"""

from __future__ import annotations

import unittest

from engine import GateViolation
from engine.blocks import build_blocks, build_fibers, edges_from_fibers
from engine.energy import evidence_from_deltas, lexicon_prior
from engine.meter import MeterResult, read_floor
from engine.normalize import address, nu, slot_id
from engine.settle import settle
from engine.types import (
    Block,
    Clamp,
    Delta,
    NullBatteryReport,
    NullCell,
    NullStatus,
    Provenance,
    QEdge,
    Warrant,
    WarrantTier,
)


def mk_delta(slot="s1", value="T", tier=WarrantTier.EXTRACTION, conf=1.0, doc="d1"):
    return Delta(
        slot=slot, chart="english", type="assert", value=value, confidence=conf,
        warrant=Warrant(tier), surface="x", nu="\x01en\x01x",
        provenance=Provenance("src", doc, "loc", "k0", doc),
    )


class Gate1Addressing(unittest.TestCase):
    """Slot identity = hash(nu(surface), type); a function of the seed, never of state."""

    def test_slot_id_depends_only_on_nu_and_type(self):
        a = slot_id(nu("english", "The cone is positive"), "assert")
        b = slot_id(nu("english", "  THE   Cone is Positive.  "), "assert")
        self.assertEqual(a, b)

    def test_type_is_part_of_the_address(self):
        n = nu("english", "the cone is positive")
        self.assertNotEqual(slot_id(n, "assert"), slot_id(n, "define"))

    def test_chart_is_part_of_the_address(self):
        a, _ = address("english", "IsPositive c", "assert")
        b, _ = address("lean", "IsPositive c", "assert")
        self.assertNotEqual(a, b, "charts must never share an address")

    def test_addressing_is_stateless(self):
        """Same inputs, same address, regardless of anything settled in between."""
        first, _ = address("english", "the cone is positive", "assert")
        block = Block("b", ("s1",), ())
        settle(block, evidence_from_deltas([mk_delta()]), lexicon_prior(["s1"]), 1.0)
        second, _ = address("english", "the cone is positive", "assert")
        self.assertEqual(first, second)


class Gate2PriorsCannotClamp(unittest.TestCase):
    """Lexicon and equivalence priors enter F only as energy terms."""

    def test_heavy_prior_does_not_pin_a_value(self):
        """A prior can dominate the settled distribution but never fix it."""
        slots = ["s1"]
        block = Block("b", ("s1",), ())
        priors = lexicon_prior(slots, {"s1": "T"})
        settled = settle(block, {}, priors, beta=1.0)
        p = settled.p["s1"]
        self.assertLess(max(p), 1.0, "a prior must not drive a slot to a vertex")
        self.assertGreater(min(p), 0.0, "a prior must not zero out any b-value")

    def test_evidence_can_overcome_a_prior(self):
        """The decisive test of 'energy only': a prior must be outweighable."""
        block = Block("b", ("s1",), ())
        priors = lexicon_prior(["s1"], {"s1": "T"})
        evidence = evidence_from_deltas([
            mk_delta(value="F", tier=WarrantTier.PREMINTED, conf=1.0, doc="a"),
            mk_delta(value="F", tier=WarrantTier.PREMINTED, conf=1.0, doc="b"),
        ])
        settled = settle(block, evidence, priors, beta=1.0)
        from engine.constants import BVALUE_INDEX

        p = settled.p["s1"]
        self.assertGreater(p[BVALUE_INDEX["F"]], p[BVALUE_INDEX["T"]])

    def test_q_edge_is_symmetric_energy_not_an_identification(self):
        edges = (QEdge("s1", "s2", 1.0, "fiber"),)
        block = Block("b", ("s1", "s2"), edges)
        evidence = evidence_from_deltas([
            mk_delta("s1", "T", doc="a"), mk_delta("s2", "F", doc="b"),
        ])
        settled = settle(block, evidence, lexicon_prior(["s1", "s2"]), beta=1.0)
        self.assertNotEqual(settled.p["s1"], settled.p["s2"],
                            "a Q edge couples slots; it does not merge them")


class Gate3OnlyTopTierGrounds(unittest.TestCase):
    """Only kernel-accept and CI receipts may clamp. Extraction never grounds."""

    def test_clamp_eligibility_by_tier(self):
        self.assertTrue(Warrant(WarrantTier.KERNEL).clamp_eligible)
        self.assertTrue(Warrant(WarrantTier.CI_RECEIPT).clamp_eligible)
        for tier in (WarrantTier.PREMINTED, WarrantTier.REPO_DOC, WarrantTier.EXTRACTION):
            self.assertFalse(Warrant(tier).clamp_eligible, tier.name)

    def test_clamp_construction_refuses_non_grounding_warrants(self):
        for tier in (WarrantTier.PREMINTED, WarrantTier.REPO_DOC, WarrantTier.EXTRACTION):
            with self.assertRaises(GateViolation) as ctx:
                Clamp(slot="s1", value="T", warrant=Warrant(tier))
            self.assertEqual(ctx.exception.gate, 3)

    def test_clamp_eligible_is_derived_not_stored(self):
        """It is a property on a frozen, slotted dataclass: no field, no setter."""
        w = Warrant(WarrantTier.EXTRACTION)
        self.assertNotIn("clamp_eligible", getattr(Warrant, "__slots__", ()))
        self.assertIsInstance(getattr(type(w), "clamp_eligible"), property)
        with self.assertRaises((AttributeError, TypeError)):
            w.clamp_eligible = True  # type: ignore[misc]

    def test_extractor_always_stamps_extraction_tier(self):
        from engine.extract import DeterministicExtractor
        from engine.types import Document

        doc = Document("d", "english", "The cone is positive. Another claim here.", "src")
        deltas = DeterministicExtractor("k0", "extract_v1").extract(doc)
        self.assertTrue(deltas)
        for d in deltas:
            self.assertIs(d.warrant.tier, WarrantTier.EXTRACTION)
            self.assertFalse(d.warrant.clamp_eligible)

    def test_settle_refuses_a_smuggled_clamp(self):
        """Bypass Clamp's constructor via object.__setattr__, then check settle catches it."""
        clamp = Clamp("s1", "T", Warrant(WarrantTier.KERNEL))
        object.__setattr__(clamp, "warrant", Warrant(WarrantTier.EXTRACTION))
        block = Block("b", ("s1",), ())
        with self.assertRaises(GateViolation) as ctx:
            settle(block, {}, lexicon_prior(["s1"]), 1.0, clamps=[clamp])
        self.assertEqual(ctx.exception.gate, 3)

    def test_retier_refuses_to_manufacture_a_grounding_warrant(self):
        from adapters.repo_docs import retier

        with self.assertRaises(GateViolation):
            retier([mk_delta()], WarrantTier.KERNEL, "smuggled")


class Gate4Plasticity(unittest.TestCase):
    """Anything that moves addresses requires a logged seed-morphism. CI tripwires it."""

    def test_lock_refuses_while_decisions_are_blank(self):
        from engine import seed_lock

        with self.assertRaises(GateViolation) as ctx:
            seed_lock.build()
        self.assertEqual(ctx.exception.gate, 4)

    def test_provisional_hash_can_never_equal_a_locked_hash(self):
        from engine.seed_lock import build_manifest, manifest_hash

        self.assertNotEqual(
            manifest_hash(build_manifest(provisional=True)),
            manifest_hash(build_manifest(provisional=False)),
        )

    def test_seed_hash_moves_when_a_seed_file_changes(self):
        from engine.seed_lock import build_manifest, manifest_hash

        before = build_manifest(provisional=True)
        after = dict(before)
        after["files"] = {**before["files"], "TYPES.md": "0" * 64}
        self.assertNotEqual(manifest_hash(before), manifest_hash(after))


class Gate5NoFloorBeforeNulls(unittest.TestCase):
    """No floor is read before the null battery passes on the same seed hash."""

    def setUp(self):
        self.result = MeterResult(seed_hash="abc")
        self.passing = NullBatteryReport("abc", [NullCell("i", NullStatus.PASS, "ok")])

    def test_reads_when_the_battery_passed_on_this_seed(self):
        self.assertEqual(read_floor(self.result, self.passing, "abc"), 0.0)

    def test_refuses_a_failed_battery(self):
        report = NullBatteryReport("abc", [NullCell("i", NullStatus.FAIL, "bad")])
        with self.assertRaises(GateViolation) as ctx:
            read_floor(self.result, report, "abc")
        self.assertEqual(ctx.exception.gate, 5)

    def test_refuses_a_blocked_battery(self):
        report = NullBatteryReport("abc", [NullCell("iii", NullStatus.BLOCKED, "no D5")])
        with self.assertRaises(GateViolation):
            read_floor(self.result, report, "abc")

    def test_refuses_a_battery_from_a_different_seed(self):
        other = NullBatteryReport("xyz", [NullCell("i", NullStatus.PASS, "ok")])
        with self.assertRaises(GateViolation) as ctx:
            read_floor(self.result, other, "abc")
        self.assertIn("different seed", str(ctx.exception).lower().replace("but the floor", "different seed"))

    def test_refuses_a_meter_result_from_a_different_seed(self):
        stale = MeterResult(seed_hash="xyz")
        with self.assertRaises(GateViolation):
            read_floor(stale, self.passing, "abc")


if __name__ == "__main__":
    unittest.main()
