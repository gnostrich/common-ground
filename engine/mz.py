"""THE MZ LAYER, physically: ONE hypergraph, TWO measures, K as a boundary-site operator.

The fast tape is not a second graph and never was. Fast and slow are two OCCUPATION MEASURES
over the same claim/arrow structure — the schematic's own words: a second measure on D, plus
one morphism K. A claim never moves from tape to corpus; its weight under the slow measure
changes. Promotion is RE-WEIGHTING, not transport.

That distinction has a physical consequence, so it gets a physical control. A measure is a
map from ADDRESS to NUMBER and holds no claim content — no nu, no chart, no value, no
surface. The moment a weight table carries content it is a second store holding the same
claim twice, and two stores of one claim is the failure regardless of how green the tests
are. `Measure.validate` is that check and it is not advisory.

-- K's SUPPORT, which is the point of the whole file --

K is not a global scan. Its support is the BOUNDARY SITES: places where fast-hot activity
touches slow-settled structure. Physically each site is a HYPEREDGE — not a pairwise edge —
because the MZ kernel is non-local in time and the thing gathered at a site is that site's
RECENT FAST HISTORY. A pair of endpoints cannot carry a history; a hyperedge over
{site, its recent extraction answers} can. The Hankel > second-FDT test then runs PER SITE on
that gathered history, which makes the kernel's support explicit in the graph instead of
implicit in code, and makes K's cost scale with the active boundary rather than the corpus.

Measured on the live field: 69,446 slots, 3,264 of them touched by any arrow, 1,891
arrow-rich, and 46 boundary sites. K is a ~1,500x smaller problem than the corpus.

-- ONE MEASUREMENT THAT CHANGES THE DEFINITION, recorded because it would have been silent --

`tier > EXTRACTION` is ZERO across all 69,446 slot records. The CI_RECEIPT clamps are applied
AT SETTLEMENT and are never written back to the slot. So "slow-settled" must be read off the
settled view, and `slow_settled` below takes `clamped` as an argument rather than reading
`rec.tier`. Defined against the snapshot, K's support would have been the empty set — every
control would still have passed, and the entire layer would have been a silent no-op.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MEASURE — the fast/slow occupation measures, made physical. No new move: this is
the existing move-2 given a representation, not a new one.
Q1: the object K ranges over is a BOUNDARY SITE with its gathered history, not a claim. That
is why the edge is a hyperedge; a claim is a projection of a site.
Q5 checked: NO second mechanism. `read_tape`, `act_on_mint` and the conservative-extension
check are `engine.mint_tape`'s, called not reimplemented. What is added is where they are
pointed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .mint_tape import (HANKEL_WINDOW, Promotion, TapeReading, act_on_mint,
                        read_tape)

#: Least declared degree that makes a slot SLOW-SETTLED by structure. Two is the smallest
#: degree at which a slot can be the middle of a length-2 path — the smallest degree at which
#: composition can happen at all. Below it there is no slow structure for fast activity to
#: touch, so this is a property of the graph rather than a tuned threshold.
SETTLED_DEGREE = 2

#: How many of the most recent extraction answers form a site's gathered history.
#:
#: DERIVED, not chosen. A Hankel matrix of window `w` consumes `2w-1` samples, so a history
#: shorter than that yields an EMPTY matrix, no singular values, and `hankel_top = 0.0` — a
#: gate that can never fire, reporting itself as a clean refusal. That is exactly what
#: happened at 64: HISTORY_DEPTH equalled HANKEL_WINDOW and every site scored zero. The depth
#: is now tied to the window so the two cannot drift apart again.
HISTORY_DEPTH = 2 * HANKEL_WINDOW

FAST, SLOW = "fast", "slow"


@dataclass(slots=True)
class Measure:
    """An occupation measure over the ONE structure: address -> weight. Nothing else.

    This is the no-second-store guarantee made checkable. If this dataclass ever grows a field
    carrying claim content — nu, chart, value, surface — then the fast and slow sides are two
    stores holding one claim, and the layer is wrong however it tests.
    """

    name: str
    weight: dict[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        """A weight table that carries content is a second store. Refuse it."""
        from . import EngineError

        for addr, w in self.weight.items():
            if not isinstance(addr, str):
                raise EngineError(f"a measure is keyed by address; got {type(addr).__name__}")
            if isinstance(w, bool) or not isinstance(w, (int, float)):
                raise EngineError(
                    f"a measure maps an address to a NUMBER. {addr[:16]} carries "
                    f"{type(w).__name__}, which means this table is holding claim content — "
                    f"a second store of a claim the one hypergraph already holds.")

    def of(self, addr: str) -> float:
        return float(self.weight.get(addr, 0.0))

    def reweight(self, addr: str, w: float) -> None:
        """Promotion and aging are BOTH this. Nothing is copied, moved or deleted."""
        self.weight[addr] = float(w)


@dataclass(frozen=True, slots=True)
class BoundarySite:
    """One place fast-hot activity touches slow-settled structure, with its gathered history.

    THE HYPEREDGE. Its members are the site and every recent extraction answer touching it —
    which is why it cannot be a pairwise edge: two endpoints have no room for a history, and
    the kernel is non-local in time.
    """

    site: str                                  # slot address
    degree: int                                # declared arrows touching it
    clamped: bool                              # clamped at settlement (not read from the slot)
    hot: int                                   # recent extraction answers touching it
    history: tuple[float, ...] = ()            # the gathered fast history K reads
    members: tuple[str, ...] = ()              # the answers gathered, by evidence id

    @property
    def slow_settled(self) -> bool:
        return self.degree >= SETTLED_DEGREE or self.clamped

    @property
    def fast_hot(self) -> bool:
        return self.hot > 0

    @property
    def is_boundary(self) -> bool:
        return self.fast_hot and self.slow_settled

    def as_record(self) -> dict[str, object]:
        return {"site": self.site[:16], "degree": self.degree, "clamped": self.clamped,
                "hot": self.hot, "history": len(self.history), "members": len(self.members)}


@dataclass(frozen=True, slots=True)
class Admission:
    """A PROMOTION AS A FIRST-CLASS OBJECT: the residuals, the decision, and the promoted form.

    Decision B. A promotion is not a weight flip plus a journal line — it is an edge in the
    graph gathering the claims/arrows it was computed from, K's own decision record, and what
    came out. "Why is this here" becomes graph-queryable instead of journal archaeology, which
    is the warrant discipline extended to admission itself.

    THE PHASING CONDITION. The graph rendering comes after the suite, but this record carries
    the FULL evidence from the very first promotion: Hankel value, second-FDT floor, the
    conservative-check result, and the residual set involved. The later edge RENDERS this; it
    never reconstructs it. Evidence not captured now cannot be recovered later, and decision B
    would silently degrade to A — a weight flip with a note attached.
    """

    site: str
    residuals: tuple[str, ...]                 # the claims/arrows the decision was computed on
    hankel_top: float
    second_fdt_floor: float                    # the floor the threshold derives from
    threshold: float
    gate_pass: bool
    conservative: bool
    promoted: bool
    reason: str
    value: str = ""
    effective_rank: int = 0
    stream_length: int = 0

    def as_record(self) -> dict[str, object]:
        return {
            "kind": "admission",
            "site": self.site,
            "residuals": list(self.residuals),
            "decision": {
                "hankel_top": self.hankel_top,
                "second_fdt_floor": self.second_fdt_floor,
                "threshold": self.threshold,
                "gate_pass": self.gate_pass,
                "conservative": self.conservative,
                "effective_rank": self.effective_rank,
                "stream_length": self.stream_length,
            },
            "promoted": {"slot": self.site, "value": self.value} if self.promoted else None,
            "reason": self.reason,
            "note": ("The in-graph face of this event is a hyperedge over {residuals, "
                     "decision, promoted}. It RENDERS this record and never reconstructs it: "
                     "evidence not captured at admission time cannot be recovered later."),
        }

    @classmethod
    def from_promotion(cls, p: Promotion, reading: TapeReading, residuals: tuple[str, ...],
                       second_fdt_floor: float) -> "Admission":
        """K's existing decision, with the evidence it was computed from attached.

        `Promotion` is unchanged and is still the decision face. What this adds is the
        residual set, which nothing carried before — and which is the whole difference
        between decision B and decision A.
        """
        return cls(site=p.slot, residuals=residuals, hankel_top=p.hankel_top,
                   second_fdt_floor=second_fdt_floor, threshold=p.threshold,
                   gate_pass=p.gate_pass, conservative=p.conservative, promoted=p.promoted,
                   reason=p.reason, value=p.value,
                   effective_rank=reading.effective_rank,
                   stream_length=reading.stream_length)


#: How an answer at a site scores in that site's own history. Bounded in [0, 1] ON PURPOSE:
#: the gate compares a Hankel singular value of this series against `3 x second_fdt_floor`,
#: and holonomy is a probability distance bounded by 2. A series on [0, 1] puts the two on
#: the same order. The block SETTLING TRACE, which this replaced, ran to ~50 in energy units
#: and made the comparison dimensionally incoherent — 123 against 0.36 is not a test.
#:
#: The relative weights are a CHOICE and are stated as one: an identity is worth more to a
#: site's history than a refinement, which is worth more than an instance. Nothing derives
#: them; they order the three kinds the base already has.
ANSWER_WEIGHT = {"same_claim": 1.0, "refines": 0.5, "instance_of": 0.25, "none": 0.0}


def site_history(records, site: str, depth: int = HISTORY_DEPTH) -> tuple[tuple[float, ...],
                                                                         tuple[str, ...]]:
    """THE SITE'S OWN recent fast history, in time order — and nobody else's.

    This is what the hyperedge formulation exists to provide, and the first wiring did not
    deliver it. It used the residual stream of the BLOCK the site sits in, which produced two
    compounding defects, both measured on the live field:

      * every site in a block got a byte-identical stream, so the "per-site" Hankel test was
        per-block. Twelve sites returned `hankel_top = 123.3673` to four decimal places.
      * that stream was a clean geometric decay at rate ~0.7745 — the SETTLING SCHEDULE. Its
        top singular value is a property of the solver, not of the claim, so the test could
        not discriminate between sites even in principle.

    Here the series is the site's own answers, in the order they were given: what the medium
    said about this claim, over time. Two sites with different histories get different series
    by construction, and a site with no history gets an empty one rather than somebody else's.
    """
    hist: list[float] = []
    members: list[str] = []
    for rec in records:
        if rec.get("kind") != "ask":
            continue
        if rec.get("src_slot") != site and rec.get("dst_slot") != site:
            continue
        hist.append(ANSWER_WEIGHT.get(str(rec.get("answer", "none")), 0.0))
        members.append(f"{rec.get('t','')}:{rec.get('src_slot','')[:8]}"
                       f"->{rec.get('dst_slot','')[:8]}:{rec.get('answer','')}")
    return tuple(hist[-depth:]), tuple(members[-depth:])


def boundary_sites(degree: dict[str, int], hot: dict[str, int],
                   history: dict[str, tuple[float, ...]] | None = None,
                   members: dict[str, tuple[str, ...]] | None = None,
                   clamped: frozenset[str] = frozenset()) -> list[BoundarySite]:
    """K's support: the sites, gathered.

    `clamped` is passed IN rather than read off the slot records, because the slot records
    say `EXTRACTION` for every one of the 69,446 slots — receipts are applied at settlement
    and never written back. See the module docstring; this is the argument that keeps the
    layer from being a silent no-op.
    """
    history = history or {}
    members = members or {}
    out = []
    for addr, h in hot.items():
        s = BoundarySite(site=addr, degree=degree.get(addr, 0), clamped=addr in clamped,
                         hot=h, history=tuple(history.get(addr, ())),
                         members=tuple(members.get(addr, ())))
        if s.is_boundary:
            out.append(s)
    out.sort(key=lambda s: (-s.hot, -s.degree, s.site))
    return out


def consider_site(site: BoundarySite, value: str, second_fdt_floor: float,
                  corpus: dict[str, str], enabled: bool | None = None) -> Admission:
    """Run K AT ONE SITE, on that site's gathered history. The per-site Hankel test.

    `read_tape` and `act_on_mint` are `engine.mint_tape`'s and are called, not reimplemented —
    the conservative-extension rule likewise. What is new is the SUPPORT: this runs over a
    site's own history rather than over a settled block chosen by a global sweep.
    """
    reading = read_tape(list(site.history), second_fdt_floor)
    try:
        gate_pass = act_on_mint(reading, enabled=enabled)
    except Exception:
        # Mint is OFF. That is the quarantine, and it is reported as a refusal rather than
        # swallowed into a False that reads like a failed gate.
        gate_pass = False
        existing = corpus.get(site.site)
        return Admission(
            site=site.site, residuals=site.members,
            hankel_top=(reading.singular_values[0] if reading.singular_values else 0.0),
            second_fdt_floor=second_fdt_floor, threshold=reading.threshold,
            gate_pass=False, conservative=existing is None or existing == value,
            promoted=False, reason="mint is OFF; the tape carries no authority",
            value=value, effective_rank=reading.effective_rank,
            stream_length=reading.stream_length)

    existing = corpus.get(site.site)
    conservative = existing is None or existing == value
    promoted = bool(gate_pass and conservative)
    reason = ("promoted through the gate" if promoted
              else "blocked: not conservative (would overwrite a settled value)"
              if not conservative else "blocked: residual below the Hankel floor (noise)")
    top = reading.singular_values[0] if reading.singular_values else 0.0
    return Admission(
        site=site.site, residuals=site.members, hankel_top=top,
        second_fdt_floor=second_fdt_floor, threshold=reading.threshold,
        gate_pass=gate_pass, conservative=conservative, promoted=promoted, reason=reason,
        value=value, effective_rank=reading.effective_rank,
        stream_length=reading.stream_length)


def promote(admission: Admission, fast: Measure, slow: Measure) -> None:
    """PROMOTION IS RE-WEIGHTING. Nothing is copied and nothing is moved.

    The claim already exists in the one hypergraph. What changes is its weight under the slow
    measure. A implementation that inserted it somewhere would be building the second store
    this whole file exists to refuse.
    """
    if not admission.promoted:
        return
    slow.reweight(admission.site, 1.0)
    fast.reweight(admission.site, 0.0)
