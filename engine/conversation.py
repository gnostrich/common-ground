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


#: THE TWO ERAS, and why this is a tag rather than a purge.
#:
#: Until `engine/referee_sweep.py` caught it, which turn ANSWERED which claim was decided by
#: `p_keys & _keywords(r.claim)` — an intersection of word bags standing in for aboutness.
#: Every verdict in every ledger built before the replacement rests on that pairing. They are
#: not known-wrong: an overlap-paired verdict is often the right one, and the cue that decided
#: it came from a declared list either way. They are UNCONFIRMED, which is a different status,
#: and it is the same one lite-era arrows and quarantined stock carry.
#:
#: So they are tagged, not trusted and not deleted — the third application of the pattern.
#: Anything reading this ledger for a signal (K-calibration, the conversation chart's
#: accept/reject) treats `keyword-era` as a LEAD pending re-confirmation, exactly as it treats
#: a lead-model arrow. Deleting them would throw away work that may well be sound; trusting
#: them would launder a resemblance mechanism's output into a warrant.
KEYWORD_ERA = "keyword-era"
ADJACENCY_ERA = "adjacency-era"

#: Verdicts a `keyword-era` record may not carry into a promotion path without re-confirmation.
UNCONFIRMED_ERAS = frozenset({KEYWORD_ERA})


def is_lead(pv: "ProposalVerdict") -> bool:
    """A verdict whose PAIRING came from the replaced mechanism. Not wrong — unconfirmed."""
    return pv.verdict_method in UNCONFIRMED_ERAS


def era_of_record(rec: dict) -> str:
    """The era of a verdict READ BACK FROM DISK, where an absent tag means the keyword era.

    The dataclass defaults to `adjacency-era`, which is correct for a record this build
    produced. It is exactly wrong for a record persisted before the tag existed: those were
    all paired by the word bag, and defaulting them to the new era would launder the thing
    being quarantined. A missing field is therefore read as the OLD era, never the current
    one — the same rule `engine/staleness.py` applies when it refuses to read `unknown` as
    `fresh`.
    """
    return str(rec.get("verdict_method") or KEYWORD_ERA)


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
    #: WHICH MECHANISM ASSIGNED THIS VERDICT. `keyword-era` records were paired by a word-bag
    #: intersection that `engine/referee_sweep.py` has since refused; `adjacency-era` records
    #: were paired by declared turn structure. The distinction travels WITH the record because
    #: a verdict is only as good as the pairing that produced it, and the era cannot be
    #: reconstructed from the record afterwards.
    verdict_method: str = ADJACENCY_ERA


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
    verdict cue from the DECLARED cue list and P is the most recent claim R could be
    answering — the latest preceding claim by a different speaker. Turn order and speaker
    identity are declared conversation structure; nothing here compares the words of P and R.

    THIS REPLACED A KEYWORD INTERSECTION, and the replacement is the point. The old rule
    required R to "share a content keyword" with P: two word bags, `p_keys & _keywords(...)`,
    with the overlap standing in for aboutness. That is similarity substituted for a declared
    relation — the move `seed/OBJECT-AMENDED.md` records as deleted — sitting inside the
    thing that decides every verdict in this ledger. `engine/referee_sweep.py` is the control
    that now refuses it, and it found this one rather than a person finding it.

    THE APPROXIMATION IS STATED, because adjacency is not free of error either. When a
    speaker makes several claims in a row and the reply carries one cue, this attributes the
    verdict to the LAST of them. That is a real limitation of turn adjacency and it is
    recorded here rather than papered over with a resemblance test that would be wrong in a
    way nobody could see. A conversation chart that needs finer attribution needs a declared
    reply-to relation in the transcript, not a better guess.

    Deterministic — a pure function of the transcript — so it is reproducible from the
    fixture bytes.
    """
    claims = speaker_claims(text)
    ledger: list[ProposalVerdict] = []
    for i, p in enumerate(claims):
        decided: tuple[Verdict, str, AttributedClaim] | None = None
        for j, r in enumerate(claims[i + 1:], start=i + 1):
            if r.speaker == p.speaker:
                continue
            v = _verdict_of(r.claim)
            if v is None:
                continue
            # ADJACENCY, DECLARED. R answers the latest claim before it by a speaker other
            # than R's own. If some later claim by p's speaker sits between p and r, then r
            # is answering that one, not p — and p stays open rather than collecting a
            # verdict it did not receive.
            latest = max((k for k in range(i, j) if claims[k].speaker != r.speaker),
                         default=None)
            if latest != i:
                break
            decided = (v[0], v[1], r)
            break
        if decided is None:
            ledger.append(ProposalVerdict(p.claim, p.speaker, p.turn, "open",
                                          None, None, None, p.locator,
                                          verdict_method=ADJACENCY_ERA))
        else:
            verdict, cue, r = decided
            ledger.append(ProposalVerdict(p.claim, p.speaker, p.turn, verdict,
                                          r.speaker, r.turn, cue, p.locator,
                                          verdict_method=ADJACENCY_ERA))
    return ledger


def as_fast_tape_entries(ledger: list[ProposalVerdict]) -> list[dict[str, object]]:
    """The proposal->verdict ledger in the shape the fast tape (p_fast) carries.

    This is what a future K would read: `accepted`/`sharpened` are promotion candidates
    (they would still have to clear the Hankel > second-FDT ∧ conservative-extension gate),
    `rejected`/`open` age out. K is INERT at v0 — this returns the signal, it promotes
    nothing.

    A `keyword-era` verdict is NOT a promotion candidate, whatever it says. Its pairing came
    from the word-bag mechanism, so the verdict is a LEAD: it survives, it is visible, and it
    cannot carry into a promotion path until a re-run under declared adjacency confirms it.
    The record says which era it came from and why it is held, so a reader downstream is never
    left inferring that an absent candidacy means a negative verdict.
    """
    return [
        {
            "proposal": pv.proposal,
            "proposer": pv.proposer,
            "turn": pv.proposal_turn,
            "verdict": pv.verdict,
            "decided_by": pv.decided_by,
            "cue": pv.cue,
            "verdict_method": pv.verdict_method,
            "lead": is_lead(pv),
            "promotion_candidate": (pv.verdict in ("accepted", "sharpened")
                                    and not is_lead(pv)),
            "held": ("paired by the replaced keyword-overlap mechanism; re-run under declared "
                     "adjacency to confirm" if is_lead(pv) else ""),
        }
        for pv in ledger
    ]


# ---- chart plug-in seam: the conversation segmenter (behavior "conversation") ----
# Registered into extract._SEGMENTERS. Speaker attribution rides in the locator, so a
# conversation delta records who said it without any new field on Delta/Provenance.

def segment_conversation(text: str) -> list[tuple[str, str]]:
    return [(c.claim, c.locator) for c in speaker_claims(text)]
