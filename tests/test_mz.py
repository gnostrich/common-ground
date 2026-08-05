"""One hypergraph, two measures, K on the boundary. The RED conditions are the point.

Three of these controls exist because the spec named a specific failure as RED: a second
store holding the same claim, an admission that cannot say what it was computed from, and a
second dormancy mechanism standing beside quarantine. Each is a shape that would pass an
ordinary test suite while being wrong, so each gets a control that fails on the SHAPE rather
than on a value.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from engine import aging, mz
from engine.aging import Aging, CONTRADICTED, SUPERSEDED, VISITED_UNCONFIRMED
from engine.journal import Journal
from engine.mz import Admission, BoundarySite, Measure, boundary_sites, consider_site


class _Region:
    def __init__(self, rid, declared):
        self.region_id = rid
        self.declared = declared


class TwoMeasuresOverOneStructure(unittest.TestCase):
    """A claim never moves. Its weight under the slow measure changes."""

    def test_promotion_is_reweighting_not_transport(self):
        fast, slow = Measure("fast"), Measure("slow")
        addr = "a" * 64
        fast.reweight(addr, 1.0)
        adm = Admission(site=addr, residuals=("r1",), hankel_top=9.0, second_fdt_floor=1.0,
                        threshold=2.0, gate_pass=True, conservative=True, promoted=True,
                        reason="promoted through the gate", value="T")
        mz.promote(adm, fast, slow)
        self.assertEqual(slow.of(addr), 1.0)
        self.assertEqual(fast.of(addr), 0.0)
        self.assertEqual(set(fast.weight), set(slow.weight),
                         "both measures range over the SAME address; a promotion that "
                         "introduced a new key would be transport, not re-weighting")

    def test_planted_a_measure_carrying_claim_content_is_a_second_store(self):
        """RED. Two stores of one claim is wrong regardless of how green the tests are."""
        from engine import EngineError

        m = Measure("fast")
        m.weight["a" * 64] = {"nu": "the cone is positive", "chart": "english"}  # type: ignore
        with self.assertRaises(EngineError) as ctx:
            m.validate()
        self.assertIn("second store", str(ctx.exception))

    def test_a_plain_weight_table_validates(self):
        m = Measure("slow")
        m.reweight("a" * 64, 0.5)
        m.validate()

    def test_planted_a_bool_is_not_a_weight(self):
        from engine import EngineError

        m = Measure("fast")
        m.weight["a" * 64] = True          # type: ignore
        with self.assertRaises(EngineError):
            m.validate()


class KsSupportIsTheBoundary(unittest.TestCase):
    def test_a_site_needs_both_halves(self):
        hot_only = BoundarySite(site="a" * 64, degree=0, clamped=False, hot=3)
        slow_only = BoundarySite(site="b" * 64, degree=5, clamped=False, hot=0)
        both = BoundarySite(site="c" * 64, degree=2, clamped=False, hot=1)
        self.assertFalse(hot_only.is_boundary)
        self.assertFalse(slow_only.is_boundary)
        self.assertTrue(both.is_boundary)

    def test_planted_clamped_is_passed_in_not_read_from_the_slot(self):
        """The measurement that would have made the whole layer a silent no-op: `tier >
        EXTRACTION` is ZERO across all 69,446 slot records, because receipts are applied at
        settlement and never written back. A degree-0 slot is only slow-settled if something
        tells this function it was clamped."""
        sites = boundary_sites(degree={}, hot={"a" * 64: 2}, clamped=frozenset())
        self.assertEqual(sites, [], "with no clamp source, a degree-0 slot is not settled")
        sites = boundary_sites(degree={}, hot={"a" * 64: 2}, clamped=frozenset({"a" * 64}))
        self.assertEqual(len(sites), 1, "the clamp must come from the settled view")

    def test_settled_degree_is_the_composition_minimum(self):
        """Two is the smallest degree at which a slot can be the middle of a length-2 path —
        a property of the graph, not a tuned threshold."""
        self.assertEqual(mz.SETTLED_DEGREE, 2)

    def test_the_support_is_smaller_than_the_corpus(self):
        degree = {f"{i:064d}": (2 if i < 50 else 0) for i in range(1000)}
        hot = {f"{i:064d}": 1 for i in range(0, 1000, 100)}
        sites = boundary_sites(degree=degree, hot=hot)
        self.assertLess(len(sites), len(degree) // 10)


class TheHyperedgeCarriesAHistory(unittest.TestCase):
    """A pairwise edge cannot: the MZ kernel is non-local in time."""

    def test_a_site_gathers_its_recent_fast_history(self):
        s = BoundarySite(site="a" * 64, degree=3, clamped=False, hot=4,
                         history=(0.9, 0.5, 0.2, 0.05), members=("e1", "e2", "e3", "e4"))
        self.assertEqual(len(s.history), 4)
        self.assertEqual(len(s.members), 4)

    def test_the_hankel_test_runs_on_that_history(self):
        s = BoundarySite(site="a" * 64, degree=3, clamped=False, hot=6,
                         history=tuple(1.0 / (i + 1) for i in range(12)),
                         members=tuple(f"e{i}" for i in range(12)))
        adm = consider_site(s, "T", second_fdt_floor=0.01, corpus={}, enabled=True)
        self.assertEqual(adm.stream_length, 12,
                         "K must read the SITE's history, not a globally chosen block")
        self.assertEqual(adm.residuals, s.members)

    def test_mint_off_is_a_refusal_not_a_failed_gate(self):
        s = BoundarySite(site="a" * 64, degree=3, clamped=False, hot=2,
                         history=(1.0, 0.5), members=("e1", "e2"))
        adm = consider_site(s, "T", second_fdt_floor=0.01, corpus={}, enabled=False)
        self.assertFalse(adm.promoted)
        self.assertIn("mint is OFF", adm.reason)

    def test_planted_a_zero_or_absent_floor_must_refuse_not_pass(self):
        """Found by producing the first real admission record. The second-FDT floor comes back
        0.0 on an empty ledger, and a probe that substituted a small epsilon for it turned the
        threshold into 3e-06 — which every residual clears. That is not a gate, it is a rubber
        stamp, and it would have read as K working.

        `read_tape` requires `threshold > 0.0`, so the engine already refuses. This pins it,
        because the tempting fix is a default floor and a default floor is exactly the defect.
        """
        # Longer than the Hankel window (64) — a shorter stream yields an empty matrix and
        # no singular values at all, which would make this pass for the wrong reason.
        n = 140
        s = BoundarySite(site="a" * 64, degree=3, clamped=False, hot=6,
                         history=tuple(50.0 / (i + 1) for i in range(n)),
                         members=tuple(f"e{i}" for i in range(n)))
        adm = consider_site(s, "T", second_fdt_floor=0.0, corpus={}, enabled=True)
        self.assertFalse(adm.gate_pass, "no floor means no gate, so nothing may pass")
        self.assertFalse(adm.promoted)
        self.assertGreater(adm.hankel_top, 0.0, "the residual was real; the floor was not")

    def test_conservative_extension_still_blocks(self):
        s = BoundarySite(site="a" * 64, degree=3, clamped=False, hot=6,
                         history=tuple(1.0 / (i + 1) for i in range(12)),
                         members=tuple(f"e{i}" for i in range(12)))
        adm = consider_site(s, "T", 0.01, corpus={"a" * 64: "F"}, enabled=True)
        self.assertFalse(adm.conservative)
        self.assertFalse(adm.promoted)


class AdmissionCarriesItsEvidence(unittest.TestCase):
    """Decision B. Without the residual set it silently degrades to decision A."""

    def test_planted_an_admission_with_no_residuals_is_refused_by_the_journal(self):
        from engine import EngineError

        adm = Admission(site="a" * 64, residuals=(), hankel_top=9.0, second_fdt_floor=1.0,
                        threshold=2.0, gate_pass=True, conservative=True, promoted=True,
                        reason="promoted", value="T")
        with tempfile.TemporaryDirectory() as tmp:
            j = Journal(Path(tmp) / "j.jsonl")
            try:
                with self.assertRaises(EngineError) as ctx:
                    j.record_admission(adm)
                self.assertIn("residual set", str(ctx.exception))
            finally:
                j.close()

    def test_the_record_carries_the_full_decision_from_the_first_promotion(self):
        adm = Admission(site="a" * 64, residuals=("e1", "e2"), hankel_top=9.0,
                        second_fdt_floor=1.5, threshold=3.0, gate_pass=True,
                        conservative=True, promoted=True, reason="promoted through the gate",
                        value="T", effective_rank=2, stream_length=12)
        rec = adm.as_record()
        self.assertEqual(rec["kind"], "admission")
        self.assertEqual(rec["residuals"], ["e1", "e2"])
        for k in ("hankel_top", "second_fdt_floor", "threshold", "gate_pass", "conservative"):
            self.assertIn(k, rec["decision"])
        self.assertEqual(rec["promoted"], {"slot": "a" * 64, "value": "T"})

    def test_it_round_trips_through_the_journal(self):
        import json as _json

        adm = Admission(site="a" * 64, residuals=("e1",), hankel_top=9.0,
                        second_fdt_floor=1.5, threshold=3.0, gate_pass=True,
                        conservative=True, promoted=True, reason="promoted", value="T")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "j.jsonl"
            j = Journal(path)
            try:
                j.record_admission(adm)
            finally:
                j.close()
            rows = [_json.loads(l) for l in path.read_text().splitlines() if l.strip()]
            row = next(r for r in rows if r.get("kind") == "admission")
            self.assertEqual(row["residuals"], ["e1"])
            self.assertEqual(row["decision"]["second_fdt_floor"], 1.5)

    def test_it_is_built_from_the_existing_promotion_not_a_reimplementation(self):
        from engine.mint_tape import Promotion, read_tape

        reading = read_tape([1.0, 0.5, 0.25, 0.1], 0.01)
        p = Promotion("a" * 64, "T", "site", 9.0, 3.0, True, True, True, "promoted")
        adm = Admission.from_promotion(p, reading, ("e1", "e2"), 1.5)
        self.assertEqual(adm.hankel_top, 9.0)
        self.assertEqual(adm.residuals, ("e1", "e2"))
        self.assertEqual(adm.stream_length, reading.stream_length)


class AgingHasNoFreeConstants(unittest.TestCase):
    def test_planted_there_is_no_n_and_no_decay_rate(self):
        """RED if either comes back. A threshold on a count is a number somebody chose."""
        for name in ("DORMANT_AFTER", "CANDIDATES", "DECAY", "HALF_LIFE", "N"):
            self.assertFalse(hasattr(aging, name), f"{name} is a free constant")
        self.assertEqual(set(aging.EVENTS),
                         {VISITED_UNCONFIRMED, SUPERSEDED, CONTRADICTED})

    def test_weight_drops_only_at_a_measured_event(self):
        led = Aging()
        a, b = "x" * 64, "y" * 64
        led.born(a, b)
        self.assertEqual(led.of(a, b), 1.0)
        led.observe_region(_Region("r0", {(a, b): "same_claim"}), named=set())
        self.assertEqual(led.of(a, b), 0.5)
        self.assertEqual(led.events[-1]["event"], VISITED_UNCONFIRMED)

    def test_planted_visiting_alone_never_reaches_dormant_by_arithmetic(self):
        """Halving is scale-free and never hits zero. An arrow can only go dormant because an
        event SAID so — otherwise unmentioned would become a denial by division."""
        led = Aging()
        a, b = "x" * 64, "y" * 64
        led.born(a, b)
        for i in range(40):
            led.observe_region(_Region(f"r{i}", {(a, b): "same_claim"}), named=set())
        self.assertGreater(led.of(a, b), 0.0)
        self.assertFalse(led.dormant(a, b))

    def test_superseded_and_contradicted_strike_it_outright(self):
        led = Aging()
        a, b, c, d = "x" * 64, "y" * 64, "p" * 64, "q" * 64
        led.born(a, b); led.born(c, d)
        led.supersede(a, b, by="promotion1")
        led.contradict(c, d, by="clamp1")
        self.assertTrue(led.dormant(a, b))
        self.assertTrue(led.dormant(c, d))
        self.assertTrue(led.events[-1]["flagged"], "a contradiction is a finding, not a decay")

    def test_planted_a_region_is_counted_once(self):
        led = Aging()
        a, b = "x" * 64, "y" * 64
        led.born(a, b)
        for _ in range(4):
            led.observe_region(_Region("same", {(a, b): "same_claim"}), named=set())
        self.assertEqual(led.of(a, b), 0.5)

    def test_re_entry_needs_a_genuinely_distinct_region(self):
        led = Aging()
        a, b = "x" * 64, "y" * 64
        led.born(a, b)
        led.observe_region(_Region("r0", {(a, b): "same_claim"}), named={(a, b)})
        led.supersede(a, b, by="p1")
        self.assertTrue(led.dormant(a, b))
        # same region that already confirmed it -> not independent, stays dormant
        led.regions_seen.discard("r0")
        led.observe_region(_Region("r0", {(a, b): "same_claim"}), named={(a, b)})
        self.assertTrue(led.dormant(a, b), "re-naming inside one co-present set is one "
                                           "measurement counted twice")
        led.observe_region(_Region("r-other", {(a, b): "same_claim"}), named={(a, b)})
        self.assertFalse(led.dormant(a, b))
        self.assertEqual(led.events[-1]["event"], "revived")

    def test_anything_retained_is_born_subject_to_the_events(self):
        led = Aging()
        a, b = "x" * 64, "y" * 64
        led.born(a, b)
        self.assertIn(led.key(a, b), led.weight,
                      "retention outside the decay is what makes the tape a second corpus")


class QuarantineAndDormantAreOneMechanism(unittest.TestCase):
    """RED if a second dormancy set appears beside quarantine."""

    def test_dormant_pairs_enter_the_same_non_acting_set(self):
        from engine.quarantine import non_acting

        led = Aging()
        a, b = "x" * 64, "y" * 64
        led.born(a, b)
        led.contradict(a, b, by="clamp1")
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "j.jsonl"
            journal.write_text("", encoding="utf-8")
            out = non_acting(journal, aging=led, path=Path(tmp) / "q.json")
        self.assertIn((a, b), out)
        self.assertIn((b, a), out, "the non-acting set is directional; staleness is not")

    def test_planted_aging_defines_no_exclusions_of_its_own(self):
        """It produces pairs. The three exclusions belong to quarantine and stay there."""
        body = Path(aging.__file__).read_text(encoding="utf-8")
        for owned in ("composition closure", "region assembly", "conditioning path"):
            self.assertNotIn(f"def {owned}", body)
        self.assertTrue(hasattr(led_module := aging, "Aging"))
        self.assertTrue(hasattr(led_module.Aging, "dormant_pairs"))

    def test_without_an_aging_ledger_the_set_is_just_quarantine(self):
        from engine.quarantine import non_acting

        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "j.jsonl"
            journal.write_text("", encoding="utf-8")
            self.assertEqual(non_acting(journal, path=Path(tmp) / "q.json"), set())


if __name__ == "__main__":
    unittest.main()
