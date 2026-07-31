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


def delta(slot, value, extractor, confidence=1.0):
    from engine.types import Delta, Provenance
    return Delta(slot=slot, chart="english", type="assert", value=value,
                 confidence=confidence, warrant=Warrant(WarrantTier.EXTRACTION),
                 provenance=Provenance("repo_docs", "doc", "loc", extractor, "hash"),
                 surface=slot, nu=slot)


def block_of(*slots, weight=0.9):
    from engine.types import QEdge
    edges = tuple(QEdge(slots[i], slots[i + 1], weight, "fiber")
                  for i in range(len(slots) - 1))
    return Block("b", tuple(slots), edges)


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

    def test_only_P7_remains_flagged(self):
        from engine.probes import PROBES, flagged_probes

        # After the item-2 refactor and the P5/P6/P9 ruling: P1 is implemented (tabular
        # chart exists), P5/P9 are confirmed mappings, P6 has its own control. Only P7 —
        # the Lean round-trip — is still stubbed, pending the Lean elaboration gate.
        self.assertEqual({p.id for p in flagged_probes()}, {"P7"})
        self.assertEqual({p.id for p in PROBES if p.status == "implemented"},
                         {"P1", "P2", "P3", "P4", "P6", "P8"})
        self.assertEqual({p.id for p in PROBES if p.status == "mapped"}, {"P5", "P9"})

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


class P1ProseVsTable(unittest.TestCase):
    """P1: the same claims settle the same whether stated as prose or as a table.

    Unblocked by the item-2 chart refactor. The two charts normalize differently and carry
    different tags, so the *addresses* differ — but the commitment is about verdicts: the
    b-value the extractor reads from a claim, and whether it contests, must not depend on
    the surface form.
    """

    # Same three claims, once as prose sentences, once as table rows. The bearing text
    # (the value-bearing phrase) is identical, only the framing differs.
    CLAIMS = [
        ("The cone is positive.", "cone | is positive"),
        ("The cone is not positive.", "cone | is not positive"),
        ("The cone may be positive.", "cone | may be positive"),
    ]

    def _values(self, chart, surfaces):
        from engine.extract import DeterministicExtractor

        ext = DeterministicExtractor("e1", "v1")
        doc_text = ("\n".join(surfaces) if chart == "english"
                    else "| subject | claim |\n|---|---|\n"
                         + "\n".join(f"| {s} |" for s in surfaces))
        return sorted(d.value for d in ext.extract(Document("d", chart, doc_text, "repo_docs")))

    def test_the_same_claims_settle_the_same_whether_prose_or_table(self):
        prose = self._values("english", [c[0] for c in self.CLAIMS])
        table = self._values("tabular", [c[1] for c in self.CLAIMS])
        self.assertEqual(prose, table,
                         "a claim's b-value must not depend on prose-vs-table framing")
        self.assertEqual(sorted(prose), ["F", "N", "T"],
                         "and the three claims must read positive / negative / hedged")

    def test_the_two_charts_are_genuinely_distinct_addresses(self):
        from engine.normalize import nu

        self.assertNotEqual(nu("english", "the cone is positive"),
                            nu("tabular", "cone | is positive"),
                            "distinct charts must not collide on an address")


class P6AbstainStability(unittest.TestCase):
    """P6 (corrected): symmetric evidence coexists on B, stably across seeds and schedules.

    Not block-independence. A block whose evidence is equal-and-opposite between two values
    should abstain — settle with its largest mass on B (contested) rather than pick an
    arbitrary winner — and should do so regardless of the seed or the verification budget.
    """

    @staticmethod
    def _symmetric_block():
        from engine.energy import evidence_from_deltas

        deltas = [delta("s1", "T", "e1"), delta("s1", "F", "e2"),
                  delta("s1", "T", "e3"), delta("s1", "F", "e4")]
        return block_of("s1", "s2"), evidence_from_deltas(deltas)

    def test_symmetric_evidence_coexists_stably_across_seeds_and_schedules(self):
        """Coexist means the two contested values keep equal mass and neither wins.

        Not "mass on B" — no source asserted `both`, so B stays empty. Abstain here is the
        settled distribution refusing to collapse: T and F hold equal mass, and that holds
        across the 1x and 4x budgets and reproduces exactly.
        """
        from engine.constants import BVALUE_INDEX
        from engine.meter import anneal

        block, ev = self._symmetric_block()
        priors = {s: list(FLAT) for s in block.slots}
        t, f = BVALUE_INDEX["T"], BVALUE_INDEX["F"]

        results = []
        for beta in (1.0, 4.0):
            p = anneal(block, ev, priors, beta).p["s1"]
            self.assertAlmostEqual(p[t], p[f], places=9,
                                   msg=f"beta={beta}: T and F must stay balanced — no winner")
            self.assertGreater(p[t] + p[f], 0.9,
                               "the contested pair must hold nearly all the mass, coexisting")
            self.assertLess(abs(p[t] - p[f]), 1e-9,
                            "and the split must be exact, not merely close")
            results.append(tuple(round(x, 9) for x in p))

        # settle() is seed-free (deterministic), so the abstain is stable by construction;
        # assert it rather than assume it, since that stability is the commitment.
        self.assertEqual(tuple(round(x, 9) for x in anneal(block, ev, priors, 1.0).p["s1"]),
                         results[0], "the abstain must be reproducible")

    def test_a_contested_source_can_still_put_mass_on_B(self):
        """B is not dead — a source that asserts `both` does land there."""
        from engine.constants import BVALUE_INDEX
        from engine.energy import evidence_from_deltas
        from engine.meter import anneal

        both = evidence_from_deltas([delta("s1", "B", "e1"), delta("s1", "B", "e2")])
        block = block_of("s1", "s2")
        p = anneal(block, both, {s: list(FLAT) for s in block.slots}, 1.0).p["s1"]
        self.assertEqual(max(range(4), key=lambda k: p[k]), BVALUE_INDEX["B"])

    def test_asymmetric_evidence_does_pick_a_winner(self):
        """The control's own control: abstain must be a response to symmetry, not a default."""
        from engine.constants import BVALUE_INDEX
        from engine.energy import evidence_from_deltas
        from engine.meter import anneal

        lopsided = evidence_from_deltas([delta("s1", "T", "e1"), delta("s1", "T", "e2"),
                                         delta("s1", "T", "e3"), delta("s1", "F", "e4")])
        block = block_of("s1", "s2")
        cold = anneal(block, lopsided, {s: list(FLAT) for s in block.slots}, 1.0)
        self.assertEqual(max(range(4), key=lambda k: cold.p["s1"][k]), BVALUE_INDEX["T"],
                         "three-to-one evidence must resolve to T, not abstain")


class TheChartRegistryIsAPlugInSeam(unittest.TestCase):
    """Item 2: a third chart is addable by manifest, and the plug-in audit says so."""

    def test_the_chart_plugin_audit_now_passes(self):
        from engine.chart_plugin_audit import verdict

        v = verdict()
        self.assertTrue(v["manifest_only_possible"],
                        "nu must accept a manifest-declared chart")
        self.assertEqual(v["blocking_sites"], [],
                         "no engine site may hardcode the chart set any longer")

    def test_the_manifest_declares_three_charts(self):
        from engine.charts import chart_names

        self.assertEqual(chart_names(), ("english", "lean", "tabular"))

    def test_a_chart_not_in_the_manifest_is_rejected(self):
        from engine.normalize import nu

        with self.assertRaises(ValueError):
            nu("hieroglyphic", "anything")

    def test_the_tag_is_seed_declared_and_hashed(self):
        """The tag rides inside every address, so it must be under the seed hash (gate 4)."""
        from engine import seed_lock

        files = seed_lock.build_manifest()["files"]
        self.assertIn("CHARTS.json", files, "the chart manifest must be a hashed seed file")

    def test_tabular_normalization_is_idempotent(self):
        from engine.normalize import nu

        raw = "| lemma | status |\n|:--|--:|\n| cone_pos | PROVED |\n| add_pos | open |"
        once = nu("tabular", raw)
        self.assertEqual(once, nu("tabular", once), "nu(nu(x)) == nu(x) for tabular")
        self.assertNotIn("--", once, "the alignment row must be gone")

    def test_no_dispatch_site_names_a_chart(self):
        """The property the audit enforces, asserted directly on nu/classify/segment."""
        import ast
        import inspect

        import engine.extract as ex
        import engine.normalize as nm

        for fn in (nm.nu, nm.classify, ex.DeterministicExtractor._candidate_spans):
            src = inspect.getsource(fn)
            tree = ast.parse(inspect.getsource(fn).lstrip())
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertNotIn(node.value, ("english", "lean", "tabular"),
                                     f"{fn.__name__} names a chart as a literal")


class TheChartAuditCanDetectAReintroducedDefect(unittest.TestCase):
    """The audit gates all future chart admission, so it must be able to FAIL.

    A gate that cannot detect its own breach is decorative — the same positive-control rule
    the null battery follows. `test_the_chart_plugin_audit_now_passes` shows the audit is
    green on clean source; these show it goes RED the moment a hardcoded dispatch is
    reintroduced, at both the detector and the end-to-end level.
    """

    def test_the_detector_flags_an_injected_dispatch_and_clears_a_clean_function(self):
        import ast

        from engine.chart_plugin_audit import _hardcodes_a_chart

        rigged = ast.parse(
            "def nu(chart, surface):\n"
            "    if chart == 'lean':\n"
            "        return _lean(surface)\n"
            "    return _prose(surface)\n"
        ).body[0]
        self.assertTrue(_hardcodes_a_chart(rigged),
                        "an `if chart == 'lean'` dispatch must be detected")

        clean = ast.parse(
            "def nu(chart, surface):\n"
            "    '''dispatches through the registry; mentions lean and english in prose'''\n"
            "    return _NORMALIZERS[chart_spec(chart).behavior](surface)\n"
        ).body[0]
        self.assertFalse(_hardcodes_a_chart(clean),
                         "a registry dispatch — even one naming charts in its docstring — "
                         "must NOT be flagged")

    def test_the_audit_goes_red_end_to_end_when_a_dispatch_is_planted(self):
        """Copy the real nu into a temp root, plant a dispatch, and audit that root."""
        import tempfile
        from pathlib import Path

        import engine.normalize as nm
        from engine.chart_plugin_audit import audit

        real = Path(nm.__file__).read_text(encoding="utf-8")
        # Plant a chart dispatch at the top of nu's body.
        planted = real.replace(
            'def nu(chart: Chart, surface: str) -> str:\n',
            'def nu(chart: Chart, surface: str) -> str:\n'
            '    if chart == "lean":\n        pass\n',
            1,
        )
        self.assertNotEqual(planted, real, "the injection must actually change nu")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            (root / "engine" / "normalize.py").write_text(planted, encoding="utf-8")
            flagged = {s.site for s in audit(root)}
            self.assertIn("engine/normalize.py:nu", flagged,
                          "a reintroduced dispatch in nu must reappear as a blocking site")

    def test_the_clean_root_has_no_blocking_sites(self):
        """The other half of the control: the real tree audits clean."""
        from engine.chart_plugin_audit import audit

        self.assertEqual(audit(), [], "the shipped engine must hardcode no chart")
