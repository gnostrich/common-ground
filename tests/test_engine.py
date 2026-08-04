"""Engine behaviour: normalization, settlement, holonomy, tape, dedupe, audit."""

from __future__ import annotations

import math
import unittest

from engine.blocks import build_fibers, edges_from_fibers
from engine.constants import BVALUE_INDEX, CHARTS, NBV
from engine.energy import dedupe_deltas, evidence_from_deltas, lexicon_prior
from engine.extract import DeterministicExtractor, build_k_extractors
from engine.hashing import DRNG, quantile
from engine.linalg import hankel, effective_rank, singular_values, total_variation
from engine.meter import edge_weight_map, holonomy, loop_shadow
from engine.mint_tape import act_on_mint, read_tape, residual_stream
from engine.normalize import address, classify, nu
from engine.pipeline import build_ledger, run_meter
from engine.settle import settle, verify_monotone
from engine.types import (
    Block,
    Delta,
    Document,
    LoopSpec,
    Provenance,
    QEdge,
    Warrant,
    WarrantTier,
)


class Normalization(unittest.TestCase):
    def test_idempotent_on_adversarial_input(self):
        rng = DRNG("test-idem")
        alphabet = "aZ0 \t\n\x00\x01\x1f*_`#>$\\()[]'\"‘’–—…:=∘→/-theorem def if must"
        for chart in CHARTS:
            for _ in range(400):
                n = rng.randrange(80) + 1
                s = "".join(alphabet[rng.randrange(len(alphabet))] for _ in range(n))
                once = nu(chart, s)
                self.assertEqual(once, nu(chart, once), f"{chart}: {s!r}")

    def test_total_on_degenerate_input(self):
        for chart in CHARTS:
            for s in ("", " ", "\x00", "\x01en\x01", "\x01lean\x01"):
                self.assertIsInstance(nu(chart, s), str)

    def test_lean_does_not_casefold(self):
        self.assertNotEqual(nu("lean", "Cone"), nu("lean", "cone"))

    def test_english_does_casefold(self):
        self.assertEqual(nu("english", "Cone"), nu("english", "cone"))

    def test_lean_proof_irrelevance_for_claims_only(self):
        with_proof = nu("lean", "theorem t (h : P) : Q := by simp")
        without = nu("lean", "theorem t (h : P) : Q")
        self.assertEqual(with_proof, without)
        # A definition's body IS its content and must survive.
        self.assertNotEqual(
            nu("lean", "def f : Nat := 1"), nu("lean", "def f : Nat := 2")
        )

    def test_nested_lean_block_comments(self):
        self.assertEqual(
            nu("lean", "theorem t /- a /- b -/ c -/ : Q"), nu("lean", "theorem t : Q")
        )

    def test_classification_rules(self):
        self.assertEqual(classify("english", "The cone is positive"), "assert")
        self.assertEqual(classify("english", "If P then Q"), "conditional")
        self.assertEqual(classify("english", "You must not read the floor"), "normative")
        self.assertEqual(classify("english", "A cone is defined as a convex set"), "define")
        self.assertEqual(classify("lean", "def f : Nat := 1"), "define")
        self.assertEqual(classify("lean", "theorem t : Q"), "assert")
        self.assertEqual(classify("lean", "theorem t (h : P) : Q"), "conditional")


class Settlement(unittest.TestCase):
    def test_certificate_is_monotone_and_trace_agrees(self):
        block = Block("b", ("s1", "s2"), (QEdge("s1", "s2", 0.7, "fiber"),))
        deltas = [
            Delta("s1", "english", "assert", "T", 0.9, Warrant(WarrantTier.REPO_DOC),
                  Provenance("s", "a", "l", "k0", "ha"), "x", "\x01en\x01x"),
            Delta("s2", "english", "assert", "F", 0.9, Warrant(WarrantTier.REPO_DOC),
                  Provenance("s", "b", "l", "k0", "hb"), "y", "\x01en\x01y"),
        ]
        s = settle(block, evidence_from_deltas(deltas), lexicon_prior(["s1", "s2"]), 1.0)
        self.assertEqual(s.certificate, "monotone")
        self.assertTrue(verify_monotone(s.f_trace))
        self.assertLessEqual(s.f_after, s.f_before + 1e-12)

    def test_settled_state_is_a_probability_distribution(self):
        block = Block("b", ("s1",), ())
        s = settle(block, {}, lexicon_prior(["s1"]), 1.0)
        for vec in s.p.values():
            self.assertAlmostEqual(math.fsum(vec), 1.0, places=10)
            self.assertTrue(all(x > 0.0 for x in vec))

    def test_clamped_slot_does_not_move(self):
        from engine.types import Clamp

        clamp = Clamp("s1", "T", Warrant(WarrantTier.KERNEL, "receipt"))
        block = Block("b", ("s1", "s2"), (QEdge("s1", "s2", 1.0, "fiber"),))
        evidence = evidence_from_deltas([
            Delta("s1", "english", "assert", "F", 1.0, Warrant(WarrantTier.REPO_DOC),
                  Provenance("s", "a", "l", "k0", "ha"), "x", "\x01en\x01x"),
        ])
        s = settle(block, evidence, lexicon_prior(["s1", "s2"]), 1.0, clamps=[clamp])
        self.assertEqual(s.clamped, ("s1",))
        self.assertGreater(s.p["s1"][BVALUE_INDEX["T"]], 0.99,
                           "a kernel clamp must hold against contrary evidence")

    def test_determinism(self):
        block = Block("b", ("s1", "s2"), (QEdge("s1", "s2", 0.5, "fiber"),))
        ev = evidence_from_deltas([
            Delta("s1", "english", "assert", "T", 0.8, Warrant(WarrantTier.REPO_DOC),
                  Provenance("s", "a", "l", "k0", "ha"), "x", "\x01en\x01x"),
        ])
        a = settle(block, ev, lexicon_prior(["s1", "s2"]), 1.0)
        b = settle(block, ev, lexicon_prior(["s1", "s2"]), 1.0)
        self.assertEqual(a.p, b.p)
        self.assertEqual(a.f_after, b.f_after)


class Holonomy(unittest.TestCase):
    def test_perfect_agreement_has_zero_holonomy(self):
        loop = LoopSpec("l", "paraphrase", ("s1", "s2", "s3"))
        shared = [0.25] * NBV
        p = {s: list(shared) for s in loop.slots}
        weights = edge_weight_map([
            QEdge("s1", "s2", 1.0, "fiber"),
            QEdge("s2", "s3", 1.0, "fiber"),
            QEdge("s3", "s1", 1.0, "fiber"),
        ])
        self.assertEqual(holonomy(loop, p, weights), 0.0)

    @staticmethod
    def _triangle():
        return edge_weight_map([
            QEdge("s1", "s2", 1.0, "fiber"),
            QEdge("s2", "s3", 1.0, "fiber"),
            QEdge("s3", "s1", 1.0, "fiber"),
        ])

    def test_disagreement_produces_positive_holonomy(self):
        loop = LoopSpec("l", "paraphrase", ("s1", "s2", "s3"))
        p = {"s1": [0.97, 0.01, 0.01, 0.01], "s2": [0.01, 0.97, 0.01, 0.01],
             "s3": [0.01, 0.01, 0.97, 0.01]}
        self.assertGreater(holonomy(loop, p, self._triangle()), 0.0)

    def test_holonomy_is_bounded_by_the_widest_disagreement_on_the_cycle(self):
        loop = LoopSpec("l", "paraphrase", ("s1", "s2", "s3"))
        p = {"s1": [0.97, 0.01, 0.01, 0.01], "s2": [0.01, 0.97, 0.01, 0.01],
             "s3": [0.01, 0.01, 0.97, 0.01]}
        widest = max(total_variation(p["s1"], p[s]) for s in ("s2", "s3"))
        self.assertLessEqual(holonomy(loop, p, self._triangle()), widest + 1e-12)

    def test_declared_shadow_is_zero_and_cannot_deflate_the_floor(self):
        from engine.constants import shadow

        loop = LoopSpec("l", "restatement", ("s1", "s2", "s3"))
        chart_of = {"s1": "english", "s2": "lean", "s3": "english"}
        self.assertEqual(loop_shadow(loop, chart_of, shadow()), 0.0)


class Deduplication(unittest.TestCase):
    def _delta(self, doc_id, content_hash, value="T"):
        return Delta("s1", "english", "assert", value, 1.0, Warrant(WarrantTier.REPO_DOC),
                     Provenance("src", doc_id, "l", "k0", content_hash), "x", "\x01en\x01x")

    def test_relabelled_duplicate_adds_no_evidence(self):
        one = [self._delta("d1", "hashA")]
        two = [self._delta("d1", "hashA"), self._delta("d2::dup", "hashA")]
        self.assertEqual(evidence_from_deltas(one), evidence_from_deltas(two))

    def test_genuinely_distinct_documents_still_corroborate(self):
        one = [self._delta("d1", "hashA")]
        two = [self._delta("d1", "hashA"), self._delta("d2", "hashB")]
        self.assertNotEqual(evidence_from_deltas(one), evidence_from_deltas(two))
        self.assertLess(
            evidence_from_deltas(two)["s1"][BVALUE_INDEX["T"]],
            evidence_from_deltas(one)["s1"][BVALUE_INDEX["T"]],
        )

    def test_dedupe_is_order_independent(self):
        ds = [self._delta("d1", "hashA"), self._delta("d2", "hashB")]
        self.assertEqual(
            [d.provenance.content_hash for d in dedupe_deltas(ds)],
            [d.provenance.content_hash for d in dedupe_deltas(list(reversed(ds)))],
        )


class LinAlg(unittest.TestCase):
    def test_singular_values_are_deterministic(self):
        # Gate 10: the docstring says the routine is deterministic; this is what makes that
        # a property of the build rather than a description of intent. The mint tape's
        # Hankel reading depends on it.
        m = [[3.0, 1.0, 0.0], [0.5, 2.0, 1.0], [0.0, 1.0, 1.0]]
        self.assertEqual(singular_values(m), singular_values(m))

    def test_singular_values_of_a_diagonal_matrix(self):
        svs = singular_values([[3.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]])
        for got, want in zip(svs, [3.0, 2.0, 1.0]):
            self.assertAlmostEqual(got, want, places=9)

    def test_rank_one_matrix_has_one_nonzero_singular_value(self):
        m = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]]
        self.assertEqual(effective_rank(singular_values(m)), 1)

    def test_frobenius_identity(self):
        m = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        frob = math.fsum(x * x for row in m for x in row)
        self.assertAlmostEqual(math.fsum(s * s for s in singular_values(m)), frob, places=8)

    def test_hankel_refuses_to_pad_a_short_stream(self):
        self.assertEqual(hankel([1.0, 2.0], 64), [])

    def test_quantile(self):
        self.assertAlmostEqual(quantile([0.0, 1.0], 0.5), 0.5)
        self.assertEqual(quantile([], 0.95), 0.0)


class MintTape(unittest.TestCase):
    def test_mint_is_live_but_refuses_when_disabled(self):
        # K is live (mint_enabled=true), so act_on_mint reports the gate rather than raising.
        reading = read_tape([0.9 ** i for i in range(200)], second_fdt_floor=0.0)
        self.assertTrue(reading.mint_enabled)
        self.assertIsInstance(act_on_mint(reading), bool)
        # With mint explicitly disabled the quarantine is intact — it refuses.
        with self.assertRaises(Exception) as ctx:
            act_on_mint(reading, enabled=False)
        self.assertIn("mint is OFF", str(ctx.exception))

    def test_K_promotes_a_real_mode_but_planted_noise_never_promotes(self):
        from engine.mint_tape import MintController

        # A clean single-mode decay clears the Hankel gate; a flat/noise residual does not.
        real = read_tape([0.9 ** i for i in range(200)], second_fdt_floor=1e-6)
        noise = read_tape([0.001] * 200, second_fdt_floor=0.5)  # top SV << 3*0.5 threshold
        self.assertTrue(real.mint_flag)
        self.assertFalse(noise.mint_flag, "noise below the floor must not flag")

        k = MintController(enabled=True)
        promoted = k.consider("slot-real", "T", real, source="test")
        self.assertTrue(promoted.promoted, promoted.reason)
        blocked = k.consider("slot-noise", "T", noise, source="test")
        self.assertFalse(blocked.promoted, "planted noise must never promote")
        self.assertEqual(set(k.corpus), {"slot-real"})

    def test_K_is_conservative_and_reversible(self):
        from engine.mint_tape import MintController

        real = read_tape([0.9 ** i for i in range(200)], second_fdt_floor=1e-6)
        k = MintController(enabled=True)
        first = k.consider("s", "T", real)
        self.assertTrue(first.promoted)
        # A contradicting value is refused (conservative-extension), corpus unchanged.
        clash = k.consider("s", "F", real)
        self.assertFalse(clash.promoted)
        self.assertFalse(clash.conservative)
        self.assertEqual(k.corpus["s"], "T")
        # Reversible.
        self.assertTrue(k.revert(first))
        self.assertNotIn("s", k.corpus)

    def test_geometric_decay_is_low_rank(self):
        stream = [0.9 ** i for i in range(200)]
        reading = read_tape(stream, second_fdt_floor=0.0)
        self.assertLessEqual(reading.effective_rank, 3,
                             "a single relaxation mode should not look high-rank")

    def test_identical_streams_have_identical_rank(self):
        stream = [0.8 ** i for i in range(150)]
        a = read_tape(stream, 0.0)
        b = read_tape(list(stream), 0.0)
        self.assertEqual(a.effective_rank, b.effective_rank)


class Determinism(unittest.TestCase):
    def test_rng_is_reproducible_from_its_parts(self):
        a = [DRNG("x", "y").random() for _ in range(5)]
        b = [DRNG("x", "y").random() for _ in range(5)]
        c = [DRNG("x", "z").random() for _ in range(5)]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_pipeline_is_reproducible(self):
        from engine.constants import decisions, shadow

        docs = [Document("d", "english", "The cone is positive. It is not positive here.", "src")]
        exts = build_k_extractors(decisions(), offline=True)
        r1, _, _ = run_meter(build_ledger(docs, exts), 1.0, "seed", shadow())
        r2, _, _ = run_meter(build_ledger(docs, exts), 1.0, "seed", shadow())
        self.assertEqual(r1.mean_floor(), r2.mean_floor())
        self.assertEqual(r1.surrogate, r2.surrogate)


class Fibers(unittest.TestCase):
    """Membership is EXACT declared correspondence — no similarity, no threshold, no cap."""

    def _slots(self, *specs):
        from engine.types import Slot
        return [Slot(id=i, nu=n, type=t, chart=c) for (i, n, t, c) in specs]

    def test_no_correspondence_means_no_fiber_even_with_total_token_overlap(self):
        # Two DISTINCT slots that share every word do NOT fiber without a declared
        # correspondence. There is no similarity path left in the engine.
        slots = self._slots(
            ("a", "\x01en\x01the cone is positive", "assert", "english"),
            ("b", "\x01en\x01the cone is not positive", "assert", "english"),
        )
        self.assertEqual(build_fibers(slots), [])
        self.assertEqual(build_fibers(slots, correspondence=[]), [])

    def test_declared_correspondence_forms_exactly_that_fiber(self):
        slots = self._slots(
            ("a", "\x01en\x01x", "assert", "english"),
            ("b", "\x01lean\x01y", "assert", "lean"),
            ("c", "\x01en\x01z", "assert", "english"),
        )
        fibers = build_fibers(slots, correspondence=[("a", "b")])
        self.assertEqual([tuple(f.slots) for f in fibers], [("a", "b")])
        self.assertNotIn("c", {s for f in fibers for s in f.slots})  # undeclared -> frozen

    def test_declared_correspondence_is_transitive(self):
        slots = self._slots(
            ("a", "\x01en\x01x", "assert", "english"),
            ("b", "\x01lean\x01y", "assert", "lean"),
            ("c", "\x01en\x01z", "assert", "english"),
        )
        fibers = build_fibers(slots, correspondence=[("a", "b"), ("b", "c")])
        self.assertEqual([tuple(f.slots) for f in fibers], [("a", "b", "c")])

    def test_edge_weight_is_the_declared_weight(self):
        from engine.blocks import DECLARED_WEIGHT
        slots = self._slots(
            ("a", "\x01en\x01x", "assert", "english"),
            ("b", "\x01lean\x01y", "assert", "lean"),
        )
        edges = edges_from_fibers(build_fibers(slots, correspondence=[("a", "b")]), slots)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].weight, DECLARED_WEIGHT)
        self.assertEqual(edges[0].origin, "correspondence")

    def test_a_declared_group_has_no_similarity_size_cap(self):
        from engine.types import Fiber
        Fiber("big", tuple(f"s{i}" for i in range(9)))  # must not raise (no FIBER_CAP)


if __name__ == "__main__":
    unittest.main()
