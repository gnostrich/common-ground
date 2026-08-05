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
