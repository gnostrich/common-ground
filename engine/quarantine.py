"""Arrows that are LEADS, not evidence, and the three places they must not act.

A walk run whose regions were 44% structurally ineligible produced 2.7% acceptance and
entered 1,455 arrows anyway. Those arrows were proposed by the same proposer through the same
inlet as every other, so nothing about their tier or provenance marks them — but the DIAGRAM
they were completing was malformed, and an arrow named against a malformed diagram is a lead
somebody should re-ask, not a fact the field may stand on.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MEASURE — it partitions the fast tape into acting and non-acting halves.
Q5: it creates no second write path and no second proposer. Quarantined arrows stay in the
journal in full; what is withdrawn is their ability to ACT.

Three exclusions, and they are the whole policy:

  * composition closure — a quarantined arrow implies nothing, so no residual is ever
    measured against a composite built on a lead,
  * region assembly — arrow-rich-first must not count them, or the walk aims itself at its
    own bad output,
  * the conditioning path — the window must not relax across them.

Re-entry is by RE-CONFIRMATION: a healthy-run region relaxation that names the arrow again
promotes it out of quarantine, and that event is logged distinctly. This is the same shape as
the walk's old-stock re-audit, extended to cover a set that was created rather than inherited.
"""

from __future__ import annotations

import json
from pathlib import Path

QUARANTINE_PATH = "runs/quarantine.json"


def cutoff(path: str | Path = QUARANTINE_PATH) -> float | None:
    """The journal timestamp at or below which region-era arrows are quarantined."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return float(json.loads(p.read_text(encoding="utf-8"))["cutoff_t"])
    except Exception:
        return None


def quarantined_pairs(journal_path: str | Path, path: str | Path = QUARANTINE_PATH
                      ) -> set[tuple[str, str]]:
    """The directed pairs whose arrows may not act. Read from the journal, not remembered."""
    cut = cutoff(path)
    if cut is None:
        return set()
    out: set[tuple[str, str]] = set()
    reconfirmed: set[tuple[str, str]] = set()
    unresolved: set[tuple[str, str]] = set()
    origin: dict[tuple[str, str], set[str]] = {}
    p = Path(journal_path)
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("kind") != "ask" or rec.get("relation") != "region":
                continue
            pair = (rec.get("src_slot", ""), rec.get("dst_slot", ""))
            region = rec.get("region_id", "")
            if float(rec.get("t", 0)) <= cut:
                out.add(pair)
                origin.setdefault(pair, set()).add(region)
            else:
                # A re-confirmation counts ONLY from a genuinely different region. Re-naming
                # inside the same co-present set is one measurement counted twice, and
                # independence is the whole reason a re-confirmation is evidence.
                if region and region not in origin.get(pair, set()):
                    reconfirmed.add(pair)
                else:
                    unresolved.add(pair)
    # An arrow whose re-confirmation cannot be shown to be independent stays quarantined.
    # Records written before `region_id` existed carry no context, so they resolve to
    # UNRESOLVED rather than to confirmed — absence of evidence is not evidence.
    return (out - reconfirmed) | (out & unresolved)


#: Models whose arrows are LEADS, not evidence. Measured, one region, temperature 0.0:
#: `gemini-2.5-flash-lite` emitted 1,789 arrow lines over 51 distinct pairs — 35 repeats
#: each — and ZERO `same_claim` in any of them. Every other model tried had repeats-per-pair
#: of exactly 1.0. `same_claim` is the only loop-eligible relation, so arrows from a model
#: that never emits it cannot be trusted to describe the field's topology.
#:
#: They are RETAINED IN FULL and stay readable, countable and auditable. What is withdrawn is
#: their ability to act — the same three exclusions quarantine already defines. Re-extraction
#: on a pinned model is what promotes them out, one region at a time.
LEAD_MODELS = frozenset({"google/gemini-2.5-flash-lite"})


def lite_pairs(journal_path: str | Path,
               lead_models: frozenset[str] = LEAD_MODELS) -> set[tuple[str, str]]:
    """Pairs whose ONLY support is an arrow served by a lead model.

    A pair re-proposed by a pinned model is clean stock and leaves this set, which is how
    Track A's tranches promote arrows out as they land. Records written before model tagging
    existed carry NO model, and those are treated as UNTAGGED rather than clean: 448 of 465
    historical calls went to the lite model, so absence of a tag is not evidence of a good
    one.
    """
    from .correspondence import KINDS

    lead: set[tuple[str, str]] = set()
    clean: set[tuple[str, str]] = set()
    p = Path(journal_path)
    if not p.exists():
        return lead
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("kind") != "ask" or rec.get("answer") not in KINDS:
                continue
            pair = (rec.get("src_slot", ""), rec.get("dst_slot", ""))
            model = rec.get("model", "")
            if model and model not in lead_models:
                clean.add(pair)
            else:
                lead.add(pair)
    return lead - clean


def non_acting(journal_path: str | Path, aging=None,
               path: str | Path = QUARANTINE_PATH) -> set[tuple[str, str]]:
    """THE ONE NON-ACTING SET. Two reasons to be in it; one set, one exclusion path.

    Quarantine and dormancy are not two states. An arrow is in this set because it was
    admitted against a malformed diagram (quarantine) or because measured events drained its
    weight under the fast measure (`engine.aging`) — and the three exclusions above apply
    identically either way. Building a second dormancy set beside this one would be the
    forbidden shape; `Aging` produces pairs and hands them here.

    Every consumer calls THIS, not `quarantined_pairs`, so a new reason to stop acting is one
    union and not an edit at three call sites.
    """
    out = quarantined_pairs(journal_path, path)
    if aging is not None:
        out = out | aging.dormant_pairs()
    # A THIRD REASON, same set: the arrow's only support came from a model whose output is
    # a lead rather than evidence. Not a third mechanism — `lite_pairs` produces pairs and
    # hands them here, exactly as `Aging` does.
    out = out | lite_pairs(journal_path)
    return out
