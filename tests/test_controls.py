"""The positive-control rule: every null cell must demonstrate it can fail.

A cell that cannot detect its own failure mode is not evidence, whatever it reports about
the real input. These tests check that each control fires, and — separately — that the
battery treats a dead control as a failure rather than reading around it.

Two cells were vacuous before this rule was adopted, and both were caught here rather than
by any other test:

- **(iv)** compared the floor against a bootstrap of the observed floors, a band centred on
  the data. `floor <= q95` held at 0.4 as readily as at 0.0.
- **(v)** compared the duplicate-ingestion residue against the same kind of band, so a
  residue of 0.013 passed against a band of 0.25 — and the `dedupe=False` switch did not
  reach the accumulator, so the control could not disable what it was testing.
"""

from __future__ import annotations

import unittest

from adapters.lexicon_imports import import_all
from engine.constants import BETA_ARMS, decisions, shadow
from engine.energy import evidence_from_deltas
from engine.extract import build_k_extractors
from engine.nulls import (
    _BROKEN_SUITE,
    _broken_normalizer,
    _contradictory_docs,
    _control_i,
    _control_ii,
    _control_iii,
    _control_iv,
    _control_ix,
    _control_v,
    _control_vi,
    _control_vii,
    _control_viii,
    cell_ii_paraphrase,
    cell_iv_single_doc,
    cell_v_duplicate_source,
    run_battery,
)
from engine.pipeline import build_ledger, consensus_ledger, run_meter
from engine.types import ControlState, Document, NullBatteryReport, NullCell, NullStatus

SEED = "control-test-seed"


def _extractors():
    return build_k_extractors(decisions(), offline=True)


def _registry():
    registry, _ = import_all(decisions().get("D8", {}))
    return registry


class EveryControlFires(unittest.TestCase):
    """One test per cell. A dead control here means that cell is decorative."""

    def test_i(self):
        fired, detail = _control_i(SEED)
        self.assertTrue(fired, detail)

    def test_ii(self):
        fired, detail = _control_ii()
        self.assertTrue(fired, detail)

    def test_iii(self):
        fired, detail = _control_iii(SEED, _extractors(), BETA_ARMS[0])
        self.assertTrue(fired, detail)

    def test_iv(self):
        fired, detail = _control_iv(SEED, _extractors(), BETA_ARMS[0])
        self.assertTrue(fired, detail)

    def test_v(self):
        fired, detail = _control_v(SEED, _extractors(), BETA_ARMS[0])
        self.assertTrue(fired, detail)

    def test_vi(self):
        fired, detail = _control_vi(_registry())
        self.assertTrue(fired, detail)

    def test_vii(self):
        fired, detail = _control_vii(_registry())
        self.assertTrue(fired, detail)

    def test_viii(self):
        fired, detail = _control_viii()
        self.assertTrue(fired, detail)

    def test_ix_does_not_depend_on_D8(self):
        """It builds its own synthetic Mathlib senses.

        Borrowing the real registry made this control dead exactly when D8 was
        unresolved — which is when you most want to know the cell works.
        """
        fired, detail = _control_ix(None, SEED)
        self.assertTrue(fired, detail)


class BatteryHonoursControls(unittest.TestCase):
    def test_all_nine_controls_are_live(self):
        report = run_battery(SEED, _extractors(), BETA_ARMS[0], samples=16, registry=_registry())
        self.assertEqual(report.dead_controls, [])
        self.assertEqual(len(report.cells), 9)
        for cell in report.cells:
            self.assertIs(cell.control, ControlState.LIVE, f"{cell.cell}: {cell.control_detail}")

    def test_a_dead_control_fails_the_battery_even_when_every_cell_passed(self):
        report = NullBatteryReport(SEED, [
            NullCell("a", NullStatus.PASS, "", control=ControlState.LIVE),
            NullCell("b", NullStatus.PASS, "", control=ControlState.DEAD),
        ])
        self.assertIs(report.status, NullStatus.FAIL)
        self.assertEqual(report.dead_controls, ["b"])

    def test_controls_can_be_skipped_for_speed_but_then_nothing_is_live(self):
        report = run_battery(SEED, _extractors(), BETA_ARMS[0], samples=8,
                             registry=_registry(), controls=False)
        self.assertTrue(all(c.control is ControlState.NOT_RUN for c in report.cells))

    def test_record_carries_control_state(self):
        record = NullBatteryReport(SEED, [
            NullCell("a", NullStatus.PASS, "d", control=ControlState.LIVE, control_detail="x"),
        ]).as_record()
        self.assertEqual(record["cells"][0]["control"], "live")
        self.assertIn("dead_controls", record)


class CellIVIsNoLongerVacuous(unittest.TestCase):
    def test_bootstrap_band_would_have_passed_any_floor(self):
        """The defect, pinned so it cannot come back.

        The band is a resample of the observed floors, so it tracks whatever floor it is
        handed: at 0.0 and at 0.4 alike it lands on the floor itself, to float noise. A
        test of the form `floor <= q95(band)` therefore carries no information about the
        floor — it is a statement about the resampler.
        """
        from engine.hashing import quantile
        from engine.meter import LoopMeasurement, surrogate_floor_distribution

        for floor in (0.0, 0.4):
            rows = [LoopMeasurement(f"l{i}", "paraphrase", 1.0, floor, floor, 0.0, floor, 0.0, ("a", "b"))
                    for i in range(6)]
            band = quantile(surrogate_floor_distribution(rows, "s"), 0.95)
            self.assertAlmostEqual(band, floor, delta=1e-9,
                                   msg="bootstrap band is centred on the data")

    def test_consensus_ledger_cannot_disagree_with_itself(self):
        docs = _contradictory_docs("t")
        ledger = build_ledger(docs, _extractors())
        consensus = consensus_ledger(ledger)
        for block in consensus.blocks:
            values = {d.value for d in consensus.deltas if d.slot in block.slots}
            self.assertLessEqual(len(values), 1, "a block must be forced to one value")

    def test_self_contradictory_document_now_fails(self):
        doc = Document("t", "english",
                       "The cone is positive. The cone is not positive. The cone may be positive.",
                       "control")
        cell = cell_iv_single_doc(SEED, doc, _extractors(), BETA_ARMS[0])
        self.assertIs(cell.status, NullStatus.FAIL)
        self.assertIn("VOID", cell.detail)

    def test_consistent_document_still_passes(self):
        doc = Document("t", "english",
                       "The cone is positive. The cone is positive under composition.",
                       "control")
        cell = cell_iv_single_doc(SEED, doc, _extractors(), BETA_ARMS[0])
        self.assertIs(cell.status, NullStatus.PASS, cell.detail)


class CellVIsNoLongerVacuous(unittest.TestCase):
    def test_dedupe_flag_reaches_the_accumulator(self):
        """The bug the control found: `dedupe=False` used to leave evidence identical.

        The `dedupe=True` half of this claim no longer holds, and that is a finding rather
        than a broken test — see `ExtractionIsNotContentDetermined` below. Content-hash
        deduplication does collapse re-ingested deltas; what it cannot collapse is a delta
        the duplicate produced and the original did not.
        """
        docs = _contradictory_docs("c")
        dup = list(docs) + [
            Document(f"dup::{d.doc_id}", d.chart, d.text, f"{d.source}::duplicate") for d in docs
        ]
        exts = _extractors()
        self.assertNotEqual(
            build_ledger(docs, exts, dedupe=False).evidence,
            build_ledger(dup, exts, dedupe=False).evidence,
            "with dedupe off, a relabelled copy must actually double-count",
        )

    def test_evidence_dedupe_parameter(self):
        docs = _contradictory_docs("c")
        deltas = build_ledger(docs, _extractors(), dedupe=False).deltas
        doubled = list(deltas) + list(deltas)
        self.assertEqual(evidence_from_deltas(doubled, dedupe=True),
                         evidence_from_deltas(deltas, dedupe=True))
        self.assertNotEqual(evidence_from_deltas(doubled, dedupe=False),
                            evidence_from_deltas(deltas, dedupe=False))

    def test_a_true_duplicate_does_move_the_floor_which_is_the_new_gap(self):
        """Cell (v) FAILS on this corpus, and it is right to.

        KICKOFF section 4 says re-ingesting one corpus under a second provenance label
        must leave zero cold residue. It does not, because extraction is seeded on
        `doc.doc_id` rather than on content — see `ExtractionIsNotContentDetermined`. The
        cell is detecting a real defect, so this asserts the failure rather than papering
        over it.
        """
        cell = cell_v_duplicate_source(SEED, _contradictory_docs("c"), _extractors(), BETA_ARMS[0])
        self.assertIs(cell.status, NullStatus.FAIL, cell.detail)
        self.assertGreater(cell.stats["residue"], 0.0)

    def test_deduplication_itself_still_works(self):
        """The mechanism cell (v) guards is sound; its input is not."""
        from engine.energy import dedupe_deltas
        from engine.pipeline import ingest

        docs = _contradictory_docs("c")
        deltas = ingest(docs, _extractors())
        self.assertEqual(dedupe_deltas(list(deltas) + list(deltas)), dedupe_deltas(deltas),
                         "an exactly repeated delta list collapses to itself")

    def test_disabled_dedup_is_caught(self):
        cell = cell_v_duplicate_source(SEED, _contradictory_docs("c"), _extractors(),
                                       BETA_ARMS[0], dedupe=False)
        self.assertIs(cell.status, NullStatus.FAIL)
        self.assertIn("corroboration", cell.detail)


class R3CarriesTheSameDefect(unittest.TestCase):
    """**Historical pin — kept after PREREG-AMENDMENT-1, deliberately.**

    R3 decides the headline result of the whole run: "the cold floor is ~0" versus "the
    floor is structured". Until 2026-07-30 it decided that with
    `floor <= q95(surrogate_floor_distribution)` — the *same* bootstrap-of-the-observed-
    floors that made null cells (iv) and (v) vacuous. The band is centred on the data, so
    it rises to meet whatever floor it is handed and the `~0` branch was taken at a large
    structured floor as readily as at zero.

    PREREG-AMENDMENT-1 replaced that with `floor <= second_fdt_surrogate_floor`, a
    loop-by-loop permutation of the warm/cold labels — a null built under the no-effect
    hypothesis rather than a resample of the answer.

    These tests exercise the **superseded computation directly**, not through
    `floor_verdict`, so they keep recording what the defect was without asserting anything
    about the current rule. Deleting them would erase the reason the amendment exists. The
    tests below this class check what `floor_verdict` does now.
    """

    @staticmethod
    def _rows(floor: float):
        from engine.meter import LoopMeasurement

        # Every loop's contest is path-dependent: the cold arm sits at `floor`, the warm
        # arm at zero. That is the shape R3 is supposed to call "structured".
        return [
            LoopMeasurement(f"loop{i}", "paraphrase", 1.0, 0.0, floor, 0.0, floor, floor, ("a", "b"))
            for i in range(8)
        ]

    def test_the_superseded_bootstrap_would_have_called_any_floor_near_zero(self):
        from engine.hashing import quantile
        from engine.meter import surrogate_floor_distribution

        for floor in (0.0, 0.45):
            rows = self._rows(floor)
            band = quantile(surrogate_floor_distribution(rows, "r3"), 0.95)
            observed = sum(m.floor for m in rows) / len(rows)
            self.assertLessEqual(observed, band + 1e-12,
                                 f"floor={floor} — the band tracks the data, so `~0` was always taken")

    def test_the_label_permutation_surrogate_separates_what_the_bootstrap_could_not(self):
        from engine.meter import second_fdt_surrogate_floor

        for floor, expect_structured in ((0.0, False), (0.45, True)):
            rows = self._rows(floor)
            observed = sum(m.floor for m in rows) / len(rows)
            fdt = second_fdt_surrogate_floor(rows, "r3")
            self.assertEqual(observed > fdt, expect_structured,
                             f"floor={floor}: a floor carried entirely by the cold arm must "
                             "beat its own label permutation, and a zero floor must not")


class R3AfterTheAmendment(unittest.TestCase):
    """PREREG-AMENDMENT-1: the second-FDT surrogate decides; the bootstrap is a diagnostic."""

    @staticmethod
    def _result(floor: float, seed: str = "r3"):
        from engine.hashing import quantile
        from engine.meter import MeterResult, second_fdt_surrogate_floor, surrogate_floor_distribution

        rows = R3CarriesTheSameDefect._rows(floor)
        result = MeterResult(seed_hash=seed, measurements=rows)
        result.surrogate = {
            "n": float(len(rows)),
            "q95": quantile(surrogate_floor_distribution(rows, seed), 0.95),
            "second_fdt_floor": second_fdt_surrogate_floor(rows, seed),
        }
        return result

    def test_a_structured_floor_is_now_called_structured(self):
        from engine.audit import Verdict, floor_verdict

        verdict = floor_verdict(self._result(0.45))
        self.assertIs(verdict.verdict, Verdict.FLOOR_STRUCTURED)
        self.assertEqual(verdict.stats["decided_by"], "second_fdt_surrogate_floor")
        self.assertTrue(verdict.stats["modes"], "the structured branch must list its modes")

    def test_a_genuinely_zero_floor_is_still_called_near_zero(self):
        """Strictness-increasing, not strictness-maximizing: the `~0` branch still exists."""
        from engine.audit import Verdict, floor_verdict

        self.assertIs(floor_verdict(self._result(0.0)).verdict, Verdict.FLOOR_NEAR_ZERO)

    def test_the_legacy_bootstrap_is_reported_but_decides_nothing(self):
        from engine.audit import floor_verdict

        verdict = floor_verdict(self._result(0.45))
        self.assertIn("surrogate_q95", verdict.stats)
        self.assertEqual(verdict.stats["legacy_bootstrap_branch"], "near_zero")
        self.assertFalse(verdict.stats["surrogates_agree"])
        self.assertIn("legacy bootstrap band disagrees", verdict.detail)

    def test_the_amendment_window_closes_when_P3_begins(self):
        """The authorization is scoped, and the scope is mechanical rather than remembered."""
        import json
        import tempfile
        from pathlib import Path

        from engine import GateViolation
        from engine.audit import check_amendment_window, p3_has_begun

        with tempfile.TemporaryDirectory() as tmp:
            reg = Path(tmp) / "REGISTRY.jsonl"
            reg.write_text(json.dumps({"entry": "phase-run", "phase": "P1"}) + "\n", encoding="utf-8")
            self.assertFalse(p3_has_begun(reg))
            check_amendment_window(reg)  # still open

            with reg.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"entry": "phase-run", "phase": "P3"}) + "\n")
            self.assertTrue(p3_has_begun(reg))
            with self.assertRaises(GateViolation):
                check_amendment_window(reg)

    def test_the_amendment_is_recorded_with_its_rationale(self):
        from engine.audit import AMENDMENTS

        one = next(a for a in AMENDMENTS if a["id"] == "PREREG-AMENDMENT-1")
        self.assertEqual(one["rule"], "R3")
        for clause in ("transcription defect", "no data has passed through R3",
                       "strictness-increasing"):
            self.assertIn(clause, one["rationale"])


class R4IsNotYetConformingToGate6(unittest.TestCase):
    """**Historical pin — kept after PREREG-AMENDMENT-2, on AMENDMENT-1's terms.**

    Until 2026-07-30 R4 compared the floor's movement under Q-edge dropout against
    `baseline.surrogate["q95"]` — the bootstrap of the observed floors, a resample of the
    observation.

    R4 was never vacuous the way R3 was, and the record should not say it was. It was
    miscalibrated in the *permissive* direction: the band scales with the observed floor,
    so the rule was strict on a run whose floor was near zero and lax on a run whose floor
    was large — relaxing exactly where dictionary sensitivity would have mattered most.
    That asymmetry is what this test pins, against the superseded computation directly.
    """

    def test_the_superseded_band_grew_with_the_floor_it_was_meant_to_police(self):
        from engine.hashing import quantile
        from engine.meter import surrogate_floor_distribution

        bands = []
        for floor in (0.0, 0.4):
            rows = R3CarriesTheSameDefect._rows(floor)
            bands.append(quantile(surrogate_floor_distribution(rows, "r4"), 0.95))
        self.assertLess(bands[0], bands[1],
                        "a larger floor bought a larger movement tolerance — the rule "
                        "relaxed as the stakes rose")


class R4AfterTheAmendment(unittest.TestCase):
    """PREREG-AMENDMENT-2: a rewire null, a second arm, and a class that is not (a)."""

    def _fixture(self):
        from engine.constants import decisions, shadow
        from engine.extract import build_k_extractors
        from engine.pipeline import build_ledger, run_meter

        docs = [Document("d1", "english",
                         "Positivity is preserved under composition. "
                         "Composition preserves positivity of cones.", "repo_docs")]
        exts = build_k_extractors(decisions(), offline=True)
        baseline, _, _ = run_meter(build_ledger(docs, exts), 1.0, SEED, shadow())
        return docs, exts, baseline, shadow()

    def test_the_rewire_preserves_degree_and_weight_marginals_exactly(self):
        """The null must differ from the real graph in pairings and nothing else."""
        from engine.blocks import degree_map, rewire_q_graph, weight_marginal
        from engine.hashing import DRNG
        from engine.types import QEdge

        edges = [QEdge(f"s{i}", f"s{(i * 3 + 1) % 11}", 0.8 if i % 2 else 0.5, "fiber")
                 for i in range(11)]
        rewired = rewire_q_graph(edges, DRNG("rewire-test"))

        self.assertEqual(degree_map(edges), degree_map(rewired))
        self.assertEqual(weight_marginal(edges), weight_marginal(rewired))
        self.assertNotEqual({(e.u, e.v) for e in edges}, {(e.u, e.v) for e in rewired},
                            "a rewire that changes no pairing is not a null")

    def test_the_rewire_makes_no_self_loops_and_no_duplicate_pairs(self):
        from engine.blocks import rewire_q_graph
        from engine.hashing import DRNG
        from engine.types import QEdge

        edges = [QEdge(f"s{i}", f"s{(i * 5 + 2) % 13}", 0.7, "fiber") for i in range(13)]
        rewired = rewire_q_graph(edges, DRNG("rewire-test-2"))
        pairs = [frozenset((e.u, e.v)) for e in rewired]
        self.assertTrue(all(len(p) == 2 for p in pairs), "no self-loops")
        self.assertEqual(len(pairs), len(set(pairs)), "no duplicate pairs")

    def test_the_rewire_keeps_weight_strata_separate(self):
        """An unstratified rewire would move a heavy edge onto a pair that never earned one."""
        from engine.blocks import rewire_q_graph
        from engine.hashing import DRNG
        from engine.types import QEdge

        heavy = {(f"h{i}", f"h{(i + 1) % 6}") for i in range(6)}
        light = {(f"l{i}", f"l{(i + 1) % 6}") for i in range(6)}
        edges = ([QEdge(u, v, 0.9, "fiber") for u, v in sorted(heavy)]
                 + [QEdge(u, v, 0.2, "fiber") for u, v in sorted(light)])
        rewired = rewire_q_graph(edges, DRNG("strata"))

        for e in rewired:
            nodes = {e.u[0], e.v[0]}
            self.assertEqual(len(nodes), 1, "a swap crossed a weight stratum")
            self.assertEqual(e.weight, 0.9 if nodes == {"h"} else 0.2)

    def test_R4_is_decided_against_the_rewire_null(self):
        from engine.audit import prior_insensitivity

        docs, exts, baseline, cfg = self._fixture()
        r = prior_insensitivity(docs, exts, 1.0, SEED, cfg, baseline, trials=2)
        self.assertEqual(r.stats["decided_by"], "null_rewire_q95")
        self.assertTrue(r.stats["gate6_conforming"])
        self.assertEqual(len(r.stats["null_movements"]), 2)
        self.assertIn("legacy_self_scaled_band", r.stats)

    def test_the_sensitivity_arm_is_inconclusive_rather_than_absent(self):
        """Reporting one arm of a two-sided test as if the test had run is a false report."""
        from engine.audit import Verdict, prior_insensitivity

        docs, exts, baseline, cfg = self._fixture()
        r = prior_insensitivity(docs, exts, 1.0, SEED, cfg, baseline, trials=1)
        self.assertIsNone(r.stats["sensitivity_arm"])
        self.assertIs(r.verdict, Verdict.CLOSED_INCONCLUSIVE)
        self.assertFalse(r.passed)

    def test_clamp_perturbation_keeps_every_clamp_eligible(self):
        """The sensitivity arm measures the meter; it is not a route around gate 3."""
        from engine.audit import _perturb_clamps
        from engine.types import Clamp, Warrant, WarrantTier

        original = [Clamp("s1", "T", Warrant(WarrantTier.KERNEL, "lean:accept"))]
        rotated = _perturb_clamps(original)
        self.assertNotEqual(rotated[0].value, original[0].value)
        self.assertTrue(rotated[0].warrant.clamp_eligible)
        self.assertEqual(rotated[0].warrant, original[0].warrant)

    def test_amendment_2_is_recorded_as_design_not_restoration(self):
        from engine.audit import AMENDMENTS

        one = next(a for a in AMENDMENTS if a["id"] == "PREREG-AMENDMENT-1")
        two = next(a for a in AMENDMENTS if a["id"] == "PREREG-AMENDMENT-2")

        self.assertEqual(one["class"], "transcription-restoration")
        self.assertEqual(one["rationales"], ["a", "b", "c"])

        self.assertEqual(two["class"], "pre-data-design")
        self.assertEqual(two["rationales"], ["b", "c"])
        self.assertIs(two["rationale_a_applies"], False)
        self.assertIn("nothing to restore", two["rationale_a_note"])


class Gate6SweepIsExecutableNotProse(unittest.TestCase):
    """The sweep has to keep working, or the next R4 is found by accident again."""

    def test_every_band_in_the_engine_is_classified(self):
        from engine.static_checks import check_gate6_classification

        result = check_gate6_classification()
        self.assertTrue(result.ok, [str(v) for v in result.violations])
        self.assertGreater(result.checked_functions, 5, "the walker found nothing to check")

    def test_an_unclassified_band_is_a_violation(self):
        """The check's own positive control."""
        import tempfile
        from pathlib import Path

        from engine.static_checks import check_gate6_classification

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            (root / "engine" / "sneaky.py").write_text(
                "def new_verdict(rows):\n"
                "    from .hashing import quantile\n"
                "    return quantile(rows, 0.95)\n",
                encoding="utf-8",
            )
            result = check_gate6_classification(root)
            self.assertFalse(result.ok)
            self.assertIn("sneaky", str(result.violations[0]))

    def test_the_surviving_non_conforming_sites_are_diagnostics_only(self):
        """The bootstrap is kept on purpose — deleting it would make the amendments
        unauditable — but nothing may decide on it."""
        from engine.static_checks import GATE6_SITES

        for s in GATE6_SITES:
            if s["conforming"] is False:
                self.assertNotEqual(s["role"], "decides",
                                    f"{s['site']} still decides on a resample")

    def test_no_amended_rule_still_decides_on_a_resample(self):
        from engine.audit import AMENDMENTS
        from engine.static_checks import GATE6_SITES

        amended = {"R2": "engine/audit.py:ground_truth_rediscovery",
                   "R3": "engine/audit.py:floor_verdict",
                   "R4": "engine/audit.py:prior_insensitivity"}
        by_site = {str(s["site"]): s for s in GATE6_SITES}
        for a in AMENDMENTS:
            site = amended[str(a["rule"])]
            self.assertIs(by_site[site]["conforming"], True,
                          f"{a['id']} amended {a['rule']} but its site is still non-conforming")


class BrokenFixtures(unittest.TestCase):
    def test_broken_normalizer_is_genuinely_non_idempotent(self):
        once = _broken_normalizer("english", "the cone is positive")
        self.assertNotEqual(once, _broken_normalizer("english", once))

    def test_broken_suite_is_genuinely_broken(self):
        self.assertIs(cell_ii_paraphrase(_BROKEN_SUITE).status, NullStatus.FAIL)

    def test_contradictory_docs_fiber_together(self):
        ledger = build_ledger(_contradictory_docs("t"), _extractors())
        self.assertTrue(
            any(len(b.slots) > 1 for b in ledger.blocks),
            "the control's two surfaces must land in one block or it tests nothing",
        )
        result, _, _ = run_meter(ledger, BETA_ARMS[0], SEED, shadow())
        self.assertGreater(result.mean_floor(), 0.0)


if __name__ == "__main__":
    unittest.main()


class R2AfterTheAmendment(unittest.TestCase):
    """PREREG-AMENDMENT-3, and the positive control that changed how it was built.

    The authorization specified `q95 of that loop's own second-FDT label-permutation null`.
    Implemented literally that flags nothing at any floor, which the mandated control is
    what caught — see `test_a_loops_own_permutation_null_is_degenerate`. The rule as
    shipped pools the other loops' permuted floors leave-one-out.
    """

    @staticmethod
    def _run(docs, seed="r2-test"):
        from engine.constants import decisions, shadow
        from engine.extract import build_k_extractors
        from engine.pipeline import build_ledger, run_meter

        ledger = build_ledger(docs, build_k_extractors(decisions(), offline=True))
        result, _, _ = run_meter(ledger, 1.0, seed, shadow())
        return ledger, result

    # Three mutually-fibering surfaces per theme: a cycle needs three slots whose Q edges
    # close, and since the tree-null repair a two-surface theme yields no loop at all.
    _CLEAN = ("Positivity is preserved under composition. Composition preserves positivity. "
              "Composition preserves the positivity of cones. "
              "The kernel accepts the statement. The kernel accepts every checked statement. "
              "The kernel accepts each checked statement.")

    def test_a_loops_own_permutation_null_is_degenerate(self):
        """Why the shipped rule deviates from the authorized wording.

        A loop with k slots has 2**k assignments of warm/cold per slot. The all-cold
        assignment IS the observed floor, and q95 of four or eight points is the maximum,
        so `floor > q95(own null)` is unsatisfiable. Measured, not argued.
        """
        from engine.constants import SURROGATE_QUANTILE
        from engine.hashing import quantile

        _, result = self._run([Document("d", "english",
                                        "The cone is positive. The cone is not positive. "
                                        "The cone may be positive. "
                                        "The kernel accepts. The kernel does not accept. "
                                        "The kernel may accept.",
                                        "repo_docs")])
        self.assertTrue(result.loop_nulls, "no loops measured; the test proves nothing")
        for m in result.measurements:
            own = result.loop_nulls[m.loop_id]
            self.assertLessEqual(len(set(own)), 2 ** len(m.slots),
                                 "support is bounded by the number of assignments")
            self.assertLessEqual(m.floor, quantile(own, SURROGATE_QUANTILE) + 1e-15,
                                 "a loop can never exceed its own permutation null")

    def test_pooled_leave_one_out_excludes_the_loops_own_draws(self):
        from engine.meter import pooled_loop_nulls

        draws = {"a": [0.0, 0.0, 0.0], "b": [1.0, 1.0, 1.0]}
        thresholds = pooled_loop_nulls(draws)
        self.assertAlmostEqual(thresholds["a"], 1.0, msg="a's bar comes from b alone")
        self.assertAlmostEqual(thresholds["b"], 0.0, msg="b's bar comes from a alone")

    def test_a_single_loop_has_no_pool_and_is_not_silently_compared_to_itself(self):
        from engine.meter import pooled_loop_nulls

        self.assertEqual(pooled_loop_nulls({"only": [0.1, 0.2]})["only"], float("inf"))

    def test_planted_gap_is_found_miss_rate_zero(self):
        """The mandated control, direction one."""
        from engine.audit import ground_truth_rediscovery

        docs = [Document("clean", "english", self._CLEAN, "repo_docs"),
                Document("gap", "english",
                         "The cone is positive. The cone is not positive. "
                         "The cone may be positive.", "repo_docs")]
        ledger, result = self._run(docs)
        r = ground_truth_rediscovery(None, result, ledger,
                                     not_claimed_spans=["the cone is positive"])
        self.assertEqual(r.stats["miss_rate"], 0.0, r.detail)
        self.assertTrue(r.passed)
        self.assertEqual(r.stats["decided_by"], "loop_permutation_null_pooled_loo")
        self.assertTrue(r.stats["gate6_conforming"])

    def test_an_insensitive_meter_is_caught(self):
        """The mandated control, planted-defect direction: R2 must be able to fail.

        Every loop given the same floor and the same null: nothing can clear a pooled
        threshold equal to itself, so the planted gap goes unflagged and R2 reports the
        meter insensitive. A rule that could not produce this outcome would be reporting
        nothing.
        """
        from engine.audit import Verdict, ground_truth_rediscovery
        from engine.meter import LoopMeasurement, MeterResult

        rows = [LoopMeasurement(f"l{i}", "paraphrase", 1.0, 0.2, 0.2, 0.0, 0.2, 0.0,
                                ("s1", "s2")) for i in range(4)]
        result = MeterResult("flat", rows, {"q95": 0.2},
                             loop_nulls={f"l{i}": [0.2] * 8 for i in range(4)})
        r = ground_truth_rediscovery(None, result, None,
                                     not_claimed_spans=["the cone is positive"])
        self.assertEqual(r.stats["miss_rate"], 1.0)
        self.assertFalse(r.passed)
        self.assertIs(r.verdict, Verdict.CLOSED_INCONCLUSIVE)

    def test_fewer_than_two_loops_is_inconclusive_not_a_verdict(self):
        from engine.audit import Verdict, ground_truth_rediscovery
        from engine.meter import LoopMeasurement, MeterResult

        rows = [LoopMeasurement("only", "paraphrase", 1.0, 0.5, 0.5, 0.0, 0.5, 0.0, ("a", "b"))]
        result = MeterResult("one", rows, {"q95": 0.1}, loop_nulls={"only": [0.1] * 8})
        r = ground_truth_rediscovery(None, result, None, not_claimed_spans=["x"])
        self.assertIs(r.verdict, Verdict.CLOSED_INCONCLUSIVE)
        self.assertIn("exchangeable unit", r.detail)

    def test_the_legacy_bootstrap_is_reported_and_decides_nothing(self):
        from engine.audit import ground_truth_rediscovery

        docs = [Document("clean", "english", self._CLEAN, "repo_docs"),
                Document("gap", "english",
                         "The cone is positive. The cone is not positive. "
                         "The cone may be positive.", "repo_docs")]
        ledger, result = self._run(docs)
        r = ground_truth_rediscovery(None, result, ledger,
                                     not_claimed_spans=["the cone is positive"])
        self.assertIn("legacy_bootstrap_band", r.stats)
        self.assertIn("legacy_bootstrap_flagged", r.stats)

    def test_amendment_3_records_the_drafting_history_check(self):
        from engine.audit import AMENDMENTS

        three = next(a for a in AMENDMENTS if a["id"] == "PREREG-AMENDMENT-3")
        self.assertEqual(three["class"], "pre-data-design")
        self.assertEqual(three["rationales"], ["b", "c"])
        self.assertIs(three["rationale_a_applies"], False)
        self.assertIn("specifies no flagging criterion", str(three["drafting_history"]))
        self.assertIn("calibration-restoring", str(three["rationale"]))
        self.assertIn("deviation", str(three).lower())


class EveryDecidingSiteConforms(unittest.TestCase):
    """The closing artifact of the amendment window."""

    def test_no_deciding_site_is_non_conforming(self):
        from engine.static_checks import GATE6_SITES

        offenders = [s["site"] for s in GATE6_SITES
                     if s["role"] == "decides" and s["conforming"] is not True]
        self.assertEqual(offenders, [], f"still deciding on a resample: {offenders}")


class StudentizationWasTriedAndRejected(unittest.TestCase):
    """PREREG-AMENDMENT-3's repair window: one attempt, rejected on its controls.

    The exchangeability limitation raw leave-one-out pooling carries — loops differ in
    slot count and edge weight, so one loud loop raises every other loop's threshold —
    was to be mitigated by scaling each loop's permuted floors by its own null MAD.

    It failed, and not marginally: it **inverted** the planted-gap control. The limitation
    therefore stays **open**, and `ground_truth_rediscovery` still uses `pooled_loop_nulls`.
    These tests pin why, so the attempt is a record rather than a memory.
    """

    def test_the_rejected_repair_is_wired_to_nothing(self):
        import inspect

        from engine.audit import ground_truth_rediscovery

        source = inspect.getsource(ground_truth_rediscovery)
        self.assertIn("pooled_loop_nulls(result.loop_nulls)", source)
        self.assertNotIn("studentized_loop_thresholds(", source)

    def test_studentizing_divides_out_the_signal(self):
        """A loop's floor and its null's scale are the same quantity.

        Warm/cold disagreement produces both, so a loop with a real gap has a large floor
        AND a large null MAD. The ratio is not distinctive; what survives it is loops whose
        null is nearly degenerate.
        """
        from engine.meter import studentized_loop_thresholds

        # A real gap: large floor, correspondingly wide null.
        # A negligible loop: tiny floor, far tinier null.
        draws = {"real": [0.0, 0.10, 0.20, 0.30], "negligible": [0.0, 1e-9, 2e-9, 3e-9]}
        floors = {"real": 0.30, "negligible": 3e-9}
        out = studentized_loop_thresholds(draws, floors)
        self.assertAlmostEqual(out["real"].observed, out["negligible"].observed,
                               msg="studentizing makes a 0.3 floor and a 3e-9 floor "
                                   "indistinguishable — the scale IS the signal")

    def test_it_inverted_the_planted_gap_control(self):
        """The measurement that rejected it, pinned."""
        from engine.audit import ground_truth_rediscovery
        from engine.constants import decisions, shadow
        from engine.extract import build_k_extractors
        from engine.meter import pooled_loop_nulls, studentized_loop_thresholds
        from engine.pipeline import build_ledger, run_meter

        docs = [Document("clean", "english", R2AfterTheAmendment._CLEAN, "repo_docs"),
                Document("gap", "english",
                         "The cone is positive. The cone is not positive. "
                         "The cone may be positive.", "repo_docs")]
        ledger = build_ledger(docs, build_k_extractors(decisions(), offline=True))
        result, _, _ = run_meter(ledger, 1.0, "r2-test", shadow())

        floors = {m.loop_id: m.floor for m in result.measurements}
        stud = studentized_loop_thresholds(result.loop_nulls, floors)
        loudest = max(result.measurements, key=lambda m: m.floor)
        self.assertGreater(loudest.floor, 0.1, "fixture must contain a real gap")
        self.assertFalse(stud[loudest.loop_id].flags,
                         "studentization does not flag the planted gap — the rejection")

        # The exact inversion (a 5.5e-08 loop flagged in the real gap's place) was measured
        # on the corpus as it stood when the repair was judged and is recorded verbatim in
        # AMENDMENTS[2].repair_attempt. What is asserted here is the corpus-robust half:
        # studentizing loses the gap that raw leave-one-out finds.
        raw = pooled_loop_nulls(result.loop_nulls)
        self.assertGreater(loudest.floor, raw[loudest.loop_id],
                           "raw leave-one-out does flag it")

        # Raw leave-one-out, as shipped, gets it right.
        r = ground_truth_rediscovery(None, result, ledger,
                                     not_claimed_spans=["the cone is positive"])
        self.assertEqual(r.stats["miss_rate"], 0.0)
        self.assertEqual(r.stats["decided_by"], "loop_permutation_null_pooled_loo")

    def test_the_loud_loop_control_is_recorded_even_though_the_repair_was_rejected(self):
        """The new control the repair was to be judged on. Raw LOO passes it here.

        Adding a loop with a far larger floor must not change a quiet loop's flag status.
        Raw pooling is *vulnerable* to this in principle — a loud loop raises everyone's
        threshold — and on this corpus it does not fire. That is one instance, not a proof,
        and the limitation stays open on that basis.
        """
        from engine.meter import pooled_loop_nulls

        quiet = [Document("quiet", "english",
                          "The kernel accepts the statement. "
                          "The kernel does not accept the statement. "
                          "The kernel may accept the statement.", "repo_docs"),
                 Document("calm", "english",
                          "Positivity is preserved under composition. "
                          "Composition preserves positivity. "
                          "Composition preserves the positivity of cones.", "repo_docs")]
        loud = Document("loud", "english",
                        "The cone is positive. The cone is not positive. "
                        "The cone is not positive under composition. "
                        "The cone may be positive. The cone is definitely not positive.",
                        "repo_docs")

        def flags(docs):
            _, result = R2AfterTheAmendment._run(docs, seed="loud-control")
            thr = pooled_loop_nulls(result.loop_nulls)
            return {m.loop_id: m.floor > thr.get(m.loop_id, float("inf"))
                    for m in result.measurements}

        without, with_loud = flags(quiet), flags(quiet + [loud])
        shared = set(without) & set(with_loud)
        self.assertTrue(shared, "the two runs must share loops or this tests nothing")
        for loop_id in shared:
            self.assertEqual(without[loop_id], with_loud[loop_id],
                             f"{loop_id}: a loud loop changed a quiet loop's flag status")


class ExtractionIsNotContentDetermined(unittest.TestCase):
    """A second implementation defect, found by the tree-null repair's fixture change.

    `DeterministicExtractor._spans` seeds its RNG with

        DRNG("extract", extractor_id, prompt_id, doc.doc_id)

    so the inclusion draw that decides whether a marginal span is kept depends on the
    document's **id**, not on its content. Re-ingesting identical text under a new id
    therefore draws a different sample and can produce a delta the original did not.

    That contradicts what cell (v) exists to check. Content-hash deduplication makes
    *re-ingested* evidence idempotent, but it cannot collapse evidence that was never
    produced the first time. The defect was latent: the old two-document fixture happened to
    put no span near the selectivity threshold. Widening it to three — required once a cycle
    needed three slots — exposed it.

    Recorded as a `gap-before-P3` row in the faithfulness audit rather than repaired here:
    changing the seed material changes every confidence jitter, hence every floor, and that
    is a ruling to make rather than a fixture to adjust.
    """

    def test_a_relabelled_copy_produces_evidence_the_original_did_not(self):
        from engine.energy import evidential_identity
        from engine.pipeline import ingest

        docs = _contradictory_docs("c")
        dup = [Document(f"dup::{d.doc_id}", d.chart, d.text, f"{d.source}::duplicate")
               for d in docs]
        exts = _extractors()

        original = {evidential_identity(d) for d in ingest(docs, exts)}
        relabelled = {evidential_identity(d) for d in ingest(dup, exts)}
        self.assertNotEqual(original, relabelled,
                            "identical text under a new doc_id must not change what is "
                            "extracted — but it does")
        self.assertTrue(relabelled - original,
                        "the copy yields at least one evidential identity the original "
                        "never produced, which no deduplication can remove")

    def test_the_content_hash_is_the_same_so_dedup_is_not_the_problem(self):
        from engine.pipeline import ingest

        docs = _contradictory_docs("c")
        dup = [Document(f"dup::{d.doc_id}", d.chart, d.text, f"{d.source}::duplicate")
               for d in docs]
        exts = _extractors()
        self.assertEqual({d.provenance.content_hash for d in ingest(docs, exts)},
                         {d.provenance.content_hash for d in ingest(dup, exts)},
                         "provenance hashing is content-based and correct; the seeding is not")

    def test_the_seed_material_is_the_document_id(self):
        import inspect

        from engine.extract import DeterministicExtractor

        source = inspect.getsource(DeterministicExtractor._spans)
        self.assertIn("doc.doc_id", source)
        self.assertNotIn("content_hash", source,
                         "the conforming seeding would key on content, not identity")
