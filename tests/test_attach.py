"""Attachment: how a bias reaches the field, and why it is not matching by another name.

The defect was inherited rather than designed. Gate 1 governs CLAIM IDENTITY and does so
correctly. A bias is not a claim, and how a bias attaches was never specified — the
implementation reused the addressing rule because it was the rule in front of it, so typed
text that did not already exist verbatim attached to nothing and a 69,000-slot corpus reported
that it had not responded.

The fix uses the mechanism that already exists: the proposer is asked whether the typed claim
CORRESPONDS to a corpus claim, in the same prompt, with the same three kinds, with `none`
legal. These controls hold that line:

  * attachment is a proposed correspondence at EXTRACTION tier — never a clamp, never
    promoted, and refused where the engine would refuse any other arrow,
  * `none` from the proposer means the field genuinely did not respond, and says so,
  * candidate ordering compares no text — it is declared degree, a property of the arrow
    graph, and what the budget does not reach is reported as unmeasured,
  * the bias is applied AT the attachment points, which is the bug that made the first
    working attachment move nothing.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.attach import ATTACH_TIER, AttachResult, Attachment, attach, candidates
from engine.constants import REPO_ROOT
from engine.corpus_state import CorpusSnapshot, SlotRecord, with_arrows
from engine.correspondence import Correspondence
from engine.extract import DeterministicExtractor
from engine.inbound import compile_input
from engine.types import Document, WarrantTier

_A = "the cone is positive under composition"
_LEAN = "theorem cone_pos : True"
#: Sentence-shaped, because the extractor addresses claims and not fragments —
#: "novel phrasing" produces no delta at all, which made three controls vacuous.
_NOVEL = "wholly novel phrasing this corpus has never carried anywhere"
_PY = "def cone_positive(x): return x"


def _corpus(rows, arrows=()) -> CorpusSnapshot:
    snap = CorpusSnapshot()
    ex = DeterministicExtractor("fixture", "test")
    ids: dict[str, str] = {}
    for i, (chart, text) in enumerate(rows):
        for d in ex.extract(Document(f"doc{i}", chart, text, "test")):
            snap.slots[d.slot] = SlotRecord(slot=d.slot, chart=chart, type=d.type, nu=d.nu,
                                            value="T", confidence=1.0, tier="EXTRACTION",
                                            docs=(f"doc{i}",))
            ids.setdefault(f"{chart}:{text}", d.slot)
    built = [Correspondence(src_chart=s.split(":", 1)[0], src_slot=ids[s],
                            dst_chart=d.split(":", 1)[0], dst_slot=ids[d], kind=k,
                            proposer="fixture", prompt_hash="t", evidence=("f",))
             for s, d, k in arrows]
    return with_arrows(snap, built) if built else snap


def _transport(answers):
    """A proposer that answers by candidate index. Records what it was shown."""
    seen = {"prompts": [], "calls": 0}

    def transport(system, user):
        import json

        seen["calls"] += 1
        seen["prompts"].append(user)
        n = user.count("SOURCE (")
        rows = [{"i": i, "kind": answers.get(i, "none"), "evidence": "fixture"}
                for i in range(n)]
        return json.dumps({"answers": rows}), {}

    transport.seen = seen
    return transport


class ABiasAttachesByProposalNotByAddress(unittest.TestCase):
    def test_planted_text_absent_from_the_corpus_still_reaches_the_field(self):
        """PLANTED: the exact input the inherited rule could never handle."""
        snap = _corpus([("english", _A), ("lean", _LEAN)],
                       arrows=[(f"english:{_A}", f"lean:{_LEAN}", "same_claim")])
        got = compile_input(_NOVEL,
                            snap, "english", transport=_transport({0: "same_claim"}))
        self.assertTrue(got.conditioned,
                        "a proposed attachment must let a novel phrase reach the field; "
                        "requiring the text to already exist is the inherited defect")
        self.assertGreater(got.reached, 0)

    def test_the_same_input_with_no_transport_cannot_attach(self):
        """The contrast that shows attachment is doing the work, not something else."""
        snap = _corpus([("english", _A), ("lean", _LEAN)],
                       arrows=[(f"english:{_A}", f"lean:{_LEAN}", "same_claim")])
        got = compile_input(_NOVEL, snap, "english")
        self.assertFalse(got.conditioned)

    def test_the_bias_is_applied_AT_the_attachment_point(self):
        """PLANTED: the bug in the first working version. Attachment succeeded, the push was
        still keyed to the typed address, that address was in no block, and nothing moved —
        a correct-looking attachment with a silent zero after it."""
        snap = _corpus([("english", _A), ("lean", _LEAN)],
                       arrows=[(f"english:{_A}", f"lean:{_LEAN}", "same_claim")])
        got = compile_input(_NOVEL, snap, "english",
                            transport=_transport({0: "same_claim"}))
        moved = {m.slot for m in got.relaxation.moved}
        seeds = got.attachment.seeds
        self.assertTrue(seeds)
        self.assertTrue(seeds & moved,
                        "the attachment point itself must move — otherwise the push was "
                        "applied to an address that is in no block")

    def test_none_everywhere_is_a_field_that_did_not_respond(self):
        snap = _corpus([("english", _A), ("lean", _LEAN)])
        got = compile_input(_NOVEL, snap, "english", transport=_transport({}))
        self.assertFalse(got.conditioned)
        self.assertIn("THE FIELD DID NOT RESPOND", got.compiled)
        self.assertIn("answered `none` to every one", got.compiled)
        self.assertIn("declines to force a match", got.compiled)
        self.assertEqual(got.facts, [])


class TheBridgeIsShownNotImplied(unittest.TestCase):
    """A relaxation standing on a proposed arrow must print the arrow."""

    def test_the_compiled_input_names_the_attachment_and_its_tier(self):
        snap = _corpus([("english", _A), ("lean", _LEAN)],
                       arrows=[(f"english:{_A}", f"lean:{_LEAN}", "same_claim")])
        got = compile_input(_NOVEL, snap, "english",
                            transport=_transport({0: "same_claim"}))
        self.assertIn("HOW THIS INPUT ATTACHED", got.compiled)
        self.assertIn("ATTACHED via same_claim", got.compiled)
        self.assertIn("EXTRACTION", got.compiled)
        self.assertIn("proposed, not confirmed", got.compiled)

    def test_declines_are_counted_so_acceptance_can_be_judged(self):
        """One acceptance out of forty-eight is a different fact from one out of one."""
        snap = _corpus([("english", _A), ("lean", _LEAN), ("python", _PY)])
        got = compile_input(_NOVEL, snap, "english",
                            transport=_transport({0: "same_claim"}))
        self.assertRegex(got.compiled, r"declined as none")
        self.assertIn("candidate(s) asked over", got.compiled)

    def test_the_record_carries_every_proposal(self):
        snap = _corpus([("english", _A), ("lean", _LEAN)])
        got = compile_input(_NOVEL, snap, "english",
                            transport=_transport({0: "same_claim"}))
        rec = got.as_record()["attachment"]
        self.assertIsNotNone(rec)
        self.assertIn("proposed", rec)
        self.assertIn("EXTRACTION", str(rec))
        self.assertIn("nothing here is promoted", rec["note"])


class AttachmentIsAnArrowUnderTheSameRules(unittest.TestCase):
    def test_it_enters_at_extraction_and_cannot_ground(self):
        self.assertEqual(ATTACH_TIER, WarrantTier.EXTRACTION)
        self.assertFalse(WarrantTier.EXTRACTION in
                         __import__("engine.types", fromlist=["TOP_TIER"]).TOP_TIER)

    def test_planted_an_intra_chart_attachment_is_refused_not_coerced(self):
        """The engine refuses intra-chart arrows; attachment must be refused with them, not
        quietly rewritten into something legal."""
        res = AttachResult(typed_chart="english")
        res.proposed.append(Attachment(kind="same_claim", dst_slot="x" * 64,
                                       dst_chart="english", dst_nu="e", evidence="v"))
        self.assertEqual(res.arrows("y" * 64), [],
                         "an intra-chart attachment must be dropped, never coerced")

    def test_candidates_are_cross_chart_and_type_compatible(self):
        snap = _corpus([("english", _A), ("lean", _LEAN), ("python", _PY)])
        got = candidates(snap, "english", "assert", limit=50)
        for _sid, rec in got:
            self.assertNotEqual(rec.chart, "english")
            self.assertEqual(rec.type, "assert")

    def test_candidate_ordering_compares_no_text(self):
        """PLANTED against selection-by-another-name: the order must be declared DEGREE.

        Word-overlap ordering is what was deleted from the read path; if it came back here it
        would be feeding the model instead of the operator, which is worse.
        """
        source = (REPO_ROOT / "engine" / "attach.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "candidates")
        body = ast.unparse(fn)
        for banned in (".lower()", "in low", "terms(", "overlap", "score"):
            self.assertNotIn(banned, body,
                             f"candidate ordering references {banned!r} — that is text "
                             f"comparison, and ordering must be structural")
        self.assertIn("degree", body)

    def test_a_higher_degree_candidate_is_offered_first(self):
        snap = _corpus([("english", _A), ("lean", _LEAN), ("python", _PY)],
                       arrows=[(f"english:{_A}", f"lean:{_LEAN}", "same_claim")])
        got = candidates(snap, "english", "assert", limit=50)
        if len(got) > 1:
            self.assertEqual(got[0][1].chart, "lean",
                             "the arrow-touched claim must come first — it is the one a "
                             "perturbation could travel from")


class WhatTheBudgetMissesIsUnmeasuredNotAbsent(unittest.TestCase):
    def test_an_exhausted_budget_says_so(self):
        rows = [("english", _A)] + [("lean", f"theorem t{i} : True") for i in range(80)]
        snap = _corpus(rows)
        got = attach(_NOVEL, snap, _transport({}), "english", call_budget=1)
        self.assertTrue(got.budget_exhausted)
        self.assertLess(got.considered, got.available)

    def test_the_compiled_input_reports_the_truncation(self):
        rows = [("english", _A)] + [("lean", f"theorem t{i} : True") for i in range(80)]
        snap = _corpus(rows)
        got = compile_input(_NOVEL, snap, "english",
                            transport=_transport({0: "same_claim"}))
        if got.attachment and got.attachment.budget_exhausted:
            self.assertIn("UNMEASURED, not ruled out", got.compiled)

    def test_a_transport_error_is_reported_not_swallowed(self):
        def boom(system, user):
            raise RuntimeError("provider said no")

        snap = _corpus([("english", _A), ("lean", _LEAN)])
        got = attach(_NOVEL, snap, boom, "english")
        self.assertIn("provider said no", got.error)
        self.assertEqual(got.seeds, set())


class TheProposerSeesTheCorpusPrompt(unittest.TestCase):
    """Attachment must be indistinguishable from a corpus proposal at the wire."""

    def test_it_uses_the_same_system_prompt(self):
        from engine.propose_correspondence import PROPOSE_SYSTEM

        seen = {}

        def capture(system, user):
            seen["system"] = system
            return '{"answers":[]}', {}

        attach(_NOVEL, _corpus([("english", _A), ("lean", _LEAN)]),
               capture, "english")
        self.assertEqual(seen["system"], PROPOSE_SYSTEM)

    def test_the_body_is_the_same_candidate_rendering(self):
        t = _transport({})
        attach(_NOVEL, _corpus([("english", _A), ("lean", _LEAN)]), t, "english")
        body = t.seen["prompts"][0]
        self.assertIn("SOURCE (english):", body)
        self.assertIn("TARGET (lean):", body)


if __name__ == "__main__":
    unittest.main()
