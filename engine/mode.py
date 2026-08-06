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
