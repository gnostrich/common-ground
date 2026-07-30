"""Fibers, equivalence-prior edges, contested blocks, and loops.

Everything here is a *prior*. Gate 2 confines all of it to energy terms in F: a fiber
licenses a Q edge, a Q edge is a quadratic coupling, and neither can fix a slot's value.
Fiber construction is deterministic and its parameters are frozen in CONSTANTS.json, so
its influence is measurable — which is precisely what PREREG R4 measures by dropping 10%
of Q edges and checking whether the cold floor moves beyond surrogate noise.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Mapping, Sequence

from .constants import (
    FIBER_CAP,
    FIBER_CROSS_THRESHOLD,
    FIBER_INTRA_THRESHOLD,
    FIBER_TOKEN_PREFIX,
    STOPWORDS,
)
from .hashing import DRNG, join_hash
from .types import Block, Chart, Delta, Fiber, LoopSpec, QEdge, Slot

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SPLIT_RE = re.compile(r"[^0-9A-Za-zÀ-ɏ]+")


def content_tokens(nu: str) -> frozenset[str]:
    """Declared, deterministic token key used for fiber similarity.

    Identifiers are split on underscores and CamelCase boundaries first, so a Lean
    `IsPositive` and an English `positivity` can share a token prefix. Tokens are then
    truncated to `FIBER_TOKEN_PREFIX` characters, which is a crude stemmer — crude on
    purpose, since a real stemmer would be a lexicon and would need to be seeded and
    hashed like one.
    """
    body = nu.lstrip("\x01")
    if body[:4] in ("en\x01", "lean"):  # tolerate either tag having been stripped
        body = body.split("\x01", 1)[-1] if "\x01" in body else body
    spaced = _CAMEL_RE.sub(" ", body)
    raw = _SPLIT_RE.split(spaced)
    out: set[str] = set()
    for tok in raw:
        t = tok.casefold()
        if not t or t in STOPWORDS or len(t) < 2:
            continue
        out.add(t[:FIBER_TOKEN_PREFIX])
    return frozenset(out)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def build_fibers(slots: Sequence[Slot]) -> list[Fiber]:
    """Group slots into co-reference hypotheses, capped at FIBER_CAP members.

    Each slot proposes a fiber consisting of itself plus its strongest neighbours;
    duplicates by membership are collapsed. A fiber is never an identification — the
    member slots keep distinct addresses and settle independently.
    """
    toks = {s.id: content_tokens(s.nu) for s in slots}
    chart_of = {s.id: s.chart for s in slots}
    ordered = sorted(slots, key=lambda s: s.id)

    seen: set[frozenset[str]] = set()
    fibers: list[Fiber] = []

    for s in ordered:
        scored: list[tuple[float, str]] = []
        for other in ordered:
            if other.id == s.id:
                continue
            sim = jaccard(toks[s.id], toks[other.id])
            threshold = (
                FIBER_INTRA_THRESHOLD
                if chart_of[s.id] == chart_of[other.id]
                else FIBER_CROSS_THRESHOLD
            )
            if sim >= threshold:
                scored.append((sim, other.id))
        if not scored:
            continue
        # Deterministic: strongest first, ties broken by slot id.
        scored.sort(key=lambda t: (-t[0], t[1]))
        members = tuple(sorted({s.id, *(sid for _, sid in scored[: FIBER_CAP - 1])}))
        key = frozenset(members)
        if key in seen:
            continue
        seen.add(key)
        fibers.append(Fiber(id=join_hash(*members)[:16], slots=members))

    return fibers


def edges_from_fibers(fibers: Sequence[Fiber], slots: Sequence[Slot]) -> list[QEdge]:
    """One undirected Q edge per within-fiber pair, weighted by token similarity."""
    toks = {s.id: content_tokens(s.nu) for s in slots}
    out: dict[tuple[str, str], QEdge] = {}
    for fiber in fibers:
        members = sorted(fiber.slots)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                u, v = members[i], members[j]
                w = jaccard(toks.get(u, frozenset()), toks.get(v, frozenset()))
                if w <= 0.0:
                    continue
                key = (u, v)
                prior = out.get(key)
                if prior is None or w > prior.weight:
                    out[key] = QEdge(u=u, v=v, weight=w, origin="fiber")
    return [out[k] for k in sorted(out)]


def build_blocks(
    slots: Sequence[Slot],
    edges: Sequence[QEdge],
    deltas: Sequence[Delta],
) -> list[Block]:
    """Connected components of Q over slots that carry at least one delta.

    Slots with no delta are dropped: settling a slot no source ever mentioned would put
    the seed's own priors into the floor, which is the circularity gate 2 exists to stop.
    """
    active = {d.slot for d in deltas}
    relevant = [s for s in slots if s.id in active]
    if not relevant:
        return []

    ids = {s.id for s in relevant}
    adj: dict[str, set[str]] = defaultdict(set)
    kept = [e for e in edges if e.u in ids and e.v in ids]
    for e in kept:
        adj[e.u].add(e.v)
        adj[e.v].add(e.u)

    seen: set[str] = set()
    blocks: list[Block] = []
    for sid in sorted(ids):
        if sid in seen:
            continue
        stack = [sid]
        component: set[str] = set()
        while stack:
            cur = stack.pop()
            if cur in component:
                continue
            component.add(cur)
            stack.extend(n for n in adj[cur] if n not in component)
        seen |= component
        members = tuple(sorted(component))
        block_edges = tuple(e for e in kept if e.u in component and e.v in component)
        blocks.append(Block(id=join_hash(*members)[:16], slots=members, edges=block_edges))

    return blocks


def is_contested(block: Block, deltas: Sequence[Delta]) -> bool:
    """A block is contested if it could disagree with itself.

    Two ways that happens: more than one slot joined by a prior, or a single slot whose
    deltas support more than one b-value.
    """
    if len(block.slots) > 1:
        return True
    values = {d.value for d in deltas if d.slot in block.slots}
    return len(values) > 1


def loops_from_fibers(
    fibers: Sequence[Fiber],
    chart_of: Mapping[str, Chart],
    restrict_to: Iterable[str] | None = None,
) -> list[LoopSpec]:
    """One canonical cycle per fiber with at least two members.

    A two-member fiber yields a 2-cycle `u -> v -> u`. That is a genuine holonomy, not a
    degenerate one: the transport operators in `meter.py` are composed in path order and
    the round trip is not the identity unless the two settled states already agree.

    `kind` is `restatement` when the cycle crosses charts (an Eng -> Lean -> Eng loop) and
    `paraphrase` when it stays inside one (an intra-English loop over REGISTRY claims) —
    the two loop families PREREG names.
    """
    allowed = set(restrict_to) if restrict_to is not None else None
    loops: list[LoopSpec] = []
    for fiber in fibers:
        members = [s for s in sorted(fiber.slots) if allowed is None or s in allowed]
        if len(members) < 2:
            continue
        charts = {chart_of.get(s) for s in members}
        kind = "restatement" if len(charts) > 1 else "paraphrase"
        loops.append(
            LoopSpec(id=join_hash("loop", *members)[:16], kind=kind, slots=tuple(members))
        )
    return loops


def drop_edges(edges: Sequence[QEdge], rate: float, rng: DRNG) -> list[QEdge]:
    """PREREG R4: drop a fraction of Q edges at random, deterministically per trial."""
    mask = rng.sample_mask(len(edges), rate)
    return [e for e, keep in zip(edges, mask) if keep]
