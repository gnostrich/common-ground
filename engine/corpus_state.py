"""The persisted corpus: build once, load on startup, never rebuild in the window.

The window used to run an empty in-memory current, so it answered against nothing and said
"corpus size 0". This is the checkpoint it loads instead: the settled material, its declared
correspondence arrows, its fibers, and — stated explicitly — the floor's status.

The snapshot deliberately carries the FLOOR STATUS as a field rather than a number. The floor
is a GAP (undefined because unmeasured) whenever no cycle exists, and a window that printed
`floor: 0.0` would be reporting agreement where there is only absence.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .correspondence import Correspondence

#: Where the window looks for its read view.
SNAPSHOT_PATH = "runs/corpus.snapshot"

FLOOR_GAP = "GAP — undefined because unmeasured (no cycle in the correspondence graph)"


@dataclass(slots=True)
class SlotRecord:
    """One addressed claim, flattened for load-time use."""
    slot: str
    chart: str
    type: str
    nu: str
    value: str
    confidence: float
    tier: str
    docs: tuple[str, ...]


@dataclass(slots=True)
class CorpusSnapshot:
    """What the window loads. Counts, slots, arrows, fibers, and the floor's STATUS."""

    slots: dict[str, SlotRecord] = field(default_factory=dict)
    arrows: list[Correspondence] = field(default_factory=list)
    fibers: list[tuple[str, ...]] = field(default_factory=list)
    blocks: dict[str, tuple[str, ...]] = field(default_factory=dict)   # slot -> block members
    contested: set[str] = field(default_factory=set)                   # contested slot ids
    floor_status: str = FLOOR_GAP
    loops: int = 0
    sources: dict[str, int] = field(default_factory=dict)              # corpus -> slot count

    @property
    def empty(self) -> bool:
        return not self.slots

    def header(self) -> dict[str, object]:
        """What the window must display so a loaded state is never mistaken for an empty one."""
        by_chart: dict[str, int] = {}
        for r in self.slots.values():
            by_chart[r.chart] = by_chart.get(r.chart, 0) + 1
        return {
            "loaded": not self.empty,
            "slots": len(self.slots),
            "by_chart": by_chart,
            "arrows": len(self.arrows),
            "same_claim": sum(1 for a in self.arrows if a.loop_eligible),
            "fibers": len(self.fibers),
            "contested_slots": len(self.contested),
            "loops": self.loops,
            "floor": self.floor_status,
            "sources": dict(self.sources),
        }

    def save(self, path: str | Path) -> None:
        with Path(path).open("wb") as fh:
            pickle.dump(self, fh, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(path: str | Path) -> "CorpusSnapshot":
        p = Path(path)
        if not p.exists():
            return CorpusSnapshot()
        with p.open("rb") as fh:
            return pickle.load(fh)


def source_bucket(doc_id: str) -> str:
    """Which corpus a document came from. Buckets, not paths.

    A doc_id is either `<repo>||<path>` (a GitHub checkout, or `claude||<uuid>:<i>` for the
    export) or a bare Lean-corpus path. Keying the header by raw doc_id produced thousands
    of entries — one per Aristotle file — which is a listing of the corpus, not a summary of
    it, and is exactly the thing that must not end up on screen or in a commit.
    """
    repo, sep, _rest = doc_id.partition("||")
    if sep:
        return "claude_export" if repo == "claude" else f"github/{repo}"
    if doc_id.startswith("lean:acct") or "_aristotle/" in doc_id:
        return "aristotle_lean"
    return "other"


def source_counts(snapshot_or_deltas) -> dict[str, int]:
    """Slots per source bucket. Accepts a snapshot or a delta sequence."""
    out: dict[str, int] = {}
    slots = getattr(snapshot_or_deltas, "slots", None)
    if isinstance(slots, dict):
        for rec in slots.values():
            key = source_bucket(rec.docs[0]) if rec.docs else "other"
            out[key] = out.get(key, 0) + 1
        return out
    seen: set[str] = set()
    for d in snapshot_or_deltas:
        if d.slot in seen:
            continue
        seen.add(d.slot)
        key = source_bucket(d.provenance.doc_id)
        out[key] = out.get(key, 0) + 1
    return out


def _flatten_deltas(deltas):
    """One pass over the deltas: votes, tier, docs and the value SET, per slot.

    The value set is what the contest predicate needs, and gathering it here is the whole
    reason the direct build is not quadratic — see `build_snapshot_direct`.
    """
    from collections import Counter

    votes: dict[str, Counter] = {}
    tiers: dict[str, str] = {}
    docs: dict[str, set[str]] = {}
    values: dict[str, set[str]] = {}
    for d in deltas:
        votes.setdefault(d.slot, Counter())[d.value] += d.confidence
        tiers.setdefault(d.slot, d.warrant.tier.name)
        docs.setdefault(d.slot, set()).add(d.provenance.doc_id)
        values.setdefault(d.slot, set()).add(d.value)
    return votes, tiers, docs, values


def build_snapshot_direct(deltas, arrows: Sequence[Correspondence] | None = None,
                          sources: dict[str, int] | None = None) -> CorpusSnapshot:
    """The read view, built from deltas WITHOUT going through `ledger_from_deltas`.

    The window needs slots, fibers, blocks, contest status and the floor's status. It does
    not need evidence vectors, lexicon priors or a settled distribution: those are
    *settlement* machinery, and settlement is not what a read view does.

    The reason this exists is a measured one rather than an aesthetic one. `Ledger.
    contested_blocks` is `[b for b in blocks if is_contested(b, deltas)]`, and `is_contested`
    scans **every delta for every block**. On the real corpus that is 183,135 blocks against
    620,503 deltas — about 1.1e11 slot comparisons — and the snapshot build was killed after
    thirty minutes in exactly that call. The predicate itself is cheap; only its access
    pattern was expensive. Here the deltas are indexed by slot once and the identical
    predicate is evaluated against that index.

    **The equivalence is asserted, not asserted-in-prose**: `tests/test_corpus_state.py:
    DirectBuildAgreesWithTheLedgerBuild` builds the same corpus both ways and compares every
    field, and plants a defect in each of the two contest arms to prove the comparison can
    fail.
    """
    from .blocks import build_blocks, build_fibers, loop_edges, loops_from_fibers, structural_edges
    from .correspondence import correspondences_from_deltas, loop_pairs
    from .extract import slots_from_deltas

    deltas = list(deltas)
    slots = slots_from_deltas(deltas)
    arrow_list = list(arrows) if arrows is not None else correspondences_from_deltas(deltas)

    fibers = build_fibers(slots, loop_pairs(arrow_list))
    edges = loop_edges(slots, arrow_list) + [
        e for e in structural_edges(slots, arrow_list)
        if e.origin != "correspondence:same_claim"
    ]
    blocks = build_blocks(slots, edges, deltas)
    chart_of = {s.id: s.chart for s in slots}
    loops = loops_from_fibers(fibers, chart_of, restrict_to=set(chart_of), edges=edges)

    votes, tiers, docs, values = _flatten_deltas(deltas)
    snap = CorpusSnapshot(arrows=arrow_list, sources=dict(sources or {}))
    for s in slots:
        counter = votes.get(s.id)
        top = counter.most_common(1) if counter else []
        snap.slots[s.id] = SlotRecord(
            slot=s.id, chart=s.chart, type=s.type, nu=s.nu,
            value=top[0][0] if top else "N",
            confidence=round(top[0][1], 3) if top else 0.0,
            tier=tiers.get(s.id, "EXTRACTION"),
            docs=tuple(sorted(docs.get(s.id, ()))[:4]),
        )
    snap.fibers = [tuple(f.slots) for f in fibers]
    for b in blocks:
        for sid in b.slots:
            snap.blocks[sid] = tuple(b.slots)
        # `is_contested`, evaluated against the index: more than one slot joined by a prior,
        # or a single slot whose deltas support more than one b-value. Same predicate, and
        # the control below is what makes "same" a measurement.
        if len(b.slots) > 1 or any(len(values.get(sid, ())) > 1 for sid in b.slots):
            snap.contested.update(b.slots)
    snap.loops = len(loops)
    snap.floor_status = FLOOR_GAP if not loops else "measurable (cycles present)"
    return snap


def with_arrows(snapshot: CorpusSnapshot,
                arrows: Sequence[Correspondence]) -> CorpusSnapshot:
    """A read view of the SAME corpus with proposed arrows laid over it.

    The corpus snapshot is built from corpus material, so it holds no correspondence claims:
    the continuous proposer's arrows live in its journal. Without this the window shows a
    183,135-slot corpus with zero arrows while the daemon has been finding them for hours —
    which is not a false statement, but it is the wrong view.

    What changes and what does not:

    - **Fibers and blocks are recomputed** from the arrows, which is pure graph structure and
      needs no deltas.
    - **Contest is the UNION** of the stored contest (the single-slot arm — one slot whose
      deltas support more than one b-value, already decided at build time over the deltas)
      and the multi-slot arm (a block with more than one slot). That is `is_contested`, both
      arms, evaluated without re-reading 620k deltas.
    - **Nothing is promoted and nothing is written.** These arrows are EXTRACTION-tier
      proposals; laying them over a read view does not change their tier, and the snapshot on
      disk is untouched.

    An arrow whose endpoints are not both in the corpus is DROPPED, not invented: it refers
    to a slot this snapshot does not contain, and silently keeping it would put an endpoint
    in the graph that has no claim behind it.
    """
    from .blocks import build_blocks, build_fibers, loop_edges, loops_from_fibers, structural_edges
    from .correspondence import loop_pairs
    from .types import Slot

    live = [a for a in arrows
            if a.src_slot in snapshot.slots and a.dst_slot in snapshot.slots]
    touched: set[str] = set()
    for a in live:
        touched.add(a.src_slot)
        touched.add(a.dst_slot)
    slots = [Slot(id=r.slot, chart=r.chart, type=r.type, nu=r.nu)
             for sid, r in snapshot.slots.items() if sid in touched]

    fibers = build_fibers(slots, loop_pairs(live))
    edges = loop_edges(slots, live) + [
        e for e in structural_edges(slots, live)
        if e.origin != "correspondence:same_claim"
    ]
    chart_of = {s.id: s.chart for s in slots}
    blocks = build_blocks(slots, edges, [_Presence(s.id) for s in slots])
    loops = loops_from_fibers(fibers, chart_of, restrict_to=set(chart_of), edges=edges)

    out = CorpusSnapshot(
        slots=snapshot.slots, arrows=list(live), blocks=dict(snapshot.blocks),
        contested=set(snapshot.contested), sources=dict(snapshot.sources),
        fibers=[tuple(f.slots) for f in fibers],
    )
    for b in blocks:
        for sid in b.slots:
            out.blocks[sid] = tuple(b.slots)
        if len(b.slots) > 1:
            out.contested.update(b.slots)      # the multi-slot arm; the other arm is stored
    out.loops = len(loops)
    out.floor_status = FLOOR_GAP if not loops else "measurable (cycles present)"
    return out


class _Presence:
    """The one field `build_blocks` reads off a delta: which slot it is evidence for.

    `build_blocks` drops slots that carry no delta, so that a slot no source ever mentioned
    cannot be settled. Every slot in a snapshot is there *because* deltas produced it, so
    presence is exactly what has to be signalled here — and signalling it with this rather
    than by carrying 620k deltas through the read path is the whole point.
    """

    __slots__ = ("slot",)

    def __init__(self, slot: str):
        self.slot = slot


def build_snapshot(ledger, arrows: Sequence[Correspondence] = (),
                   sources: dict[str, int] | None = None) -> CorpusSnapshot:
    """Flatten a built ledger into the window's load-time form."""
    from collections import Counter

    votes: dict[str, Counter] = {}
    tiers: dict[str, str] = {}
    docs: dict[str, set[str]] = {}
    for d in ledger.deltas:
        votes.setdefault(d.slot, Counter())[d.value] += d.confidence
        tiers.setdefault(d.slot, d.warrant.tier.name)
        docs.setdefault(d.slot, set()).add(d.provenance.doc_id)

    snap = CorpusSnapshot(arrows=list(arrows), sources=dict(sources or {}))
    for s in ledger.slots:
        counter = votes.get(s.id) or Counter()
        top = counter.most_common(1)
        snap.slots[s.id] = SlotRecord(
            slot=s.id, chart=s.chart, type=s.type, nu=s.nu,
            value=top[0][0] if top else "N",
            confidence=round(top[0][1], 3) if top else 0.0,
            tier=tiers.get(s.id, "EXTRACTION"),
            docs=tuple(sorted(docs.get(s.id, ()))[:4]),
        )
    snap.fibers = [tuple(f.slots) for f in ledger.fibers]
    for b in ledger.blocks:
        for sid in b.slots:
            snap.blocks[sid] = tuple(b.slots)
    for b in ledger.contested_blocks:
        snap.contested.update(b.slots)
    snap.loops = len(ledger.loops)
    snap.floor_status = FLOOR_GAP if not ledger.loops else "measurable (cycles present)"
    return snap
