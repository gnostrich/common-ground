"""A PERTURBATION IS A REGION RELAXATION. One call, one diagram, one mechanism.

This file exists because there were two. The sampler asked the medium to complete a region;
the window ran a different thing — a candidate list ordered by declared degree, cut to a call
budget, interrogated twelve pairs at a time — and the two stood side by side doing one job.
That is the shape `engine/region`'s own docstring calls forbidden, and the window had the worse
half of it: forty-eight claims out of thirty-seven thousand, each asked in isolation, which
reads exactly like a lookup because structurally it is one.

What replaces it is not a better candidate list. It is the region, unchanged, with the typed
input as ONE MORE OBJECT in it:

    typed text -> addressed exactly (gate 1, unchanged)
               -> entered into a region as [0|bias], beside arrow-rich provenance-near claims
               -> ONE call: declared arrows in, implied arrows in, medium completes the diagram
               -> arrows touching [0]        = ATTACHMENT: ephemeral, conditioning-only
               -> arrows among corpus objects = ordinary EXTRACTION, same as the walk's
               -> attachment points seed `engine/relax`; settlement runs; what moved is the answer

Every step after addressing is `engine.region` code the walk calls too: `build_region`,
`render_region`, `REGION_SYSTEM`, `parse_region`, `residuals`, `arrows_from`. This module holds
no wire format, no prompt, no parser and no kind vocabulary of its own. That is what makes it
one mechanism rather than two that agree.

**There is no budget, so there is nothing to disclaim.** The old path reported "48 of 28,398
candidates asked; the rest are UNMEASURED" — true, and a confession that the unit was wrong. A
region is the unit of measurement. It is a SAMPLE of the corpus and the window says so plainly,
but it is not a truncated interrogation of a list, because there is no list.

**The window extracts.** Arrows the medium draws among the corpus objects are real proposals at
extraction tier, identical in kind and warrant to the walk's, and they are returned for the
operator to send through the one inlet. Asking a question therefore does the same work the
sampler does — the corpus grows from being used.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MORPHISM — a proposer into D. The same proposer, the same prompt, pointed at a
region that has a boundary condition in it.
Q2 is why the bias must be IN the diagram: a typed input is an object with no morphisms until
morphisms are proposed for it, so it has no image under any functor and cannot propagate. It
is not enough to ask about it; it has to be an object the medium can draw arrows to.
Q5 is the load-bearing check and it passes ONLY as a REPLACEMENT. `engine/attach` is deleted
by this commit, not supplemented — standing beside it, this would be the second mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .corpus_state import CorpusSnapshot
import time as _time

from .transcript import CURRENT as TRANSCRIPT

from .region import (BEARS_ON, BIAS_CHART, REGION_SIZE, REGION_SYSTEM, Region, anchor_for,
                     arrows_from, build_region, parse_region, render_region, residuals)
from .relax import Relaxation, relax
from .types import WarrantTier

#: Attachment enters where every LM proposal enters, and cannot ground or clamp. It does not
#: enter at all, in fact — it evaporates — but the tier is stated because the operator is
#: standing on it while reading the answer.
ATTACH_TIER = WarrantTier.EXTRACTION


@dataclass(frozen=True, slots=True)
class Attachment:
    """One arrow the medium drew to the boundary condition. Ephemeral by construction.

    It is never journalled, never composed, never counted as an arrow and never in the atlas.
    That is not enforced here by remembering to: `region.arrows_from` drops anything touching
    the `bias` chart, so there is no route by which one of these becomes a Correspondence.
    """

    kind: str                                 # bears_on | same_claim | refines | instance_of
    dst_slot: str
    dst_chart: str
    dst_nu: str
    evidence: str
    tier: str = ATTACH_TIER.name

    @property
    def is_bias_only(self) -> bool:
        """True for `bears_on`. Kept as a property because the window prints the two apart:
        a question that is ABOUT a claim and a claim that RESTATES it are different facts."""
        return self.kind == BEARS_ON

    def as_record(self) -> dict[str, object]:
        return {"kind": self.kind, "tier": self.tier, "to": self.dst_slot[:16],
                "chart": self.dst_chart, "nu": self.dst_nu,
                "evidence": self.evidence[:400], "ephemeral": True}


@dataclass(slots=True)
class Perturbation:
    """What one call produced: where the input attached, what else the region yielded, silence."""

    typed_slot: str = ""
    typed_chart: str = ""
    typed_nu: str = ""
    region: Region | None = None
    attachment: list[Attachment] = field(default_factory=list)
    #: Corpus-to-corpus arrows from the SAME call. Ordinary extraction; the window's own yield.
    extracted: list = field(default_factory=list)
    residual: object | None = None             # region.Residual — the full reading discipline
    void: int = 0
    calls: int = 0
    cost: float = 0.0
    error: str = ""
    #: What the medium SAID on turn 1, verbatim. Testimony, not extraction.
    prose: str = ""
    #: HOW THE UTTERANCE'S ACT WAS READ — a gated proposal, displayed at the top of every
    #: response so a misread is visible and correctable rather than silent.
    #: The region could not be aimed — no live arrow anywhere to aim it at. Stated, because
    #: unstated it looks exactly like a region that was aimed.
    unanchored: bool = False
    note: str = ""

    #: THE DISCRIMINATION GUARD, symmetric to the acceptance guard on the walk.
    #: A medium that attaches the boundary condition to EVERY object in the region has not
    #: related it to anything — the same degeneracy class as force-matching, where a proposer
    #: that answers `same_claim` to everything carries no information in any single answer.
    #: The battery measured 59 attachments out of a 59-claim region: total attachment,
    #: reported as a rich result. The fraction is computed per perturbation, logged, and
    #: crosses into RED at `INDISCRIMINATE`.
    #:
    #: The threshold is stated rather than tuned. A boundary condition genuinely about a
    #: coherent neighbourhood can legitimately touch most of it, so this is not set low; what
    #: it refuses is the limit case where the medium drew an arrow to everything it was shown
    #: and the answer therefore rests on the region's membership rather than on any relation.
    INDISCRIMINATE = 0.9

    @property
    def attachment_fraction(self) -> float:
        """Attached corpus objects over corpus objects SHOWN. The bias itself is not a corpus
        object and is excluded from the denominator, so a full sweep reads as 1.0 exactly."""
        shown = max(0, self.members - 1)
        if not shown:
            return 0.0
        return len({a.dst_slot for a in self.attachment}) / shown

    @property
    def indiscriminate(self) -> bool:
        """RED: the medium attached to (almost) everything it was shown."""
        return self.attachment_fraction >= Perturbation.INDISCRIMINATE

    @property
    def discrimination(self) -> dict[str, object]:
        f = self.attachment_fraction
        return {
            "attached": len({a.dst_slot for a in self.attachment}),
            "shown": max(0, self.members - 1),
            "fraction": round(f, 4),
            "threshold": Perturbation.INDISCRIMINATE,
            "red": self.indiscriminate,
            "note": ("the medium drew an arrow to essentially every object it was shown, so "
                     "the attachment carries no information about which claims the input "
                     "bears on — the same degeneracy as a proposer that answers the same "
                     "relation to everything" if self.indiscriminate else ""),
        }

    @property
    def consulted(self) -> bool:
        """Was the medium actually asked? The battery's no-silent-zero property turns on this:
        silence after a call is a decline, silence before one is a filter, and the window has
        to be able to tell the operator which it was."""
        return self.calls > 0

    def trace(self) -> dict[str, object]:
        """WHAT WAS ASKED, of whom, over what — so silence is never a bare zero.

        The standing battery requires that every input yields either a conditioned region or
        this: which question was put, how many objects were seated in the diagram, and what
        came back. A silent zero with no trace is the failure this exists to make impossible.
        """
        return {
            "consulted": self.consulted,
            "question": ("complete the diagram: which corpus objects, and which of them bear "
                         "on the boundary condition at index 0"),
            "seated": self.members,
            "corpus_objects": max(0, self.members - 1),
            "declared_in": len(self.region.declared) if self.region else 0,
            "implied_in": len(self.region.implied) if self.region else 0,
            "attached": len(self.attachment),
            "extracted": len(self.extracted),
            "void": self.void,
            "unanchored": self.unanchored,
            "note": self.note,
            "error": self.error,
        }

    @property
    def seeds(self) -> set[str]:
        """Corpus addresses the boundary condition attached to. `engine/relax` starts here."""
        return {a.dst_slot for a in self.attachment}

    @property
    def members(self) -> int:
        return len(self.region.members) if self.region else 0

    @property
    def region_id(self) -> str:
        return self.region.region_id if self.region else ""

    def as_record(self) -> dict[str, object]:
        return {
            "typed_slot": self.typed_slot[:16], "typed_chart": self.typed_chart,
            "region_id": self.region_id, "members": self.members,
            "clamp": self.region.clamp[:16] if self.region else "",
            "declared": len(self.region.declared) if self.region else 0,
            "implied": len(self.region.implied) if self.region else 0,
            "attachment": [a.as_record() for a in self.attachment],
            "attached": len(self.attachment),
            "discrimination": self.discrimination,
            "extracted": len(self.extracted),
            # TURN 1'S WORDS, on the record the window reads. Without this the dialogue
            # cannot seed its first turn and spends a call re-asking a smaller field.
            "prose": self.prose,
            "void": self.void, "calls": self.calls, "cost": round(self.cost, 6),
            "error": self.error,
            "note": ("The typed input entered a REGION as one more object, over the pseudo-"
                     "chart `bias`, and one call completed the diagram. Arrows to the bias "
                     "object are attachment and are EPHEMERAL: conditioning-only, never "
                     "journalled, never composable, never counted. Arrows among the corpus "
                     "objects are ordinary extraction at the same tier the sampler produces. "
                     "The region is a SAMPLE of the corpus chosen by declared structure — it "
                     "is not the part that matches the question, and no text was compared."),
        }


def perturb(text: str, snapshot: CorpusSnapshot, transport, chart: str = "english",
            size: int = REGION_SIZE, quarantined: frozenset = frozenset(),
            system: str = "") -> Perturbation:
    """Put the typed text in a diagram and let the medium complete it. Exactly one call.

    THE TYPED TEXT GOES TO THE MEDIUM RAW. It used to be segmented by the claim extractor
    first, so a question or a bare topic that yielded no spans bounced before the field was
    ever consulted — and "the field did not respond" then meant a parser had filtered the
    input. That is an ingestion rule governing the bias path, the same class of defect as
    attachment inheriting the identity rule. The extractor's span-typing remains for corpus
    ingestion and for anything the operator proposes into the tape; a bias is neither.
    """
    from .normalize import address

    out = Perturbation()
    if not text.strip():
        out.error = "nothing was typed"
        return out

    # Addressed FIRST, and unconditionally. Gate 1 does not need a model, a corpus or a
    # region — so even the degenerate cases below carry a real address, which is what lets
    # `commit` retain the claim by the ONE path instead of a caller inventing a second one.
    slot, nu_value = address(chart, text, "assert")
    out.typed_slot, out.typed_chart, out.typed_nu = slot, chart, nu_value

    if transport is None:
        # NO MODEL. Situating is an LM proposal, so without one the input cannot be
        # situated at all — and the tempting fallback, dropping the claim on the tape
        # unsituated and calling it normal, is precisely the organ that was removed. It is
        # a stated degenerate case of this path, not a second path: `commit` will retain an
        # isolated claim and say so, which is what Q2 says an object with no morphisms is.
        out.error = ("no model is configured, so the input could not be put to a region. "
                     "It has an address and nothing else: an object with no morphisms.")
        return out
    if snapshot.empty:
        out.error = "the corpus is empty"
        return out

    # The TYPED TEXT reaches the seeder, so a question naming material the corpus
    # literally holds is sampled from there rather than from the walk's history.
    anchor = anchor_for(snapshot, slot, quarantined, text=text, chart=chart)
    region = build_region(snapshot, clamp=anchor, size=size, quarantined=quarantined,
                          bias=(slot, nu_value, text))
    out.region = region
    # A snapshot with no live arrow has no arrow-rich neighbourhood, so `anchor_for` returns
    # nothing and `build_region` falls back to the chart-spanning directory — the SAME region
    # for every question, with an empty declared section. That is a real state of the corpus,
    # but silently it reads as "your question landed here", so it is named. The shape was
    # measured: the on-disk snapshot carries 69,446 slots and zero arrows, because the arrows
    # live in the proposer's journal and are laid over the read view by the caller. A caller
    # that forgets makes every perturbation identical and nothing says so.
    out.unanchored = not anchor
    if not anchor:
        out.note = ("no arrow-rich neighbourhood exists: this snapshot carries no declared "
                    "arrow, so the region could not be aimed and is the corpus's most "
                    "chart-spanning directory instead. Every input gets the same one. If the "
                    "corpus does have arrows, they were not laid over this read view.")
    if len(region.members) < 2:
        out.error = ("no corpus claim carries a declared arrow, so there is no region to "
                     "perturb — the field has no structure for a boundary condition to reach")
        return out

    try:
        # THE ATTACHMENT CALL IS RECORDED, and it is the one that matters most: it decides
        # what the answer can possibly be about. Recording only the render call would show
        # the answer's input and hide its cause.
        # THE DAEMON'S PROMPT IS THE DEFAULT, and that is the whole separation. The
        # unattended walk passes nothing and gets REGION_SYSTEM — coordinates only, no prose,
        # forever. The interactive path passes the dialogue's prompt, which is the same wire
        # legend plus the citation grammar. Two paths, one call site, and the daemon cannot
        # acquire a dialogue by accident because acquiring one takes an argument.
        _sys, _user = (system or REGION_SYSTEM), render_region(region)
        _t = _time.time()
        raw, usage = transport(_sys, _user)
        # NO ACT IS READ. The null surface removed the question: every utterance enters the
        # tape as an authored record, so there is no mode to select and nothing for a speech-act
        # reader to decide. The reply carries arrows and nothing else.
        TRANSCRIPT.record("turn 1" if system else "propose", _sys, _user, raw or "",
                          model=str((usage or {}).get("model") or ""),
                          seconds=_time.time() - _t)
    except Exception as exc:                      # a dead call is reported, never silent
        out.error = f"{type(exc).__name__}: {exc}"
        return out
    out.calls = 1
    out.cost = float((usage or {}).get("cost") or 0.0)

    # TURN 1'S PROSE, kept. The dialogue needs the medium's own words — the arrows are
    # parsed out here, but the sentences are testimony and the answer turn is put to the
    # field they moved. Dropping the words was how the half-collapse lost them.
    out.prose = raw or ""
    proposals = parse_region(raw, region)
    res = residuals(proposals, region)
    out.residual = res
    out.void = len(res.void)

    for p in res.attachment:
        other = p.dst if p.src.chart == BIAS_CHART else p.src
        out.attachment.append(Attachment(kind=p.kind, dst_slot=other.slot,
                                         dst_chart=other.chart, dst_nu=other.nu,
                                         evidence=p.evidence))
    # The corpus-to-corpus half of the same answer. `arrows_from` drops bias-touching
    # proposals itself, so this cannot leak an attachment into the extraction stream.
    out.extracted = arrows_from(res.novel, proposer="lm", prompt_hash="region")
    return out


#: THE PERSISTENCE FLAG. Ask and propose are one act; this is the only thing that differs.
RELEASE, RETAIN = "release", "retain"
MODES = (RELEASE, RETAIN)


@dataclass(slots=True)
class Retention:
    """What committing a perturbation kept, and what it let go — with the reason for each.

    ASK and PROPOSE were two mechanisms doing overlapping work: `propose` ran the extractor
    and the LM proposer against a fresh Current that knew nothing about the corpus, while
    `ask` ran a region relaxation against the real one. So a proposed claim arrived with no
    position in the field, and the relaxation that could have situated it had already been
    run and thrown away by the other button.

    They are one act with a persistence flag. The call is BYTE-IDENTICAL in both modes — same
    region, same prompt, same parse — and the flag decides only what survives it. That is
    strictly better under Q5 than two mechanisms that agree: there is nothing left to drift.

      RELEASE (ask)     — everything about [0] evaporates. The answer was conditioned by it
                          and that is all it was for.
      RETAIN (propose)  — [0] enters the fast tape as a claim at EXTRACTION tier, and its
                          correspondence-kind attachments are retained as proposals. A
                          proposed claim therefore arrives PRE-SITUATED, by the same
                          relaxation that conditioned the answer.

    `bears_on` is released in BOTH modes, and that is not an oversight. It is not a morphism
    of the base; retaining one would put a fourth kind into the corpus vocabulary by the back
    door, which is the exact thing the attachment law exists to prevent. An aboutness relation
    between a question and a claim is a boundary condition, and boundary conditions do not
    persist. When that is all a perturbation produced, this says so rather than retaining
    nothing quietly.

    Corpus-to-corpus arrows are kept in BOTH modes, unchanged: they are ordinary extraction
    and have nothing to do with [0].
    """

    mode: str = RELEASE
    claim: object | None = None                # the Delta [0] entered as, when retained
    arrows: tuple = ()                         # attachment arrows retained as proposals
    released: tuple = ()                       # attachments deliberately not retained
    released_reason: str = ""
    extracted: int = 0                         # corpus arrows — kept either way
    note: str = ""

    def as_record(self) -> dict[str, object]:
        return {"mode": self.mode, "retained_claim": bool(self.claim),
                "retained_arrows": len(self.arrows), "released": len(self.released),
                "released_reason": self.released_reason, "extracted": self.extracted,
                "note": self.note}


def commit(pert: Perturbation, tape=None, mode: str = RELEASE,
           source: str = "me") -> Retention:
    """Apply the persistence flag. The perturbation itself is already done and is not re-run.

    Retained material lands on the FAST tape at extraction tier, which is where it must land:
    only `K` promotes to the slow side, and nothing here confers warrant. It then AGES —
    see `engine/aging` — because retention without decay is the tape becoming a second corpus
    by accretion, which is NELL at one remove and is what the memory kernel was the answer to.
    """
    from . import EngineError
    from .correspondence import Correspondence
    from .region import BEARS_ON

    if mode not in MODES:
        raise EngineError(f"mode must be one of {MODES}, not {mode!r}")

    out = Retention(mode=mode, extracted=len(pert.extracted))
    bias_only = [a for a in pert.attachment if a.kind == BEARS_ON]
    out.released = tuple(bias_only)
    out.released_reason = (
        "`bears_on` is not a morphism of the base. It is an aboutness relation between a "
        "boundary condition and a claim, and retaining one would put a fourth kind into the "
        "corpus vocabulary. Released in both modes, by rule rather than by budget.")

    if mode == RELEASE:
        out.note = ("perturb-and-release: [0] and every arrow to it evaporated. The answer "
                    "was conditioned by them and that is all they were for.")
        return out

    corresponds = [a for a in pert.attachment if a.kind != BEARS_ON]
    if tape is not None and pert.typed_slot:
        out.claim = _bias_delta(pert)
        tape.propose(out.claim, source)

    kept = []
    for a in corresponds:
        try:
            kept.append(Correspondence(
                src_chart=pert.typed_chart, src_slot=pert.typed_slot,
                dst_chart=a.dst_chart, dst_slot=a.dst_slot, kind=a.kind,
                tier=ATTACH_TIER, proposer="lm", prompt_hash="region",
                evidence=(a.evidence,)))
        except EngineError:
            continue          # refused (intra-chart, self-pair) — dropped, never coerced
    out.arrows = tuple(kept)
    tail = ("Nothing here is promoted — only K crosses to the slow side — and everything "
            "retained AGES (D14).")
    if kept:
        out.note = (
            f"perturb-and-retain: [0] entered the fast tape as a claim at EXTRACTION tier "
            f"and {len(kept)} attachment arrow(s) were retained as proposals, so it arrives "
            f"PRE-SITUATED by the same relaxation that conditioned the answer. {tail}")
    else:
        # NOT situated, and it must not say it was. An earlier version printed the
        # pre-situated sentence unconditionally, so a claim that attached to nothing — or
        # that never reached a model at all — reported itself as positioned in the field.
        # That is a false statement about the mechanism in a string the operator reads.
        why = (f" The region call reported: {pert.error}" if pert.error else
               " Every attachment the medium drew was `bears_on`, which is a boundary "
               "relation and cannot persist." if bias_only else
               " The medium was consulted and drew no arrow to it.")
        out.note = (
            f"perturb-and-retain: [0] entered the fast tape as a claim at EXTRACTION tier "
            f"and it is ISOLATED — no attachment arrow was retained, so it has no morphisms "
            f"and cannot propagate. That is what Q2 says an unattached object is, and it is "
            f"a real state rather than a failure.{why} {tail}")
    return out


def _bias_delta(pert: Perturbation):
    """[0] as a Delta at EXTRACTION tier, at the address the region already used.

    The SAME address the medium saw — not a re-extraction. Running the claim extractor here
    would segment the text into spans and retain something other than the object that was in
    the diagram, so the thing retained would not be the thing the relaxation was about.
    """
    from .types import Delta, Provenance, Warrant

    return Delta(
        slot=pert.typed_slot, chart=pert.typed_chart, type="assert", value="T",
        confidence=0.5, warrant=Warrant(ATTACH_TIER),
        provenance=Provenance(source="me", doc_id="typed", locator="perturb[0]"),
        surface=pert.typed_nu, nu=pert.typed_nu)


def relax_from(perturbation: Perturbation, text: str, snapshot: CorpusSnapshot,
               chart: str = "english") -> Relaxation:
    """Settle the corpus with the boundary condition applied at its attachment points.

    The arrows the same call extracted are laid over the READ VIEW so the perturbation can
    travel them. They are extraction tier and are written nowhere; `Moved.weakest_tier` reports
    EXTRACTION on any path that used one, which is how the operator sees that a hop rests on a
    proposal made in this very call rather than on a confirmed arrow.
    """
    return relax(text, snapshot, chart, seeds_from=perturbation.seeds or None,
                 extra_arrows=list(perturbation.extracted) or None)
