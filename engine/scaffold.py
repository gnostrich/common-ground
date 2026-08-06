"""DEPENDS_ON: the declared structure inside a chart, parsed from the artifact, zero LM calls.

THE DEFECT. Each chart's native declared structure is the graph its claims hang off, and it
was discarded at ingest. Lean: 12,466 slots FLAT — the namespace tree and the
theorem-uses-definition graph thrown away, with `#doc:` containment the only structural fact
kept, and that is provenance. Python and Go: import graph, call structure, class hierarchy,
all discarded. The Gibbs energy has been running over mostly-bare ground while the scaffolds
sat on disk, already ingested, free. Same omission class as the docstrings: declared structure
discarded at the door.

WHY THIS IS NOT A `Correspondence`, and the reason is structural rather than stylistic.
`Correspondence.__post_init__` REFUSES an intra-chart arrow, and it is right to: exact
addressing already owns intra-chart identity under gate 1, so an intra-chart correspondence
would re-introduce similarity by the back door. But every scaffold edge is intra-chart by
nature — a Lean theorem depends on a Lean definition, a module imports a module — so making
`depends_on` a correspondence kind would mean relaxing that guard for everything.

So it is a separate edge type. Three of the operator's requirements then hold BY CONSTRUCTION
rather than by a flag somebody has to remember to check:

  HOLONOMY-EXCLUDED   holonomy is computed over `Correspondence.loop_eligible` pairs. A
                      Scaffold is not a Correspondence, so it cannot reach a loop at all —
                      there is no `loop_eligible` attribute to set wrongly.
  NOT MIS-KINDABLE    a dependency cannot be stored as same_claim/refines/instance_of,
                      because those are values of a field on a different class. The
                      containment mistake — a relation jammed into the wrong kind because the
                      kind system had no room for it — is impossible here rather than
                      forbidden.
  FIREWALLED          K's candidate set and the contest machinery both read Correspondences.

WHAT MAKES AN EDGE. The dependency is written in the source or it does not exist. There is no
proposer, no medium, no similarity, and no tokenizer in this module: a referenced identifier
resolves EXACTLY to a declared slot's address or the edge is VOID. Resolve-or-void, the same
discipline the wire format uses, and voids are COUNTED rather than dropped — an unresolved
reference is a measurement about the corpus's coverage, not noise.

COMPOSITION. `depends_on ∘ depends_on = depends_on` — a dependency chain is a real dependency.
Everything else is UNDEFINED: composing a dependency with an equivalence implies nothing, and
the table in `seed/COMPOSITION.json` says so rather than defaulting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .nonempty import census

#: The relation. One kind at v0; the family is open but each member needs its own ruling.
DEPENDS_ON = "depends_on"
SCAFFOLD_KINDS = frozenset({DEPENDS_ON})

#: Reference tier. It conditions and scaffolds; it never promotes as knowledge and never
#: contests a claim's value. The same containment shape `bears_on` and the medium chart have.
REFERENCE_TIER = "REFERENCE"


@dataclass(frozen=True, slots=True)
class Scaffold:
    """One declared, parsed, intra-chart dependency. Not a claim about the world."""

    chart: str
    src_slot: str
    dst_slot: str
    kind: str = DEPENDS_ON
    #: The identifier as WRITTEN in the source, kept so a void can be reported by name.
    symbol: str = ""
    #: Which parse produced it, and from what. Era-tagged like every other declaration, so a
    #: changed source is a new era with the old edge aging rather than a silent mutation.
    era: str = ""
    provenance: str = ""
    tier: str = REFERENCE_TIER

    def __post_init__(self) -> None:
        if self.kind not in SCAFFOLD_KINDS:
            raise ValueError(f"unknown scaffold kind {self.kind!r}")
        if self.src_slot == self.dst_slot:
            raise ValueError("a dependency needs two distinct slots; this is one claim")

    @property
    def pair(self) -> tuple[str, str]:
        return (self.src_slot, self.dst_slot)

    def as_record(self) -> dict[str, object]:
        return {"chart": self.chart, "src": self.src_slot[:16], "dst": self.dst_slot[:16],
                "kind": self.kind, "symbol": self.symbol, "era": self.era,
                "provenance": self.provenance, "tier": self.tier}


@dataclass
class ScaffoldParse:
    """What one parse produced, INCLUDING what it could not resolve.

    `void` is the point of this object. A parser that reports only the edges it made cannot be
    distinguished from one that made none, and the ratio of resolved to void is the honest
    statement of how much of a chart's declared structure this corpus actually contains.
    """

    edges: list = field(default_factory=list)
    void: list = field(default_factory=list)          # (src_slot, symbol, reason)
    symbols: int = 0                                  # references seen, resolved or not

    @property
    def resolved(self) -> int:
        return len(self.edges)

    def as_record(self) -> dict[str, object]:
        by_reason: dict[str, int] = {}
        for _, _, reason in self.void:
            by_reason[reason] = by_reason.get(reason, 0) + 1
        return {"edges": self.resolved, "void": len(self.void), "references_seen": self.symbols,
                "resolution_rate": round(self.resolved / self.symbols, 4) if self.symbols else 0.0,
                "void_by_reason": by_reason}


def holonomy_excluded(edge) -> bool:
    """A Scaffold can never reach a loop: it is not a Correspondence and has no eligibility.

    Stated as a function so the property is assertable rather than merely true today.
    """
    return isinstance(edge, Scaffold) or getattr(edge, "kind", "") in SCAFFOLD_KINDS


def void_ledger(parse, top: int = 40) -> list[tuple[str, int]]:
    """WHAT THE CORPUS REACHES FOR AND DOES NOT CONTAIN, ranked by how often.

    A void is usually read as a parser's shortfall. It is better read as a MEASUREMENT: an
    undeclared reference names something this material depends on and this corpus has never
    ingested. Ranked by reference count that is an ingestion wishlist, derived rather than
    guessed, and it costs nothing — the parse already had to resolve every name to know which
    ones failed. If the named source is ever ingested, these voids resolve on the next parse
    with no edge invented in the meantime.
    """
    counts: dict[str, int] = {}
    for _, symbol, reason in parse.void:
        if reason == "undeclared":
            counts[symbol] = counts.get(symbol, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]


def ambiguity_census(snapshot, index_fn) -> dict:
    """Names this corpus declares MORE THAN ONCE, split by whether the declarations differ.

    Two shapes hide in one number. A genuine OVERLOAD declares the same name with different
    content in one body of work. A COPY declares it identically in several repositories —
    and a copy is a same_claim candidate nominated by a DECLARED FACT (identical declared
    name, identical declaration text), not by resemblance. The walk can be pointed at those;
    they are not asserted here, and this function creates no arrow.
    """
    seen: dict[str, list] = {}
    for sid, rec in (getattr(snapshot, "slots", None) or {}).items():
        if getattr(rec, "chart", "") != "lean":
            continue
        name = index_fn(getattr(rec, "nu", "") or "")
        if name:
            seen.setdefault(name, []).append((sid, getattr(rec, "nu", "") or ""))
    overloads, copies = [], []
    for name, rows in seen.items():
        if len(rows) < 2:
            continue
        bodies = {nu for _, nu in rows}
        (copies if len(bodies) == 1 else overloads).append((name, len(rows)))
    # OI-24: censused over the LEAN SLOTS EXAMINED, not over the whole snapshot. A snapshot
    # with no lean material produces zero ambiguous names, which is not a fact about ambiguity.
    return census("ambiguity_census", list(seen), {
            "ambiguous_names": len(overloads) + len(copies),
            "copies": sorted(copies, key=lambda kv: -kv[1]),
            "overloads": sorted(overloads, key=lambda kv: -kv[1]),
            "note": ("a COPY is a same_claim candidate nominated by a declared fact — "
                     "identical declared name AND identical declaration text across "
                     "repositories. Nominated for the walk, never asserted here.")},
            unit="declared lean name")
