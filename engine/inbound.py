"""INBOUND: my input is a BIAS on the field, not a prompt and not a lookup key.

The outbound direction is built: material -> claims -> proposer -> settlement. This is the
other direction, and the accumulated structure determines what the LM actually receives:

    typed text -> addressed by the ordinary extractor (not privileged)
               -> entered into the CORPUS's energy as soft evidence
               -> settlement runs on the real corpus, twice: without the bias and with it
               -> what MOVED is the response, reached over declared correspondences
               -> the moved region, with its path, is compiled into the LM's input

The typed text is the boundary condition. The field supplies the content.

**Exact addressing governs claim identity, never how a bias reaches the field.** Gate 1 says
two claims are the same claim iff `hash(nu(surface), type)` agrees. That is right and is
untouched. It is not a gate on whether the field may be consulted — and making it one is what
produced a window that answered every real question with "nothing addressed", then reached for
word matching to fill the silence.

**No string comparison anywhere in this path.** Propagation is over `engine/blocks`'s Q edges,
which are exactly the declared correspondences: an edge exists iff an arrow declared it. A
compiled fact names a slot the bias REACHED, and carries the chain of arrows it was reached
by; a moved slot with no path is not compiled, because a fact whose provenance cannot be shown
is not a fact this engine may state.

**Silence is a result.** A corpus where nothing responds says so and names the structural
reason — the biased address carries no declared arrow, or the corpus's own evidence outweighs
a soft constraint. It does not degrade into a keyword list. That degradation is what a
previous build did, and it made the two modes indistinguishable from the outside.

**Status conditions as much as content.** Whether the region is settled, provisional, contested
or a GAP is compiled in, so the answer is shaped by the epistemic state and not only by the
subject matter.

**Read-side only.** Nothing here writes to the corpus or touches the tape. Settlement runs on
a reconstructed read view; the snapshot on disk is untouched, the bias is soft and could not
clamp even if it tried, since extraction never grounds. The response may be proposed back
through the one inlet at extraction tier, but only if the operator explicitly chooses.

A NOTE ON THIS FILE'S OWN HISTORY, kept because the pattern recurred three times in one day:
this docstring claimed "settlement runs with the input as soft evidence" from the day it was
written, while the code did a dict lookup and called `settle` nowhere. Gate 10 now treats a
mechanism claim like any other claimed property — see `MECHANISM_CLAIMS` in
`engine/static_checks.py` — so a docstring can no longer describe a call graph that does not
exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .corpus_state import CorpusSnapshot
from .extract import DeterministicExtractor
from .attach import attach
from .relax import Relaxation, relax
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
    conditioned: bool = False                  # did the FIELD respond to the bias?
    relaxation: Relaxation | None = None
    attachment: object | None = None           # attach.AttachResult — the bridge, shown

    @property
    def reached(self) -> int:
        """Slots the bias reached over declared arrows, having moved when it was applied."""
        return len(self.relaxation.moved) if self.relaxation else 0

    @property
    def addressed(self) -> int:
        """Biased addresses the corpus already carried. Reported, never gated on.

        This is the number the old build branched on: no exact hit meant no field at all.
        It is kept because it is informative — a bias on an address the corpus does not hold
        has nothing coupled to it — but nothing in this module reads it to decide anything.
        """
        return len(self.relaxation.bias_in_field) if self.relaxation else 0

    def as_record(self) -> dict[str, object]:
        return {
            "typed": self.typed, "compiled": self.compiled,
            "conditioned": self.conditioned, "field_status": self.field_status,
            "spans": len(self.landings), "landed": self.addressed,
            "moved": self.reached,
            "facts": self.facts,
            "landings": [l.as_record() for l in self.landings],
            "relaxation": self.relaxation.as_record() if self.relaxation else None,
            "attachment": self.attachment.as_record() if self.attachment else None,
        }


def display(nu: str) -> str:
    """A nu-string with its chart tag stripped, for READING only.

    `nu` carries `\x01<chart>\x01` so that two charts can never share an address (gate 1).
    Rendered raw it comes out as `enthe cone is positive`, which reads as a typo. The tag is
    removed here and nowhere else: addressing, hashing and comparison all keep it.
    """
    if nu.startswith("\x01"):
        end = nu.find("\x01", 1)
        if end != -1:
            return nu[end + 1:]
    return nu


def _arrows_for(snapshot: CorpusSnapshot, slot: str) -> list[str]:
    """Every declared correspondence touching this slot, once each.

    Two arrows can land on the same neighbour — the proposer asks a pair in both directions,
    and both answers are kept in the ledger on purpose. Rendering both prints the same line
    twice, which reads as two independent corroborations of one thing when it is one thing
    seen twice.
    """
    out: list[str] = []
    seen: set[str] = set()
    for a in snapshot.arrows:
        if a.src_slot == slot or a.dst_slot == slot:
            other = a.dst_slot if a.src_slot == slot else a.src_slot
            rec = snapshot.slots.get(other)
            tier = "provisional" if a.provisional else "confirmed"
            line = (f"{a.kind} ({tier}) -> [{rec.chart if rec else '?'}] "
                    f"{(display(rec.nu)[:110] if rec else other[:16])}")
            if line in seen:
                continue
            seen.add(line)
            out.append(line)
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


def _attachment_block(att) -> str:
    """The bridge, shown rather than implied: what the proposer said, and at what tier.

    A bias that reaches the field through a proposed correspondence is standing on a claim
    somebody's model made, at extraction tier, which could be wrong. Printing the result
    without printing the bridge would present a relaxation as though the attachment were
    given. So every proposal is listed — including the `none`s, which are the proposer
    declining to force a match and are as informative as the acceptances.
    """
    lines = [
        "HOW THIS INPUT ATTACHED. The typed text is not in this corpus verbatim, so the "
        "proposer was asked which corpus claims it CORRESPONDS to — the same proposer, "
        "prompt and three kinds the corpus's own arrows use, with `none` legal and expected. "
        "Every accepted attachment below is a correspondence at EXTRACTION tier: proposed, "
        "not confirmed, and the relaxation that follows rests on it.",
    ]
    for a in att.proposed:
        if not a.accepted:
            continue
        lines.append(f"ATTACHED via {a.kind} (warrant {a.tier}) -> [{a.dst_chart}] "
                     f"{display(a.dst_nu)[:200]}")
        if a.evidence:
            lines.append(f"  BECAUSE {a.evidence[:300]}")
    declined = sum(1 for a in att.proposed if not a.accepted)
    lines.append(f"({len(att.accepted)} attachment(s) accepted, {declined} declined as none, "
                 f"out of {att.considered} candidate(s) asked over {att.calls} call(s).)")
    if att.budget_exhausted:
        lines.append(f"(The call budget stopped the search at {att.considered} of "
                     f"{att.available} type-compatible candidates. The rest are UNMEASURED, "
                     f"not ruled out.)")
    if att.error:
        lines.append(f"(Attachment reported an error: {att.error})")
    return "\n".join(lines)


def _no_attachment(att) -> str:
    """Why nothing attached. Never a bare zero."""
    if att.error:
        return f"the input could not be attached: {att.error}"
    if not att.proposed:
        return ("the proposer returned no usable answer over "
                f"{att.considered} candidate(s) in {att.calls} call(s).")
    tail = ""
    if att.budget_exhausted:
        tail = (f" The budget stopped at {att.considered} of {att.available} "
                f"type-compatible candidates, so the rest are UNMEASURED, not ruled out.")
    return (f"the proposer was asked about {att.considered} corpus claim(s) and answered "
            f"`none` to every one. It declines to force a match, so there is no bridge from "
            f"this input into the field and nothing to propagate.{tail}")


def _relaxed_block(rel: Relaxation, snapshot: CorpusSnapshot) -> tuple[list[str], list[dict]]:
    """The moved region, each row carrying the declared path the bias reached it by.

    A row here is not "a claim that resembles the query". It is a claim whose settled
    distribution CHANGED when the query was applied as a soft constraint, and the path is the
    chain of declared correspondences the perturbation travelled along to reach it. Nothing
    was compared as a string.
    """
    lines: list[str] = [
        "WHAT MOVED. The typed text entered this corpus's energy as a soft constraint and "
        "settlement was run twice — once on the corpus alone, once with the bias. Every line "
        "below is a claim whose settled distribution CHANGED, listed with how far it moved "
        "and the declared correspondences the bias reached it through. Nothing here was "
        "matched by words; a slot that moved but could not be reached over a declared arrow "
        "is not listed, because its provenance could not be shown.",
    ]
    facts: list[dict] = []
    for m in rel.moved:
        mark = "CONTESTED" if m.contested else "settled"
        origin = ("the bias landed on this address" if m.hops == 0
                  else f"reached in {m.hops} declared hop(s), weakest arrow "
                       f"{m.weakest_tier}")
        lines.append(f"MOVED [{m.chart}/{m.type}] value={m.value} warrant={m.tier} ({mark}) "
                     f"shift={m.shift:.4f} — {origin} :: {display(m.nu)[:220]}")
        for step in m.path:
            lines.append(f"  VIA {step.render()}")
        facts.append({"kind": "moved", **m.as_record()})
    if rel.moved_dropped:
        lines.append(f"({rel.moved_dropped} further slot(s) moved and are not shown — the "
                     f"list is cut at the least-responsive end, and the count is stated "
                     f"rather than the cut being silent.)")
    if rel.blocks_skipped:
        lines.append(f"({rel.blocks_skipped} block(s) exceeded the settling cap and were NOT "
                     f"relaxed. Anything they hold is unmeasured here, not absent.)")
    return lines, facts


def compile_input(text: str, snapshot: CorpusSnapshot, chart: str = "english",
                  index=None, transport=None) -> CompiledInput:
    """Compile the LM's input FROM WHAT THE FIELD DID, not from what the text resembles.

    The typed text is applied to the real corpus as a soft constraint, settlement runs, and
    the compiled result is the moved region with the declared path to each moved slot. When
    nothing moves, that is stated together with the structural reason — a biased address the
    corpus does not carry, a block over the settling cap, or a field whose own evidence
    outweighed the bias. There is no fallback: silence is a result about the corpus, and a
    second mechanism that produced words anyway would make the two indistinguishable.

    `index` is accepted and ignored. It is the last parameter of the deleted retrieval layer,
    kept for one release so an old caller fails loudly on behaviour rather than on a TypeError
    that reads like an unrelated bug.
    """
    landings = land(text, snapshot, chart)

    # WHERE THE BIAS ATTACHES. With a transport, the proposer is asked which corpus claims
    # the typed input corresponds to, and the accepted proposals are the seeds. Without one,
    # the bias can only attach at its own address — which is right only when the typed text
    # already exists verbatim, and is the inherited defect this parameter exists to fix.
    att = None
    seeds, extra = None, None
    if transport is not None:
        att = attach(text, snapshot, transport, chart)
        seeds, extra = att.seeds, att.arrows(att.typed_slot)
        if not seeds:
            status = ("THE FIELD DID NOT RESPOND — " + _no_attachment(att))
            return CompiledInput(
                typed=text, compiled=f"{status}\n\n{_attachment_block(att)}\n\n"
                                     f"BOUNDARY CONDITION:\n{text}",
                landings=landings, field_status=status, conditioned=False,
                relaxation=None, attachment=att)

    rel = relax(text, snapshot, chart, seeds_from=seeds, extra_arrows=extra)

    if not rel.responded:
        status = f"THE FIELD DID NOT RESPOND — {rel.silence}"
        return CompiledInput(
            typed=text, compiled=f"{status}\n\nBOUNDARY CONDITION:\n{text}",
            landings=landings, field_status=status, conditioned=False, relaxation=rel,
            attachment=att)

    lines: list[str] = [
        "FIELD STATE after relaxation. The boundary condition below was applied to this "
        "corpus as a soft constraint and the field was allowed to settle; what follows is "
        "what moved.",
        f"floor: {snapshot.floor_status}",
        "",
    ]
    if att is not None:
        lines.extend(_attachment_block(att).splitlines())
        lines.append("")
    moved_lines, facts = _relaxed_block(rel, snapshot)
    lines.extend(moved_lines)
    lines.append("")

    contested_here = sum(1 for m in rel.moved if m.contested)
    reached = sum(1 for m in rel.moved if m.hops > 0)
    status = (f"RELAXED: {len(rel.moved)} slot(s) moved across {rel.blocks_settled} settled "
              f"block(s) covering {rel.slots_considered} slot(s); {reached} were reached "
              f"through declared correspondence rather than biased directly; "
              f"{contested_here} contested; floor is {snapshot.floor_status}")
    lines.append(status)
    if reached == 0:
        lines.append("NOTE: everything that moved was biased directly — no declared "
                     "correspondence carried the perturbation further. The cross-chart "
                     "relation around this region is a GAP.")
    lines.append("")
    lines.append("BOUNDARY CONDITION (what was typed; it is the constraint, not the content):")
    lines.append(text)

    return CompiledInput(typed=text, compiled="\n".join(lines), landings=landings,
                         facts=facts, field_status=status, conditioned=True, relaxation=rel,
                         attachment=att)


INBOUND_SYSTEM = (
    "You are answering from a FIELD, not from your own knowledge. The input below is not a "
    "search result. The user's text was applied to a reconciliation engine's corpus as a soft "
    "constraint, the field was allowed to settle, and every MOVED line is a claim whose "
    "settled state CHANGED as a result — listed with how far it moved and the chain of "
    "declared correspondences the perturbation reached it through (the VIA lines).\n\n"
    "This means a moved claim need not share any wording with what the user typed, and a "
    "claim that shares wording is absent unless the field actually moved it. Do not treat the "
    "list as keyword matches and do not apologise for lines that look unrelated — being "
    "reached through structure IS the relation, and the VIA lines say what that structure "
    "was. A hop count of 0 means the constraint applied to that claim directly.\n\n"
    "Answer only from that state. Where the field says CONTESTED, do not resolve it — report "
    "the contest. Where it reports a GAP or says no correspondence carried the perturbation "
    "further, say the relation is unmeasured rather than supplying one. Where it says blocks "
    "exceeded the settling cap, treat their contents as unmeasured, not as absent.\n\n"
    "If the field DID NOT RESPOND, say so in one sentence and give the structural reason the "
    "input states. Do not fill the silence: 'nothing in this corpus moved when that was "
    "applied' is a real answer about the corpus, and inventing a plausible one would be a "
    "claim the engine did not make.\n\n"
    "WRITE AN ANSWER, NOT AN INVENTORY. The user can already see the field. Read what moved, "
    "then say in prose what it amounts to and where it does not reach. Name a specific claim "
    "when it carries your point; otherwise leave it out."
)
