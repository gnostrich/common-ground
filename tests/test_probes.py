"""Controls for the four probes that can run before ingestion: P2, P3, P4, P8.

P1 and P7 are stubbed (they need the tabular and Lean charts). P5, P6, P9 are mapped to
existing controls with their commitment inferred and flagged. See `engine/probes.py`.
"""

from __future__ import annotations

import unittest

from engine import GateViolation
from engine.constants import decisions, shadow
from engine.energy import evidential_identity, lexicon_prior
from engine.extract import build_k_extractors
from engine.pipeline import build_ledger, ingest, run_meter
from engine.settle import settle
from engine.types import Block, Clamp, Document, Warrant, WarrantTier

FLAT = [0.0, 0.0, 0.0, 0.0]

# A small corpus that fibers and contests, so there is real structure to preserve.
CORPUS = [
    Document("pos", "english", "The cone is positive. Positivity is preserved under "
             "composition. Composition preserves the positivity of cones.", "repo_docs"),
    Document("neg", "english", "The cone is not positive. The cone may be positive. "
             "The cone is not positive under composition.", "repo_docs"),
]


def _relabelled(docs, tag="zz"):
    return [Document(f"{tag}::{d.doc_id}", d.chart, d.text, f"{d.source}::{tag}")
            for d in docs]


class P2RelabelAndReorderInvariance(unittest.TestCase):
    """P2: verdicts depend on content, never on labels or arrival order."""

    def _run(self, docs, seed="P2"):
        ledger = build_ledger(docs, build_k_extractors(decisions(), offline=True))
        result, _, _ = run_meter(ledger, 1.0, seed, shadow())
        return ledger, result

    def test_relabel_and_reorder_is_bit_identical(self):
        base_ledger, base = self._run(CORPUS)
        moved_ledger, moved = self._run(list(reversed(_relabelled(CORPUS))))

        self.assertEqual(
            sorted((m.loop_id, m.floor) for m in base.measurements),
            sorted((m.loop_id, m.floor) for m in moved.measurements),
            "relabelling and reordering must not move a single floor",
        )
        self.assertEqual(
            {s.id: tuple(round(x, 12) for x in v)
             for s, v in _settled_states(base_ledger)}.keys(),
            {s.id: tuple(round(x, 12) for x in v)
             for s, v in _settled_states(moved_ledger)}.keys(),
            "the slot inventory must be identical",
        )
        self.assertEqual(
            [c.eps_measured for c in base.shadow_calibration],
            [c.eps_measured for c in moved.shadow_calibration],
            "the shadow calibration is content-derived, so it too must be bit-identical",
        )

    def test_the_evidence_itself_is_label_independent(self):
        exts = build_k_extractors(decisions(), offline=True)
        self.assertEqual(
            sorted(evidential_identity(d) for d in ingest(CORPUS, exts)),
            sorted(evidential_identity(d) for d in ingest(_relabelled(CORPUS), exts)),
        )


class P3DuplicationGrowsNoStructure(unittest.TestCase):
    """P3: a duplicated corpus adds no slots, blocks, fibers, loops, or rank."""

    def test_a_relabelled_duplicate_adds_no_structure(self):
        exts = build_k_extractors(decisions(), offline=True)
        once = build_ledger(CORPUS, exts)
        twice = build_ledger(list(CORPUS) + _relabelled(CORPUS, "dup"), exts)

        self.assertEqual(once.summary(), twice.summary(),
                         "every structural count must be identical")
        r1, _, _ = run_meter(once, 1.0, "P3", shadow())
        r2, _, _ = run_meter(twice, 1.0, "P3", shadow())
        self.assertEqual(r1.mean_floor(), r2.mean_floor(),
                         "and the cold floor must be bit-identical")

    def test_the_probe_is_strictly_stronger_than_cell_v(self):
        """Cell (v) checks the floor residue; this checks the whole structure."""
        exts = build_k_extractors(decisions(), offline=True)
        once = build_ledger(CORPUS, exts)
        twice = build_ledger(list(CORPUS) + _relabelled(CORPUS, "dup"), exts)
        self.assertEqual(once.summary()["slots"], twice.summary()["slots"])
        self.assertEqual(once.summary()["blocks"], twice.summary()["blocks"])
        self.assertEqual(once.summary()["fibers"], twice.summary()["fibers"])


class P4ClampScreening(unittest.TestCase):
    """P4: only a clamp-eligible warrant can ground a value."""

    def test_only_eligible_warrants_ground(self):
        # Constructible from the two grounding tiers.
        for tier in (WarrantTier.KERNEL, WarrantTier.CI_RECEIPT):
            Clamp("s1", "T", Warrant(tier, "receipt"))

        # Refused from every other tier.
        for tier in (WarrantTier.PREMINTED, WarrantTier.REPO_DOC, WarrantTier.EXTRACTION):
            with self.assertRaises(GateViolation, msg=f"{tier.name} must not ground"):
                Clamp("s1", "T", Warrant(tier, "not a receipt"))

    def test_a_clamp_holds_against_contrary_evidence(self):
        from engine.energy import evidence_from_deltas
        from engine.types import Delta, Provenance

        contra = [
            Delta("s1", "english", "assert", "F", 1.0, Warrant(WarrantTier.EXTRACTION),
                  Provenance("repo_docs", "d", "l", f"e{i}", "h"), "s1", "s1")
            for i in range(3)
        ]
        settled = settle(Block("b", ("s1", "s2"), ()), evidence_from_deltas(contra),
                         {"s1": list(FLAT), "s2": list(FLAT)}, 1.0,
                         clamps=[Clamp("s1", "T", Warrant(WarrantTier.KERNEL, "k"))])
        self.assertGreater(settled.p["s1"][2], 0.99, "the clamp must hold")

    def test_a_heavy_prior_screens_out_and_never_grounds(self):
        heavy = {"s1": [v * 1000.0 for v in lexicon_prior(["s1"], {"s1": "T"})["s1"]]}
        settled = settle(Block("b", ("s1",), ()), {}, heavy, 1.0)
        self.assertLess(settled.p["s1"][2], 1.0,
                        "a prior tilts but never fixes — only a clamp grounds")


class P8ProvenanceWalker(unittest.TestCase):
    """P8: every delta fully provenanced; no generative key reads identity."""

    def test_every_delta_is_fully_provenanced_and_no_key_is_identity_keyed(self):
        from engine.static_checks import check_generative_keys

        exts = build_k_extractors(decisions(), offline=True)
        by_hash = {d.doc_id: d.content_hash for d in CORPUS}

        for delta in ingest(CORPUS, exts):
            prov = delta.provenance
            self.assertTrue(prov.source, "source is required")
            self.assertTrue(prov.doc_id, "doc_id is required")
            self.assertTrue(prov.extractor_id, "extractor_id is required")
            self.assertTrue(prov.content_hash, "content_hash is required")
            self.assertEqual(prov.content_hash, by_hash[prov.doc_id],
                             "the delta's content hash must match its document's")

        # The generative-key half: identity may label evidence, never generate it.
        result = check_generative_keys()
        self.assertTrue(result.ok, [str(v) for v in result.violations])

    def test_the_walk_reaches_every_document(self):
        exts = build_k_extractors(decisions(), offline=True)
        reached = {d.provenance.doc_id for d in ingest(CORPUS, exts)}
        self.assertEqual(reached, {d.doc_id for d in CORPUS},
                         "a provenance walk that skips a document proves nothing about it")


class TheProbeBatteryIsWellFormed(unittest.TestCase):
    def test_every_probe_is_statused_and_live_controls_resolve(self):
        from engine.probes import check_probe_battery

        result = check_probe_battery()
        self.assertTrue(result.ok, result.missing_control + result.unstatused)
        self.assertEqual(result.checked, 9)

    def test_the_flagged_rows_are_exactly_the_ones_without_a_committed_probe(self):
        from engine.probes import PROBES, flagged_probes

        flagged = {p.id for p in flagged_probes()}
        self.assertEqual(flagged, {"P1", "P5", "P6", "P7", "P9"},
                         "P1/P7 stubbed on a missing chart; P5/P6/P9 commitment inferred")
        # The four buildable-now probes are implemented, not flagged.
        implemented = {p.id for p in PROBES if p.status == "implemented"}
        self.assertEqual(implemented, {"P2", "P3", "P4", "P8"})

    def test_a_probe_naming_a_nonexistent_control_is_caught(self):
        from engine.probes import IMPLEMENTED, Probe, check_probe_battery
        import engine.probes as mod

        original = mod.PROBES
        mod.PROBES = original + (
            Probe(id="PX", commitment="x", probe="x", status=IMPLEMENTED,
                  control="tests/test_probes.py:Nope.test_nope"),
        )
        try:
            self.assertFalse(check_probe_battery().ok)
        finally:
            mod.PROBES = original


def _settled_states(ledger):
    """(slot, vector) for every slot, via a fresh cold settle. Order-independent."""
    from engine.meter import anneal

    out = []
    for block in ledger.blocks:
        cold = anneal(block, ledger.evidence, ledger.priors, 1.0)
        for s in ledger.slots:
            if s.id in block.slots:
                out.append((s, cold.p[s.id]))
    return out


if __name__ == "__main__":
    unittest.main()
