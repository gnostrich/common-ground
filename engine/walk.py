"""THE SAMPLER: a walk over the field. No pool, no order — every question conditioned on it.

The pairwise daemon consumed a list. The list was enumerated once, before any arrow existed,
from two structural relations over a corpus snapshot — so every question it asked was decided
before any of its answers were known. That is the shape being replaced. Here the next position
is drawn from what the last query produced, and there is no list anywhere.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MORPHISM — a proposer into D. The same one; this changes where it is pointed, not
how many of it there are.
Q4: it is move 3 and nothing else — no new chart, no new measure, no second write path.
Q5 is the load-bearing check and it passes ONLY as a REPLACEMENT. A sampler standing beside
the pairwise loop would be two proposers walking one field with two policies, which is the
forbidden shape. The pairwise loop is retired by this, not supplemented.
Q2 motivated the frontier: an isolated claim has no morphisms, so no amount of visiting it
will make anything propagate. The walk therefore prefers positions where structure already
exists, and reaches dark parts of the corpus only by explicit random jump.

THE FOUR STEP TYPES, in priority order. The order is the claim this module makes:

  RESIDUAL   — an implied arrow the query did not name. Prediction error: composition says
               the arrow is there and the medium, looking straight at it, did not see it.
               Highest priority, because error is the only thing that carries information
               about where the model of the field is wrong.
  COMPOSITION— a pair a length-2 path implies but nothing has checked. These are the cycle
               route: confirming one closes a triangle, and a closed triangle is the only
               thing that can make holonomy nonzero.
  NEIGHBOUR  — the provenance-neighbourhood of an arrow just created. Structure begets
               structure; a directory that yielded one arrow is likelier to yield another.
  RANDOM     — a small probability of jumping anywhere, so a dark region is not permanently
               unvisited. Without it the walk is confined to the component it started in,
               and "we found nothing there" would be a fact about the walk.

Every step records its type and its reason, and the walk log reports the FIRING DISTRIBUTION
across the four — which is the number that shows the chain is aimed by error rather than
orbiting whatever it happened to touch first.

THE GLUE LAW. `S(g o f) = S(g) o S(f)` is the schematic's coherence equation, and the walk is
where it becomes measurable. An implied arrow the medium CONFIRMS is composition holding. An
implied arrow the medium repeatedly declines to name across overlapping regions is
COMPOSITION DRIFT — two hops that do not compose — and that is holonomy arriving through the
walk rather than through a cycle search. The two are logged as distinct classes and never
summed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .corpus_state import CorpusSnapshot
from .region import Region, arrows_from, build_region, parse_region, render_region
from .region import REGION_SIZE, REGION_SYSTEM, Residual, residuals

#: Where the walk writes its log. Append-only, one JSON object per step.
WALK_PATH = "runs/walk.jsonl"

#: Step types, in the priority order the frontier pops them.
RESIDUAL, COMPOSITION, NEIGHBOUR, RANDOM = "residual", "composition", "neighbour", "random"
STEP_TYPES = (RESIDUAL, COMPOSITION, NEIGHBOUR, RANDOM)

#: How often to jump somewhere unrelated. Small, and NOT zero: a walk with no jump is
#: confined to its starting component, and its silence about the rest of the corpus would be
#: a fact about the walk rather than about the field.
JUMP_EVERY = 12

#: An implied arrow must be declined this many times, in DIFFERENT regions, before it is
#: called composition drift. Once is a region that did not show it well; repeatedly, looking
#: straight at it, is the glue law failing.
DRIFT_AFTER = 2


@dataclass(frozen=True, slots=True)
class Step:
    """One position the walk visited, why it went there, and what came back."""

    n: int
    kind: str                                 # one of STEP_TYPES
    reason: str
    clamp: str
    members: int
    named: int
    void: int
    novel: int
    confirmed_declared: int
    confirmed_implied: int                    # composition holding
    residual: int                             # implied, not named — prediction error
    drift: int                                # implied, declined repeatedly — glue-law failure
    old_stock: int                            # confirmations touching pre-table arrows
    unmeasured: int
    acceptance: float
    cost: float
    #: The actual drifting triples, not just how many. An earlier version logged the COUNT
    #: and the pairs lived only in memory, so the first glue-law failures this engine ever
    #: measured were unrecoverable when the process exited. A number is not a finding.
    drift_triples: tuple = ()

    def as_record(self) -> dict[str, object]:
        out = {k: getattr(self, k) for k in self.__slots__}
        out["drift_triples"] = [list(x) for x in self.drift_triples]
        return out


@dataclass(slots=True)
class Walk:
    """The frontier and the accounting. The only state; there is no pool."""

    steps: list[Step] = field(default_factory=list)
    #: position -> (kind, reason). A dict, so a position queued twice keeps its FIRST reason:
    #: the earliest justification is the truest one, and re-queuing must not launder a random
    #: jump into a residual.
    frontier: dict[str, tuple[str, str]] = field(default_factory=dict)
    visited: set[str] = field(default_factory=set)
    #: implied pair -> how many DIFFERENT regions declined to name it.
    declines: dict[tuple[str, str], int] = field(default_factory=dict)
    drift: list[tuple[str, str]] = field(default_factory=list)
    old_stock: set[tuple[str, str]] = field(default_factory=set)   # arrows predating the table
    #: Co-present sets already queried. `visited` tracks CLAMPS, but two different clamps in
    #: one provenance directory assemble the SAME region — so steps 4,5,6 and 8 of an eight-
    #: step walk came back byte-identical, and every drift and confirmation in them was one
    #: measurement counted four times. Independence is a property of the region, not the clamp.
    regions_seen: set[str] = field(default_factory=set)

    def push(self, slot: str, kind: str, reason: str) -> None:
        if slot and slot not in self.visited and slot not in self.frontier:
            self.frontier[slot] = (kind, reason)

    def pop(self, snapshot: CorpusSnapshot) -> tuple[str, str, str]:
        """The next position, by priority, with a forced jump every `JUMP_EVERY` steps."""
        if self.steps and len(self.steps) % JUMP_EVERY == 0:
            jump = self._jump(snapshot)
            if jump:
                return jump, RANDOM, f"forced jump every {JUMP_EVERY} steps"
        for kind in STEP_TYPES:
            for slot, (k, reason) in self.frontier.items():
                if k == kind:
                    del self.frontier[slot]
                    return slot, kind, reason
        jump = self._jump(snapshot)
        return (jump, RANDOM, "frontier empty") if jump else ("", RANDOM, "nothing left")

    def _jump(self, snapshot: CorpusSnapshot) -> str:
        """A deterministic jump: the unvisited slot whose id sorts furthest from the last one.

        Deterministic on purpose. `Math.random`-style choice would make a walk unreproducible,
        and a walk nobody can replay is a walk whose findings cannot be checked.
        """
        anchor = self.steps[-1].clamp if self.steps else ""
        best, best_key = "", None
        for sid in snapshot.slots:
            if sid in self.visited:
                continue
            key = (sid > anchor, sid)
            if best_key is None or key > best_key:
                best_key, best = key, sid
        return best

    def counts(self) -> dict[str, int]:
        out = {k: 0 for k in STEP_TYPES}
        for s in self.steps:
            out[s.kind] = out.get(s.kind, 0) + 1
        return out

    def report(self) -> dict[str, object]:
        n = len(self.steps)
        named = sum(s.named for s in self.steps)
        void = sum(s.void for s in self.steps)
        return {
            "steps": n,
            "step_types": self.counts(),
            "step_type_share": {k: round(v / n, 3) for k, v in self.counts().items()} if n else {},
            "novel": sum(s.novel for s in self.steps),
            "confirmed_declared": sum(s.confirmed_declared for s in self.steps),
            "composition_confirmed": sum(s.confirmed_implied for s in self.steps),
            "composition_drift": len(self.drift),
            "residual_open": sum(1 for v in self.declines.values() if 0 < v < DRIFT_AFTER),
            "old_stock_touched": len(self.old_stock),
            "unmeasured": sum(s.unmeasured for s in self.steps),
            "acceptance": round(named / (named + void), 3) if (named + void) else 0.0,
            "cost": round(sum(s.cost for s in self.steps), 6),
            "guard": ("acceptance near the pairwise baseline (~50%) is healthy; trending "
                      "toward ~90% means the region is condensing noise and must shrink "
                      "before anything scales"),
        }


def _chart(region: Region, slot: str) -> str:
    for m in region.members:
        if m.slot == slot:
            return m.chart
    return "?"


def _nu(region: Region, slot: str) -> str:
    for m in region.members:
        if m.slot == slot:
            return m.nu[:180]
    return ""


def unwalked_mass(snapshot: CorpusSnapshot) -> dict[str, int]:
    """Per provenance: how many of its slots no arrow has ever touched.

    This is the COVERAGE IMBALANCE, measured, and it is the whole of the exploration term.
    There is no fraction to declare and no knob to tune: a provenance's pull on the rotation
    is the mass it has left unwalked, so the pressure is derived from the imbalance itself and
    SELF-EXTINGUISHES as the walk equalises. When every slot has an arrow the dictionary is
    empty and the term vanishes rather than continuing to spend calls on a constant.

    Same shape as event-quantized aging replacing an N-based rate: the quantity that decides
    is the state, not a number somebody chose.
    """
    touched: set[str] = set()
    for a in snapshot.arrows:
        touched.add(a.src_slot)
        touched.add(a.dst_slot)
    out: dict[str, int] = {}
    for sid, rec in (getattr(snapshot, "slots", None) or {}).items():
        if sid in touched:
            continue
        docs = list(getattr(rec, "docs", None) or ())
        root = str(docs[0]).split("||")[0] if docs else "?"
        out[root] = out.get(root, 0) + 1
    return out


def _unwalked_seeds(snapshot: CorpusSnapshot, want: int) -> list[tuple[str, str]]:
    """One seed per provenance, drawn in proportion to unwalked mass. No constant anywhere.

    Largest-remainder apportionment over the measured masses: a provenance holding a tenth of
    the corpus's untouched slots gets a tenth of the exploration seeds. A provenance with
    nothing untouched gets none, which is why the pressure ends by itself.
    """
    mass = unwalked_mass(snapshot)
    total = sum(mass.values())
    if not total or want <= 0:
        return []
    touched: set[str] = set()
    for a in snapshot.arrows:
        touched.add(a.src_slot)
        touched.add(a.dst_slot)
    by_root: dict[str, list[str]] = {}
    for sid, rec in sorted((getattr(snapshot, "slots", None) or {}).items()):
        if sid in touched:
            continue
        docs = list(getattr(rec, "docs", None) or ())
        by_root.setdefault(str(docs[0]).split("||")[0] if docs else "?", []).append(sid)

    exact = {r: want * m / total for r, m in mass.items()}
    take = {r: int(v) for r, v in exact.items()}
    for r, _ in sorted(exact.items(), key=lambda kv: (-(kv[1] - int(kv[1])), kv[0])):
        if sum(take.values()) >= want:
            break
        take[r] += 1
    out: list[tuple[str, str]] = []
    for root in sorted(take):
        for sid in by_root.get(root, ())[:take[root]]:
            out.append((sid, f"seed: {mass[root]:,} slot(s) of {root} carry no arrow yet — "
                             f"{mass[root] / total:.1%} of the corpus's unwalked mass"))
    return out


def _seed_frontier(walk: Walk, snapshot: CorpusSnapshot) -> None:
    """Start where structure already is — AND where it measurably is not.

    Degree seeding alone is self-reinforcing: walked material gets arrows, arrows make it
    eligible, eligibility routes the walk there, and the walk produces more arrows there.
    Measured on the live corpus the eligible set was 71% one repository holding 15% of the
    material, while 12,466 Lean slots had 1.7% of them touched by any arrow. A corpus region
    nothing has walked can never earn its way into a rotation that admits by arrow count.

    So half the frontier is drawn by declared degree and half by UNWALKED MASS. The split is
    not a tuned fraction: the exploration half is apportioned by the measured imbalance and
    empties itself as the walk equalises, at which point the frontier is degree-seeded again
    with nothing switched off.
    """
    degree: dict[str, int] = {}
    for a in snapshot.arrows:
        degree[a.src_slot] = degree.get(a.src_slot, 0) + 1
        degree[a.dst_slot] = degree.get(a.dst_slot, 0) + 1
    seeds = sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))[:32]
    for sid, _ in seeds:
        walk.push(sid, NEIGHBOUR, "seed: already carries declared arrows")
    for sid, reason in _unwalked_seeds(snapshot, len(seeds) or 32):
        walk.push(sid, NEIGHBOUR, reason)


def step(walk: Walk, snapshot: CorpusSnapshot, transport, size: int = REGION_SIZE,
         old_stock: frozenset[tuple[str, str]] = frozenset()) -> tuple[Step, list, Region]:
    """One position: build the region, query it, read the outcomes, aim the next step."""
    clamp, kind, reason = walk.pop(snapshot)
    region = build_region(snapshot, clamp=clamp, size=size)
    # Skip a co-present set already queried. Re-querying it re-measures, and re-measurement
    # dressed as a new step inflates every count downstream of it.
    tries = 0
    while region.region_id in walk.regions_seen and tries < 24:
        walk.visited.add(clamp)
        clamp, kind, reason = walk.pop(snapshot)
        if not clamp:
            break
        region = build_region(snapshot, clamp=clamp, size=size)
        tries += 1
    walk.regions_seen.add(region.region_id)
    body = render_region(region)
    raw, usage = transport(REGION_SYSTEM, body)
    proposals = parse_region(raw, region)
    res = residuals(proposals, region)
    walk.visited.add(clamp)

    # RESIDUALS first: an implied arrow nobody named is prediction error, and repeated
    # declines across DIFFERENT regions are the glue law failing rather than a bad view.
    drift_here = 0
    drifted: list[tuple] = []
    for pair in res.residual:
        walk.declines[pair] = walk.declines.get(pair, 0) + 1
        if walk.declines[pair] >= DRIFT_AFTER and pair not in walk.drift:
            walk.drift.append(pair)
            drift_here += 1
            # WHAT composes to this implied arrow, in full, so the operator can eyeball
            # whether it is a genuine translation defect or a region-assembly artifact.
            a, c = pair
            for (u, v), k1 in region.declared.items():
                for (x, y), k2 in region.declared.items():
                    if u == a and v == x and y == c:
                        drifted.append((
                            {"slot": u[:16], "chart": _chart(region, u), "nu": _nu(region, u)},
                            k1,
                            {"slot": v[:16], "chart": _chart(region, v), "nu": _nu(region, v)},
                            k2,
                            {"slot": y[:16], "chart": _chart(region, y), "nu": _nu(region, y)},
                            region.implied.get(pair, "?"), clamp[:16]))
        walk.push(pair[0], RESIDUAL,
                  f"implied arrow unnamed {walk.declines[pair]}x — prediction error")

    # COMPOSITION: pairs a length-2 path implies that this region did not carry.
    for (a, _b) in region.implied:
        walk.push(a, COMPOSITION, "composition-implied pair, unchecked")

    # NEIGHBOUR: the provenance-neighbourhood of what was just found.
    for p in res.novel:
        walk.push(p.dst.slot, NEIGHBOUR, "provenance-neighbour of a new arrow")

    touched = {tuple(sorted((p.src.slot, p.dst.slot))) for p in res.confirmed_declared}
    old = touched & old_stock
    walk.old_stock |= old

    s = Step(n=len(walk.steps) + 1, kind=kind, reason=reason, clamp=clamp,
             members=len(region.members), named=res.named_pairs, void=len(res.void),
             novel=len(res.novel), confirmed_declared=len(res.confirmed_declared),
             confirmed_implied=len(res.confirmed_implied), residual=len(res.residual),
             drift=drift_here, old_stock=len(old), unmeasured=res.unmeasured_pairs,
             acceptance=round(res.acceptance, 3), cost=float(usage.get("cost") or 0.0),
             drift_triples=tuple(drifted))
    walk.steps.append(s)
    return s, proposals, region


def log_step(step_record: Step, path: str | Path = WALK_PATH) -> None:
    """Append one step. The log is how the operator sees the chain follow structure."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(step_record.as_record(), sort_keys=True) + "\n")
        fh.flush()
