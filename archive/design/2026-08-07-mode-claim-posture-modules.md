# SUPERSEDED — the mode / claim / posture modules, verbatim

    SUPERSEDED BY : the NULL SURFACE ruling, 2026-08-07.
    WHY           : these three implemented the two-coordinate surface and the speech-act
                    reader that stood in front of the tape. The null surface removes the gate
                    entirely — every utterance enters the tape directly — so there is nothing
                    left for a mode to select, a claim to pull back, or an act to read.
    KEPT AS RECORD: the docstrings argue for the design. The design was superseded; the
                    arguments are still the honest record of why it was built, including
                    OI-43's conservative-direction inversion, which was correct reasoning
                    about a mechanism that no longer exists.
    NOTE          : engine/posture.py's ACT_GRAMMAR was live on the wire and the medium was
                    answering it. That is measured history, not speculation — see
                    seed/INVENTORY.md rows 501 and 502.
    STATUS        : NOT LAW, NOT CODE. seed/ is the law; engine/ is the code.

---


## engine/mode.py

```python
"""THE WARRANT SELECTOR on the operator's input. Not a new mechanism — an unhardcoding.

`WarrantTier` has always carried AUTHORSHIP — "the operator's explicit confirmation of a
specific claim" — and the window has always used it, unconditionally, for anything typed. That
was a hardcoded choice about what typing MEANS, made once in the UI and never surfaced as the
choice it is. Typing a claim and typing a hunch are different acts and were entering at the
same warrant.

  ASSERT      the input carries AUTHORSHIP. The operator is standing behind it; the medium
              surveys and measures around it. This is what the window has always done.
  BRAINSTORM  the input carries NO warrant at all — it is bias and nothing else. It never
              becomes a claim, in this session or any other. What the medium proposes in
              response enters at EXTRACTION like every other proposal, and the operator's
              reaction to it in-session confers nothing.

"ZERO WARRANT" IS NOT A NEW TIER, and that is the point. EXTRACTION is already the floor and
already never grounds; below it there is no tier because below it there is no claim. A
brainstormed input is not a badly-warranted claim, it is not a claim — so it does not enter
the tape, and the selector is `AUTHORSHIP or nothing`, which is exactly what the type system
already expressed.

THE LOCK. A brainstorm proposal is EXTRACTION-tier REGARDLESS of what the operator says about
it during the session. Agreeing with a proposal in conversation is not the act that confers
warrant; re-asserting it through the normal path is. Without this the mode would be a
laundering channel — think out loud, like the answer, and watch it become authored — which is
precisely the "warrant conferred only at the gate" rule being routed around in the friendliest
possible way.

IT COMPOSES WITH RETAIN, and all four cells mean something:
  assert     + release   the operator states a claim, sees what moves, keeps nothing
  assert     + retain    the operator states a claim and it enters at AUTHORSHIP
  brainstorm + release   pure exploration; nothing enters, nothing is claimed
  brainstorm + retain    the medium's cited proposals enter at EXTRACTION; the prompt does not

MODE IS STAMPED ON EVERY RECORD it produces. A proposal that cannot say which act produced it
cannot be re-read later as what it was, and an era tag that omits the mode would make an
exploratory arrow indistinguishable from an asserted one the moment the session ended.
"""

from __future__ import annotations

from .types import WarrantTier

ASSERT = "assert"
BRAINSTORM = "brainstorm"
MODES = (ASSERT, BRAINSTORM)

#: What the OPERATOR'S OWN INPUT enters at. `None` means it does not enter: there is no tier
#: below EXTRACTION because below EXTRACTION there is no claim.
INPUT_TIER = {ASSERT: WarrantTier.AUTHORSHIP, BRAINSTORM: None}

#: What the MEDIUM'S proposals enter at, in either mode. Unchanged, and unchangeable by the
#: mode: the medium is a peripheral and its output is extraction whoever asked.
PROPOSAL_TIER = WarrantTier.EXTRACTION


def normalize(mode: str | None) -> str:
    """Unknown modes are ASSERT — the stricter reading of an ambiguous act.

    Defaulting the other way would let a malformed request silently strip warrant from
    something the operator meant to stand behind.
    """
    m = (mode or ASSERT).strip().lower()
    return m if m in MODES else ASSERT


def input_tier(mode: str | None):
    return INPUT_TIER[normalize(mode)]


def input_enters(mode: str | None) -> bool:
    """Does the typed text become a claim at all?"""
    return input_tier(mode) is not None


def stamp(mode: str | None) -> dict:
    """The provenance every record carries. Never omitted, so a later reader can tell an
    exploratory arrow from an asserted one after the session that produced it is gone."""
    m = normalize(mode)
    return {"mode": m,
            "input_tier": (input_tier(m).name if input_tier(m) is not None else "none"),
            "proposal_tier": PROPOSAL_TIER.name,
            "note": ("brainstorm: the typed text is bias only and never becomes a claim; what "
                     "the medium proposes enters at EXTRACTION and the operator's in-session "
                     "reaction confers nothing — re-assertion through the normal act is the "
                     "only path to warrant" if m == BRAINSTORM else
                     "assert: the typed text carries the operator's AUTHORSHIP")}


def cell(mode: str | None, retain: bool) -> str:
    """The 2x2, named. All four are meaningful acts, not a flag crossed with a flag."""
    m = normalize(mode)
    return {(ASSERT, False): "state a claim, see what moves, keep nothing",
            (ASSERT, True): "state a claim and enter it at AUTHORSHIP",
            (BRAINSTORM, False): "explore; nothing enters and nothing is claimed",
            (BRAINSTORM, True): "keep the medium's cited proposals at EXTRACTION; the prompt "
                                "does not enter"}[(m, bool(retain))]

```

## engine/claim.py

```python
"""THE AUTHORSHIP PULLBACK: the operator claims a sentence the medium said.

THE DERIVATION, because this is read off the object rather than designed. The operator's
utterance is a candidate object approaching the category, and the type system exposes exactly
two independent binary coordinates plus one constructible arrow:

  OBJECTHOOD   AUTHORSHIP or nothing — the utterance is a claim of the operator's, or it is a
               pure boundary condition and not an object at all. Binary because objecthood is
               binary. (assert / brainstorm)
  PERSISTENCE  discard or keep — the input adjoins a transient object to the diagram, and the
               question is whether that extension survives settling. Binary because a colimit
               is either taken or not. (retain)

The 2x2 is FORCED AND COMPLETE: the product of two two-element sets. No fifth state is
constructible.

THIS MODULE IS THE ONE ARROW. Firing `claim` on something the medium said constructs a NEW
object: the same surface text, the operator's authorship, entering through the ordinary inlet.
It is a VERB, not a state — an arrow the operator fires, not a place the system sits — and it
is available in any mode at any time, because the MODE governs the PROMPT'S standing and never
the gesture's. The gesture IS assert.

THIS IS NOT A NEW WRITE-POINT. The gesture invokes the EXISTING `perturb.retain` write-point
with authorship warrant and `claimed_from` provenance. The closed set — `perturb.retain`,
`walk.arrow`, `aging.decay`, `mz.promote` — is unchanged (OI-33), and a claim implemented as
any other path must trip the existing write-point control. A gesture that quietly opened a
fifth door would be the tape growing a second entrance, which is the one thing the inlet rule
exists to prevent.

ALWAYS RETAIN, and it is not a convenience: claiming-to-discard is incoherent. The gesture's
whole content is "this becomes mine", and an object that vanishes after settling was never
taken.

"ACCEPT" DOES NOT EXIST AND CANNOT BE ADDED (OI-41). It would be warrant increasing by
approval WITHOUT authorship — a third arrow up the tier poset, which has exactly two lifts: K
promotes by measurement, authorship enters by assertion. An accept button is an arrow that is
not in the diagram, and its absence is constitutional rather than an omission.

THE PULLBACK IS AUDITABLE. `claimed_from` names the record the surface came from, so a later
reader can see that this AUTHORSHIP claim began as something a model said and which act
produced it. Laundering is prevented by the gesture being explicit, not by hoping nobody
routes around it: in-session agreement, however enthusiastic, confers nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .mode import ASSERT
from .types import WarrantTier

#: What a claimed object enters at. The operator asserted it; that is what AUTHORSHIP means.
CLAIM_TIER = WarrantTier.AUTHORSHIP

#: Claiming always retains. Claiming-to-discard is incoherent — the gesture's content is that
#: this becomes the operator's, and an object discarded after settling was never taken.
CLAIM_RETAINS = True


@dataclass(frozen=True, slots=True)
class Claim:
    """One firing of the pullback."""

    surface: str               # BYTE-IDENTICAL to what was displayed. No paraphrase.
    chart: str
    claimed_from: str          # the record id the surface came from
    source_mode: str           # the mode the ORIGINAL act ran in, kept for audit
    tier: WarrantTier = CLAIM_TIER
    retains: bool = CLAIM_RETAINS
    #: The gesture is always an assertion. The mode of the act that produced the SOURCE is
    #: recorded above; it does not travel into the claim, because the mode governs the
    #: prompt's standing and never the gesture's.
    mode: str = ASSERT

    def __post_init__(self) -> None:
        if not (self.surface or "").strip():
            raise ValueError("a claim needs a surface; there is nothing to assert")
        if not (self.claimed_from or "").strip():
            raise ValueError(
                "a claim needs `claimed_from`: the pullback is auditable or it is laundering. "
                "Without the source record nobody can see that this AUTHORSHIP claim began as "
                "something a model said.")

    def as_record(self) -> dict[str, object]:
        return {"surface": self.surface, "chart": self.chart, "tier": self.tier.name,
                "mode": self.mode, "retains": self.retains,
                "claimed_from": self.claimed_from, "source_mode": self.source_mode,
                "note": ("the authorship pullback: the operator asserted a sentence the medium "
                         "produced. Same surface, operator warrant, source recorded. This is "
                         "one of exactly two lifts up the tier poset — the other is K, which "
                         "promotes by measurement (OI-41).")}


def claim(surface: str, chart: str, claimed_from: str, source_mode: str = "") -> Claim:
    """Fire the pullback. The surface travels VERBATIM: a paraphrase would be a new claim
    wearing the old one's provenance."""
    return Claim(surface=surface, chart=chart, claimed_from=claimed_from,
                 source_mode=source_mode or ASSERT)


def lifts() -> tuple[str, ...]:
    """The COMPLETE set of ways warrant rises. Stated as a function so it is assertable."""
    return ("K promotes by measurement", "authorship enters by assertion")

```

## engine/posture.py

```python
"""THE UTTERANCE'S ACT, READ AT ATTACHMENT — a gated coordinate, not a pre-set control.

Same object, different presentation. Posture, retain and claim were toggles the operator set
before speaking; here they are read OFF the speaking, as one more thing the attachment call
emits. "keep that one" is a retain intent. "that's mine" is a claim. "what if" is exploration.
Making the operator translate those into checkbox state is making them speak the machine's
language when the machine is already asking a medium to read language.

IT IS A PROPOSAL LIKE ANY OTHER. Extracted at EXTRACTION tier, through the one inlet, gated,
era-tagged, and WRONG SOMETIMES. Nothing here confers warrant: the reading decides how the
utterance is TREATED, and every lock on what can become a claim is unchanged.

READ FROM A DECLARED TOKEN, NEVER FROM PROSE. The medium emits `ACT: explore keep-nothing` or
`ACT: claim-of 7` — a closed vocabulary in the output grammar, resolve-or-void, exactly like
the arrow triples. A reading inferred from the shape of a sentence would be a fluency
judgement steering warrant, which is the one thing that must never happen.

THE CONSERVATIVE DIRECTION INVERTS HERE, and the inversion is the whole safety argument.
Everywhere else an unknown mode defaults to ASSERT, because defaulting the other way would
silently strip warrant from something the operator meant to stand behind. When the machine is
READING rather than being told, the risk reverses: a misread that invents a claim confers
authorship nobody asserted. **When unsure whether you claimed, assume you didn't.** Ambiguity
resolves to explore/keep-nothing.

MISREADS ARE VISIBLE, NEVER SILENT. Every response opens with the reading — "reading this as:
exploration, keeping nothing" — and the next utterance can correct it. A correction re-stamps
the prior record's mode with an ERA TRAIL: the original reading is kept, not overwritten, so
the record shows what was read, what it was corrected to, and when.

CLAIM-OF RESOLVES TO DISPLAYED BYTES OR VOIDS. Never paraphrased: the claimed surface must be
the sentence the operator actually saw, byte for byte, or there is no claim. A pullback onto a
reconstruction would be a new claim wearing the old one's provenance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .mode import ASSERT, BRAINSTORM

#: THE CLOSED ACT VOCABULARY. Declared tokens, matched exactly. Nothing is inferred from prose.
ASSERT_ACT, EXPLORE_ACT, CLAIM_ACT = "assert", "explore", "claim-of"
ACTS = (ASSERT_ACT, EXPLORE_ACT, CLAIM_ACT)

KEEP, DISCARD = "keep", "keep-nothing"
PERSISTENCE = (KEEP, DISCARD)

#: THE CONSERVATIVE READING. Explore, keep nothing. The stricter direction inverts when the
#: machine is reading rather than being told: a misread that invents a claim confers authorship
#: nobody asserted, so ambiguity must never resolve toward claiming.
CONSERVATIVE = (EXPLORE_ACT, DISCARD)

#: `ACT: <act> <persistence>` or `ACT: claim-of <n> <persistence>`. One line, one grammar.
#: CASE-EXACT, deliberately. An earlier version matched case-insensitively and then folded the
#: token to canonicalise it — which the referee sweep refused, correctly: folding is folding
#: whatever it is folding. The grammar declares lowercase tokens, so a token in another case
#: simply does not match and reads conservatively. That is resolve-or-void applied to case, and
#: it removes the fold rather than arguing for an exemption.
#: THE SEPARATOR IS WHITESPACE OR A COMMA, and that is a LEXING fact, not a tolerance for
#: meaning. `ACT: explore, banana` still voids. It is here because the grammar used to
#: DESCRIBE the form in prose — "then keep or keep-nothing" — and English "then X" invites a
#: comma, so the medium wrote `ACT: explore, keep` on live traffic and the line read as absent.
#: The grammar below now SHOWS the form instead of describing it, which is the real fix; this
#: is the lexer no longer disagreeing with the sentence that asked for the token.
_SEP = r"(?:\s*,\s*|\s+)"
_ACT = re.compile(r"^\s*ACT:\s*(assert|explore|claim-of)(?:" + _SEP + r"(\d+))?"
                  r"(?:" + _SEP + r"(keep|keep-nothing))?\s*$", re.M)


@dataclass(frozen=True, slots=True)
class Reading:
    """How the utterance's act was read. A proposal — gated, era'd, correctable."""

    act: str = EXPLORE_ACT
    persistence: str = DISCARD
    claim_index: int | None = None
    #: Why this reading rather than another. Never empty: a reading nobody can question is a
    #: reading nobody can correct.
    reason: str = ""
    era: str = ""
    #: Readings this one replaced, oldest first. A correction keeps the trail rather than
    #: overwriting: the record must show what was read, what it became, and when.
    superseded: tuple = ()

    @property
    def mode(self) -> str:
        """The warrant coordinate this reading implies. `claim-of` is an assertion."""
        return ASSERT if self.act in (ASSERT_ACT, CLAIM_ACT) else BRAINSTORM

    @property
    def retains(self) -> bool:
        return self.persistence == KEEP or self.act == CLAIM_ACT

    def render(self) -> str:
        """The line every response opens with. A misread must be visible to be correctable."""
        what = {ASSERT_ACT: "a claim of yours", EXPLORE_ACT: "exploration",
                CLAIM_ACT: f"a claim of sentence [{self.claim_index}]"}[self.act]
        kept = "keeping it" if self.retains else "keeping nothing"
        return f"reading this as: {what}, {kept}"

    def as_record(self) -> dict[str, object]:
        return {"act": self.act, "persistence": self.persistence,
                "claim_index": self.claim_index, "mode": self.mode, "retains": self.retains,
                "reason": self.reason, "era": self.era,
                "superseded": [dict(s) for s in self.superseded],
                "display": self.render()}


def parse(raw: str, era: str = "") -> Reading:
    """Read the declared ACT token. Anything else is the conservative reading, said so.

    Resolve-or-void: an absent, malformed or duplicated ACT line does not become a guess. It
    becomes explore/keep-nothing WITH THE REASON, because a default nobody is told about is
    indistinguishable from a reading.
    """
    hits = _ACT.findall(raw or "")
    if not hits:
        return Reading(*CONSERVATIVE, reason=(
            "the medium emitted no ACT line, so the act was not read. Explore/keep-nothing is "
            "the conservative reading: assuming a claim would confer authorship nobody made."),
            era=era)
    if len(hits) > 1:
        return Reading(*CONSERVATIVE, reason=(
            f"{len(hits)} ACT lines came back and nothing says which is the reading. Ambiguity "
            f"resolves away from claiming."), era=era)
    act, index, persistence = hits[0]
    if act == CLAIM_ACT and not index:
        return Reading(*CONSERVATIVE, reason=(
            "claim-of with no sentence number resolves to nothing, and a claim of an "
            "unspecified sentence is not a claim."), era=era)
    return Reading(act=act,
                   persistence=persistence or DISCARD,
                   claim_index=int(index) if index else None,
                   reason=f"the medium read the act as {act!r}", era=era)


def resolve_claim(reading: Reading, displayed: dict) -> tuple[str, str]:
    """(surface, void_reason). The claimed sentence's DISPLAYED BYTES, or nothing.

    `displayed` maps sentence index -> the exact bytes the operator saw. A claim-of that does
    not resolve VOIDS: reconstructing the sentence, or paraphrasing it, would make the pullback
    land on something the operator never read.
    """
    if reading.act != CLAIM_ACT:
        return "", "not a claim"
    n = reading.claim_index
    if n not in displayed:
        return "", (f"sentence [{n}] was not displayed in the response being claimed from, so "
                    f"there are no bytes to claim. VOID rather than reconstructed.")
    surface = displayed[n]
    if not (surface or "").strip():
        return "", f"sentence [{n}] displayed as empty"
    return surface, ""


def correct(prior: Reading, new: Reading) -> Reading:
    """Re-stamp a prior reading, KEEPING the trail.

    The original is not overwritten. A record that silently becomes what it was corrected to
    cannot show that it was ever misread, and a misread nobody can see is a misread nobody
    fixes twice.
    """
    trail = tuple(prior.superseded) + ({k: v for k, v in prior.as_record().items()
                                        if k != "superseded"},)
    return Reading(act=new.act, persistence=new.persistence, claim_index=new.claim_index,
                   reason=f"corrected by the operator: {new.reason}", era=new.era,
                   superseded=trail)


#: The line added to the attachment prompt. Codomain syntax, one sentence — the razor.
#: SHOWN, NOT DESCRIBED. The previous wording described the line in English and the medium
#: answered in English — `ACT: explore, keep` — which the lexer refused, so the whole reading
#: fell to the conservative default on live traffic. This is the same move REGION_SYSTEM makes
#: for arrow forms: enumerate the form and the wrong form has nothing to be written in.
#: The instruction ends with its ONE period and the forms follow as a list, so there is no
#: trailing punctuation for the medium to copy onto the line — `ACT: explore keep.` voids.
ACT_GRAMMAR = ("On its own line write exactly one of these six lines, character for character. "
               "ACT: assert keep-nothing  |  ACT: assert keep  |  "
               "ACT: explore keep-nothing  |  ACT: explore keep  |  "
               "ACT: claim-of <n> keep-nothing  |  ACT: claim-of <n> keep")

```
