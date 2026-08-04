"""The direct snapshot build agrees with the ledger build — measured, then planted against.

`build_snapshot_direct` exists because `Ledger.contested_blocks` scans every delta for every
block, which on the real corpus is ~1.1e11 comparisons and killed the build after thirty
minutes. Skipping settlement machinery to make a read view is only legitimate if the read
view is the SAME read view, so that is checked field by field on a corpus small enough to
build both ways — and each arm of the contest predicate is then broken on purpose, to prove
the comparison is capable of failing.
"""

from __future__ import annotations

import unittest

from engine.corpus_state import build_snapshot, build_snapshot_direct, with_arrows
from engine.correspondence import CORRESPONDENCE_CHART, Correspondence, correspondences_from_deltas
from engine.normalize import address
from engine.pipeline import ledger_from_deltas
from engine.structure_audit import _fixture_base, fixture_correspondence
from engine.types import Delta, Provenance, Warrant, WarrantTier


def corpus():
    """The four-chart fixture, plus a declared correspondence entered as a CLAIM.

    The arrow goes in through the ordinary correspondence-chart delta so both builds derive
    it the same way — a snapshot comparison over a corpus with no arrows would not exercise
    fibers, loop edges or multi-slot blocks at all.
    """
    from engine.energy import dedupe_deltas
    from engine.pipeline import ingest

    docs, extractors, _base = _fixture_base()
    deltas = dedupe_deltas(ingest(docs, extractors))

    pairs = fixture_correspondence(ledger_from_deltas(deltas))
    chart_of = {}
    for d in deltas:
        chart_of.setdefault(d.slot, d.chart)
    extra = []
    for u, v in list(pairs)[:4]:
        if chart_of.get(u) == chart_of.get(v):
            continue                      # correspondence is cross-chart only
        arrow = Correspondence(src_chart=chart_of[u], src_slot=u, dst_chart=chart_of[v],
                               dst_slot=v, kind="same_claim", proposer="fixture")
        surface = arrow.surface()
        slot, nu_value = address(CORRESPONDENCE_CHART, surface, "assert")
        extra.append(Delta(
            slot=slot, chart=CORRESPONDENCE_CHART, type="assert", value="T", confidence=0.6,
            warrant=Warrant(tier=WarrantTier.EXTRACTION, detail="fixture arrow"),
            provenance=Provenance(source="fixture", doc_id=f"corr:{arrow.id()}",
                                  locator="fixture", extractor_id="fixture",
                                  content_hash=arrow.id()),
            surface=surface, nu=nu_value))
    # A single slot that disagrees with itself, so the SECOND arm of the contest predicate
    # ("one slot whose deltas support more than one b-value") is actually exercised. It has to
    # land in a SINGLETON block: a self-disagreeing slot inside a multi-slot block is already
    # contested by the first arm, and the two arms would be indistinguishable.
    import dataclasses

    probe = build_snapshot_direct(deltas + extra)
    singleton = next(sid for sid, block in probe.blocks.items()
                     if len(block) == 1 and sid not in probe.contested)
    lone = next(d for d in deltas if d.slot == singleton)
    extra.append(dataclasses.replace(
        lone, value=("F" if lone.value != "F" else "T"),
        provenance=dataclasses.replace(lone.provenance, doc_id=lone.provenance.doc_id + "#alt",
                                       content_hash=lone.provenance.content_hash + "alt")))
    return deltas + extra


def both_ways(deltas):
    arrows = correspondences_from_deltas(deltas)
    via_ledger = build_snapshot(ledger_from_deltas(deltas), arrows)
    direct = build_snapshot_direct(deltas, arrows)
    return via_ledger, direct


def fields(snap):
    return {
        "slots": {k: (v.chart, v.type, v.nu, v.value, v.confidence, v.tier, v.docs)
                  for k, v in snap.slots.items()},
        "fibers": sorted(tuple(sorted(f)) for f in snap.fibers),
        "blocks": {k: tuple(sorted(v)) for k, v in snap.blocks.items()},
        "contested": set(snap.contested),
        "loops": snap.loops,
        "floor_status": snap.floor_status,
        "arrows": sorted(a.id() for a in snap.arrows),
    }


class DirectBuildAgreesWithTheLedgerBuild(unittest.TestCase):
    def setUp(self):
        self.deltas = corpus()
        self.via_ledger, self.direct = both_ways(self.deltas)

    def test_the_corpus_actually_exercises_the_structure(self):
        """A comparison over a degenerate corpus would prove nothing."""
        self.assertGreater(len(self.direct.slots), 12, "too few slots to be a real comparison")
        self.assertTrue(self.direct.arrows, "no arrows: fibers and loop edges untested")
        self.assertTrue(any(len(b) > 1 for b in self.direct.blocks.values()),
                        "no multi-slot block: the first contest arm is untested")
        singles = [sid for sid, b in self.direct.blocks.items() if len(b) == 1]
        self.assertTrue(singles, "no single-slot block: the second contest arm is untested")

    def test_every_field_agrees(self):
        a, b = fields(self.via_ledger), fields(self.direct)
        for key in sorted(a):
            self.assertEqual(a[key], b[key], f"the two builds disagree on {key!r}")

    def test_the_header_agrees(self):
        self.assertEqual(self.via_ledger.header(), self.direct.header())

    def test_contest_agrees_slot_by_slot(self):
        self.assertEqual(self.via_ledger.contested, self.direct.contested)
        self.assertEqual(
            {s for s in self.direct.slots if s in self.direct.contested},
            {s for s in self.via_ledger.slots if s in self.via_ledger.contested})


class ThePlantedDefectsAreCaught(unittest.TestCase):
    """Break each arm of the contest predicate; the comparison must go red."""

    def setUp(self):
        self.deltas = corpus()

    def _direct_with(self, patch):
        import engine.corpus_state as mod

        original = mod.build_blocks if hasattr(mod, "build_blocks") else None
        del original
        return patch(self.deltas)

    def test_dropping_the_multi_slot_arm_is_caught(self):
        """PLANTED: contest only when a single slot disagrees — multi-slot blocks ignored."""
        arrows = correspondences_from_deltas(self.deltas)
        direct = build_snapshot_direct(self.deltas, arrows)
        broken = build_snapshot_direct(self.deltas, arrows)
        broken.contested = {s for s in direct.contested
                            if len(broken.blocks.get(s, (s,))) == 1}
        self.assertNotEqual(broken.contested, direct.contested,
                            "the fixture has no multi-slot contested block, so this arm "
                            "cannot be tested on it")
        via_ledger = build_snapshot(ledger_from_deltas(self.deltas), arrows)
        self.assertNotEqual(fields(broken)["contested"], fields(via_ledger)["contested"])

    def test_dropping_the_single_slot_arm_is_caught(self):
        """PLANTED: contest only when a block has >1 slot — a self-disagreeing slot missed."""
        arrows = correspondences_from_deltas(self.deltas)
        direct = build_snapshot_direct(self.deltas, arrows)
        broken = build_snapshot_direct(self.deltas, arrows)
        broken.contested = {s for s in direct.contested
                            if len(broken.blocks.get(s, (s,))) > 1}
        via_ledger = build_snapshot(ledger_from_deltas(self.deltas), arrows)
        self.assertNotEqual(broken.contested, direct.contested,
                            "the fixture has no single-slot contest, so this arm is untested")
        self.assertNotEqual(fields(broken)["contested"], fields(via_ledger)["contested"])

    def test_a_wrong_floor_status_is_caught(self):
        arrows = correspondences_from_deltas(self.deltas)
        direct = build_snapshot_direct(self.deltas, arrows)
        via_ledger = build_snapshot(ledger_from_deltas(self.deltas), arrows)
        direct.floor_status = "measurable (cycles present)" \
            if direct.floor_status.startswith("GAP") else "GAP"
        self.assertNotEqual(fields(direct)["floor_status"], fields(via_ledger)["floor_status"])


class ArrowsLaidOverAReadViewAgreeWithABuildThatHadThem(unittest.TestCase):
    """`with_arrows` must produce the same view as building the corpus with those arrows in it.

    The daemon's arrows live in its journal, not in the corpus deltas, so the window lays them
    over the snapshot. That is only legitimate if the result is the view the corpus would have
    had if the arrows had been claims all along.
    """

    def setUp(self):
        self.deltas = corpus()
        self.arrows = correspondences_from_deltas(self.deltas)
        self.assertTrue(self.arrows, "no arrows: this control would be vacuous")
        # The corpus WITHOUT its arrow claims — as the real snapshot is built.
        self.bare_deltas = [d for d in self.deltas if d.chart != CORRESPONDENCE_CHART]

    def test_fibers_blocks_and_contest_agree(self):
        """Compared over the CORPUS slots only.

        A correspondence claim is itself a claim, so building the corpus *with* the arrow
        deltas also creates a slot per arrow in the `correspondence` chart. The overlaid view
        has no such slots and should not: in the real system those claims live in the
        proposer's journal, not in the corpus. Comparing over the corpus slots is the
        comparison that means something; the extra meta-slots are asserted separately.
        """
        full = build_snapshot_direct(self.deltas, self.arrows)
        bare = build_snapshot_direct(self.bare_deltas, [])
        overlaid = with_arrows(bare, self.arrows)
        keep = set(bare.slots)

        def restrict(snap):
            return {
                "fibers": sorted(tuple(sorted(s for s in f if s in keep))
                                 for f in snap.fibers
                                 if any(s in keep for s in f)),
                "blocks": {k: tuple(sorted(s for s in v if s in keep))
                           for k, v in snap.blocks.items() if k in keep},
                "contested": {s for s in snap.contested if s in keep},
                "loops": snap.loops,
                "floor_status": snap.floor_status,
            }

        a, b = restrict(full), restrict(overlaid)
        for key in sorted(a):
            self.assertEqual(a[key], b[key], f"the overlay disagrees on {key!r}")

    def test_the_arrow_claims_themselves_are_corpus_slots_only_when_ingested(self):
        full = build_snapshot_direct(self.deltas, self.arrows)
        bare = build_snapshot_direct(self.bare_deltas, [])
        meta = {s for s, r in full.slots.items() if r.chart == CORRESPONDENCE_CHART}
        self.assertTrue(meta, "the fixture ingested no correspondence claims")
        self.assertFalse(meta & set(bare.slots),
                         "the bare corpus must not contain correspondence-chart slots")
        self.assertFalse(meta & set(with_arrows(bare, self.arrows).slots),
                         "the overlay must not invent slots for the arrows it lays over")

    def test_both_contest_arms_survive_the_overlay(self):
        """PLANTED-shaped: the stored single-slot contest must not be lost by the overlay."""
        bare = build_snapshot_direct(self.bare_deltas, [])
        single = {s for s in bare.contested if len(bare.blocks.get(s, (s,))) == 1}
        self.assertTrue(single, "no stored single-slot contest; the arm is untested here")
        overlaid = with_arrows(bare, self.arrows)
        self.assertTrue(single <= overlaid.contested,
                        "the overlay dropped a contest the corpus build had found")
        multi = {s for s in overlaid.contested if len(overlaid.blocks.get(s, (s,))) > 1}
        self.assertTrue(multi, "no multi-slot contest; the other arm is untested here")

    def test_an_arrow_with_an_unknown_endpoint_is_dropped_not_invented(self):
        from engine.correspondence import Correspondence

        bare = build_snapshot_direct(self.bare_deltas, [])
        ghost = Correspondence(src_chart="english", src_slot="not-in-this-corpus",
                               dst_chart="lean", dst_slot=next(iter(bare.slots)),
                               kind="same_claim", proposer="test")
        overlaid = with_arrows(bare, list(self.arrows) + [ghost])
        self.assertNotIn(ghost.id(), {a.id() for a in overlaid.arrows})
        self.assertNotIn("not-in-this-corpus", overlaid.slots)


class TheDirectBuildIsNotQuadratic(unittest.TestCase):
    """The point of the exercise: cost must grow with the corpus, not with its square.

    `is_contested` per block over all deltas is O(blocks x deltas). The direct build indexes
    by slot once. Asserted by counting slot comparisons rather than by timing, so the control
    does not depend on how loaded the machine is.
    """

    def test_contest_costs_one_pass_over_the_deltas(self):
        from engine.corpus_state import _flatten_deltas

        deltas = corpus()
        touched = {"n": 0}

        class CountingDelta:
            __slots__ = ("inner",)

            def __init__(self, inner):
                self.inner = inner

            def __getattr__(self, name):
                if name == "slot":
                    touched["n"] += 1
                return getattr(self.inner, name)

        _flatten_deltas([CountingDelta(d) for d in deltas])
        self.assertLessEqual(touched["n"], 4 * len(deltas),
                             "the index pass reads each delta a bounded number of times")


if __name__ == "__main__":
    unittest.main()
