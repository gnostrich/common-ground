"""THE STRUCTURE LAYER, COMPILED AND CITED. Some questions are about shape, not displacement.

"common thread through the math" is a question about Pi-1 — about which claims this corpus
joins, across which charts, into what. The relaxation path cannot answer it. It applies the
input as a soft constraint and reports which OBJECTS moved, and objects moving is the wrong
category: the answer to a question about the corpus's shape lives in its loops, its fibers and
its cross-chart clusters, all of which are already measured and already sitting in the header
the operator reads every time the page loads. Asked that question, the window returned
`role_unit_pool` and `compute_eigenmodes` — implementation details of an unrelated repository,
displaced by a bias landing directly on them.

THE SIGNATURE IS DETECTABLE, which is why this is a compile step and not a mode the operator
has to select. Two facts, both already on the record:

  BEARS-ON ONLY   every attachment the medium drew is `bears_on` and none is a correspondence.
                  A claim asserts a proposition and can correspond; a question or a bare topic
                  asserts nothing and can only be ABOUT something. All-bears-on says the input
                  was not a claim.
  NO ARROW REACH  no moved slot has a nonzero hop count. Everything that moved was biased
                  directly; no declared correspondence carried the perturbation anywhere. The
                  field's own structure contributed nothing to the answer.

Together those say: the input was a topic, and the relaxation found nothing structural to say
about it. That is exactly when the structural layer should be what gets voiced.

WHAT IS COMPILED, and each line is CITABLE with the same integer counter the movers use, so
the answer cites a loop exactly as it cites a moved claim:

  LOOP     a verified cycle — claims joined into a closed path across charts. The strongest
           structural fact this corpus has, and the only one that produces a floor.
  FIBER    a `same_claim` equivalence class: one proposition carried in several charts at once.
           The largest ones are where the corpus most agrees with itself.
  CLUSTER  a chart-pair with its arrow count. Which two languages this corpus actually joins,
           as opposed to which two it merely contains.

NOTHING HERE IS COMPUTED FRESH. Loops, fibers and arrows are read off the snapshot the walk
already built. This module selects and numbers; it measures nothing, and gate 10 applies to
that sentence — there is no settlement, no propagation and no proposal anywhere in this file.
"""

from __future__ import annotations

from dataclasses import dataclass

#: How many of each kind to compile. The cut is stated rather than tuned: a prompt that
#: carries every one of 1,046 fibers is a prompt nothing can read, and a structural answer
#: needs the LARGEST structures, which are the ones that say what the corpus is joined by.
#: Anything dropped is COUNTED in the emitted header line, never silently cut.
TOP_FIBERS = 8
TOP_CLUSTERS = 8
TOP_LOOPS = 8

#: THE CANONICAL STRUCTURAL QUESTION, verbatim. It has failed enough times to be a fixture
#: rather than an example, and it lives here so the harness and the battery cite one string.
STRUCTURAL_QUESTION_DEFAULT = "common thread through the math"

#: A fiber smaller than this is a pair, and a pair is an arrow — already visible as one.
MIN_FIBER = 3


@dataclass(frozen=True, slots=True)
class Signature:
    """Why the structural layer was or was not compiled. Both branches are stated."""

    bears_on_only: bool
    no_arrow_reach: bool
    attachments: int
    correspondences: int
    moved: int
    reached: int

    @property
    def structural(self) -> bool:
        return self.bears_on_only and self.no_arrow_reach

    def render(self) -> str:
        if self.structural:
            return (f"STRUCTURAL QUESTION DETECTED: all {self.attachments} attachment(s) are "
                    f"bears_on with no correspondence, and {self.reached} of {self.moved} "
                    f"moved slot(s) were reached over a declared arrow. The input was a topic, "
                    f"not a claim, and the relaxation carried nothing structural — so the "
                    f"corpus's OWN SHAPE is compiled below and is what should be answered "
                    f"from.")
        return ""

    def as_record(self) -> dict[str, object]:
        return {"structural": self.structural, "bears_on_only": self.bears_on_only,
                "no_arrow_reach": self.no_arrow_reach, "attachments": self.attachments,
                "correspondences": self.correspondences, "moved": self.moved,
                "reached": self.reached}


def signature_of(pert, rel) -> Signature:
    """Read the two facts off the records. Nothing is inferred and no text is read."""
    from .region import BEARS_ON

    att = list(getattr(pert, "attachment", []) or []) if pert is not None else []
    corr = [a for a in att if a.kind != BEARS_ON]
    moved = list(getattr(rel, "moved", []) or []) if rel is not None else []
    reached = sum(1 for m in moved if m.hops > 0)
    return Signature(
        bears_on_only=bool(att) and not corr,
        no_arrow_reach=bool(moved) and reached == 0,
        attachments=len(att), correspondences=len(corr),
        moved=len(moved), reached=reached,
    )


def _nu(snapshot, slot: str) -> tuple[str, str]:
    s = (getattr(snapshot, "slots", None) or {}).get(slot)
    if s is None:
        return ("?", slot[:16])
    return (getattr(s, "chart", "?"), getattr(s, "nu", "") or slot[:16])


def structure_lines(snapshot, cites: list, Citable) -> list[str]:
    """The corpus's shape, numbered into the same citation stream the movers use."""
    from .inbound import display

    slots = getattr(snapshot, "slots", None) or {}
    arrows = list(getattr(snapshot, "arrows", None) or [])
    fibers = list(getattr(snapshot, "fibers", None) or [])

    def cite(kind: str, chart: str, slot: str, nu: str) -> int:
        n = len(cites) + 1
        cites.append(Citable(n=n, kind=kind, chart=chart, slot=slot, nu=nu))
        return n

    lines: list[str] = [
        "THE CORPUS'S OWN STRUCTURE. These are not claims the bias moved — they are the shape "
        "the corpus already has, measured by the walk and read off the snapshot. A question "
        "about what this corpus joins is answered from HERE. Every line carries a number and "
        "is cited exactly like a moved claim.",
    ]

    # ---- FIBERS: one proposition carried in several charts at once.
    big = sorted((f for f in fibers if len(f) >= MIN_FIBER), key=len, reverse=True)
    lines.append(f"-- FIBERS: {len(fibers)} same_claim classes, {len(big)} of size "
                 f"{MIN_FIBER}+; the {min(TOP_FIBERS, len(big))} largest are numbered below. "
                 f"{max(0, len(big) - TOP_FIBERS)} further class(es) of size {MIN_FIBER}+ are "
                 f"not shown and are stated rather than silently cut.")
    for fib in big[:TOP_FIBERS]:
        members = [(_nu(snapshot, s)) for s in list(fib)]
        charts = sorted({c for c, _ in members})
        head = display(members[0][1]) if members else "?"
        n = cite("fiber", "+".join(charts), list(fib)[0], head)
        lines.append(f"[{n}] FIBER of {len(fib)} claim(s) across {len(charts)} chart(s) "
                     f"({', '.join(charts)}) — the same proposition carried in each. "
                     f"One member: {head}")
        for c, nu in members[1:4]:
            lines.append(f"      also [{c}] {display(nu)}")
        if len(members) > 4:
            lines.append(f"      (+{len(members) - 4} more member(s) in this fiber)")

    # ---- CLUSTERS: which two charts this corpus actually joins.
    pairs: dict[tuple[str, str], int] = {}
    for a in arrows:
        key = tuple(sorted((a.src_chart, a.dst_chart)))
        pairs[key] = pairs.get(key, 0) + 1
    ranked = sorted(pairs.items(), key=lambda kv: -kv[1])
    lines.append(f"-- CROSS-CHART CLUSTERS: {len(arrows)} declared arrow(s) over "
                 f"{len(pairs)} chart-pair(s); the {min(TOP_CLUSTERS, len(ranked))} heaviest "
                 f"are numbered below.")
    for (a_chart, b_chart), count in ranked[:TOP_CLUSTERS]:
        same = "within one chart" if a_chart == b_chart else "across two charts"
        n = cite("cluster", f"{a_chart}+{b_chart}", f"{a_chart}|{b_chart}",
                 f"{count} declared arrow(s) joining {a_chart} and {b_chart}")
        lines.append(f"[{n}] CLUSTER {a_chart} <-> {b_chart}: {count} declared arrow(s), "
                     f"{same}.")

    # ---- LOOPS: the closed paths. The only structure that produces a floor.
    loops = getattr(snapshot, "loops", 0)
    if isinstance(loops, int):
        lines.append(f"-- LOOPS: {loops} verified cycle(s) in this corpus. A loop is a closed "
                     f"path of declared correspondences returning to its start, and it is the "
                     f"only structure that yields a floor. Their membership is not carried on "
                     f"this snapshot, so the COUNT is stated and the members are not — an "
                     f"absent detail, not an absent structure.")
    else:
        for loop in list(loops)[:TOP_LOOPS]:
            members = [_nu(snapshot, s) for s in list(loop)]
            charts = sorted({c for c, _ in members})
            n = cite("loop", "+".join(charts), list(loop)[0],
                     display(members[0][1]) if members else "?")
            lines.append(f"[{n}] LOOP of {len(members)} claim(s) closing across "
                         f"{', '.join(charts)}.")
            for c, nu in members[:4]:
                lines.append(f"      [{c}] {display(nu)}")

    lines.append(f"-- SLOTS: {len(slots)} addressed claim(s) in total. The structure above is "
                 f"what joins them; the moved list is what the boundary condition displaced.")
    return lines
