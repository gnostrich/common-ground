"""Fibers, equivalence-prior edges, contested blocks, and loops.

Everything here is a *prior*. Gate 2 confines all of it to energy terms in F: a fiber
licenses a Q edge, a Q edge is a quadratic coupling, and neither can fix a slot's value.
Fiber construction is deterministic and its parameters are frozen in CONSTANTS.json, so
its influence is measurable — which is precisely what PREREG R4 measures by dropping 10%
of Q edges and checking whether the cold floor moves beyond surrogate noise.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MORPHISM — the base's morphisms, materialised as the Q graph settlement runs on.
Q3 motivated it. The SHAPE of this graph decides whether holonomy can be nonzero at all:
stars and forests give trivial Pi_1 and a necessarily-zero floor, so an edge that no arrow
declared would manufacture a cycle and with it a fake invariant. Hence loop_edges is exactly
the declared same_claim pairs and never a clique over a fiber.

"""

from __future__ import annotations

from collections import defaultdict
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


#: How an apex node is addressed in the Q graph. NOT a slot id and deliberately not shaped
#: like one: an apex is an ENERGY OBJECT, not a claim. It has no nu, no address, no type and
#: no tier; it cannot be cited, proposed, promoted or typed into. The prefix makes a stray
#: apex in a slot-shaped position visible instantly rather than silently plausible.
APEX_PREFIX = "apex:"


def apex_id(fiber) -> str:
    """The coequalizer's name. Derived from the fiber's own members, so it is stable."""
    members = sorted(getattr(fiber, "slots", fiber))
    return APEX_PREFIX + join_hash(*members)[:16]


def is_apex(node: str) -> bool:
    return str(node).startswith(APEX_PREFIX)


def edges_from_fibers(fibers: Sequence[Fiber], slots: Sequence[Slot] = ()) -> list[QEdge]:
    """APEX-STAR: one derived apex per fiber, k face-edges to it. NOT all-pairs.

    A fiber is a QUOTIENT — several claims declared to be one proposition — and the
    coequalizer of that quotient is a single object the faces map onto. This function used to
    emit one edge per within-fiber PAIR, so an n-member fiber contributed n(n-1)/2 couplings
    at full declared weight from what is, in the declarations, a chain. Measured on the live
    corpus before the repair: one 120-member fiber carried 73% of the entire corpus's
    fiber-coupling energy, and the corpus-wide over-coupling factor was 5.6x. Large fibers
    were rigidified in proportion to the SQUARE of their size and manufactured pair-level
    contest between claims nobody had compared.

    All-pairs also asserts something the declarations never did: that member 7 and member 92
    were directly declared equivalent, when what was declared is a path between them.

    THE WEIGHT WAS JUSTIFIED AND THE COUNT NEVER WAS. `DECLARED_WEIGHT` on every face-edge
    stands — a declared correspondence is asserted, not scored, and there is no similarity to
    weight it by. What changes is that k members now contribute k edges instead of k(k-1)/2.

    THE DEVIATION COST BECOMES k-INDEPENDENT in the sense that matters: a member's coupling to
    the quotient no longer grows with how many siblings it has, so a fiber cannot dominate its
    block by being large. A control plants a 120-member fiber and asserts exactly that.

    `slots` is accepted for call-site compatibility and unused.
    """
    out: dict[tuple[str, str], QEdge] = {}
    for fiber in fibers:
        members = sorted(fiber.slots)
        if len(members) < 2:
            continue
        apex = apex_id(fiber)
        for m in members:
            out[(apex, m)] = QEdge(u=apex, v=m, weight=DECLARED_WEIGHT,
                                   origin="correspondence")
    return [out[k] for k in sorted(out)]


def expand_stars(edges: Sequence[QEdge]) -> list[QEdge]:
    """The FACE-TO-FACE view of apex-star edges, for consumers that need slot adjacency.

    Apex-star is the right shape for the ENERGY: k face-edges to a derived consensus, so a
    member's coupling does not grow with its sibling count. It is the wrong shape for anything
    that asks "are these two slots joined" — the loop finder walking adjacency, the meter
    looking up a pair's weight — because under it two faces of one fiber are two hops apart
    through a node that is not a slot. Both consumers silently produced NOTHING: the loop
    finder found no cycles, so `measurements` came back empty and `mean_floor()` returned
    exactly 0.0, and the null battery's planted-defect cells stopped firing. A false zero,
    not a smaller number.

    THE EXPANSION IS THE SAME IDENTITY THE ENERGY USES, so the two views cannot drift.
    (lambda*w/2)*(k/(k-1))*sum_i ||p_i - p_bar||^2 is the same quadratic form as pairwise
    couplings of w/(k-1) between every pair of faces. At k=2 that is exactly w — a two-member
    fiber is one declared pair and nothing about it changed — and at k=120 it is w/119.
    Zero freedom: the anchor case fixes it and the algebra does the rest.
    """
    out: list[QEdge] = []
    stars: dict[str, tuple[float, str, list[str]]] = {}
    for e in edges:
        apex = e.u if is_apex(e.u) else (e.v if is_apex(e.v) else None)
        if apex is None:
            out.append(e)
            continue
        w, origin, faces = stars.get(apex, (e.weight, e.origin, []))
        faces.append(e.v if apex == e.u else e.u)
        stars[apex] = (w, origin, faces)
    for w, origin, faces in stars.values():
        if len(faces) < 2:
            continue
        implied = w / (len(faces) - 1.0)
        members = sorted(faces)
        for i, u in enumerate(members):
            for v in members[i + 1:]:
                out.append(QEdge(u=u, v=v, weight=implied, origin=origin))
    return out


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
    # APEX NODES CARRY NO DELTA, because they are not claims — nobody proposed one and nobody
    # can. They are the coequalizers the faces couple to, so they join the graph on the
    # strength of an ACTIVE face rather than on their own: an apex whose members are all
    # inactive contributes nothing, and one with an active member is what connects it to its
    # siblings. Without this the apex-star edges would be filtered out entirely and the
    # quotient would silently stop coupling.
    ids |= {n for e in edges for n in (e.u, e.v)
            if is_apex(n) and (e.u in ids or e.v in ids)}
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
        # AN APEX IS NOT A BLOCK MEMBER. It couples the faces and it is not one of them: a
        # block listing an apex among its slots would put a non-claim into contest counts,
        # settlement and every downstream reading that treats block membership as claims.
        members = tuple(sorted(n for n in component if not is_apex(n)))
        if not members:
            continue
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


#: Kept at 0 and always 0. The Hamiltonian search that needed a bound is gone — girth by
#: BFS is polynomial, so no fiber is ever declined. The name survives one release because
#: `loops_from_fibers` reported it and a reader may look for it; it is not a cap.
LOOPS_UNSEARCHED = 0


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
    """A CYCLE in Q among `members` — the shortest one, not one spanning all of them.

    Returns `None` when the members carry no cycle at all: they are in one fiber but Q is a
    tree over them, so there is nothing to measure a holonomy around. That is the tree case
    and it yields no loop, rather than a spec whose closing edge is missing.

    THE CORRECTION. This used to demand a cycle through EVERY member — a Hamiltonian cycle —
    and that was an over-strong accident rather than a definition. Holonomy is measured around
    a cycle in the fundamental groupoid; nothing requires that cycle to span its fiber. The
    cost of the accident was total and silent: on the live field, EIGHT same_claim components
    contained a real closed english<->python cycle and the constructor reported zero loops,
    because each had a leaf hanging off it. The floor, K, and every composition measurement
    were blocked behind a leaf.

    Two things follow, and both are improvements rather than trades:

      * NP-hardness goes away. A Hamiltonian-cycle search has no cheap bound, which is why
        `CYCLE_BRUTE_MAX` existed and why an unbounded `(n-1)!` search once stopped the read
        view from ever returning. Girth by breadth-first search is polynomial — O(V*E) — so
        the cap is DELETED rather than raised, and no fiber is ever left unsearched.
      * The preference survives. Among shortest cycles this still prefers the most chart
        alternations, then a crossing on the first step, then lexicographic order — so a
        restatement loop still reads `Eng_1 -> Lean -> Eng_2 -> Eng_1`, and the choice is
        deterministic and replayable from the seed.
    """
    inside = set(members)
    if len(inside) < 3:
        return None

    best: tuple[str, ...] | None = None
    best_key: tuple | None = None

    # Standard girth-by-BFS: from each root, the first non-tree edge encountered closes a
    # cycle through that root, and the minimum over all roots is the true shortest cycle.
    for root in sorted(inside):
        parent: dict[str, str | None] = {root: None}
        depth: dict[str, int] = {root: 0}
        queue = [root]
        while queue:
            x = queue.pop(0)
            for y in sorted(adj.get(x, ())):
                if y not in inside:
                    continue
                if y not in depth:
                    parent[y], depth[y] = x, depth[x] + 1
                    queue.append(y)
                elif parent.get(x) != y:
                    cycle = _close(x, y, parent)
                    if cycle is None:
                        continue
                    key = (len(cycle),
                           -_alternations(cycle, chart_of),
                           chart_of.get(cycle[0]) == chart_of.get(cycle[1]),
                           cycle)
                    if best_key is None or key < best_key:
                        best, best_key = cycle, key
    return best


def _close(x: str, y: str, parent: Mapping[str, str | None]) -> tuple[str, ...] | None:
    """The cycle formed by the non-tree edge (x, y), read off the BFS parent chains.

    Returns `None` if the two chains share any vertex besides their meeting point — that
    would be a figure-eight rather than a simple cycle, and holonomy around a walk that
    repeats a slot is not holonomy around a loop.
    """
    px: list[str] = [x]
    while parent[px[-1]] is not None:
        px.append(parent[px[-1]])          # type: ignore[arg-type]
    py: list[str] = [y]
    while parent[py[-1]] is not None:
        py.append(parent[py[-1]])          # type: ignore[arg-type]
    sx, sy = set(px), set(py)
    shared = sx & sy
    if len(shared) != 1:
        return None
    cycle = tuple(px[::-1] + py[:-1])
    return cycle if len(set(cycle)) == len(cycle) and len(cycle) >= 3 else None


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
    global LOOPS_UNSEARCHED

    allowed = set(restrict_to) if restrict_to is not None else None
    # THE EXPANDED VIEW. Adjacency is a question about SLOTS, and apex-star answers it
    # with a non-slot in between — the BFS drops the apex, finds no adjacency, and
    # reports no cycles at all. `expand_stars` restores the face-to-face view from the
    # same identity the energy uses, so the two cannot drift.
    adj = _adjacency(expand_stars(edges))
    loops: list[LoopSpec] = []
    seen: set[frozenset[str]] = set()
    unsearched = 0

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
    LOOPS_UNSEARCHED = unsearched
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
