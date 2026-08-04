"""Composition: the arrows the algebra ALREADY implies, and where they contradict an answer.

A base category has composition. Once the corpus holds `A -same_claim-> B` and
`B -same_claim-> C`, the pair `(A, C)` is not an open question in the same sense the others
are — the structure already says something about it. Two consequences, both acted on here:

1. **Prioritization.** An implied pair is the highest-value thing to ask, because the answer
   either closes a triangle (structure the graph did not have) or exposes an inconsistency in
   what has already been accepted. Star-shaped confirmation cannot produce a cycle; composition
   is where a cycle can come from.

2. **Contradiction, not silence.** If the proposer has already answered `none` on a pair the
   structure now implies, that is a genuine inconsistency in the accumulated state. It is
   recorded as a `contradiction` in the journal and surfaced. It is **never** auto-resolved in
   either direction: the daemon does not delete the `none`, and does not mint the implied arrow.

**The composition table is partial, and deliberately so.**

    same_claim  ∘ same_claim   = same_claim
    same_claim  ∘ refines      = refines          (and the mirror)
    refines     ∘ refines      = refines
    same_claim  ∘ instance_of  = instance_of      (and the mirror)

Everything else is **undefined and stays undefined**. `refines ∘ instance_of` is not a legal
composite — "a more specific form of a particular instance" names no relation the three kinds
express — and `instance_of ∘ instance_of` is not transitive in general. Filling those cells
with the nearest-looking kind is exactly the substitution this build keeps deleting, so the
cells are absent and the pairs they would have generated are simply not implied by anything.

**Intra-chart residue.** Composition through a hub can imply a relation between two slots in
the *same* chart. `Correspondence` refuses that by construction (gate 1 owns intra-chart
identity), so such an implication cannot be expressed as an arrow. It is not discarded: it is
returned as a **residue** — a place where the accumulated structure says two distinct addresses
in one chart are the same claim, which the algebra at v0 has no morphism for. That is a real
statement about the corpus and about this version's expressiveness, and it is reported as one.

**Cost.** Composition over a hub `b` is `indeg(b) x outdeg(b)`; the total is
`sum_b indeg(b)*outdeg(b)`, which is quadratic in the degree of a heavily-bridged slot. That is
a real bound, not an asymptotic hope, so it is enforced rather than described: `hub_cap` limits
how many composites any single hub may contribute, and whatever the cap drops is COUNTED and
returned in `dropped`, never silently truncated.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from .correspondence import INSTANCE_OF, REFINES, SAME_CLAIM, Correspondence

#: The partial composition table. Absent cells are UNDEFINED — see the module docstring.
COMPOSITION: dict[tuple[str, str], str] = {
    (SAME_CLAIM, SAME_CLAIM): SAME_CLAIM,
    (SAME_CLAIM, REFINES): REFINES,
    (REFINES, SAME_CLAIM): REFINES,
    (REFINES, REFINES): REFINES,
    (SAME_CLAIM, INSTANCE_OF): INSTANCE_OF,
    (INSTANCE_OF, SAME_CLAIM): INSTANCE_OF,
}

#: How many composites one hub slot may contribute before the rest are dropped and counted.
HUB_CAP = 64


@dataclass(frozen=True, slots=True)
class Implied:
    """A pair the accumulated arrows already imply, with the path that implies it."""

    src_chart: str
    src_slot: str
    dst_chart: str
    dst_slot: str
    kind: str
    type: str
    via: tuple[str, str, str]        # (a, b, c) — the hub is b

    @property
    def cross_chart(self) -> bool:
        return self.src_chart != self.dst_chart

    def as_record(self) -> dict[str, object]:
        return {"src_chart": self.src_chart, "src_slot": self.src_slot,
                "dst_chart": self.dst_chart, "dst_slot": self.dst_slot,
                "kind": self.kind, "via": list(self.via)}


@dataclass(frozen=True, slots=True)
class Contradiction:
    """Composition implies one relation; the proposer already answered another."""

    src_slot: str
    dst_slot: str
    implied: str
    recorded: str
    via: tuple[str, str, str]

    @property
    def note(self) -> str:
        if self.recorded == "none":
            return ("accumulated arrows imply this pair corresponds, but the proposer answered "
                    "`none` on it. One of the three arrows on the path is wrong, or the `none` "
                    "is. Neither is resolved automatically.")
        return ("accumulated arrows imply a different kind than the proposer answered. The "
                "path and the direct answer disagree about which relation holds.")

    def as_record(self) -> dict[str, object]:
        return {"src_slot": self.src_slot, "dst_slot": self.dst_slot,
                "implied": self.implied, "recorded": self.recorded, "via": list(self.via),
                "note": self.note}


@dataclass(slots=True)
class CompositionResult:
    implied: list[Implied]
    residues: list[Implied]          # intra-chart: the algebra cannot express these at v0
    dropped: int                     # composites the hub cap refused, COUNTED not hidden
    hubs_capped: int


def compose(arrows: Sequence[Correspondence], hub_cap: int = HUB_CAP,
            type_of: dict[str, str] | None = None) -> CompositionResult:
    """Every pair the arrow set implies, one composition step out.

    One step, not transitive closure: the closure would re-derive the same pairs through every
    path and the daemon asks each pair once anyway. Re-running after new arrows land is what
    reaches further, and it does so with the new arrows actually confirmed rather than assumed.
    """
    out_edges: dict[str, list[Correspondence]] = defaultdict(list)
    in_edges: dict[str, list[Correspondence]] = defaultdict(list)
    charts: dict[str, str] = {}
    for a in arrows:
        out_edges[a.src_slot].append(a)
        in_edges[a.dst_slot].append(a)
        charts[a.src_slot] = a.src_chart
        charts[a.dst_slot] = a.dst_chart

    types = type_of or {}
    implied: list[Implied] = []
    residues: list[Implied] = []
    seen: set[tuple[str, str, str]] = set()
    dropped = 0
    hubs_capped = 0

    for hub in sorted(set(in_edges) | set(out_edges)):
        made = 0
        capped = False
        for first in in_edges.get(hub, ()):              # a -> hub
            for second in out_edges.get(hub, ()):        # hub -> c
                a, c = first.src_slot, second.dst_slot
                if a == c:
                    continue                              # a round trip is not a composite
                kind = COMPOSITION.get((first.kind, second.kind))
                if kind is None:
                    continue                              # undefined cell: implies nothing
                if made >= hub_cap:
                    dropped += 1
                    capped = True
                    continue
                key = (a, c, kind)
                if key in seen:
                    continue
                seen.add(key)
                made += 1
                item = Implied(
                    src_chart=charts.get(a, first.src_chart), src_slot=a,
                    dst_chart=charts.get(c, second.dst_chart), dst_slot=c,
                    kind=kind, type=types.get(a, "assert"),
                    via=(a, hub, c),
                )
                (implied if item.cross_chart else residues).append(item)
        if capped:
            hubs_capped += 1

    return CompositionResult(implied=implied, residues=residues,
                             dropped=dropped, hubs_capped=hubs_capped)


def contradictions(implied: Sequence[Implied], journal) -> list[Contradiction]:
    """Implied pairs the journal has already answered otherwise. Flagged, never resolved."""
    out: list[Contradiction] = []
    for item in implied:
        recorded = journal.answer_for(item.src_slot, item.dst_slot)
        if recorded is None or recorded == item.kind:
            continue
        out.append(Contradiction(src_slot=item.src_slot, dst_slot=item.dst_slot,
                                 implied=item.kind, recorded=recorded, via=item.via))
    return out


def unasked(implied: Sequence[Implied], journal) -> list[Implied]:
    """Implied pairs nobody has been asked about yet — the daemon's highest-priority work."""
    return [i for i in implied if journal.answer_for(i.src_slot, i.dst_slot) is None]
