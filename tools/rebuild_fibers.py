"""Re-adjudicate an EXISTING snapshot's identity layer in place. Minutes, not a re-extraction.

`proposerd.py build-snapshot` rebuilds everything from the corpus source material and takes
~35 minutes against a container that has been reclaimed repeatedly. Nothing about the kind
re-adjudication needs that: the arrows, the slots and their provenance are all already in the
snapshot, and the demotion reads exactly those three things. So this loads the snapshot,
re-kinds the containment class, rebuilds the fibers and loops from what survives, and writes
it back — the same function `build_snapshot_direct` calls, applied to material already built.

The census it prints IS the committed table. The earlier one was an in-memory filter over the
same data and is superseded by this; any difference between them is a finding, not a rounding
error, and the two known causes are separated in the report rather than one absorbing the
other.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.blocks import build_fibers, edges_from_fibers, loop_edges, loops_from_fibers  # noqa: E402
from engine.corpus_state import SNAPSHOT_PATH, CorpusSnapshot, _demote_containment  # noqa: E402
from engine.correspondence import loop_pairs  # noqa: E402


class _Slot:
    __slots__ = ("id", "chart")

    def __init__(self, sid, chart):
        self.id, self.chart = sid, chart


def main(path: str = SNAPSHOT_PATH) -> None:
    t0 = time.time()
    snap = CorpusSnapshot.load(path)
    if snap.empty:
        raise SystemExit(f"no snapshot at {path}")
    print(f"loaded {len(snap.slots):,} slots, {len(snap.arrows):,} arrows, "
          f"{len(snap.fibers):,} fibers in {time.time() - t0:.1f}s")

    before = {
        "fibers": len(snap.fibers),
        "multi": sum(1 for f in snap.fibers if len(f) > 1),
        "largest": max((len(f) for f in snap.fibers), default=0),
        "in_multi": sum(len(f) for f in snap.fibers if len(f) > 1),
        "loops": snap.loops,
        "same_claim": sum(1 for a in snap.arrows if a.kind == "same_claim"),
        "fiber_edges": len(edges_from_fibers(
            [type("F", (), {"slots": f})() for f in snap.fibers])),
    }

    slots = [_Slot(k, v.chart) for k, v in snap.slots.items()]
    docs = {k: set(v.docs or ()) for k, v in snap.slots.items()}
    arrows, census = _demote_containment(list(snap.arrows), slots, docs)

    fibers = build_fibers(slots, loop_pairs(arrows))
    chart_of = {s.id: s.chart for s in slots}
    edges = loop_edges(slots, arrows)
    loops = loops_from_fibers(fibers, chart_of, restrict_to=set(chart_of), edges=edges)

    snap.arrows = arrows
    snap.fibers = [tuple(f.slots) for f in fibers]
    snap.loops = len(loops)
    snap.floor_status = ("GAP — undefined because unmeasured (no cycle in the correspondence "
                         "graph)" if not loops else "measurable (cycles present)")
    snap.demotion = census

    after = {
        "fibers": len(snap.fibers),
        "multi": sum(1 for f in snap.fibers if len(f) > 1),
        "largest": max((len(f) for f in snap.fibers), default=0),
        "in_multi": sum(len(f) for f in snap.fibers if len(f) > 1),
        "loops": snap.loops,
        "same_claim": sum(1 for a in arrows if a.kind == "same_claim"),
        "fiber_edges": len(edges_from_fibers(fibers)),
    }

    print("\nTHE COMMITTED CENSUS")
    print(f"  {'quantity':22s} {'before':>10s} {'after':>10s}")
    for k in before:
        print(f"  {k:22s} {before[k]:>10,} {after[k]:>10,}")
    print(f"\n  same_claim pairs before : {census['same_claim_pairs_before']:,}")
    print(f"  surviving pairs         : {census['surviving_pairs']:,}")
    print(f"  demoted records         : {census['demoted_records']:,}")
    print(f"  by class                : {census['by_class']}")
    print(f"  pigeonhole              : {census['pigeonhole']}")

    snap.save(path)
    print(f"\nwritten to {path} in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else SNAPSHOT_PATH)
