"""Region relaxation, and the one place it rots.

The unit of extraction moved from the pair to the region: one settling, every correspondence
the medium sees in it. That is a large efficiency change and it buys a large new risk —
"name everything you see" gives far more room to force a match than "does A correspond to B?"
did. So these controls hold two lines:

  * **RESOLVE-OR-VOID.** The medium answers only in indices. It never emits a name, a surface
    or an id, so there is nothing for a fuzzy match to attach to. Anything that is not a
    resolvable index is VOID with a stated reason — planted against with a quoted surface,
    an out-of-range index, a float, a bool, a self-pair and an intra-chart pair.
  * **SILENCE IS NOT `none`.** A pair the medium did not mention was never put to it. Counting
    those as declines would manufacture refusals nobody made — in a 60-claim region that is
    1,770 pairs of fabricated evidence per call.
"""

from __future__ import annotations

import json
import unittest

from engine.corpus_state import CorpusSnapshot, SlotRecord, with_arrows
from engine.correspondence import Correspondence
from engine.extract import DeterministicExtractor
from engine.region import (
    NU_CAP,
    REGION_SYSTEM,
    Member,
    Region,
    arrows_from,
    build_region,
    parse_region,
    render_region,
    residuals,
)
from engine.types import Document, WarrantTier


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
    snap = with_arrows(snap, built) if built else snap
    snap_ids = ids
    return snap, snap_ids


def _region(members) -> Region:
    return Region(members=[Member(index=i, slot=f"{i:064d}", chart=c, type="assert",
                                  nu=f"\x01{c}\x01claim {i}", attached=False)
                           for i, c in enumerate(members)])


def _reply(pairs) -> str:
    return json.dumps({"pairs": pairs})


class ResolveOrVoid(unittest.TestCase):
    """Every proposal resolves to an exact address or is discarded with a reason."""

    def setUp(self):
        self.region = _region(["english", "lean", "python", "english"])

    def test_a_valid_cross_chart_pair_resolves(self):
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "same_claim", "evidence": "e"}]),
                           self.region)
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0].ok)
        self.assertEqual(got[0].src.slot, self.region.members[0].slot)
        self.assertEqual(got[0].dst.slot, self.region.members[1].slot)

    def test_planted_a_quoted_surface_where_an_index_belongs_is_void(self):
        """THE failure this guards against. A model that emits text invites someone to match
        it, and matching is the thing that was deleted twice."""
        got = parse_region(
            _reply([{"i": "the cone is positive", "j": 1, "kind": "same_claim"}]), self.region)
        self.assertFalse(got[0].ok)
        self.assertIn("not an integer", got[0].void)

    def test_planted_an_index_outside_the_region_is_void(self):
        for bad in (99, -1, 4):
            got = parse_region(_reply([{"i": 0, "j": bad, "kind": "same_claim"}]), self.region)
            self.assertFalse(got[0].ok, f"index {bad} resolved and must not have")

    def test_planted_a_float_or_bool_index_is_void(self):
        for bad in (1.0, True, None, [1]):
            got = parse_region(_reply([{"i": bad, "j": 1, "kind": "same_claim"}]), self.region)
            self.assertFalse(got[0].ok, f"{bad!r} resolved as an index")

    def test_planted_a_self_pair_is_void(self):
        got = parse_region(_reply([{"i": 2, "j": 2, "kind": "same_claim"}]), self.region)
        self.assertFalse(got[0].ok)
        self.assertIn("i == j", got[0].void)

    def test_planted_an_intra_chart_pair_is_void(self):
        """Indices 0 and 3 are both english. Exact addressing owns intra-chart identity."""
        got = parse_region(_reply([{"i": 0, "j": 3, "kind": "same_claim"}]), self.region)
        self.assertFalse(got[0].ok)
        self.assertIn("intra-chart", got[0].void)

    def test_planted_an_unknown_kind_is_void(self):
        for bad in ("approximates", "related", "", "none"):
            got = parse_region(_reply([{"i": 0, "j": 1, "kind": bad}]), self.region)
            self.assertFalse(got[0].ok, f"kind {bad!r} was accepted")

    def test_void_proposals_never_become_arrows(self):
        got = parse_region(_reply([
            {"i": 0, "j": 1, "kind": "same_claim", "evidence": "good"},
            {"i": 0, "j": 3, "kind": "same_claim", "evidence": "intra-chart"},
            {"i": "text", "j": 1, "kind": "same_claim", "evidence": "quoted"},
        ]), self.region)
        self.assertEqual(len(arrows_from(got)), 1)

    def test_arrows_enter_at_extraction_tier(self):
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "same_claim"}]), self.region)
        for arrow in arrows_from(got):
            self.assertEqual(arrow.tier, WarrantTier.EXTRACTION)

    def test_a_reply_that_is_not_json_at_all_yields_nothing_rather_than_crashing(self):
        self.assertEqual(parse_region("the model wrote prose instead", self.region), [])


class SilenceIsNotADecline(unittest.TestCase):
    """In the pairwise loop `none` was an answer. Here it would be a fabrication."""

    def test_unmentioned_pairs_are_counted_separately_from_declines(self):
        region = _region(["english", "lean", "python", "go"])
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "same_claim"}]), region)
        res = residuals(got, region)
        self.assertEqual(res.mentioned_pairs, 1)
        self.assertEqual(res.unmentioned_pairs, 5, "4 claims -> 6 pairs, 1 mentioned")
        self.assertIn("NOT a `none`", res.as_record()["note"])

    def test_the_record_never_reports_a_none_count(self):
        region = _region(["english", "lean"])
        rec = residuals(parse_region(_reply([]), region), region).as_record()
        self.assertNotIn("none", [k.lower() for k in rec])
        self.assertEqual(rec["mentioned_pairs"], 0)


class TheResidualRuleRecordsBothDirections(unittest.TestCase):
    def test_named_but_not_implied_becomes_a_candidate(self):
        region = _region(["english", "lean"])
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "refines"}]), region)
        res = residuals(got, region)
        self.assertEqual(len(res.named_not_implied), 1)
        self.assertEqual(res.named_and_implied, 0)

    def test_named_and_already_implied_is_not_a_new_candidate(self):
        region = _region(["english", "lean"])
        region.implied = {(region.members[0].slot, region.members[1].slot)}
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "same_claim"}]), region)
        res = residuals(got, region)
        self.assertEqual(res.named_not_implied, [])
        self.assertEqual(res.named_and_implied, 1)

    def test_planted_implied_but_not_named_is_flagged(self):
        """Declared structure the medium does not see is worth knowing — it is either a bad
        arrow already in the corpus or a blind spot in the medium, and both are findings."""
        region = _region(["english", "lean"])
        region.implied = {(region.members[0].slot, region.members[1].slot)}
        res = residuals(parse_region(_reply([]), region), region)
        self.assertEqual(len(res.implied_not_named), 1)


class RegionAssemblyIsStructural(unittest.TestCase):
    def test_the_clamp_and_its_declared_neighbours_come_first(self):
        snap, ids = _corpus([("english", "the cone is positive under composition"),
                             ("lean", "theorem cone_pos : True"),
                             ("python", "def unrelated(): pass")],
                            arrows=[("english:the cone is positive under composition",
                                     "lean:theorem cone_pos : True", "same_claim")])
        clamp = ids["english:the cone is positive under composition"]
        region = build_region(snap, clamp=clamp, size=3)
        self.assertEqual(region.members[0].slot, clamp)
        self.assertIn(ids["lean:theorem cone_pos : True"],
                      {m.slot for m in region.members[:2]},
                      "a declared neighbour must be shown, or the medium re-names it and the "
                      "call buys something already recorded")

    def test_already_declared_pairs_are_carried_as_implied(self):
        snap, ids = _corpus([("english", "the cone is positive under composition"),
                             ("lean", "theorem cone_pos : True")],
                            arrows=[("english:the cone is positive under composition",
                                     "lean:theorem cone_pos : True", "same_claim")])
        region = build_region(snap, clamp=ids["english:the cone is positive under composition"])
        self.assertEqual(len(region.implied), 1)

    def test_indices_are_dense_and_match_the_rendering(self):
        snap, _ = _corpus([("english", "a claim about cones here"),
                           ("lean", "theorem t : True")])
        region = build_region(snap, size=8)
        self.assertEqual([m.index for m in region.members], list(range(len(region.members))))
        body = render_region(region)
        for m in region.members:
            self.assertIn(f"[{m.index}] ({m.chart}/{m.type})", body)

    def test_the_rendering_marks_where_it_cut(self):
        region = Region(members=[Member(index=0, slot="s" * 64, chart="english",
                                        type="assert", nu="\x01en\x01" + "x" * (NU_CAP + 50),
                                        attached=False)])
        self.assertIn("…[cut]", render_region(region))

    def test_the_rendering_carries_no_slot_ids(self):
        """The medium must not be handed an address; it answers in indices only."""
        snap, _ = _corpus([("english", "a claim about cones here"),
                           ("lean", "theorem t : True")])
        region = build_region(snap, size=8)
        body = render_region(region)
        for m in region.members:
            self.assertNotIn(m.slot, body)


class ThePromptForbidsForcingMatches(unittest.TestCase):
    """"Name everything you see" gives far more room to force a match than the pairwise
    question did. The prompt has to push back explicitly, or acceptance is noise."""

    def test_it_says_naming_nothing_is_legal(self):
        self.assertIn("Naming nothing is a legal", REGION_SYSTEM)

    def test_it_rejects_word_overlap_and_negation(self):
        self.assertIn("word overlap is NOT a correspondence", REGION_SYSTEM)
        self.assertIn("negation", REGION_SYSTEM)

    def test_it_demands_indices_and_says_text_is_discarded(self):
        self.assertIn("Answer ONLY with indices", REGION_SYSTEM)
        self.assertIn("discarded", REGION_SYSTEM)

    def test_it_states_the_cross_chart_rule(self):
        self.assertIn("CROSS-CHART only", REGION_SYSTEM)

    def test_it_measures_precision_not_yield(self):
        self.assertIn("precision, not on yield", REGION_SYSTEM)


if __name__ == "__main__":
    unittest.main()
