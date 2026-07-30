"""Adapters, casting policy, PREREG rule evaluation, and the seed-lock round trip."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.claude_export import load_claude_export
from adapters.lean_corpus import KernelReceipt, clamps_from_receipts, load_lean_corpus
from adapters.repo_docs import load_preminted, load_repo_docs
from engine import EngineError, GateViolation, seed_lock
from engine.audit import (
    AuditReport,
    Verdict,
    floor_verdict,
    ground_truth_rediscovery,
    harness,
    prior_insensitivity,
)
from engine.cast import cast, may_cast, t2_schedule
from engine.constants import CAST_T2_END, CAST_T2_START, decisions, shadow
from engine.extract import build_k_extractors
from engine.meter import MeterResult
from engine.mint_tape import read_tape, residual_stream
from engine.pipeline import build_ledger, run_meter
from engine.settle import settle
from engine.types import (
    Block,
    Clamp,
    Document,
    LoopSpec,
    NullBatteryReport,
    NullCell,
    NullStatus,
    QEdge,
    Warrant,
    WarrantTier,
)
from engine.meter import LoopMeasurement


class ClaudeExportAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "export.json"
        self.path.write_text(json.dumps([
            {
                "uuid": "t1",
                "name": "positivity thread",
                "chat_messages": [
                    {"sender": "human", "text": "Is positivity preserved under composition?"},
                    {"sender": "assistant", "content": [
                        {"type": "text", "text": "Positivity is preserved under composition."}
                    ]},
                    {"sender": "assistant", "text": "   "},
                ],
            },
            {
                "uuid": "t2",
                "name": "private matters",
                "chat_messages": [{"sender": "human", "text": "my home address is secret"}],
            },
        ]), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_exclusions_none_is_refused(self):
        """The privacy pass is mandatory; 'unset' must not silently mean 'nothing'."""
        with self.assertRaises(EngineError) as ctx:
            load_claude_export(self.path, exclusions=None)
        self.assertIn("EXCLUSIONS", str(ctx.exception))

    def test_empty_exclusions_is_an_explicit_and_valid_decision(self):
        docs = load_claude_export(self.path, exclusions=[])
        self.assertEqual(len(docs), 3)

    def test_one_document_per_turn_not_per_thread(self):
        docs = load_claude_export(self.path, exclusions=[])
        self.assertEqual({d.meta["thread_id"] for d in docs}, {"t1", "t2"})
        self.assertEqual(len([d for d in docs if d.meta["thread_id"] == "t1"]), 2)

    def test_blank_turns_are_dropped(self):
        docs = load_claude_export(self.path, exclusions=[])
        self.assertTrue(all(d.text.strip() for d in docs))

    def test_exclusions_are_applied_before_extraction(self):
        docs = load_claude_export(self.path, exclusions=["home address"])
        self.assertNotIn("t2", {d.meta["thread_id"] for d in docs})

    def test_block_structured_content_is_read(self):
        docs = load_claude_export(self.path, exclusions=[])
        self.assertTrue(any("preserved under composition" in d.text for d in docs))

    def test_turn_content_hash_is_independent_of_labels(self):
        docs = load_claude_export(self.path, exclusions=[])
        a = docs[0]
        relabelled = Document("other:id", a.chart, a.text, "other-source")
        self.assertEqual(a.content_hash, relabelled.content_hash)


class LeanAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "Cone.lean").write_text(
            "theorem comp_pos (f g : Cone) : IsPositive (f ∘ g) := by simp\n"
            "def Cone.mk (x : Nat) : Cone := ⟨x⟩\n",
            encoding="utf-8",
        )
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def test_loads_documents_without_a_toolchain_but_emits_no_receipts(self):
        docs, receipts = load_lean_corpus(self.root, lean_toolchain=None)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].chart, "lean")
        self.assertEqual(receipts, [], "no pinned toolchain means no receipts")

    def test_clamps_refuse_without_a_pinned_toolchain(self):
        docs, _ = load_lean_corpus(self.root, lean_toolchain=None)
        with self.assertRaises(EngineError) as ctx:
            clamps_from_receipts(docs, [], lean_toolchain=None)
        self.assertIn("D6", str(ctx.exception))

    def test_receipts_ground_only_propositions(self):
        docs, _ = load_lean_corpus(self.root, lean_toolchain="leanprover/lean4:v4.99.0")
        receipt = KernelReceipt("Cone.lean", "deadbeef", "leanprover/lean4:v4.99.0", True, "")
        clamps = clamps_from_receipts(docs, [receipt], "leanprover/lean4:v4.99.0")
        self.assertEqual(len(clamps), 1, "the `def` must not be clamped; only the theorem")
        self.assertIs(clamps[0].warrant.tier, WarrantTier.KERNEL)
        self.assertTrue(clamps[0].warrant.clamp_eligible)
        self.assertIn("toolchain=", clamps[0].warrant.detail)

    def test_a_rejected_receipt_grounds_nothing(self):
        docs, _ = load_lean_corpus(self.root, lean_toolchain="v4.99.0")
        rejected = KernelReceipt("Cone.lean", "deadbeef", "v4.99.0", False, "error")
        self.assertEqual(clamps_from_receipts(docs, [rejected], "v4.99.0"), [])


class RepoDocsAdapter(unittest.TestCase):
    def test_loads_listed_files_and_hashes_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("The cone is positive.", encoding="utf-8")
            docs = load_repo_docs(root, "demo", include=["README.md"])
            self.assertEqual(len(docs), 1)
            self.assertEqual(len(docs[0].meta["sha256"]), 64)

    def test_missing_listed_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EngineError):
                load_repo_docs(tmp, "demo", include=["absent.md"])

    def test_preminted_is_empty_and_that_is_not_an_error(self):
        """D5 unresolved. Returns [], which is what makes null cell (iii) BLOCKED."""
        self.assertEqual(load_preminted(), [])


class CastingPolicy(unittest.TestCase):
    def setUp(self):
        self.block = Block("b", ("s1", "s2"), (QEdge("s1", "s2", 0.8, "fiber"),))
        self.settled = settle(self.block, {}, {"s1": [0.0] * 4, "s2": [0.0] * 4}, 1.0)

    def test_t2_schedule_runs_from_start_to_floor(self):
        sched = t2_schedule()
        self.assertEqual(sched[0], CAST_T2_START)
        self.assertEqual(sched[-1], CAST_T2_END)
        self.assertTrue(all(b < a for a, b in zip(sched, sched[1:])))

    def test_casting_is_withheld_by_default(self):
        with self.assertRaises(GateViolation) as ctx:
            cast(self.block, self.settled.p, "seed")
        self.assertIn("withheld at v0", str(ctx.exception))

    def test_may_cast_requires_a_kernel_clamp_not_merely_a_grounding_one(self):
        ci = Clamp("s1", "T", Warrant(WarrantTier.CI_RECEIPT, "green"))
        kernel = Clamp("s1", "T", Warrant(WarrantTier.KERNEL, "receipt"))
        self.assertFalse(may_cast(self.block, [ci]),
                         "a CI receipt grounds, but does not license casting at v0")
        self.assertTrue(may_cast(self.block, [kernel]))

    def test_cast_is_deterministic_and_respects_clamps(self):
        kernel = Clamp("s1", "T", Warrant(WarrantTier.KERNEL, "receipt"))
        a = cast(self.block, self.settled.p, "seed", clamps=[kernel], allow=True)
        b = cast(self.block, self.settled.p, "seed", clamps=[kernel], allow=True)
        self.assertEqual(a.commitment, b.commitment)
        self.assertEqual(a.commitment["s1"], "T")
        self.assertEqual(set(a.commitment), {"s1", "s2"})

    def test_different_seeds_can_differ(self):
        kernel = Clamp("s1", "T", Warrant(WarrantTier.KERNEL, "receipt"))
        a = cast(self.block, self.settled.p, "seedA", clamps=[kernel], allow=True)
        self.assertEqual(a.sweeps, len(t2_schedule()))


class PreregRules(unittest.TestCase):
    def _measurement(self, floor, loop_id="l"):
        return LoopMeasurement(loop_id, "paraphrase", 1.0, floor, floor, 0.0, floor, 0.0, ("s1", "s2"))

    def test_R1_void_on_blocked(self):
        report = NullBatteryReport("s", [
            NullCell("i", NullStatus.PASS, ""), NullCell("iii", NullStatus.BLOCKED, "")
        ])
        r = harness(report)
        self.assertFalse(r.passed)
        self.assertIs(r.verdict, Verdict.VOID)
        self.assertIn("never tested", r.detail)

    def test_R1_distinguishes_blocked_from_failed(self):
        failed = harness(NullBatteryReport("s", [NullCell("i", NullStatus.FAIL, "")]))
        blocked = harness(NullBatteryReport("s", [NullCell("i", NullStatus.BLOCKED, "")]))
        self.assertIn("FAILED", failed.detail)
        self.assertIn("BLOCKED", blocked.detail)
        self.assertNotEqual(failed.detail, blocked.detail)

    def test_R1_passes_when_all_green(self):
        r = harness(NullBatteryReport("s", [NullCell("i", NullStatus.PASS, "")]))
        self.assertTrue(r.passed)
        self.assertIsNone(r.verdict)

    def test_R2_is_inconclusive_without_STATEMENTS(self):
        r = ground_truth_rediscovery(None, MeterResult("s"), None)  # type: ignore[arg-type]
        self.assertFalse(r.passed)
        self.assertIs(r.verdict, Verdict.CLOSED_INCONCLUSIVE)
        self.assertIn("D5", r.detail)

    # PREREG-AMENDMENT-1: the surrogate that decides R3 is `second_fdt_floor` (warm/cold
    # label permutation), not `q95` (bootstrap of the observed floors). `q95` is still
    # supplied here so the legacy-diagnostic reporting stays exercised.

    def test_R3_near_zero_branch(self):
        result = MeterResult("s", [self._measurement(0.0)],
                             {"q95": 0.01, "second_fdt_floor": 0.01})
        r = floor_verdict(result)
        self.assertIs(r.verdict, Verdict.FLOOR_NEAR_ZERO)
        self.assertIn("protocol claims NOT advanced", r.detail)

    def test_R3_structured_branch_lists_modes_verbatim(self):
        result = MeterResult("s", [self._measurement(0.5, "hot"), self._measurement(0.0, "cold")],
                             {"q95": 0.01, "second_fdt_floor": 0.01})
        r = floor_verdict(result)
        self.assertIs(r.verdict, Verdict.FLOOR_STRUCTURED)
        modes = r.stats["modes"]
        self.assertEqual(len(modes), 1)
        self.assertEqual(modes[0]["loop_id"], "hot")

    def test_R3_reads_near_zero_against_the_null_not_by_eye(self):
        tight = MeterResult("s", [self._measurement(0.02)],
                            {"q95": 0.01, "second_fdt_floor": 0.01})
        loose = MeterResult("s", [self._measurement(0.02)],
                            {"q95": 0.01, "second_fdt_floor": 0.5})
        self.assertIs(floor_verdict(tight).verdict, Verdict.FLOOR_STRUCTURED)
        self.assertIs(floor_verdict(loose).verdict, Verdict.FLOOR_NEAR_ZERO)

    def test_R3_ignores_the_legacy_bootstrap_band(self):
        """A generous bootstrap band no longer rescues a structured floor."""
        result = MeterResult("s", [self._measurement(0.4)],
                             {"q95": 0.9, "second_fdt_floor": 0.01})
        r = floor_verdict(result)
        self.assertIs(r.verdict, Verdict.FLOOR_STRUCTURED)
        self.assertEqual(r.stats["legacy_bootstrap_branch"], "near_zero")
        self.assertEqual(r.stats["decided_by"], "second_fdt_surrogate_floor")
        self.assertIn("legacy bootstrap band disagrees", r.detail)

    def test_R4_on_a_real_corpus(self):
        docs = [Document("d1", "english",
                         "Positivity is preserved under composition. "
                         "Composition preserves positivity of cones.", "repo_docs")]
        exts = build_k_extractors(decisions(), offline=True)
        baseline, _, _ = run_meter(build_ledger(docs, exts), 1.0, "seed", shadow())
        r = prior_insensitivity(docs, exts, 1.0, "seed", shadow(), baseline, trials=2)
        self.assertIn("movements", r.stats)
        self.assertEqual(len(r.stats["movements"]), 2)

    def test_R5_verdict_is_always_terminal(self):
        report = AuditReport("s", [harness(NullBatteryReport("s", [NullCell("i", NullStatus.BLOCKED, "")]))])
        self.assertIs(report.terminal_verdict, Verdict.VOID)
        self.assertNotIn("pending", [v.value.lower() for v in Verdict])

    def test_audit_record_carries_the_not_claimed_list(self):
        from engine.audit import NOT_CLAIMED

        self.assertIn("growth law (mint off)", NOT_CLAIMED)
        self.assertIn("generality beyond this corpus and seed hash", NOT_CLAIMED)


class SeedLockRoundTrip(unittest.TestCase):
    def test_build_then_verify_then_detect_drift(self):
        """Full gate-4 cycle against a temp lock path, leaving the repo's own lock alone."""
        original = seed_lock.SEED_LOCK_PATH
        with tempfile.TemporaryDirectory() as tmp:
            seed_lock.SEED_LOCK_PATH = Path(tmp) / "SEED.lock"
            try:
                state = seed_lock.build(force=True)
                self.assertEqual(len(state.seed_hash), 64)

                ok, problems = seed_lock.verify()
                self.assertTrue(ok, problems)

                # Simulate content drift in a seed file.
                payload = json.loads(seed_lock.SEED_LOCK_PATH.read_text(encoding="utf-8"))
                payload["manifest"]["files"]["TYPES.md"] = "0" * 64
                seed_lock.SEED_LOCK_PATH.write_text(json.dumps(payload), encoding="utf-8")

                ok, problems = seed_lock.verify()
                self.assertFalse(ok)
                self.assertTrue(any("content drift" in p for p in problems), problems)
            finally:
                seed_lock.SEED_LOCK_PATH = original

    def test_verify_reports_an_absent_lock(self):
        original = seed_lock.SEED_LOCK_PATH
        with tempfile.TemporaryDirectory() as tmp:
            seed_lock.SEED_LOCK_PATH = Path(tmp) / "nope.lock"
            try:
                ok, problems = seed_lock.verify()
                self.assertFalse(ok)
                self.assertIn("absent", problems[0])
            finally:
                seed_lock.SEED_LOCK_PATH = original


class LexiconPins(unittest.TestCase):
    """D8 fixes a fetch *policy*; `record_pin` records what that policy resolved to.

    "Latest stable Mathlib" and "current nLab" name a rule, not an artifact — they resolve
    to different bytes next week. The digest recorded here is what makes a run replayable,
    so these tests care that it reaches SEED.lock and that it cannot be rewritten under a
    live seed.
    """

    def setUp(self):
        self._saved = (seed_lock.DECISIONS_PATH, seed_lock.SEED_DIR, seed_lock.SEED_LOCK_PATH)
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        seed_lock.DECISIONS_PATH = tmp / "DECISIONS.json"
        seed_lock.SEED_DIR = tmp
        seed_lock.SEED_LOCK_PATH = tmp / "SEED.lock"
        seed_lock.DECISIONS_PATH.write_text(json.dumps({"D8": {
            "status": "partial", "mathlib_policy": "latest-stable-at-fetch",
            "wordnet_version": "3.1",
        }}), encoding="utf-8")
        (tmp / "DECISIONS.md").write_text(
            "| source | policy | artifact | digest |\n"
            "| Mathlib | latest stable at fetch | `____` | `____` |\n",
            encoding="utf-8",
        )
        self.dump = tmp / "dump.json"
        self.dump.write_text('{"declarations": []}', encoding="utf-8")

    def tearDown(self):
        seed_lock.DECISIONS_PATH, seed_lock.SEED_DIR, seed_lock.SEED_LOCK_PATH = self._saved
        self._tmp.cleanup()

    def test_pin_records_path_label_and_digest(self):
        rec = seed_lock.record_pin("mathlib", self.dump, "abc123def456")
        self.assertEqual(len(rec["digest"]), 64)
        d8 = json.loads(seed_lock.DECISIONS_PATH.read_text())["D8"]
        self.assertEqual(d8["mathlib_commit"], "abc123def456")
        self.assertEqual(d8["mathlib_dump_sha256"], rec["digest"])
        self.assertEqual(d8["status"], "partial", "one pin of three does not resolve D8")
        self.assertEqual(rec["still_blank"], ["nlab", "wordnet"])

    def test_pin_updates_the_prose_record_too(self):
        """Otherwise a `____` survives in DECISIONS.md and blocks the lock it just unblocked."""
        seed_lock.record_pin("mathlib", self.dump, "abc123def456")
        md = (seed_lock.SEED_DIR / "DECISIONS.md").read_text()
        self.assertNotIn("____", md)
        self.assertIn("dump.json", md)

    def test_a_label_alone_is_not_a_pin(self):
        """WordNet 3.1 is a real version and D8 carries it — but the artifact still has to land."""
        d8 = json.loads(seed_lock.DECISIONS_PATH.read_text())["D8"]
        self.assertEqual(d8["wordnet_version"], "3.1")
        self.assertIsNone(d8.get("wordnet_sha256"))
        with self.assertRaises(GateViolation):
            seed_lock.record_pin("wordnet", seed_lock.SEED_DIR / "absent.json")

    def test_missing_provenance_is_refused(self):
        with self.assertRaises(GateViolation) as ctx:
            seed_lock.record_pin("mathlib", self.dump)
        self.assertIn("commit", str(ctx.exception))

    def test_pinning_under_a_written_lock_is_a_seed_morphism(self):
        seed_lock.SEED_LOCK_PATH.write_text("{}", encoding="utf-8")
        with self.assertRaises(GateViolation) as ctx:
            seed_lock.record_pin("mathlib", self.dump, "abc123def456")
        self.assertIn("re-anneal", str(ctx.exception))

    def test_digest_reaches_the_lock_manifest(self):
        pins = seed_lock.lexicon_pins({"D8": {
            "mathlib_dump_sha256": "a" * 64, "nlab_scrape_sha256": "b" * 64,
            "wordnet_sha256": "c" * 64, "wordnet_version": "3.1",
        }})
        self.assertEqual(pins["mathlib_dump_sha256"], "a" * 64)
        self.assertEqual(pins["wordnet_sha256"], "c" * 64)

    def test_a_directory_digest_follows_content_not_layout(self):
        """Mathlib may arrive as a tree. The digest must not depend on the walk or on .git."""
        from engine.hashing import artifact_digest

        root = seed_lock.SEED_DIR / "tree"
        (root / "sub").mkdir(parents=True)
        (root / "a.lean").write_text("theorem a : True := trivial\n", encoding="utf-8")
        (root / "sub" / "b.lean").write_text("theorem b : True := trivial\n", encoding="utf-8")
        first = artifact_digest(root)

        (root / ".git").mkdir()
        (root / ".git" / "HEAD").write_text("ref: refs/heads/master\n", encoding="utf-8")
        self.assertEqual(first, artifact_digest(root), "fetch history is not content")

        (root / "sub" / "b.lean").write_text("theorem b : False := sorry\n", encoding="utf-8")
        self.assertNotEqual(first, artifact_digest(root))


class TapeOnRealSettlement(unittest.TestCase):
    def test_residual_stream_is_non_negative_and_decaying(self):
        block = Block("b", ("s1", "s2"), (QEdge("s1", "s2", 0.9, "fiber"),))
        s = settle(block, {}, {"s1": [0.0] * 4, "s2": [0.0] * 4}, 1.0)
        stream = residual_stream(s)
        self.assertTrue(all(x >= 0.0 for x in stream))
        self.assertTrue(all(b <= a + 1e-12 for a, b in zip(stream, stream[1:])))

    def test_tape_on_a_short_stream_is_empty_not_padded(self):
        reading = read_tape([1.0, 0.5], second_fdt_floor=0.0)
        self.assertEqual(reading.singular_values, [])
        self.assertEqual(reading.effective_rank, 0)
        self.assertFalse(reading.mint_flag)


if __name__ == "__main__":
    unittest.main()
