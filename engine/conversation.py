"""The conversation chart (move-1): a transcript -> speaker-attributed claims + a ledger.

Two outputs, both listable, both demonstrated on synthetic fixtures before any real
transcript is ingested:

1. `speaker_claims(transcript)` -> `[AttributedClaim]` — the segmentation gap closed:
   every claim carries who said it and in which turn. These are what the extractor turns
   into deltas whose provenance locator names the speaker.

2. `proposal_verdict_ledger(transcript)` -> `[ProposalVerdict]` — the load-bearing one:
   each proposal (a claim) paired with the verdict a later turn passed on it —
   **accepted / rejected / sharpened / open**. This is the *content* of the fast tape
   (`p_fast = proposals + verdicts`), the calibration signal a future K (memory kernel) and
   proposer consume. Producing it on synthetic data proves the horizon hook is real before
   the build-transcript itself is ingested.

K stays INERT at v0 (`mint_tape.act_on_mint` raises): this module only *produces* the
signal — it promotes nothing. `as_fast_tape_entries()` shows the shape K would read; it is
not wired to any actuator.

The chart is registered by a manifest row (`seed/CHARTS.json`) plus behavior functions,
with **no dispatch edit** — so the three-moves audit classifies it as *swap-base* and the
chart plug-in audit stays PASS. This module imports nothing from the engine's behavior
layer, so `normalize.py` / `extract.py` register it without an import cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Verdict = Literal["accepted", "rejected", "sharpened", "open"]

# A speaker line: "Name: utterance". Name starts uppercase so a lowercased prose colon
# ("however: ...") does not read as a speaker. A line without this prefix continues the
# current turn.
_SPEAKER_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9 ._'-]{0,39}?):\s+(.*\S)\s*$")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Verdict cues, checked reject -> sharpen -> accept so that "no, more precisely" reads as a
# rejection and "yes, but more precisely" reads as a sharpening (refinement beats bare
# assent). Matched on the casefolded response text.
_REJECT = ("that is wrong", "that's wrong", "thats wrong", "i disagree", "disagree",
           "incorrect", "not true", "is false", "no, ", "no,")
_SHARPEN = ("more precisely", "to be precise", "more exactly", "to sharpen", "sharper",
            "strictly speaking", "to qualify", "qualify", "refine", "rather, ")
_ACCEPT = ("agreed", "i agree", "that is right", "that's right", "thats right", "correct",
           "confirmed", "exactly", "indeed", "yes")

_STOP = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of", "in", "on",
    "and", "or", "not", "that", "this", "it", "its", "as", "for", "with", "by", "we",
    "you", "i", "under", "over", "no", "yes", "more", "less", "than", "then", "so",
    "but", "if", "at", "from", "into", "precisely", "exactly", "agreed", "wrong",
})


@dataclass(frozen=True, slots=True)
class Turn:
    speaker: str
    index: int
    text: str


@dataclass(frozen=True, slots=True)
class AttributedClaim:
    speaker: str
    turn: int
    claim: str
    locator: str          # "turn:{turn}:{speaker}:{sentence}"


@dataclass(frozen=True, slots=True)
class ProposalVerdict:
    proposal: str
    proposer: str
    proposal_turn: int
    verdict: Verdict
    decided_by: str | None       # speaker who passed the verdict, or None if open
    decided_turn: int | None
    cue: str | None              # the phrase that decided it
    locator: str


def parse_transcript(text: str) -> list[Turn]:
    """Split a transcript into speaker turns. Unattributed lines extend the current turn."""
    turns: list[Turn] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = _SPEAKER_RE.match(raw)
        if m:
            turns.append(Turn(speaker=m.group(1).strip(), index=len(turns),
                              text=m.group(2).strip()))
        elif turns:
            prev = turns[-1]
            turns[-1] = Turn(prev.speaker, prev.index, f"{prev.text} {raw.strip()}")
    return turns


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text) if len(s.split()) >= 3]


def speaker_claims(text: str) -> list[AttributedClaim]:
    """Output 1: every claim, attributed to its speaker and turn (segmentation gap closed)."""
    claims: list[AttributedClaim] = []
    for turn in parse_transcript(text):
        for j, sentence in enumerate(_sentences(turn.text)):
            claims.append(AttributedClaim(
                speaker=turn.speaker, turn=turn.index, claim=sentence,
                locator=f"turn:{turn.index}:{turn.speaker}:{j}",
            ))
    return claims


def _keywords(claim: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]+", claim.casefold())
            if len(t) >= 4 and t not in _STOP}


def _verdict_of(response: str) -> tuple[Verdict, str] | None:
    low = response.casefold()
    for cue in _REJECT:
        if cue in low:
            return "rejected", cue.strip()
    for cue in _SHARPEN:
        if cue in low:
            return "sharpened", cue.strip()
    for cue in _ACCEPT:
        if cue in low:
            return "accepted", cue.strip()
    return None


def proposal_verdict_ledger(text: str) -> list[ProposalVerdict]:
    """Output 2 (load-bearing): each proposal with the verdict a later turn passed on it.

    A claim R (later turn, different speaker) is the verdict on proposal P iff R carries a
    verdict cue AND shares a content keyword with P. The earliest such R decides P; a
    proposal no one takes up stays `open`. Deterministic — no randomness, a pure function of
    the transcript — so it is reproducible from the fixture bytes.
    """
    claims = speaker_claims(text)
    ledger: list[ProposalVerdict] = []
    for i, p in enumerate(claims):
        p_keys = _keywords(p.claim)
        decided: tuple[Verdict, str, AttributedClaim] | None = None
        for r in claims[i + 1:]:
            if r.speaker == p.speaker or not (p_keys & _keywords(r.claim)):
                continue
            v = _verdict_of(r.claim)
            if v is not None:
                decided = (v[0], v[1], r)
                break
        if decided is None:
            ledger.append(ProposalVerdict(p.claim, p.speaker, p.turn, "open",
                                          None, None, None, p.locator))
        else:
            verdict, cue, r = decided
            ledger.append(ProposalVerdict(p.claim, p.speaker, p.turn, verdict,
                                          r.speaker, r.turn, cue, p.locator))
    return ledger


def as_fast_tape_entries(ledger: list[ProposalVerdict]) -> list[dict[str, object]]:
    """The proposal->verdict ledger in the shape the fast tape (p_fast) carries.

    This is what a future K would read: `accepted`/`sharpened` are promotion candidates
    (they would still have to clear the Hankel > second-FDT ∧ conservative-extension gate),
    `rejected`/`open` age out. K is INERT at v0 — this returns the signal, it promotes
    nothing.
    """
    return [
        {
            "proposal": pv.proposal,
            "proposer": pv.proposer,
            "turn": pv.proposal_turn,
            "verdict": pv.verdict,
            "decided_by": pv.decided_by,
            "cue": pv.cue,
            "promotion_candidate": pv.verdict in ("accepted", "sharpened"),
        }
        for pv in ledger
    ]


# ---- chart plug-in seam: the conversation segmenter (behavior "conversation") ----
# Registered into extract._SEGMENTERS. Speaker attribution rides in the locator, so a
# conversation delta records who said it without any new field on Delta/Provenance.

def segment_conversation(text: str) -> list[tuple[str, str]]:
    return [(c.claim, c.locator) for c in speaker_claims(text)]
