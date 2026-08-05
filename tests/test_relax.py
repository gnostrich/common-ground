"""Bias-and-relax, and the three ways it could quietly be lookup again.

The read path used to address the typed text, look the id up in a dict, and match words when
that missed. Settlement was named in the docstring and called nowhere. These controls are
shaped so that the old implementation, and any drift back toward it, fails them:

  * **Relaxation, not lookup.** The same typed input against two corpora that differ only in
    their DECLARED ARROWS must produce different compiled inputs. A lookup cannot tell those
    corpora apart — the biased address is identical in both — so this is the control that
    distinguishes the two mechanisms rather than the two labels.
  * **Silence is a result.** A corpus that does not respond says so and names the structural
    reason. It must not degrade into anything that produces words anyway; that degradation is
    what made the two modes indistinguishable from outside.
  * **Every fact traces.** Each line of a compiled input names a slot the bias REACHED, and
    carries the chain of declared arrows it was reached by. A moved slot with no path is not
    compiled at all.

And one more, for the gate that should have caught the original: a mechanism claim in a module
with none of the machinery must be red.
"""

from __future__ import annotations

import unittest

from engine.corpus_state import CorpusSnapshot, SlotRecord, with_arrows
from engine.correspondence import Correspondence
from engine.extract import DeterministicExtractor
from engine.inbound import compile_input
from engine.relax import BIAS_WEIGHT, MOVED_EPS, relax
from engine.types import Document

_A = "the cone is positive under composition"
_B = "positivity is preserved by pullback"


def _corpus(rows, arrows=()) -> CorpusSnapshot:
    """A snapshot whose addresses are REAL — computed by the extractor the corpus uses.

    Addressing is not faked here. The bias has to reach the field through the same addresses
    corpus material gets, so inventing slot ids would make every control vacuous.
    """
    snap = CorpusSnapshot()
    extractor = DeterministicExtractor("fixture", "test")
    ids: dict[str, str] = {}
    for i, (chart, text) in enumerate(rows):
        for d in extractor.extract(Document(f"doc{i}", chart, text, "test")):
            snap.slots[d.slot] = SlotRecord(slot=d.slot, chart=chart, type=d.type, nu=d.nu,
                                            value="T", confidence=1.0, tier="EXTRACTION",
                                            docs=(f"doc{i}",))
            ids.setdefault(f"{chart}:{text}", d.slot)
    built = []
    for src_key, dst_key, kind in arrows:
        built.append(Correspondence(
            src_chart=src_key.split(":", 1)[0], src_slot=ids[src_key],
            dst_chart=dst_key.split(":", 1)[0], dst_slot=ids[dst_key],
            kind=kind, proposer="fixture", prompt_hash="test", evidence=("fixture",)))
    return with_arrows(snap, built) if built else snap


def _slot_for(snapshot: CorpusSnapshot, text: str) -> str:
    for sid, rec in snapshot.slots.items():
        if text in rec.nu:
            return sid
    raise AssertionError(f"no slot carries {text!r}")


class TheFieldIsActuallyRelaxed(unittest.TestCase):
    """PLANTED against lookup: two corpora a lookup cannot distinguish."""

    def test_the_same_input_gives_different_output_on_differently_wired_corpora(self):
        # Cross-chart, because a correspondence IS cross-chart only: exact addressing owns
        # intra-chart identity (gate 1), and an intra-chart arrow would re-introduce
        # similarity by the back door. The engine refuses to build one, which is why this
        # control could not be written the lazy way.
        rows = [("english", _A), ("lean", "theorem cone_pos : True")]
        # Identical slots, identical addresses. The ONLY difference is a declared arrow.
        unwired = _corpus(rows)
        wired = _corpus(rows, arrows=[(f"english:{_A}", "lean:theorem cone_pos : True",
                                       "same_claim")])

        a = compile_input(_A, unwired, "english")
        b = compile_input(_A, wired, "english")

        self.assertNotEqual(a.compiled, b.compiled,
                            "a lookup cannot tell these corpora apart — the biased address "
                            "is the same in both. Only relaxation over declared structure "
                            "can, so identical output here means this is lookup again.")
        self.assertGreater(b.reached, a.reached)

    def test_a_claim_reached_only_through_an_arrow_appears(self):
        """The claim that proves it is not word matching: `_B` shares no discriminating
        word with the typed `_A` beyond 'positivity', and it is reached because an arrow
        was declared, not because a string matched."""
        wired = _corpus([("english", _A), ("lean", "theorem cone_pos : True")],
                        arrows=[(f"english:{_A}", "lean:theorem cone_pos : True",
                                 "same_claim")])
        got = compile_input(_A, wired, "english")
        self.assertTrue(got.conditioned)
        reached = [m for m in got.relaxation.moved if m.hops > 0]
        self.assertTrue(reached, "nothing was reached through a declared arrow")
        self.assertEqual(reached[0].chart, "lean")
        self.assertIn("MOVED [lean", got.compiled)

    def test_the_shift_decays_with_distance(self):
        """A perturbation that propagated should weaken as it travels; equal shifts at every
        hop would mean the rows were assembled rather than settled."""
        chain = _corpus(
            [("english", _A), ("lean", "theorem cone_pos : True"), ("english", _B)],
            arrows=[(f"english:{_A}", "lean:theorem cone_pos : True", "same_claim"),
                    ("lean:theorem cone_pos : True", f"english:{_B}", "same_claim")])
        # english -> lean -> english: two declared cross-chart arrows forming a 2-hop path.
        moved = relax(_A, chain, "english").moved
        by_hop = {m.hops: m.shift for m in moved}
        self.assertIn(0, by_hop)
        for hop in sorted(by_hop):
            if hop + 1 in by_hop:
                self.assertGreater(by_hop[hop], by_hop[hop + 1],
                                   "shift must decay with declared distance")

    def test_the_bias_is_soft_and_does_not_overwrite_the_corpus(self):
        """A question must not be able to rewrite an answer. The bias tilts F; it never
        clamps, and it cannot, since extraction does not ground (gate 3)."""
        snap = _corpus([("english", _A)])
        moved = relax(_A, snap, "english").moved
        self.assertTrue(moved)
        self.assertLess(moved[0].shift, 2.0, "a soft constraint cannot move a slot to a "
                                             "corner; that would be a clamp")
        self.assertLess(BIAS_WEIGHT, 1.0)


class SilenceIsAResultNotADegradation(unittest.TestCase):
    def test_an_uncoupled_bias_reports_the_structural_reason(self):
        """PLANTED: a corpus holding the words and no arrow. The old build answered this
        with a keyword list; the new one must answer it with a fact about the corpus."""
        snap = _corpus([("english", _B)])
        got = compile_input("a sentence this corpus has never seen", snap, "english")
        self.assertFalse(got.conditioned)
        self.assertIn("THE FIELD DID NOT RESPOND", got.compiled)
        self.assertIn("no declared arrow", got.compiled.replace("no declared arrow touching it",
                                                                "no declared arrow"))
        self.assertIn("no words were compared", got.compiled)

    def test_silence_names_which_kind_of_silence_it_is(self):
        empty = compile_input("anything", CorpusSnapshot(), "english")
        self.assertIn("corpus is empty", empty.compiled)

        uncoupled = compile_input("wholly novel phrasing here",
                                  _corpus([("english", _A)]), "english")
        self.assertIn("none of which this corpus carries", uncoupled.compiled)
        self.assertNotEqual(empty.field_status, uncoupled.field_status,
                            "an empty corpus and an uncoupled bias are different facts")

    def test_there_is_no_second_mechanism_to_fall_back_to(self):
        """The module must not import or reference a string-matching path. Enforced on the
        AST, because 'we removed the fallback' is exactly the kind of claim that rots."""
        import ast

        from engine.constants import REPO_ROOT

        for name in ("engine/inbound.py", "engine/relax.py"):
            source = (REPO_ROOT / name).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.lstrip("."))
                elif isinstance(node, ast.Import):
                    imported.update(a.name for a in node.names)
            self.assertNotIn("retrieval", imported, f"{name} reaches a second mechanism")
            self.assertFalse((REPO_ROOT / "engine" / "retrieval.py").exists(),
                             "the retrieval layer is still on disk")

    def test_nothing_moved_means_no_facts_at_all(self):
        got = compile_input("wholly novel phrasing here", _corpus([("english", _A)]),
                            "english")
        self.assertEqual(got.facts, [], "silence must not emit facts")
        self.assertEqual(got.reached, 0)


class EveryCompiledFactTracesToDeclaredStructure(unittest.TestCase):
    def test_every_fact_names_a_moved_slot_and_its_path(self):
        wired = _corpus([("english", _A), ("lean", "theorem cone_pos : True")],
                        arrows=[(f"english:{_A}", "lean:theorem cone_pos : True",
                                 "same_claim")])
        got = compile_input(_A, wired, "english")
        self.assertTrue(got.facts)
        for fact in got.facts:
            self.assertEqual(fact["kind"], "moved")
            self.assertGreater(fact["shift"], MOVED_EPS)
            if fact["hops"] == 0:
                self.assertEqual(fact["path"], [])
            else:
                self.assertEqual(len(fact["path"]), fact["hops"],
                                 "a reached slot must show one declared step per hop")
                for step in fact["path"]:
                    self.assertIn("correspondence:", step,
                                  "every step must name the arrow kind that carried it")

    def test_a_moved_slot_with_no_declared_path_is_not_compiled(self):
        """The rule that keeps this honest: provenance that cannot be shown is not stated."""
        wired = _corpus([("english", _A), ("lean", "theorem cone_pos : True")],
                        arrows=[(f"english:{_A}", "lean:theorem cone_pos : True",
                                 "same_claim")])
        rel = relax(_A, wired, "english")
        for m in rel.moved:
            self.assertEqual(len(m.path), m.hops)
            self.assertTrue(m.hops == 0 or m.path)

    def test_the_path_steps_are_arrows_that_exist_in_the_corpus(self):
        wired = _corpus([("english", _A), ("lean", "theorem cone_pos : True")],
                        arrows=[(f"english:{_A}", "lean:theorem cone_pos : True",
                                 "same_claim")])
        rel = relax(_A, wired, "english")
        kinds = {a.kind for a in wired.arrows}
        for m in rel.moved:
            for step in m.path:
                self.assertTrue(any(f"correspondence:{k}" in step for k in kinds),
                                f"path step {step!r} names no arrow this corpus declares")

    def test_what_is_cut_is_counted_not_dropped(self):
        from engine.relax import MOVED_CAP

        self.assertGreater(MOVED_CAP, 0)
        rel = relax(_A, _corpus([("english", _A)]), "english")
        self.assertEqual(rel.moved_dropped, 0)
        self.assertEqual(rel.blocks_skipped, 0)


class GateTenCatchesAMechanismClaim(unittest.TestCase):
    """The gate that should have caught the original, with the original as its control."""

    def test_planted_the_historical_sentence_is_red_without_the_machinery(self):
        from engine.static_checks import _mechanism_claims_in

        got = _mechanism_claims_in(
            "settlement runs with the input as soft evidence", "engine/fake.py", set())
        self.assertTrue(got, "the exact sentence engine/inbound.py carried for its whole "
                             "life must be caught when the module cannot perform it")
        self.assertIn("settlement", {kind for kind, _ in got})

    def test_the_same_sentence_is_fine_where_the_machinery_is_referenced(self):
        from engine.static_checks import _mechanism_claims_in

        self.assertEqual(
            _mechanism_claims_in("settlement runs with the input as soft evidence",
                                 "engine/fake.py", {"settle"}), [])

    def test_descriptive_mentions_do_not_fire(self):
        """A gate that cries wolf gets ignored, which is how the first one survived."""
        from engine.static_checks import _mechanism_claims_in

        for benign in ("the cast/settle split: settling produces a distribution",
                       "a tree-shaped contest settles to floor exactly 0",
                       "ingest -> address -> prior -> block -> settle -> meter"):
            self.assertEqual(_mechanism_claims_in(benign, "engine/fake.py", set()), [],
                             f"{benign!r} describes settlement, it does not claim to run it")

    def test_the_repository_is_clean_under_the_extended_gate(self):
        from engine.static_checks import check_claim_discipline

        result = check_claim_discipline()
        self.assertEqual([str(v) for v in result.violations], [])


if __name__ == "__main__":
    unittest.main()
