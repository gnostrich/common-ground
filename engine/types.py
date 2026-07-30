"""Core types: slots, warrants, deltas, fibers, blocks, loops.

Gate 3 lives here. `Warrant.clamp_eligible` is a derived property, not a settable field,
so there is no way to construct a clamp-eligible warrant out of extraction provenance —
the tier is the only input, and the extractor base class stamps `EXTRACTION` on every
delta it produces without offering an override.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Literal, Sequence

from .constants import BVALUES, CHARTS, CLAIM_FORMS, FIBER_CAP

Chart = Literal["english", "lean"]
ClaimForm = Literal["assert", "define", "conditional", "normative"]
BValue = Literal["N", "F", "T", "B"]


class WarrantTier(IntEnum):
    """Ordered warrant tiers. Lower is stronger.

    The tier ordering is not a confidence scale. It is a statement about what kind of
    thing could make the warrant wrong: a kernel receipt is wrong only if the toolchain
    is wrong, whereas an extraction is wrong if a model misread a sentence.
    """

    KERNEL = 0  # Lean kernel-accept under the pinned toolchain (D6)
    CI_RECEIPT = 1  # CI-green test receipt
    PREMINTED = 2  # D5 pre-minted lexicon entry
    REPO_DOC = 3  # README / STATEMENTS / docs, with repo provenance
    EXTRACTION = 4  # k-extractor output. Never grounds.


#: Gate 3. The only two tiers that may clamp.
TOP_TIER: frozenset[WarrantTier] = frozenset({WarrantTier.KERNEL, WarrantTier.CI_RECEIPT})

#: Energy weight contributed by a warrant tier, used by `energy.py`. A non-clamping
#: warrant can be arbitrarily heavy and still never fix a value — that is the whole
#: content of gate 2 and gate 3 taken together.
TIER_WEIGHT: dict[WarrantTier, float] = {
    WarrantTier.KERNEL: 8.0,
    WarrantTier.CI_RECEIPT: 6.0,
    WarrantTier.PREMINTED: 4.0,
    WarrantTier.REPO_DOC: 2.0,
    WarrantTier.EXTRACTION: 1.0,
}


@dataclass(frozen=True, slots=True)
class Warrant:
    tier: WarrantTier
    detail: str = ""

    @property
    def clamp_eligible(self) -> bool:
        """Gate 3. Derived, never stored, never overridable."""
        return self.tier in TOP_TIER

    @property
    def weight(self) -> float:
        return TIER_WEIGHT[self.tier]

    def as_record(self) -> dict[str, object]:
        return {
            "tier": self.tier.name,
            "detail": self.detail,
            "clamp_eligible": self.clamp_eligible,
        }


@dataclass(frozen=True, slots=True)
class Provenance:
    source: str  # "claude_export" | "lean_corpus" | "repo_docs" | "seed"
    doc_id: str
    locator: str = ""
    extractor_id: str = ""
    content_hash: str = ""

    def as_record(self) -> dict[str, object]:
        return {
            "source": self.source,
            "doc_id": self.doc_id,
            "locator": self.locator,
            "extractor_id": self.extractor_id,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class Slot:
    """An address. `id` is sha256(nu(surface), type) — see engine/normalize.py."""

    id: str
    nu: str
    type: ClaimForm
    chart: Chart

    def as_record(self) -> dict[str, object]:
        return {"slot": self.id, "type": self.type, "chart": self.chart}


@dataclass(frozen=True, slots=True)
class Delta:
    """A typed, warranted, addressed candidate. The unit an extractor emits."""

    slot: str
    chart: Chart
    type: ClaimForm
    value: BValue
    confidence: float
    warrant: Warrant
    provenance: Provenance
    surface: str
    nu: str

    def __post_init__(self) -> None:
        if self.value not in BVALUES:
            raise ValueError(f"unknown b-value {self.value!r}; expected one of {BVALUES}")
        if self.type not in CLAIM_FORMS:
            raise ValueError(f"unknown claim-form {self.type!r}")
        if self.chart not in CHARTS:
            raise ValueError(f"unknown chart {self.chart!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence} outside [0, 1]")

    def as_record(self) -> dict[str, object]:
        return {
            "slot": self.slot,
            "chart": self.chart,
            "type": self.type,
            "value": self.value,
            "confidence": self.confidence,
            "warrant": self.warrant.as_record(),
            "provenance": self.provenance.as_record(),
        }


@dataclass(frozen=True, slots=True)
class Fiber:
    """A co-reference *hypothesis* over at most FIBER_CAP slots.

    Membership never merges addresses. Two slots in a fiber keep distinct ids and settle
    to their own distributions; the fiber only licenses an equivalence-prior edge, which
    by gate 2 can enter F as energy and nothing more.
    """

    id: str
    slots: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.slots) > FIBER_CAP:
            raise ValueError(
                f"fiber {self.id} has {len(self.slots)} slots, cap is {FIBER_CAP}"
            )
        if len(set(self.slots)) != len(self.slots):
            raise ValueError(f"fiber {self.id} has duplicate slots")


@dataclass(frozen=True, slots=True)
class QEdge:
    """An equivalence-prior edge. Energy only (gate 2)."""

    u: str
    v: str
    weight: float
    origin: str  # "fiber" | "lexicon" | "preminted"

    def crosses_charts(self, chart_of: dict[str, Chart]) -> bool:
        return chart_of.get(self.u) != chart_of.get(self.v)


@dataclass(frozen=True, slots=True)
class Clamp:
    """A grounded value assignment. Only constructible from a clamp-eligible warrant.

    The check is in the constructor rather than at the call site so that no code path can
    produce a Clamp object carrying a non-grounding warrant, whatever it intends.
    """

    slot: str
    value: BValue
    warrant: Warrant

    def __post_init__(self) -> None:
        if not self.warrant.clamp_eligible:
            from . import GateViolation

            raise GateViolation(
                3,
                f"attempted clamp on slot {self.slot} with tier "
                f"{self.warrant.tier.name}, which is not clamp-eligible",
            )


@dataclass(slots=True)
class Block:
    """A contested block: a connected component of Q restricted to slots with deltas."""

    id: str
    slots: tuple[str, ...]
    edges: tuple[QEdge, ...]

    def neighbours(self) -> dict[str, list[tuple[str, float]]]:
        adj: dict[str, list[tuple[str, float]]] = {s: [] for s in self.slots}
        for e in self.edges:
            if e.u in adj and e.v in adj:
                adj[e.u].append((e.v, e.weight))
                adj[e.v].append((e.u, e.weight))
        return adj


@dataclass(slots=True)
class SettledBlock:
    """The result of running mirror descent on one block."""

    block_id: str
    p: dict[str, list[float]]
    f_before: float
    f_after: float
    certificate: Literal["monotone", "violated"]
    iterations: int
    backtracks: int
    grad_norm: float
    f_trace: list[float] = field(default_factory=list)
    clamped: tuple[str, ...] = ()

    @property
    def converged(self) -> bool:
        return self.certificate == "monotone"


@dataclass(frozen=True, slots=True)
class Document:
    doc_id: str
    chart: Chart
    text: str
    source: str
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        """Hash of the text alone, independent of doc_id and source label.

        This is what makes re-ingestion under a different provenance label idempotent
        (null cell v) without also collapsing genuine corroboration: two different
        documents asserting the same claim have different content hashes and both count.
        """
        from .hashing import sha256_text

        return sha256_text(self.text)


@dataclass(frozen=True, slots=True)
class LoopSpec:
    """A closed path through slots, over which holonomy is measured.

    `slots` is the ordered cycle; the closing edge from the last slot back to the first
    is implicit. A restatement loop (Eng -> Lean -> Eng) and an intra-English paraphrase
    loop differ only in which slots appear, not in how the holonomy is computed.
    """

    id: str
    kind: Literal["restatement", "paraphrase"]
    slots: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.slots) < 2:
            raise ValueError(f"loop {self.id} needs at least 2 slots")

    def edges(self) -> list[tuple[str, str]]:
        n = len(self.slots)
        return [(self.slots[i], self.slots[(i + 1) % n]) for i in range(n)]


class NullStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"  # cannot run: an input the cell needs is unresolved


class ControlState(str, Enum):
    """Whether a cell's positive control fired.

    A positive control feeds the cell a deliberately broken input that it MUST flag. If
    the control does not fire, the cell cannot detect what it claims to detect, and its
    PASS is worthless — so `DEAD` is treated as a battery failure regardless of what the
    cell said about the real input.
    """

    LIVE = "live"  # control fired: the cell demonstrably can fail
    DEAD = "dead"  # control did NOT fire: the cell cannot detect its own failure mode
    NOT_RUN = "not-run"


@dataclass(slots=True)
class NullCell:
    cell: str
    status: NullStatus
    detail: str
    stats: dict[str, object] = field(default_factory=dict)
    control: ControlState = ControlState.NOT_RUN
    control_detail: str = ""


@dataclass(slots=True)
class NullBatteryReport:
    seed_hash: str
    cells: list[NullCell]

    @property
    def dead_controls(self) -> list[str]:
        return [c.cell for c in self.cells if c.control is ControlState.DEAD]

    @property
    def status(self) -> NullStatus:
        """A battery is PASS only if every cell passed *and* every control fired.

        A dead control outranks everything: a cell that cannot fail is not evidence, so
        its verdict on the real input carries no information and the battery must not be
        read as green because of it.

        Otherwise BLOCKED dominates FAIL in reporting order, because a blocked cell means
        the run was never in a position to be judged — a different verdict from a cell
        that ran and failed.
        """
        if self.dead_controls:
            return NullStatus.FAIL
        if any(c.status is NullStatus.FAIL for c in self.cells):
            return NullStatus.FAIL
        if any(c.status is NullStatus.BLOCKED for c in self.cells):
            return NullStatus.BLOCKED
        return NullStatus.PASS

    def as_record(self) -> dict[str, object]:
        return {
            "seed_hash": self.seed_hash,
            "status": self.status.value,
            "dead_controls": self.dead_controls,
            "cells": [
                {
                    "cell": c.cell,
                    "status": c.status.value,
                    "detail": c.detail,
                    "control": c.control.value,
                    "control_detail": c.control_detail,
                    "stats": c.stats,
                }
                for c in self.cells
            ],
        }


def chart_map(slots: Sequence[Slot]) -> dict[str, Chart]:
    return {s.id: s.chart for s in slots}
