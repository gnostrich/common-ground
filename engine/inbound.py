"""INBOUND: my input is a BIAS on the field, not a prompt and not a lookup key.

The outbound direction is built: material -> claims -> proposer -> settlement. This is the
other direction, and the accumulated structure determines what the LM actually receives:

    typed text -> addressed exactly (gate 1, unchanged)
               -> entered into a REGION as one more object, [0|bias] (`engine/perturb`)
               -> ONE call completes the diagram; arrows to [0] are the attachment points
               -> entered into the CORPUS's energy as soft evidence, at those points
               -> settlement runs on the real corpus, twice: without the bias and with it
               -> what MOVED is the response, reached over declared correspondences
               -> the moved region, with its path, is compiled into the LM's input

The typed text is the boundary condition. The field supplies the content.

**ONE MECHANISM, and it is the sampler's.** This path used to run a candidate list — degree-
ordered, budget-capped, interrogated twelve pairs at a time — while the walk ran region
relaxation. Two mechanisms for one job, and this one was the worse half: forty-eight claims
out of thirty-seven thousand, each asked in isolation, which reads as lookup because it is
one. The list is deleted. A perturbation is a region with a boundary condition in it, and
every wire-level step is `engine/region` code the walk calls too.

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

from .grammar import render_prompt
from .corpus_state import CorpusSnapshot
from .extract import DeterministicExtractor
from .perturb import perturb, relax_from
from .relax import Relaxation, relax
from .structure_trace import signature_of, structure_lines
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


@dataclass(frozen=True, slots=True)
class Citable:
    """One object the answer is allowed to cite, and the LABEL it cites it by.

    The label is the WHOLE relation between a sentence and the trace. It is assigned here,
    printed into the prompt here, and resolved by `engine.grounded` as EXACT MEMBERSHIP IN A
    DECLARED LABEL SET — no text is compared at any point. The referee that licenses
    answer-first cannot itself be a similarity mechanism, and a citation index is the only
    shape that avoids it.
    """

    n: str
    kind: str          # "moved" | "attached" | "bears_on" | "arrow" | "absent"
    chart: str
    slot: str
    nu: str
    #: For an ARROW citation: the two object numbers it joins. The weld rule reads this and
    #: nothing else — a sentence may assert a relation only by citing the line that states it.
    joins: tuple = ()
    #: True when the field holds more than one value for this object. The grammar requires a
    #: sentence citing it to carry [!], so a contest cannot be silently resolved in prose.
    contested: bool = False
    #: Which declared group this object belongs to — a fiber, a span, a block. The weld rule
    #: is about claims from DIFFERENT groups: co-citing two faces of one quotient asserts no
    #: relation the field lacks, because the quotient IS the declared relation between them.
    group: str = ""

    def as_record(self) -> dict[str, object]:
        # JOINS, CONTESTED AND GROUP TRAVEL. They did not, and the consequence was that the
        # checker convicted CORRECT answers: two claims in one fiber, co-cited, came back
        # WELDED because `group` was dropped before `check_answer` could read it — and the
        # weld rule is precisely about claims from DIFFERENT groups. A field the referee
        # cannot see is a field the referee rules against.
        return {"n": self.n, "kind": self.kind, "chart": self.chart,
                "slot": self.slot[:16], "nu": self.nu,
                "joins": list(self.joins), "contested": self.contested, "group": self.group}


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
    attachment: object | None = None           # perturb.Perturbation — the diagram, shown
    #: Per-stage wall clock. A window that takes half a minute must be able to say WHICH
    #: stage took it — the same rule as the walk's phase announcements: silence must never
    #: mean unknown-phase.
    #: THE SCOPE VIEW. Everything the renderer must NOT see — the mechanism prose, the
    #: field statistics, the floor status — kept on the record so it is inspectable
    #: rather than deleted. Removed from the renderer's input; not removed from the world.
    scope: str = ""
    diagnostics: tuple = ()
    stages: dict = field(default_factory=dict)
    #: The numbered objects the answer may cite. Empty when nothing attached and nothing
    #: moved, in which case an answer citing anything is citing something that is not there.
    citations: list = field(default_factory=list)
    #: Why the structural layer was or was not compiled. Both branches are stated, so a reader
    #: never has to infer from an absent block that the question was not structural.
    signature: object | None = None
    #: The per-sheet permutation salt. Recorded so a shuffled sheet is still reproducible.
    order_salt: str = ""
    #: Per group: the arrow ids that constitute the fiber. Auditable back to the journal.
    groups: list = field(default_factory=list)

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
            "stages": dict(self.stages),
            "citations": [c.as_record() for c in self.citations],
            "signature": self.signature.as_record() if self.signature else None,
            "order_salt": self.order_salt,
            # THE SCOPE VIEW travels with the record. What the renderer must not see is not
            # thereby hidden from the operator: it is one click below, on the page.
            "scope": self.scope,
            "diagnostics": list(self.diagnostics), "groups": list(self.groups),
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


#: FIELD STATISTICS ARE SCOPE DATA, NEVER RENDERER INPUT. Void counts, dropped-mover counts
#: and settling-cap counts describe the MEASUREMENT, not the field, and a model handed them
#: alongside the claims enumerates them — it answered a question about certified positivity by
#: reciting how many lines were void. They stay in the record for the collapsed scope view and
#: leave the string the renderer reads.
DIAGNOSTICS: list = []

#: A STATE LINE carries a numbered object, a declared relation, or a stated absence. Anything
#: else is explanation, and explanation in the renderer's input gets recited back as an
#: answer. Recognised by the emitters' own declared prefixes — not by reading the prose.
_STATE_PREFIXES = ("[", "  -", "   -", "ARROW", "ABSENT", "==", "  ")


def _dedupe_claims(state: list) -> list:
    """OI-10's counting rule, on the render input: one line per distinct CLAIM.

    Identical lines were already collapsed, which was not enough. A claim reached both as an
    ATTACHMENT and as a MOVED slot appears twice under different prefixes — `[4] BEARS ON ->
    [english] machine-checked positivity results...` and `[32] [english] machine-checked
    positivity results...` — same sentence, two numbers. The renderer then cited both, and the
    weld rule convicted it for relating two objects with no arrow between them. They are one
    object. The duplication was the defect and the weld was the symptom.

    The FIRST occurrence keeps its number: attachments are emitted before movers, and an
    attachment line says how the input reached the field, which the mover line does not.
    """
    seen, out = set(), []
    for line in state:
        body = line.split("] ", 1)[-1]
        body = body.split("-> ", 1)[-1].strip()
        if not body or not line.strip().startswith("["):
            out.append(line)
            continue
        if body in seen:
            continue
        seen.add(body)
        out.append(line)
    return out


def _is_state(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("[") or stripped.startswith("-") or stripped.startswith("=="):
        return True
    return stripped.startswith("WHAT THIS PROPOSITION IS LINKED TO")


def _region_block(pert, cites: list | None = None, *, labeller=None, snapshot=None) -> str:
    """The diagram the boundary condition entered, and what the medium drew in it.

    A bias that reaches the field through a proposed arrow is standing on a claim somebody's
    model made, at extraction tier, which could be wrong. Printing the result without printing
    the bridge would present a relaxation as though the attachment were given.

    It also states, unprompted, that the region is a SAMPLE. Sixty claims came back and 69,000
    did not, and an operator who is not told how those sixty were chosen will infer that they
    were the relevant ones — which is the inference the whole engine exists to refuse.
    """
    from .region import BEARS_ON, BIAS_CHART, label

    # NO REGION IS A STATE, not a crash. `perturb` returns early — empty corpus, no model,
    # nothing typed — with `region` unset, and this block was called on exactly that path
    # because an early return also means no seeds. It then read `.declared` off None and took
    # the whole request down. Found by the OI-19 control asking what the LM reads when nothing
    # moved; the honest answer is the reason, not a fabricated count of zero arrows.
    if pert.region is None:
        return ("THE DIAGRAM. There was none: " +
                (pert.error or "the region could not be built") +
                ". No call was made, so nothing was completed and nothing was drawn.")

    bias_only = [a for a in pert.attachment if a.kind == BEARS_ON]
    corresponds = [a for a in pert.attachment if a.kind != BEARS_ON]
    lines = [
        # THE LABEL IS READ FROM THE RENDERER, not spelled here. This line said `[0|bias]`
        # for as long as the wire said `[b0]` — a disclosure describing a format the engine
        # had stopped using, in the one paragraph whose job is to tell the operator what the
        # medium saw.
        f"THE DIAGRAM. The typed text entered a REGION of this corpus as one more object — "
        f"[{label(BIAS_CHART, 0)}], carrying what was typed BYTE FOR BYTE — beside "
        f"{pert.members - 1} corpus claim(s), with "
        f"{len(pert.region.declared)} declared arrow(s) and {len(pert.region.implied)} "
        f"composition-implied arrow(s) already in it. One call asked the medium to complete "
        f"the diagram. This is the same region, wire format and prompt the sampler runs; "
        f"there is no candidate list and no interrogation budget anywhere in this path.",
        f"WHICH REGION: sampled by declared structure — an arrow-rich neighbourhood, chosen "
        f"by a hash of the input's address, then filled provenance-near and chart-balanced. "
        f"A hash is not a similarity. These claims are NOT the part of the corpus that "
        f"matches the question; nothing here could compute that, and no text was compared. "
        f"The rest of the corpus is UNMEASURED IN THIS REGION, which is what a sample means.",
        "TWO KINDS OF ARROW came back, and they are not the same fact:",
        "  CORRESPONDS  — the input asserts the same proposition as a claim, refines it, or "
        "instances it.",
        "  BEARS ON     — a claim is ABOUT what the input is about. A question or a topic "
        "asserts nothing, so it cannot correspond; it can still be about something.",
        "BOTH are EPHEMERAL here: they condition this one perturbation, are never journalled, "
        "never compose, and never become arrows. An arrow to a boundary condition is not "
        "structure.",
    ]
    def _cite(kind: str, a) -> str:
        """One LABEL, assigned here and printed here. The prompt and the record cannot disagree
        about it because there is no second place that assigns one — and now there is no second
        NUMBERING either: the label is the region's own, so the medium, the extractor and the
        checker all resolve against the same string."""
        n = labeller.label_for(a.dst_slot, a.dst_chart) if labeller else str(len(cites) + 1)
        if cites is not None:
            cites.append(Citable(n=n, kind=kind, chart=a.dst_chart, slot=a.dst_slot,
                                 nu=display(a.dst_nu)))
        return n

    if corresponds:
        lines.append(f"-- {len(corresponds)} CORRESPONDENCE attachment(s) --")
    for a in corresponds:
        lines.append(f"[{_cite('attached', a)}] ATTACHED via {a.kind} (warrant {a.tier}) -> "
                     f"[{a.dst_chart}] {display(a.dst_nu)}")
    if bias_only:
        lines.append(f"-- {len(bias_only)} BEARS-ON attachment(s) --")
    for a in bias_only:
        lines.append(f"[{_cite('bears_on', a)}] BEARS ON -> [{a.dst_chart}] "
                     f"{display(a.dst_nu)}")
    if pert.extracted:
        lines.append(f"({len(pert.extracted)} arrow(s) among the CORPUS objects came back in "
                     f"the same call. Those are ordinary extraction at the same tier the "
                     f"sampler produces — asking a question does the sampler's work — and "
                     f"they are offered to the inlet, not written by this read path.)")
    # THE CHECKER'S RESOLVABLE SET IS THE SHOWN SET, BYTE-DERIVED FROM THE SAME COMPILE,
    # NEVER REBUILT.
    #
    # Not "kept in sync", which is two constructions and a promise, and not "a superset", which
    # is two constructions and a direction. The act that PRINTS a label to the medium is the act
    # that REGISTERS it as citable, so there is no second construction to drift. Every defect in
    # the row-523 class is a second construction of a thing that already existed.
    #
    # Turn 1 is seated in front of the WHOLE region — sixty labelled objects with their claim
    # text, printed by `region.render_region` — and answers by citing those labels. The
    # compiled record used to register only the handful that ATTACHED or MOVED, so
    # `engine.grounded` resolved against three labels while the medium had been shown sixty.
    # On the frozen fixture that convicted [e20], [e49] and [e50] as UNRESOLVED: three real
    # corpus claims, shown to the medium by this very act, ruled fabricated by the checker
    # downstream of it. The answer was correct and the verdict was RED.
    #
    # Fourth instance of one class — A RULE THE MEDIUM CANNOT COMPLY WITH IS A RULE THAT ONLY
    # EVER CONVICTS — and the sharpest of them, because here the medium DID comply with what it
    # was shown. The fix is not a wider checker. It is that the two sheets must not differ:
    # every object the medium is shown is PRINTED here and REGISTERED here, in one act, so the
    # set the referee accepts is by construction the set the prompt contains. The equality is
    # asserted directly rather than left to reading — see tests/test_inbound.py.
    #
    # SEATED IS NOT ATTACHED, and the line says so. A seated object is a real corpus claim the
    # region sampled; an answer may rest on it and must cite it when it does. What seating is
    # NOT is a relation to the boundary condition — `bears_on` is that, and the attachment
    # lines above are the only place in this block where it is asserted.
    groups = _fiber_index(snapshot) if snapshot is not None else {}
    contested = getattr(snapshot, "contested", None) or frozenset()
    already = {c.n for c in (cites or ())}
    seated: list = []
    for m in pert.region.members:
        if m.chart == BIAS_CHART:
            continue                  # [b0] is the question, not evidence for its own answer
        n = labeller.label_for(m.slot, m.chart) if labeller else label(m.chart, m.index)
        if n in already:
            continue                  # already printed above as an attachment
        already.add(n)
        seated.append((n, m))
        if cites is not None:
            fiber = groups.get(m.slot)
            cites.append(Citable(n=n, kind="seated", chart=m.chart, slot=m.slot,
                                 nu=display(m.nu), contested=m.slot in contested,
                                 group=(str(fiber[0]) if fiber and len(fiber) > 1 else "")))
    if seated:
        lines.append(f"-- {len(seated)} SEATED object(s) — shown, not attached to. Citable: an "
                     f"answer may rest on one and must cite it. Seating asserts NO relation to "
                     f"the boundary condition; only the attachment lines above do that. --")
        for n, m in seated:
            lines.append(f"[{n}] SEATED -> [{m.chart}] {display(m.nu)}")

    d = pert.discrimination
    if d["shown"]:
        line = (f"ATTACHMENT DISCRIMINATION: {d['attached']} of {d['shown']} corpus object(s) "
                f"shown were attached to ({d['fraction']:.0%}).")
        if d["red"]:
            line += (f" RED — at or above {d['threshold']:.0%} this is INDISCRIMINATE "
                     f"attachment: {d['note']}. Treat the attachment as carrying no "
                     f"information about which claims the input bears on, and say so.")
        lines.append(line)
    if pert.void:
        DIAGNOSTICS.append(f"({pert.void} line(s) were VOID: outside the region, self-paired, "
                     f"intra-chart, or an unknown kind. Discarded with the reason, never "
                     f"repaired into a nearby address.)")
    if pert.error:
        lines.append(f"(The region call reported an error: {pert.error})")
    return "\n".join(lines)


def _no_attachment(pert) -> str:
    """Why nothing attached. Never a bare zero."""
    if pert.error:
        return f"the input could not be put to the field: {pert.error}"
    return (f"the medium was shown one region of {pert.members - 1} corpus claim(s) with the "
            f"typed text as an object in it, and drew no arrow to it. It declines to relate "
            f"a boundary condition it does not see a relation to, so there is nothing to "
            f"propagate from. The rest of the corpus was not in this region and is UNMEASURED, "
            f"not ruled out — a different sample may answer differently.")


def _fiber_index(snapshot) -> dict:
    """slot -> the fiber it belongs to. READ off the fiber registry, computed from nothing.

    This is the whole grouping rule and it is one dictionary lookup. Groups are `same_claim`
    equivalence classes exactly as the journal declared them; there is no clustering step, no
    distance, and no comparison of claim text anywhere on this path. A grouping that produced
    the same groups on a fixture by any other means would be a different mechanism wearing
    this one's output, which is why `engine/referee_sweep` now sweeps this module too.
    """
    out: dict[str, tuple] = {}
    for fib in (getattr(snapshot, "fibers", None) or []):
        members = tuple(fib)
        for slot in members:
            out[slot] = members
    return out


def _fiber_arrows(snapshot, members: set) -> list[str]:
    """The arrow ids that CONSTITUTE this fiber, so a group is auditable back to the journal."""
    out = []
    for a in (getattr(snapshot, "arrows", None) or []):
        if a.kind == "same_claim" and a.src_slot in members and a.dst_slot in members:
            # `Correspondence.id` is a METHOD, not an attribute. `getattr(a, "id", "")`
            # returned the bound method — truthy, so it sailed through — and the record then
            # failed JSON serialisation at the server boundary, 500-ing every /ask on the
            # deployed build. The control that existed used a stub with no `id` at all, so it
            # took the fallback branch and never touched a real Correspondence.
            ident = getattr(a, "id", None)
            ident = ident() if callable(ident) else ident
            out.append(str(ident) if ident else f"{a.src_slot[:8]}~{a.dst_slot[:8]}")
    return out


def _links_for(snapshot, slot: str, inside: set) -> list[str]:
    """The declared arrows leaving this claim, rendered. The corpus's own decomposition.

    A fiber says these claims are one proposition; the arrows LEAVING it say what that
    proposition refines, instances and bears on. That is the decompression the corpus has
    already written, and until this function existed it never reached the medium.
    """
    out = []
    for a in (getattr(snapshot, "arrows", None) or []):
        for src, dst in ((a.src_slot, a.dst_slot), (a.dst_slot, a.src_slot)):
            if src != slot or dst in inside or a.kind == "same_claim":
                continue
            rec = (getattr(snapshot, "slots", None) or {}).get(dst)
            if rec is None:
                continue
            out.append(f"      -{a.kind}-> [{getattr(rec, 'chart', '?')}] "
                       f"{display(getattr(rec, 'nu', '') or '')}")
    return out[:4]


def _sheet_order(keys: list, salt: str) -> list:
    """THE SHUFFLE LAW, EXTENDED TO GROUPS. Position is attention-salient; it may not rank.

    A group list ordered by size, recency or chart would put an undeclared ranking in front of
    the reader in the one channel nobody reads as a claim. So order is permuted per SHEET —
    two compiles of the same region come out in different orders with identical content.

    The salt is RECORDED on the compiled input, which is what keeps this replayable. A
    content-derived permutation (what `engine/region._shuffle` uses) is stable for a given
    region and therefore cannot vary per sheet; an unrecorded random one would make a sheet
    unreproducible. A recorded salt is both.
    """
    from .hashing import sha256_text

    return sorted(keys, key=lambda k: sha256_text(salt + str(k)))


def mover_text(n, m) -> str:
    """The claim a moved object carries — and a DIAGNOSTIC when it carries none.

    A numbered object with no sentence is something an answer can CITE and cannot rest on.
    Twenty-four of them once made an entire input uncitable and the answer cited one line
    twice because it was among the few that said anything. The earlier control caught that on
    the state-line pipe and does not cover this one, so the guard lives here, at the line's
    own construction, where nothing can route around it.
    """
    text = display(getattr(m, "nu", "") or "")
    if not (text or "").strip():
        DIAGNOSTICS.append(f"TEXTLESS MOVER [{n}] over {getattr(m, 'chart', '?')}: slot "
                           f"{str(getattr(m, 'slot', ''))[:12]} moved and carries no claim text")
    return text


def _relaxed_block(rel: Relaxation, snapshot: CorpusSnapshot,
                   cites: list | None = None, salt: str = "", *,
                   labeller=None) -> tuple[list[str], list[dict]]:
    """The moved region, GROUPED BY FIBER, each row carrying the path the bias reached it by.

    THE FLAT LIST WAS THE DEFECT. A numbered list of claims presents a corpus as an
    undifferentiated pile, and the medium attaches to a pile indiscriminately — 59 of 59 on
    the measured run — because there is nothing in the presentation to attach to more
    precisely than "one of these". The corpus is not a pile: a `same_claim` fiber says several
    of these claims are ONE proposition written in different charts, and the arrows leaving
    that fiber say what the proposition refines, instances and bears on. That structure has
    been in the snapshot the whole time and was flattened away on the way into the prompt.

    THIS IS A VIEW AND HAPPENS AFTER SETTLEMENT. Every number here — which slots moved, how
    far, over which arrows — was computed before this function was called, and a control
    asserts a grouped compile and a flat one produce byte-identical movers. A view that
    changed what moved would be the presentation leaking into the physics.

    THE HEADER IS READ, NOT COMPUTED. It names the fiber by its id and states counts. There is
    no summarisation step and no call: a generated group header would be medium-written prose
    in the operator's voice, sitting above the operator's own verbatim claims, which is the
    one place a confabulation would be least visible.
    """
    from .medium import fiber_label

    lines: list[str] = [
        "WHAT MOVED. The typed text entered this corpus's energy as a soft constraint and "
        "settlement was run twice — once on the corpus alone, once with the bias. Every claim "
        "below is one whose settled distribution CHANGED. Nothing here was matched by words.",
        "",
        "GROUPED BY FIBER. A group is ONE PROPOSITION the corpus has declared is carried "
        "across several charts, followed by the declared arrows leaving it — what it refines, "
        "what it instances, what it bears on. The group is the unit to relate to; its members "
        "are the same thing written differently, and attaching to all of them is attaching "
        "once, not several times. GROUP HEADERS ARE NOT CITABLE: they are display labels, not "
        "claims. Cite the numbered members.",
        "ORDER CARRIES NO SIGNAL. Groups and members are permuted per sheet, so position "
        "encodes nothing about size, recency or importance.",
    ]
    facts: list[dict] = []
    index = _fiber_index(snapshot)
    groups: dict[tuple, list] = {}
    for m in rel.moved:
        groups.setdefault(index.get(m.slot, (m.slot,)), []).append(m)

    for members in _sheet_order(list(groups), salt):
        moved = _sheet_order(groups[members], salt)
        inside = set(members)
        charts = sorted({m.chart for m in moved})
        label = fiber_label(members[0])
        lines.append("")
        if len(members) > 1:
            head = (f"== FIBER {members[0][:12]} — ONE PROPOSITION carried across "
                    f"{len(members)} claim(s) [{'+'.join(charts)}], {len(moved)} of which "
                    f"moved")
        else:
            # A SINGLETON IS THE DEFAULT, NOT A REPORT. Fifteen copies of "a claim in no
            # declared fiber — its own group of one; 1 claim(s), 1 of which moved" carry no
            # information at all: every claim not in a fiber is one, and saying so once per
            # claim is boilerplate crowding out the claims. Grouping is worth a header only
            # when there is a group.
            head = ""
        if head:
            lines.append(head + (f" — the medium reads this as: {label}" if label else "") + " ==")
        for m in moved:
            # A MOVED CLAIM CAN BE OUTSIDE THE REGION — reached over a declared arrow — so it
            # has no region label and the labeller mints one in its own chart. One label space,
            # not two: the letter means the chart everywhere or it means nothing anywhere.
            n = labeller.label_for(m.slot, m.chart) if labeller else str(len(cites) + 1)
            mark = "CONTESTED" if m.contested else "settled"
            if cites is not None:
                cites.append(Citable(n=n, kind="moved", chart=m.chart, slot=m.slot,
                                     nu=display(m.nu), contested=bool(m.contested),
                                     # THE FIBER IS THE GROUP. Two faces of one quotient are
                                     # not a weld — the quotient IS the declared relation
                                     # between them — and the referee can only know that if
                                     # the group travels.
                                     group=(str(members[0]) if len(members) > 1 else "")))
            origin = ("the bias landed here" if m.hops == 0
                      else f"reached in {m.hops} declared hop(s), weakest arrow "
                           f"{m.weakest_tier}")
            # THE CLAIM ITSELF. It was missing: the line printed chart, value, warrant, a
            # shift to four decimals and how the bias arrived, and NOT the sentence. Twenty-
            # four numbered objects with no content, so the only citable text in the whole
            # input was the attachment block — and the answer cited [4] twice because [4] was
            # one of the few lines that said anything. A state line whose state is metadata
            # about the state is not a state line.
            # A TEXTLESS MOVER IS A DEFECT, not a claim with an empty surface. The earlier
            # control caught it on the state-line pipe and does not cover this one, so it is
            # caught HERE, where the line is built: a numbered object carrying no sentence is
            # something the answer can cite and cannot rest on, and twenty-four of them once
            # made the whole input uncitable. Reported, never silently printed.
            _text = mover_text(n, m)
            # ONCE, not twice. The claim was printed on the label line and again on the line
            # below it — the same sentence, doubled, in every mover of every answer's input.
            # THE CONTEST IS SHOWN. `mark` was computed and never printed — dead since it
            # was written — so the grammar required a sentence citing a contested claim to
            # carry [!] while the input never said which claim was contested. A rule the
            # medium cannot comply with is a rule that only ever convicts.
            lines.append(f"  [{n}] [{m.chart}]"
                         + (" [CONTESTED]" if mark == "CONTESTED" else "")
                         + f" {_text}")
            for step in m.path:
                lines.append(f"      VIA {step.render()}")
            facts.append({"kind": "moved", **m.as_record()})
        links = []
        for slot in members:
            links.extend(_links_for(snapshot, slot, inside))
        if links:
            lines.append("   WHAT THIS PROPOSITION IS LINKED TO, by declared arrows:")
            lines.extend(links[:6])

    if rel.moved_dropped:
        DIAGNOSTICS.append(f"({rel.moved_dropped} further slot(s) moved and are not shown — the "
                     f"list is cut at the least-responsive end, and the count is stated "
                     f"rather than the cut being silent.)")
    if rel.blocks_skipped:
        DIAGNOSTICS.append(f"({rel.blocks_skipped} block(s) exceeded the settling cap and were NOT "
                     f"relaxed. Anything they hold is unmeasured here, not absent.)")
    return lines, facts


def group_provenance(rel, snapshot) -> list[dict]:
    """Per group: the arrow ids that constitute the fiber, for the collapsed scope.

    A group that cannot produce its arrows is a group nobody can audit back to the journal
    entries — proposer, model served, era tags — that formed it. Every group answers.
    """
    index = _fiber_index(snapshot)
    seen: dict[tuple, list] = {}
    for m in (getattr(rel, "moved", None) or []):
        seen.setdefault(index.get(m.slot, (m.slot,)), []).append(m.slot)
    out = []
    for members, moved in seen.items():
        out.append({"fiber_id": members[0][:16], "members": len(members),
                    "moved": len(moved),
                    "arrows": _fiber_arrows(snapshot, set(members)),
                    "singleton": len(members) == 1})
    return out


def compile_input(text: str, snapshot: CorpusSnapshot, chart: str = "english",
                  index=None, transport=None, on_stage=None) -> CompiledInput:
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
    import time as _time

    def _phase(name: str) -> None:
        """Announce the stage ENTERED, not the stage guessed.

        The window takes tens of seconds and 76-94% of it is one call, so a blank wait is
        indistinguishable from a wedge. This is the walk's phase rule applied to the request
        path: silence must never mean unknown-phase. The callback is optional so every
        non-streaming caller is unaffected.
        """
        if on_stage is not None:
            try:
                on_stage(name)
            except Exception:
                pass                    # a progress channel must never break the answer

    import secrets

    from .region import Labeller

    stages: dict[str, float] = {}
    cites: list[Citable] = []
    # THE ORDER SALT, recorded. Groups are permuted per sheet so position ranks nothing, and
    # the salt travels on the record so the sheet stays reproducible from it.
    salt = secrets.token_hex(8)
    _t0 = _time.time()
    _phase("addressing")
    landings = land(text, snapshot, chart)
    stages["address"] = round(_time.time() - _t0, 3)

    # WHERE THE BIAS ATTACHES. With a transport, the typed input enters a REGION as one more
    # object and one call completes the diagram; the arrows the medium draws to it are the
    # seeds. Without one, the bias can only attach at its own address — which is right only
    # when the typed text already exists verbatim, and is the inherited defect the region
    # path exists to fix.
    # ONE LABEL SPACE PER ACT, seeded by the region. Built before anything is cited so
    # every citation in this compile — attachments and movers alike — draws from it.
    labeller = None
    att = None
    if transport is not None:
        _phase("attaching")
        _t = _time.time()
        # TURN 1 OF THE DIALOGUE. Passing a prompt is what makes this a conversational turn
        # rather than the daemon's coordinate call — the medium is seated in front of the WHOLE
        # region and answers in cited prose, so the arrows and the words come from one reply.
        # Half-collapsing this is what shipped green this morning: the propose call kept doing
        # the attachment and handed the dialogue a field of two objects, which is why it drew
        # no arrows. seed/FIXTURE-CERTIFIED-POSITIVITY.md column B is the record of it.
        from .dialogue import turn_one_prompt

        att = perturb(text, snapshot, transport, chart, system=turn_one_prompt())
        labeller = Labeller(att.region) if att.region is not None else Labeller()
        stages["attach"] = round(_time.time() - _t, 3)
        if not att.seeds:
            status = ("THE FIELD DID NOT RESPOND — " + _no_attachment(att))
            stages["total"] = round(_time.time() - _t0, 3)
            return CompiledInput(
                stages=stages,
                typed=text, compiled=f"{status}\n\n{_region_block(att, cites, labeller=labeller, snapshot=snapshot)}\n\n"
                                     f"BOUNDARY CONDITION:\n{text}",
                landings=landings, field_status=status, conditioned=False,
                relaxation=None, attachment=att, citations=cites)
        _phase("settling")
        _t = _time.time()
        rel = relax_from(att, text, snapshot, chart)
        stages["settle"] = round(_time.time() - _t, 3)
    else:
        _t = _time.time()
        rel = relax(text, snapshot, chart)
        stages["settle"] = round(_time.time() - _t, 3)

    if not rel.responded:
        status = f"THE FIELD DID NOT RESPOND — {rel.silence}"
        return CompiledInput(
            typed=text, compiled=f"{status}\n\nBOUNDARY CONDITION:\n{text}",
            landings=landings, field_status=status, conditioned=False, relaxation=rel,
            attachment=att, citations=cites)

    lines: list[str] = [
        "FIELD STATE after relaxation. The boundary condition below was applied to this "
        "corpus as a soft constraint and the field was allowed to settle; what follows is "
        "what moved.",
        f"floor: {snapshot.floor_status}",
        "",
    ]
    if att is not None:
        lines.extend(_region_block(att, cites, labeller=labeller, snapshot=snapshot).splitlines())
        lines.append("")

    moved_lines, facts = _relaxed_block(rel, snapshot, cites, salt, labeller=labeller)
    lines.extend(moved_lines)
    lines.append("")

    # THE STRUCTURE LAYER, when the question was about shape rather than displacement. The
    # signature is read off the records — all-bears-on attachment and zero arrow reach — so
    # this is a compile step, not a mode the operator has to select. See
    # engine/structure_trace.py for why relaxation cannot answer a Pi-1 question.
    sig = signature_of(att, rel)
    out_signature = sig
    if sig.structural:
        lines.append(sig.render())
        lines.extend(structure_lines(snapshot, cites, Citable, labeller=labeller))
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

    # THE RENDERER RECEIVES STATE AND THE QUESTION. NOTHING ELSE.
    #
    # It was receiving 18,474 characters of which the first eight lines explained the
    # MECHANISM — what a region is, that a hash is not a similarity, that two kinds of arrow
    # came back and are not the same fact, that both are ephemeral. Every word of that is
    # true and none of it is state, and a model handed it recited it: asked what the
    # certified positivity work establishes, it described the sampling procedure and
    # enumerated void counts. That is the prompt-strip defect one layer down — editorial in
    # the INPUT rather than in the instructions — and it is the same fix.
    #
    # The explanatory prose and the field statistics stay in the RECORD for the collapsed
    # scope view. `compiled` is what the renderer reads, and it is numbered objects, declared
    # relations, stated absences, and the question.
    scope_text = "\n".join(lines)
    state = [ln for ln in lines if _is_state(ln)]
    state = _dedupe_claims(state)
    # THE QUESTION IS NOT APPENDED HERE. `engine.dialogue._put` puts the question to the state
    # for each turn, so a copy baked into the compile appeared twice in every turn's body —
    # and on an interrogation turn the baked one is the WRONG question, since that turn is
    # answering the interrogator rather than the operator. One asker, one question.
    _phase("rendering")
    stages["render"] = round(_time.time() - _t0 - sum(stages.values()), 3)
    stages["total"] = round(_time.time() - _t0, 3)
    out = CompiledInput(typed=text, compiled="\n".join(state), landings=landings,
                        scope=scope_text, diagnostics=tuple(DIAGNOSTICS),
                        facts=facts, field_status=status, conditioned=True, relaxation=rel,
                        attachment=att, citations=cites)
    out.stages = stages
    out.signature = out_signature
    out.order_salt = salt
    out.groups = group_provenance(rel, snapshot)
    return out


#: THE RENDERER PROMPT. Wire format, grammar, and nothing else — `engine/grammar.py` holds
#: the blocks and a control asserts every one of them is tagged WIRE, GRAMMAR or STATE. What
#: used to be here was 4,889 characters, and most of it was editorial: how to open, whose
#: voice to prefer, what not to apologise for, an exhortation to say what is not there, and
#: the citation rule stated three times in three registers. Each of those sentences was added
#: in answer to a defect that should have been answered with a checker, and none of them was
#: enforceable. A rule the build cannot check is a hope.
INBOUND_SYSTEM = render_prompt()
