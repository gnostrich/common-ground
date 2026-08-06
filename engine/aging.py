"""AGING is EVENT-QUANTIZED. No N, no decay rate, no free constant anywhere in this file.

An earlier version of this module had `DORMANT_AFTER = 5` and a written argument for it. The
argument was fine and the shape was wrong: a threshold on a count is a free constant, and a
free constant is a number somebody chose. It was deleted rather than deprecated.

Weight under the fast measure drops ONLY at measured events. There are three, and each is a
thing that HAPPENED rather than a duration that elapsed:

  VISITED_UNCONFIRMED — a walk region contained this arrow and the medium did not name it.
                        That is one genuine opportunity to re-confirm, passed. Weight steps
                        down. It is not a denial: an unmentioned pair is UNMEASURED, and the
                        step is proportional to opportunity, not to belief.
  SUPERSEDED          — a promotion covers the same content. The slow measure now carries it,
                        so the fast weight is not evidence any more; it is a duplicate.
  CONTRADICTED        — a clamp or confirmed structure conflicts with it. Dormant, and
                        FLAGGED, because a contradiction is a finding and not just a decay.

DORMANT IS NOT DELETION and it is not a new state. It is the SAME non-acting set quarantine
already defines, entered for a different reason. Quarantine's own docstring names the three
exclusions verbatim — composition closure, region assembly, the conditioning path — and
re-entry is by re-confirmation from a genuinely DISTINCT region, the independence rule that is
already built and keyed on `region_id`. Building a second dormancy mechanism beside it would
be the forbidden shape; this module produces pairs and hands them to that one set.

WEIGHT, not a counter. `VISITED_UNCONFIRMED` halves the fast weight: it is scale-free, it has
no threshold to choose, and it never reaches zero by arithmetic — so an arrow can only become
dormant by an event that SAYS it is dormant (superseded, contradicted) or by falling below the
measure's own floor, which is a property of float arithmetic and not a policy number. That is
what "no free constants" costs and buys.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MEASURE — this is policy ON the fast measure, which already exists (`engine/mz`).
No new object, no new proposer, no new write path.
Q5 checked: NO second mechanism. The non-acting set is `engine.quarantine`'s, and the
independence rule for re-entry is the one the walk already uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: The three events. There is no fourth, and there is no clock.
VISITED_UNCONFIRMED = "visited_unconfirmed"
SUPERSEDED = "superseded"
CONTRADICTED = "contradicted"
EVENTS = (VISITED_UNCONFIRMED, SUPERSEDED, CONTRADICTED)

#: Where the aging events are recorded. Append-only, like everything else that is evidence.
AGING_PATH = "runs/aging.jsonl"

#: Weight at birth. Not a tuning constant — it is "present", and the only alternative to 1.0
#: would be a number somebody chose.
BORN = 1.0


@dataclass(slots=True)
class Aging:
    """The event ledger over the fast measure. Every drop is an event with a name."""

    #: pair -> current fast weight. The measure itself; no counters.
    weight: dict[tuple[str, str], float] = field(default_factory=dict)
    #: pair -> True once an event said DORMANT outright (superseded / contradicted).
    struck: dict[tuple[str, str], str] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    #: regions already folded in. The walk had a defect of exactly this shape — four steps
    #: assembled one co-present set and every finding in them was counted four times — so the
    #: guard lives here rather than in the caller.
    regions_seen: set[str] = field(default_factory=set)
    #: pair -> region_ids that confirmed it. Re-entry needs a DISTINCT one; the independence
    #: rule, keyed on region_id, exactly as the quarantine re-confirmation uses it.
    confirmed_in: dict[tuple[str, str], set[str]] = field(default_factory=dict)

    @staticmethod
    def key(a: str, b: str) -> tuple[str, str]:
        """Unordered. An arrow and its reverse are one relation for the purpose of staleness,
        even though they are two proposals in the journal."""
        return (a, b) if a <= b else (b, a)

    def born(self, a: str, b: str) -> None:
        """Anything RETAINED is born subject to these events. That is what stops the tape
        becoming a second corpus: there is no way to retain something outside the decay."""
        self.weight.setdefault(self.key(a, b), BORN)

    def of(self, a: str, b: str) -> float:
        return self.weight.get(self.key(a, b), 0.0)

    def dormant(self, a: str, b: str) -> bool:
        """Dormant iff an event struck it, or its weight underflowed to nothing.

        No threshold. `<= 0.0` is float arithmetic reaching bottom, not a policy number.
        """
        k = self.key(a, b)
        return k in self.struck or self.weight.get(k, BORN) <= 0.0

    def _record(self, event: str, k: tuple[str, str], **extra) -> dict:
        row = {"event": event, "pair": [k[0][:16], k[1][:16]],
               "weight": round(self.weight.get(k, 0.0), 6), **extra}
        self.events.append(row)
        return row

    def observe_region(self, region, named: set[tuple[str, str]]) -> list[dict]:
        """VISITED_UNCONFIRMED, and re-entry. One region, counted once.

        Every declared arrow inside the region either was named — which confirms it and, if it
        came from a DISTINCT region, revives it — or was an opportunity that passed.
        """
        rid = getattr(region, "region_id", "")
        if rid in self.regions_seen:
            return []
        self.regions_seen.add(rid)

        out: list[dict] = []
        norm = {self.key(a, b) for a, b in named}
        for (a, b) in getattr(region, "declared", {}):
            k = self.key(a, b)
            self.weight.setdefault(k, BORN)
            if k in norm:
                seen = self.confirmed_in.setdefault(k, set())
                independent = rid not in seen
                seen.add(rid)
                if self.dormant(*k) and independent:
                    # RE-ENTRY. A re-confirmation counts only from a region that differs from
                    # the one that saw it before — the independence rule, already built.
                    self.struck.pop(k, None)
                    self.weight[k] = BORN
                    out.append(self._record("revived", k, region=rid, independent=True))
                elif self.dormant(*k):
                    out.append(self._record("reconfirmed_same_region", k, region=rid,
                                            independent=False))
                else:
                    self.weight[k] = BORN
            else:
                self.weight[k] = self.weight[k] / 2.0
                out.append(self._record(VISITED_UNCONFIRMED, k, region=rid))
        return out

    def supersede(self, a: str, b: str, by: str) -> dict:
        """A promotion covers this content. The slow measure carries it; the fast weight is a
        duplicate, not evidence."""
        k = self.key(a, b)
        self.weight[k] = 0.0
        self.struck[k] = SUPERSEDED
        return self._record(SUPERSEDED, k, by=by[:16])

    def contradict(self, a: str, b: str, by: str) -> dict:
        """A clamp or confirmed structure conflicts. Dormant AND flagged — a contradiction is
        a finding, not merely a decay."""
        k = self.key(a, b)
        self.weight[k] = 0.0
        self.struck[k] = CONTRADICTED
        return self._record(CONTRADICTED, k, by=by[:16], flagged=True)

    def dormant_pairs(self) -> set[tuple[str, str]]:
        """The pairs to hand to the ONE non-acting set. Both directions, because that set is
        keyed directionally and an arrow's staleness is not a direction."""
        out: set[tuple[str, str]] = set()
        for (a, b) in list(self.weight) + list(self.struck):
            if self.dormant(a, b):
                out.add((a, b))
                out.add((b, a))
        return out

    def as_record(self) -> dict[str, object]:
        return {"tracked": len(self.weight), "dormant": len(self.struck),
                "regions": len(self.regions_seen), "events": len(self.events),
                "by_event": {e: sum(1 for x in self.events if x["event"] == e)
                             for e in EVENTS},
                "revived": sum(1 for x in self.events if x["event"] == "revived"),
                "note": ("Event-quantized: no N, no decay rate, no clock. Weight drops only "
                         "at measured events, and dormancy is entry into the SAME non-acting "
                         "set quarantine defines — not a second state.")}


def log(ledger: Aging, path: str | Path = AGING_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ledger.as_record(), sort_keys=True) + "\n")
        fh.flush()
