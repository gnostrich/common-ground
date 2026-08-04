"""Fibers, equivalence-prior edges, contested blocks, and loops.

Everything here is a *prior*. Gate 2 confines all of it to energy terms in F: a fiber
licenses a Q edge, a Q edge is a quadratic coupling, and neither can fix a slot's value.
Fiber construction is deterministic and its parameters are frozen in CONSTANTS.json, so
its influence is measurable — which is precisely what PREREG R4 measures by dropping 10%
of Q edges and checking whether the cold floor moves beyond surrogate noise.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import permutations
from typing import Iterable, Mapping, Sequence

from .constants import REWIRE_PASSES
from .hashing import DRNG, join_hash
from .types import Block, Chart, Delta, Fiber, LoopSpec, QEdge, Slot

#: The declared correspondence weight. A declared typed translation is ASSERTED, not scored,
#: so its equivalence-prior coupling carries full weight; there is no similarity to grade it
#: by. Gate 2 still confines it to energy — a full-weight prior tilts, it never clamps.
DECLARED_WEIGHT = 1.0


def build_loop_fibers(slots: Sequence[Slot], arrows) -> list[Fiber]:
    """Fibers eligible to carry holonomy — built from `same_claim` arrows ONLY.

    `refines` and `instance_of` are directed and non-invertible, so a round trip through one
    is not a round trip: it may not be reversed even in principle. Including them would put
    holonomy on a path that never closes, which is the open-walk defect the tree-null repair
    removed. They still couple (see `structural_edges`); they just never make a loop.
    """
    from .correspondence import loop_pairs

    return build_fibers(slots, loop_pairs(arrows))


def loop_edges(slots: Sequence[Slot], arrows) -> list[QEdge]:
    """Q edges that may carry holonomy: EXACTLY the declared `same_claim` pairs.

    Deliberately NOT a clique over the fiber. Cliquing manufactures an edge that no arrow
    declared — and when a fiber's members are joined by a path `a~b~c`, the invented closing
    edge `a—c` let a cycle form through a pair whose only declared arrow was a non-invertible
    `refines`. The holonomy-exclusion control caught exactly that. An edge exists iff someone
    claimed it; a fiber that is a path stays a path, and a path has no holonomy (tree-null).
    """
    present = {s.id for s in slots}
    out: dict[tuple[str, str], QEdge] = {}
    for a in arrows:
        if not a.loop_eligible:
            continue
        u, v = a.pair
        if u in present and v in present:
            out[(u, v)] = QEdge(u=u, v=v, weight=DECLARED_WEIGHT,
                                origin="correspondence:same_claim")
    return [out[k] for k in sorted(out)]


def structural_edges(slots: Sequence[Slot], arrows) -> list[QEdge]:
    """Q edges for EVERY arrow kind — the coupling structure, loop-eligible or not.

    A `refines` arrow is real structure and enters F as energy (gate 2), so it ties the graph
    together and can be reported; it simply carries no holonomy. The origin tag records the
    kind so the structure audit can classify it and the meter can exclude it from loops.
    """
    present = {s.id for s in slots}
    out: dict[tuple[str, str], QEdge] = {}
    for a in arrows:
        u, v = a.pair
        if u in present and v in present:
            out[(u, v)] = QEdge(u=u, v=v, weight=DECLARED_WEIGHT,
                                origin=f"correspondence:{a.kind}")
    return [out[k] for k in sorted(out)]


def build_fibers(
    slots: Sequence[Slot],
    correspondence: Iterable[tuple[str, str]] = (),
) -> list[Fiber]:
    """Fibers = co-reference groups from EXACT DECLARED correspondence. No similarity.

    Gate 1 makes addressing exact, so two DISTINCT slots are distinct claims and two
    IDENTICAL addresses are already one slot (deduped upstream). Co-reference across distinct
    addresses is therefore never inferred from string overlap — it is DECLARED, as a typed
    translation (OBJECT.md `hol : Pi_1(B) -> Aut(Sem)`), and passed in as `correspondence`:
    a set of unordered slot-id pairs resolved by `engine/correspondence.py` from the seed.

    A fiber is a connected component of that declaration graph, restricted to present slots.
    With no declared correspondence every slot is its own singleton and NO multi-member fiber
    exists — which is the honest v0 state (the correspondence gap), not an empty result to be
    papered over with a similarity fallback.
    """
    present = {s.id for s in slots}
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for u, v in correspondence:
        if u in present and v in present:
            union(u, v)

    groups: dict[str, list[str]] = defaultdict(list)
    for s in slots:
        groups[find(s.id)].append(s.id)

    fibers: list[Fiber] = []
    for members in groups.values():
        if len(members) < 2:
            continue  # a lone slot is not a fiber
        m = tuple(sorted(members))
        fibers.append(Fiber(id=join_hash(*m)[:16], slots=m))
    return fibers


def edges_from_fibers(fibers: Sequence[Fiber], slots: Sequence[Slot] = ()) -> list[QEdge]:
    """One undirected Q edge per within-fiber pair. Weight is the DECLARED weight.

    A declared correspondence is asserted, not scored, so every within-fiber pair carries
    `DECLARED_WEIGHT`; there is no token similarity to weight it by. `slots` is accepted for
    call-site compatibility and unused — edges are a function of the fibers alone now.
    """
    out: dict[tuple[str, str], QEdge] = {}
    for fiber in fibers:
        members = sorted(fiber.slots)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                u, v = members[i], members[j]
                out[(u, v)] = QEdge(u=u, v=v, weight=DECLARED_WEIGHT, origin="correspondence")
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


def _adjacency(edges: Sequence[QEdge]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        if e.weight > 0.0:
            adj[e.u].add(e.v)
            adj[e.v].add(e.u)
    return adj


def _alternations(order: Sequence[str], chart_of: Mapping[str, Chart]) -> int:
    """How many consecutive pairs of the cycle cross charts."""
    n = len(order)
    return sum(
        1 for i in range(n)
        if chart_of.get(order[i]) != chart_of.get(order[(i + 1) % n])
    )


def order_cycle(
    members: Sequence[str],
    chart_of: Mapping[str, Chart],
    adj: Mapping[str, set[str]],
) -> tuple[str, ...] | None:
    """A cyclic ordering of `members` in which every consecutive pair is a Q edge.

    Returns `None` when no such ordering exists — the members are in one fiber but Q does
    not connect them in a cycle, so there is nothing to measure a holonomy around. That is
    the tree case, and it now yields no loop at all rather than a spec whose closing edge
    is missing.

    Among valid orderings it prefers the one with the most chart alternations, which is
    what makes a restatement loop come out as the genuine triangle
    `Eng_1 -> Lean -> Eng_2 -> Eng_1` rather than `Eng_1 -> Eng_2 -> Lean -> Eng_1`. Both
    are cycles over the same three slots, but only the first traverses the correspondence
    twice and the paraphrase once, which is the shape PREREG's matrix names. Ties break
    lexicographically so the choice is deterministic and replayable from the seed.

    Brute force over member orderings is exact and cheap for the small declared groups this
    build produces; a large declared correspondence group would need a non-brute-force cycle
    finder (recorded limitation on `Fiber`).
    """
    if len(members) < 3:
        return None

    first, rest = members[0], list(members[1:])
    best: tuple[str, ...] | None = None
    best_key: tuple[int, bool, tuple[str, ...]] | None = None

    for perm in permutations(rest):
        order = (first, *perm)
        # Both traversal directions are enumerated rather than filtered to a canonical one.
        # They are the same edge set, but holonomy starts at `slots[0]` and walks forward,
        # so the direction decides whether a restatement cycle opens on the correspondence
        # leg or on the paraphrase leg. The key below picks; its lexicographic tail keeps
        # the choice deterministic.
        n = len(order)
        if any(order[(i + 1) % n] not in adj.get(order[i], ()) for i in range(n)):
            continue
        # Prefer, in order: most chart alternations; then a crossing on the very first
        # step, so a restatement cycle reads literally `Eng_1 -> Lean -> Eng_2 -> Eng_1`
        # rather than starting on the paraphrase leg; then lexicographic, for determinism.
        opens_on_a_crossing = chart_of.get(order[0]) != chart_of.get(order[1])
        key = (-_alternations(order, chart_of), not opens_on_a_crossing, order)
        if best_key is None or key < best_key:
            best, best_key = order, key

    return best


def loops_from_fibers(
    fibers: Sequence[Fiber],
    chart_of: Mapping[str, Chart],
    restrict_to: Iterable[str] | None = None,
    edges: Sequence[QEdge] = (),
) -> list[LoopSpec]:
    """One verified cycle per fiber that has one. **Cycles only — never walks.**

    A loop is a cycle in the Q graph, and always was: `hol(loop) = TV(p_start,
    T_loop(p_start))` only means path dependence if the transport genuinely returns to
    where it started. This constructor now enforces that rather than assuming it.

    Two things changed in the tree-null repair, and both were defects rather than choices:

    - **A two-member fiber yields no loop.** It used to yield the backtracking walk
      `u -> v -> u`, whose residual is nonzero on a tree — where theory says all contest is
      path-debt and the floor is exactly zero. That residual is a property of the transport
      operator (a contraction, not a reversible transport), not of the ledger. It is now
      collected by `meter.measured_shadow` as the edge's closure defect, which is the
      quantity it always was.
    - **Closure is verified against Q.** The cycle used to be built from fiber *membership*,
      so a three-member fiber over the path `u-v-x` produced the spec `(u,v,x)` whose
      closing edge `(x,u)` did not exist; `holonomy` skipped it and silently measured an
      open walk. `order_cycle` now returns `None` unless Q actually closes, and `holonomy`
      raises rather than skipping.

    `kind` is `restatement` when the cycle crosses charts and `paraphrase` when it stays
    inside one — the two loop families PREREG names, unchanged, and now correctly
    instantiated.
    """
    allowed = set(restrict_to) if restrict_to is not None else None
    adj = _adjacency(edges)
    loops: list[LoopSpec] = []
    seen: set[frozenset[str]] = set()

    for fiber in fibers:
        members = [s for s in sorted(fiber.slots) if allowed is None or s in allowed]
        if len(members) < 3:
            continue
        key = frozenset(members)
        if key in seen:
            continue
        order = order_cycle(members, chart_of, adj)
        if order is None:
            continue
        seen.add(key)
        kind = "restatement" if _alternations(order, chart_of) else "paraphrase"
        loops.append(
            LoopSpec(id=join_hash("loop", *order)[:16], kind=kind, slots=order)
        )
    return loops


def backtrack_edges(
    fibers: Sequence[Fiber],
    restrict_to: Iterable[str] | None = None,
    edges: Sequence[QEdge] = (),
) -> list[tuple[str, str]]:
    """The `u -> v` pairs whose round trip is a measured-shadow channel, not a loop.

    Every Q edge inside a fiber contributes one. These used to be counted as holonomy when
    the fiber had exactly two members; now their closure defect is measured and compared
    against the shadow the seed declared.
    """
    allowed = set(restrict_to) if restrict_to is not None else None
    present = {
        (e.u, e.v) if e.u <= e.v else (e.v, e.u) for e in edges if e.weight > 0.0
    }
    out: set[tuple[str, str]] = set()
    for fiber in fibers:
        members = [s for s in sorted(fiber.slots) if allowed is None or s in allowed]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pair = (members[i], members[j])
                if pair in present:
                    out.add(pair)
    return sorted(out)


def drop_edges(edges: Sequence[QEdge], rate: float, rng: DRNG) -> list[QEdge]:
    """PREREG R4: drop a fraction of Q edges at random, deterministically per trial."""
    mask = rng.sample_mask(len(edges), rate)
    return [e for e, keep in zip(edges, mask) if keep]


def rewire_q_graph(
    edges: Sequence[QEdge],
    rng: DRNG,
    passes: int = REWIRE_PASSES,
) -> list[QEdge]:
    """The R4 null: a Q graph with the same shape but no dictionary content.

    PREREG-AMENDMENT-2 needs a reference built under the hypothesis *the dictionary does
    not matter*. Comparing dropout movement against a resample of the observed floors
    cannot do that (gate 6), so this constructs a graph that is exchangeable with the real
    one under that hypothesis: same nodes, same degree per node, same multiset of weights,
    same edge count per weight stratum — but the *pairings* randomized. Anything the real
    graph knows that survives here is topology, not semantics.

    Mechanism: edges are stratified by weight, and within each stratum endpoints are
    permuted by double-edge swaps (Maslov-Sneppen). Swapping `(u1,v1),(u2,v2)` for
    `(u1,v2),(u2,v1)` leaves every node's degree untouched and, because both edges are
    drawn from the same stratum, leaves the weight attached to that stratum. Swaps that
    would create a self-loop or a duplicate pair are refused rather than accepted with a
    fixup, so the invariants hold exactly rather than approximately.

    Stratifying matters. A rewire that ignored weight would move a heavy fiber edge onto a
    pair that never earned one, so the null would differ from the observation in edge
    *strength* as well as in pairing, and a rejection could not be attributed to the
    dictionary. Within a stratum every edge carries the same weight, so the only thing the
    randomization destroys is which slots the dictionary chose to link.

    `origin` rides with the stratum key too: a `fiber` edge and a `lexicon` edge of equal
    weight are different claims about why two slots are alike, and mixing them would let
    the null borrow structure across provenance.
    """
    if len(edges) < 2:
        return list(edges)

    strata: dict[tuple[float, str], list[QEdge]] = defaultdict(list)
    for e in edges:
        strata[(e.weight, e.origin)].append(e)

    out: list[QEdge] = []
    for key in sorted(strata, key=lambda k: (k[0], k[1])):
        group = sorted(strata[key], key=lambda e: (e.u, e.v))
        pairs = [(e.u, e.v) for e in group]
        present = {frozenset(p) for p in pairs}
        weight, origin = key

        for _ in range(passes * len(pairs)):
            if len(pairs) < 2:
                break
            i, j = rng.randrange(len(pairs)), rng.randrange(len(pairs))
            if i == j:
                continue
            (u1, v1), (u2, v2) = pairs[i], pairs[j]
            a, b = frozenset((u1, v2)), frozenset((u2, v1))
            if u1 == v2 or u2 == v1 or len(a) < 2 or len(b) < 2:
                continue          # would make a self-loop
            if a in present or b in present or a == b:
                continue          # would make a duplicate pair
            present.discard(frozenset(pairs[i]))
            present.discard(frozenset(pairs[j]))
            pairs[i], pairs[j] = (u1, v2), (u2, v1)
            present.add(a)
            present.add(b)

        out.extend(QEdge(u=u, v=v, weight=weight, origin=origin) for u, v in pairs)

    return sorted(out, key=lambda e: (e.u, e.v, e.origin))


def degree_map(edges: Sequence[QEdge]) -> dict[str, int]:
    """Node -> degree. What `rewire_q_graph` must leave invariant."""
    deg: dict[str, int] = defaultdict(int)
    for e in edges:
        deg[e.u] += 1
        deg[e.v] += 1
    return dict(deg)


def weight_marginal(edges: Sequence[QEdge]) -> dict[tuple[float, str], int]:
    """(weight, origin) -> count. The other invariant."""
    out: dict[tuple[float, str], int] = defaultdict(int)
    for e in edges:
        out[(e.weight, e.origin)] += 1
    return dict(out)
