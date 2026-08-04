"""INBOUND: my input is a BIAS on the field, not a prompt to the model.

The outbound direction is built: material → claims → proposer → settlement. The window's
"ask" was retrieval-with-receipts — fetch relevant facts, staple them to a prompt. That is
not this. Here the accumulated structure determines what the LM actually receives:

    typed text → normalized and ADDRESSED like any input
               → the addresses it LANDS ON in the field (exact, gate 1)
               → their fibers, declared correspondences, contest status, warrant tiers
               → settlement runs with the input as soft evidence
               → the RELAXED STATE is compiled into the LM's input

The typed text is the boundary condition. The field supplies the content.

**Landing is EXACT, never similar.** A span lands on a slot iff `hash(nu(surface), type)`
matches one already in the corpus — gate 1, the same addressing everything else uses. There is
no nearest-neighbour search, no token overlap, no threshold: this build deleted a similarity
fiber relation and is not going to reintroduce one in the read path. The honest consequence is
that novel phrasing lands nowhere, and when that happens the compiler SAYS so rather than
quietly degrading into a plain prompt.

**Status conditions as much as content.** Whether the region is settled, provisional, contested
or a GAP is compiled in, so the answer is shaped by the epistemic state and not only by the
subject matter.

**Read-side only.** Nothing here writes to the corpus or touches the tape. The response may be
proposed back through the one inlet at extraction tier, but only if the operator explicitly
chooses; never automatically. The one-write-path assertion is untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .corpus_state import CorpusSnapshot
from .extract import DeterministicExtractor
from .types import Document

#: How many neighbouring slots a single landing may contribute. A landing inside a large
#: block would otherwise flood the compiled input with one region's contents.
NEIGHBOUR_CAP = 12


@dataclass(slots=True)
class Landing:
    """One span of the typed input, and where it landed in the field."""
    surface: str
    slot: str
    nu: str
    type: str
    hit: bool                                  # exact address match in the corpus
    value: str = ""
    tier: str = ""
    contested: bool = False
    docs: tuple[str, ...] = ()
    fiber: tuple[str, ...] = ()
    block: tuple[str, ...] = ()
    arrows: tuple[str, ...] = ()               # rendered declared correspondences

    def as_record(self) -> dict[str, object]:
        return {"surface": self.surface[:120], "slot": self.slot[:16], "hit": self.hit,
                "value": self.value, "tier": self.tier, "contested": self.contested,
                "fiber": len(self.fiber), "block": len(self.block),
                "arrows": list(self.arrows), "docs": list(self.docs)}


@dataclass(slots=True)
class CompiledInput:
    """What the LM actually receives, and the provenance of every line in it."""
    typed: str
    compiled: str
    landings: list[Landing] = field(default_factory=list)
    facts: list[dict[str, object]] = field(default_factory=list)   # one per compiled fact
    field_status: str = ""
    conditioned: bool = False                  # did the field supply anything at all?

    @property
    def reached(self) -> int:
        return sum(1 for l in self.landings if l.hit)

    def as_record(self) -> dict[str, object]:
        return {
            "typed": self.typed, "compiled": self.compiled,
            "conditioned": self.conditioned, "field_status": self.field_status,
            "spans": len(self.landings), "landed": self.reached,
            "facts": self.facts,
            "landings": [l.as_record() for l in self.landings],
        }


def _arrows_for(snapshot: CorpusSnapshot, slot: str) -> list[str]:
    out: list[str] = []
    for a in snapshot.arrows:
        if a.src_slot == slot or a.dst_slot == slot:
            other = a.dst_slot if a.src_slot == slot else a.src_slot
            rec = snapshot.slots.get(other)
            tier = "provisional" if a.provisional else "confirmed"
            out.append(f"{a.kind} ({tier}) -> [{rec.chart if rec else '?'}] "
                       f"{(rec.nu[:110] if rec else other[:16])}")
    return out


def land(text: str, snapshot: CorpusSnapshot, chart: str = "english") -> list[Landing]:
    """Address the typed input and find which addresses already exist in the field.

    Uses the ordinary extractor, so the input is segmented and addressed exactly as corpus
    material would be — the typed text is not privileged.
    """
    extractor = DeterministicExtractor("inbound", "typed")
    out: list[Landing] = []
    for d in extractor.extract(Document("inbound", chart, text, "typed")):
        rec = snapshot.slots.get(d.slot)
        if rec is None:
            out.append(Landing(surface=d.surface, slot=d.slot, nu=d.nu, type=d.type, hit=False))
            continue
        block = snapshot.blocks.get(d.slot, ())
        fiber = next((f for f in snapshot.fibers if d.slot in f), ())
        out.append(Landing(
            surface=d.surface, slot=d.slot, nu=d.nu, type=d.type, hit=True,
            value=rec.value, tier=rec.tier, contested=d.slot in snapshot.contested,
            docs=rec.docs, fiber=tuple(fiber)[:NEIGHBOUR_CAP],
            block=tuple(block)[:NEIGHBOUR_CAP], arrows=tuple(_arrows_for(snapshot, d.slot)),
        ))
    return out


def compile_input(text: str, snapshot: CorpusSnapshot, chart: str = "english") -> CompiledInput:
    """Compile the LM's input FROM THE RELAXED STATE, not from the raw text.

    Every line of the result traces to a slot or an arrow that exists in the field. The typed
    text appears only as the boundary condition it is.
    """
    landings = land(text, snapshot, chart)
    hits = [l for l in landings if l.hit]

    if snapshot.empty:
        status = ("NO FIELD TO CONDITION ON — the corpus is empty. This is a near-passthrough: "
                  "the answer is the model's own, not the field's.")
        return CompiledInput(typed=text, compiled=f"{status}\n\nBOUNDARY CONDITION:\n{text}",
                             landings=landings, field_status=status, conditioned=False)

    if not hits:
        status = (f"NO FIELD TO CONDITION ON — none of the {len(landings)} span(s) address to a "
                  f"claim in this corpus ({len(snapshot.slots)} slots). Landing is EXACT "
                  "(gate 1: hash(nu, type)); novel phrasing lands nowhere. This is a "
                  "near-passthrough and is reported as one.")
        return CompiledInput(typed=text, compiled=f"{status}\n\nBOUNDARY CONDITION:\n{text}",
                             landings=landings, field_status=status, conditioned=False)

    lines: list[str] = []
    facts: list[dict[str, object]] = []
    seen: set[str] = set()

    lines.append("FIELD STATE around the boundary condition. Every line below is a claim or a "
                 "declared correspondence that exists in this corpus, with its status.")
    lines.append(f"floor: {snapshot.floor_status}")
    lines.append("")

    for l in hits:
        rec = snapshot.slots.get(l.slot)
        status = "CONTESTED" if l.contested else "settled"
        lines.append(f"LANDED [{rec.chart}/{l.type}] value={l.value} warrant={l.tier} "
                     f"({status}) :: {rec.nu[:200]}")
        facts.append({"kind": "landing", "slot": l.slot, "chart": rec.chart,
                      "value": l.value, "tier": l.tier, "contested": l.contested,
                      "docs": list(l.docs)})
        seen.add(l.slot)
        for rendered in l.arrows:
            lines.append(f"  CORRESPONDENCE {rendered}")
            facts.append({"kind": "arrow", "slot": l.slot, "rendered": rendered})
        for nid in l.block:
            if nid in seen:
                continue
            n = snapshot.slots.get(nid)
            if n is None:
                continue
            seen.add(nid)
            mark = "CONTESTED" if nid in snapshot.contested else "settled"
            lines.append(f"  NEIGHBOUR [{n.chart}/{n.type}] value={n.value} ({mark}) "
                         f":: {n.nu[:160]}")
            facts.append({"kind": "neighbour", "slot": nid, "chart": n.chart,
                          "value": n.value, "contested": nid in snapshot.contested})
        lines.append("")

    contested_here = sum(1 for l in hits if l.contested)
    arrows_here = sum(len(l.arrows) for l in hits)
    status = (f"CONDITIONED on {len(hits)} landed span(s) of {len(landings)}; "
              f"{arrows_here} declared correspondence(s); "
              f"{contested_here} contested; floor is {snapshot.floor_status}")
    lines.append(status)
    if arrows_here == 0:
        lines.append("NOTE: no declared cross-chart correspondence reaches this region — the "
                     "conditioning is single-chart, and the cross-chart relation here is a GAP.")
    lines.append("")
    lines.append("BOUNDARY CONDITION (what was typed; it is the constraint, not the content):")
    lines.append(text)

    return CompiledInput(typed=text, compiled="\n".join(lines), landings=landings,
                         facts=facts, field_status=status, conditioned=True)


INBOUND_SYSTEM = (
    "You are answering from a FIELD, not from your own knowledge. The input below is compiled "
    "from a reconciliation engine's settled state: every claim, correspondence and status line "
    "is something that engine actually holds, with its warrant tier and contest status. Answer "
    "only from that state. Where the field says CONTESTED, do not resolve it — report the "
    "contest. Where the field says GAP or reports no correspondence, say the relation is "
    "unmeasured rather than supplying one. If the field does not cover the boundary condition, "
    "say so plainly; that is a fact about the corpus, not a failure to answer."
)
