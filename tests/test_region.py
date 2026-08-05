"""Region query, and the one place it rots.

The unit of extraction moved from the pair to the region: one call, every arrow
the medium names in it. That is a large efficiency change and it buys a large new risk —
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
        for d in ex.extract(Document(f"repo||dir/f{i}", chart, text, "test")):
            snap.slots[d.slot] = SlotRecord(slot=d.slot, chart=chart, type=d.type, nu=d.nu,
                                            value="T", confidence=1.0, tier="EXTRACTION",
                                            docs=(f"repo||dir/f{i}",))
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
    """The wire format on the way back: `i -kind-> j` lines and nothing else."""
    return "\n".join(f"{p['i']} -{p.get('kind','same_claim')}-> {p['j']}" for p in pairs)


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
        got = parse_region("the cone is positive -same_claim-> 1", self.region)
        self.assertEqual(got, [], "a surface where an index belongs matches no arrow line at "
                                  "all — there is nothing in the format for it to be")

    def test_planted_an_index_outside_the_region_is_void(self):
        for bad in (99, -1, 4):
            got = parse_region(_reply([{"i": 0, "j": bad, "kind": "same_claim"}]), self.region)
            self.assertFalse(got[0].ok, f"index {bad} resolved and must not have")

    def test_planted_non_integer_indices_have_no_representation_at_all(self):
        """The format admits integers. A float, a name or a quoted claim is not an index and
        is not an arrow line, so it cannot even be uttered."""
        for bad in ("1.0 -same_claim-> 2", "foo -same_claim-> 2", "[1] -same_claim-> 2"):
            self.assertEqual([p for p in parse_region(bad, self.region) if p.ok], [],
                             f"{bad!r} produced an arrow")

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
            got = [p for p in parse_region(_reply([{"i": 0, "j": 1, "kind": bad}]),
                                           self.region) if p.ok]
            self.assertEqual(got, [], f"kind {bad!r} was accepted")

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


class TheOutputGrammarIsTheTrustedBase(unittest.TestCase):
    """ITEM 3. The strictness of this parse is the kernel of the whole LM interaction.

    Only `(i, kind, j)` lines are read. Everything else is silently UNPARSED — never
    interpreted, never tolerantly recovered, no machine-read rationale, and above all no
    self-reported confidence: warrant is assigned at ingestion and is never proposed by the
    thing being warranted.
    """

    def test_planted_prose_plus_one_valid_triple_yields_exactly_one_arrow(self):
        reply = (
            "Looking carefully at this region, I can see several relationships.\n"
            "First, claim 0 seems quite similar to claim 1 in spirit.\n"
            "0 -same_claim-> 1\n"
            "I am about 85% confident in this. Other pairs may also relate but I am unsure.\n"
            '{"pairs": [{"i": 0, "j": 2, "kind": "refines"}]}\n'
            "Let me know if you would like me to reconsider."
        )
        region = _region(["english", "lean", "python"])
        got = [p for p in parse_region(reply, region) if p.ok]
        self.assertEqual(len(got), 1, "prose, a confidence claim and a JSON block must all be "
                                      "unparsed; exactly the one arrow LINE is read")
        self.assertEqual((got[0].src.index, got[0].kind, got[0].dst.index), (0, "same_claim", 1))

    def test_no_self_reported_confidence_can_enter(self):
        """Warrant is assigned at ingestion, never proposed. There is no field for it."""
        region = _region(["english", "lean"])
        got = parse_region('0 -same_claim-> 1 (confidence: 0.97)', region)
        self.assertTrue(got[0].ok)
        for attr in ("confidence", "score", "certainty"):
            self.assertFalse(hasattr(got[0], attr), f"a proposal carries no {attr}")

    def test_a_rationale_is_never_machine_read(self):
        from engine.region import Proposal

        self.assertNotIn("rationale", Proposal.__slots__)
        self.assertNotIn("reasoning", Proposal.__slots__)

    def test_the_wire_carries_the_bytes_the_hash_was_computed_over(self):
        """ITEM 2: no re-wrapping, no whitespace normalization; escaping is invertible."""
        from engine.region import escape_nu, render_region, unescape_nu

        nu = "\x01en\x01a claim with\na newline and a \\ backslash"
        region = Region(members=[Member(index=0, slot="s" * 64, chart="english",
                                        type="assert", nu=nu, attached=False)])
        body = render_region(region)
        self.assertNotIn("\n" + "a newline", body, "the nu must not break the line format")
        line = [l for l in body.splitlines() if l.startswith("[0|")][0]
        self.assertEqual(unescape_nu(line.split("] ", 1)[1]), nu,
                         "inversion must reproduce the hashed bytes exactly")

    def test_planted_index_order_carries_no_signal(self):
        """ITEM 1: any systematic order leaks an undeclared ranking into an attention-salient
        position. The permutation is content-derived, so it is reproducible and uninformative."""
        from engine.region import _shuffle

        slots = [f"{i:064d}" for i in range(40)]
        once, twice = _shuffle(slots), _shuffle(list(reversed(slots)))
        self.assertEqual(once, twice, "the shuffle must depend on the SET, not on input order")
        self.assertNotEqual(once, slots, "an unshuffled order is a ranking signal")


class SilenceIsNotADecline(unittest.TestCase):
    """In the pairwise loop `none` was an answer. Here it would be a fabrication."""

    def test_unmentioned_pairs_are_counted_separately_from_declines(self):
        region = _region(["english", "lean", "python", "go"])
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "same_claim"}]), region)
        res = residuals(got, region)
        self.assertEqual(res.named_pairs, 1)
        self.assertEqual(res.unmeasured_pairs, 5, "4 claims -> 6 pairs, 1 named")
        self.assertIn("NOT a `none`", res.as_record()["note"])

    def test_the_record_never_reports_a_none_count(self):
        region = _region(["english", "lean"])
        rec = residuals(parse_region(_reply([]), region), region).as_record()
        self.assertNotIn("none", [k.lower() for k in rec])
        self.assertEqual(rec["named_pairs"], 0)


class TheResidualRuleRecordsBothDirections(unittest.TestCase):
    def test_named_but_not_implied_becomes_a_candidate(self):
        region = _region(["english", "lean"])
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "refines"}]), region)
        res = residuals(got, region)
        self.assertEqual(len(res.novel), 1)
        self.assertEqual(len(res.confirmed_implied), 0)

    def test_named_and_already_implied_is_not_a_new_candidate(self):
        region = _region(["english", "lean"])
        region.implied = {(region.members[0].slot, region.members[1].slot): "same_claim"}
        got = parse_region(_reply([{"i": 0, "j": 1, "kind": "same_claim"}]), region)
        res = residuals(got, region)
        self.assertEqual(res.novel, [])
        self.assertEqual(len(res.confirmed_implied), 1)

    def test_planted_implied_but_not_named_is_flagged(self):
        """Declared structure the medium does not see is worth knowing — it is either a bad
        arrow already in the corpus or a blind spot in the medium, and both are findings."""
        region = _region(["english", "lean"])
        region.implied = {(region.members[0].slot, region.members[1].slot): "same_claim"}
        res = residuals(parse_region(_reply([]), region), region)
        self.assertEqual(len(res.residual), 1)


class RegionAssemblyIsStructural(unittest.TestCase):
    def test_the_clamp_and_its_declared_neighbours_come_first(self):
        snap, ids = _corpus([("english", "the cone is positive under composition"),
                             ("lean", "theorem cone_pos : True"),
                             ("python", "def unrelated(): pass")],
                            arrows=[("english:the cone is positive under composition",
                                     "lean:theorem cone_pos : True", "same_claim")])
        clamp = ids["english:the cone is positive under composition"]
        region = build_region(snap, clamp=clamp, size=3)
        # The clamp is SELECTED first but no longer rendered first: item 1 shuffles the index
        # order so position carries no signal. Membership is the property under test.
        self.assertIn(clamp, {m.slot for m in region.members})
        self.assertIn(ids["lean:theorem cone_pos : True"],
                      {m.slot for m in region.members},
                      "a declared neighbour must be shown, or the medium re-names it and the "
                      "call buys something already recorded")

    def test_already_declared_pairs_are_carried_as_implied(self):
        snap, ids = _corpus([("english", "the cone is positive under composition"),
                             ("lean", "theorem cone_pos : True")],
                            arrows=[("english:the cone is positive under composition",
                                     "lean:theorem cone_pos : True", "same_claim")])
        region = build_region(snap, clamp=ids["english:the cone is positive under composition"])
        self.assertEqual(len(region.declared), 1)

    def test_the_wire_carries_all_three_sections(self):
        """A partial diagram is only well-posed if the partial diagram is given."""
        snap, ids = _corpus([("english", "the cone is positive under composition"),
                             ("lean", "theorem cone_pos : True")],
                            arrows=[("english:the cone is positive under composition",
                                     "lean:theorem cone_pos : True", "same_claim")])
        body = render_region(build_region(snap, size=8))
        for section in ("OBJECTS", "ARROWS (declared)", "ARROWS (implied by composition)"):
            self.assertIn(section, body)
        self.assertIn("-same_claim->", body, "declared arrows must GO IN, or the medium "
                                             "re-derives known structure and the residual "
                                             "measurement is destroyed")

    def test_the_task_line_states_unmeasured_is_not_denied(self):
        from engine.region import TASK_LINE
        self.assertIn("UNMEASURED, not denied", TASK_LINE)
        self.assertIn("Do not introduce new objects", TASK_LINE)
        self.assertIn(TASK_LINE, render_region(_region(["english", "lean"])))

    def test_the_object_line_carries_the_chart_because_it_is_the_base_object(self):
        body = render_region(_region(["english", "lean"]))
        self.assertIn("[0|english]", body)
        self.assertIn("[1|lean]", body)

    def test_indices_are_dense_and_match_the_rendering(self):
        snap, _ = _corpus([("english", "a claim about cones here"),
                           ("lean", "theorem t : True")])
        region = build_region(snap, size=8)
        self.assertEqual([m.index for m in region.members], list(range(len(region.members))))
        body = render_region(region)
        for m in region.members:
            self.assertIn(f"[{m.index}|{m.chart}]", body)

    def test_the_rendering_never_cuts_because_byte_exact_forbids_it(self):
        """Truncation and byte-exactness cannot both hold, and byte-exactness wins.

        The nu-string IS the address span — gate 8 already chose the truncation when the
        claim was addressed. Cutting it again on the wire would present the medium with a
        string the engine does not hold, hashing to a different address. So the earlier
        `…[cut]` marker is gone and the exact bytes go over.
        """
        from engine.region import unescape_nu

        nu = "\x01en\x01" + "x" * (NU_CAP + 50)
        region = Region(members=[Member(index=0, slot="s" * 64, chart="english",
                                        type="assert", nu=nu, attached=False)])
        body = render_region(region)
        self.assertNotIn("[cut]", body)
        line = [l for l in body.splitlines() if l.startswith("[0|")][0]
        self.assertEqual(unescape_nu(line.split("] ", 1)[1]), nu)

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
        self.assertIn("Naming nothing is a legal completion", REGION_SYSTEM)

    def test_it_rejects_word_overlap(self):
        self.assertIn("word overlap", REGION_SYSTEM)

    def test_it_admits_only_arrow_lines(self):
        self.assertIn("i -kind-> j", REGION_SYSTEM)
        self.assertIn("no claim text, no names", REGION_SYSTEM)

    def test_it_states_the_cross_chart_rule(self):
        self.assertIn("CROSS-CHART only", REGION_SYSTEM)

    def test_it_forbids_introducing_objects(self):
        self.assertIn("Do not introduce new objects", REGION_SYSTEM)

    def test_it_says_unnamed_is_unmeasured_not_denied(self):
        self.assertIn("UNMEASURED, not denied", REGION_SYSTEM)

    def test_no_physics_vocabulary_is_applied_to_the_model(self):
        """The LM is QUERIED over a region. Relaxation is a motivating picture, and the wire
        format is justified by diagram-completion — borrowed physics is how a picture hardens
        into a claimed mechanism, which gate 10 now catches."""
        low = REGION_SYSTEM.lower()
        for word in ("relax", "settl", "equilibr"):
            self.assertNotIn(word, low)


if __name__ == "__main__":
    unittest.main()
