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
