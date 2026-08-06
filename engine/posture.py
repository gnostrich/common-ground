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
