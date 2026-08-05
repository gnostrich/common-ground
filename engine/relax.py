"""A typed query is a BIAS on the corpus's energy. This runs the relaxation and reports it.

What this replaces, and why the replacement is not a refinement of it:

`engine/inbound.py` used to address the typed text (gate 1, exact), look the resulting slot
ids up in a dict, and — when the lookup missed — fall back to matching words. Settlement was
named in its docstring and called nowhere. That is lookup-with-fallback wearing the name of
bias-and-relax, and the two are not close. A lookup asks *is this string already here*. A
relaxation asks *what in the field moves when this constraint is applied*, and the answer can
name claims whose words appear nowhere in the query, while a corpus that holds the words but
no coupling correctly reports that nothing moved.

Exact addressing governs CLAIM IDENTITY — two claims are the same claim or they are not, and
the answer is a hash. It never governed how a bias reaches the field, and making it do so is
what produced a window that answered every real question with "nothing addressed".

How the bias reaches the field, with no fuzzy matching anywhere:

  1. The typed text is extracted into deltas by the ordinary extractor, so it is addressed
     exactly as corpus material would be. It is not privileged and not softened by guessing.
  2. Those deltas enter the corpus's energy as SOFT evidence — scaled by `BIAS_WEIGHT`, so
     they tilt F without fixing anything. A bias is not a clamp; gate 3 is untouched, and
     nothing here could clamp if it wanted to since extraction never grounds.
  3. Settlement runs twice on each affected block: once on the corpus alone, once with the
     bias added. Mirror descent, the same `engine/settle.settle` the meter uses.
  4. What MOVED is the difference between the two settled distributions. Propagation happens
     over the block's edges, and those edges are EXACTLY the declared correspondences — the
     coupling graph is `engine/blocks.structural_edges`, built from arrows somebody proposed.
     No edge exists that no arrow declared.
  5. Every moved slot carries the PATH by which the bias reached it: a sequence of declared
     arrows from a bias-carrying slot to that slot. A fact with no path is not compiled.

There is no gate on whether the bias "hit" anything. A typed claim whose address is new to
the corpus simply joins the graph with no edges, so nothing is coupled to it and nothing
moves — and that is REPORTED as a property of the field ("nothing responded, and here is
why") rather than treated as a failed lookup with a keyword list for consolation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .blocks import structural_edges
from .constants import BVALUES
from .corpus_state import CorpusSnapshot, with_arrows
from .energy import evidence_from_deltas, lexicon_prior
from .extract import DeterministicExtractor
from .settle import settle
from .types import Block, Document, Slot, Warrant, WarrantTier

NBV = len(BVALUES)
BVALUE_INDEX = {v: i for i, v in enumerate(BVALUES)}

#: How hard the typed input pushes. A bias, not an assertion: it tilts F and is outweighed by
#: a slot the corpus has real evidence on, which is the point — a question should not be able
#: to overwrite an answer. Small enough to be a perturbation, large enough to propagate.
BIAS_WEIGHT = 0.35

#: Inverse temperature for the read-side relaxation. The meter's arms run 1.0 and 4.0; the
#: read path uses the softer one, because a sharp objective drives every block to a corner
#: and a corner cannot show which way the bias pushed.
READ_BETA = 1.0

#: A slot has MOVED if its settled distribution shifts by more than this in L1. Mirror descent
#: leaves float noise well below it; the threshold is what separates a response from a rounding
#: difference, and it is stated rather than tuned per query.
MOVED_EPS = 1e-4

#: Blocks larger than this are not settled. Settling is superlinear in block size and a hub
#: block can swallow a whole corpus; what is skipped is COUNTED and reported, never dropped
#: silently, because a truncated relaxation reported as a complete one is a false negative
#: with no signal attached.
BLOCK_CAP = 400

#: How many moved slots reach the compiled input. Ordered by how far they moved, so the cut
#: is at the least-responsive end, and the count of what was cut is reported.
MOVED_CAP = 24


@dataclass(frozen=True, slots=True)
class Hop:
    """One declared arrow the perturbation travelled, with the warrant it travelled on.

    Rendered as a string this was unreadable and, worse, unusable: "how far did it reach"
    and "on what warrant" are different questions, and a reach of three hops on three
    EXTRACTION arrows is a much weaker statement than one hop on a CI_RECEIPT. The tier
    rides on every step so the strength of a path is visible rather than inferred from its
    length.
    """

    kind: str                                 # same_claim | refines | instance_of
    tier: str                                 # the ARROW's warrant tier, not the slot's
    provisional: bool
    to_slot: str
    to_chart: str
    to_nu: str

    def as_record(self) -> dict[str, object]:
        return {"kind": self.kind, "tier": self.tier, "provisional": self.provisional,
                "to": self.to_slot[:16], "chart": self.to_chart, "nu": self.to_nu[:200]}

    def render(self) -> str:
        state = "provisional" if self.provisional else "confirmed"
        return (f"{self.kind} ({state}, warrant {self.tier}) -> [{self.to_chart}] "
                f"{self.to_nu[:110]}")


@dataclass(frozen=True, slots=True)
class Moved:
    """One slot that responded to the bias, and the declared path by which it was reached."""

    slot: str
    chart: str
    type: str
    nu: str
    value: str
    tier: str
    contested: bool
    shift: float                              # L1 distance between settled and baseline
    before: tuple[float, ...]
    after: tuple[float, ...]
    path: tuple[Hop, ...]                     # declared arrows, bias-side first
    hops: int                                 # 0 = the bias landed on this slot itself

    @property
    def weakest_tier(self) -> str:
        """The weakest arrow on the path — what the whole reach actually rests on.

        A chain is no stronger than its weakest declared link, so reporting the path's tiers
        without this invites reading the first hop's warrant as the path's.
        """
        if not self.path:
            return ""
        order = {"KERNEL": 0, "CI_RECEIPT": 1, "AUTHORSHIP": 2, "PREMINTED": 3,
                 "REPO_DOC": 4, "EXTRACTION": 5}
        return max((h.tier for h in self.path), key=lambda x: order.get(x, 99))

    def as_record(self) -> dict[str, object]:
        return {"slot": self.slot[:16], "chart": self.chart, "type": self.type,
                "value": self.value, "tier": self.tier, "contested": self.contested,
                "shift": round(self.shift, 6), "hops": self.hops,
                "path": [h.as_record() for h in self.path],
                "weakest_tier": self.weakest_tier,
                "reached_by": ("the bias landed on this slot" if self.hops == 0
                               else f"{self.hops} declared arrow(s) from a biased slot")}


@dataclass(slots=True)
class Relaxation:
    """What the field did when the bias was applied. Empty is a result, not a failure."""

    bias_slots: tuple[str, ...] = ()          # addresses the typed text produced
    bias_in_field: tuple[str, ...] = ()       # those the corpus already carried
    moved: list[Moved] = field(default_factory=list)
    blocks_settled: int = 0
    blocks_skipped: int = 0                   # over BLOCK_CAP; counted, never silent
    slots_considered: int = 0
    moved_dropped: int = 0                    # over MOVED_CAP
    silence: str = ""                         # why nothing moved, when nothing moved

    @property
    def responded(self) -> bool:
        return bool(self.moved)

    def as_record(self) -> dict[str, object]:
        return {"responded": self.responded, "bias_slots": len(self.bias_slots),
                "bias_in_field": len(self.bias_in_field), "moved": len(self.moved),
                "blocks_settled": self.blocks_settled,
                "blocks_skipped": self.blocks_skipped,
                "slots_considered": self.slots_considered,
                "moved_dropped": self.moved_dropped, "silence": self.silence,
                "rows": [m.as_record() for m in self.moved]}


def bias_deltas(text: str, chart: str = "english"):
    """The typed text as addressed claims. The ordinary extractor; nothing privileged."""
    return list(DeterministicExtractor("inbound", "typed").extract(
        Document("inbound", chart, text, "typed")))


def _corpus_evidence(snapshot: CorpusSnapshot, slots) -> dict[str, list[float]]:
    """Per-slot evidence energy from what the corpus already holds.

    The snapshot stores one settled value and confidence per slot rather than the deltas it
    came from, so the energy is reconstructed the same way `evidence_from_deltas` builds it —
    supporting a value lowers its energy, weighted by confidence and warrant tier.
    """
    out: dict[str, list[float]] = {}
    for sid in slots:
        rec = snapshot.slots.get(sid)
        if rec is None or rec.value not in BVALUE_INDEX:
            continue
        try:
            weight = Warrant(WarrantTier[rec.tier]).weight
        except (KeyError, ValueError):
            weight = Warrant(WarrantTier.EXTRACTION).weight
        vec = out.setdefault(sid, [0.0] * NBV)
        vec[BVALUE_INDEX[rec.value]] -= float(rec.confidence) * weight
    return out


def _blocks_touching(snapshot: CorpusSnapshot, seeds: set[str]) -> list[Block]:
    """The corpus blocks any biased address falls in, rebuilt with their declared edges.

    Block MEMBERSHIP is read off the snapshot, which computed it at build time from the same
    connected-components pass; the edges are rebuilt here from the arrows so that `settle`
    receives real coupling rather than a bare member list.
    """
    seen: set[tuple[str, ...]] = set()
    out: list[Block] = []
    for sid in sorted(seeds):
        members = snapshot.blocks.get(sid)
        if not members:
            members = (sid,)
        if members in seen:
            continue
        seen.add(members)
        slots = [Slot(id=m, chart=r.chart, type=r.type, nu=r.nu)
                 for m in members if (r := snapshot.slots.get(m)) is not None]
        if not slots:
            continue
        edges = tuple(structural_edges(slots, snapshot.arrows))
        out.append(Block(id=members[0][:16], slots=tuple(s.id for s in slots), edges=edges))
    return out


def _paths_from(block: Block, seeds: set[str], snapshot: CorpusSnapshot
                ) -> dict[str, tuple[int, tuple[Hop, ...]]]:
    """Shortest declared-arrow path from any biased slot to every slot it can reach.

    Breadth-first over the block's edges. Those edges are exactly the declared arrows, so a
    path here IS a chain of correspondences somebody proposed — which is what makes it
    showable as provenance rather than as an assertion that two things are related. Each step
    carries the ARROW's own kind and warrant tier, because how far a perturbation reached and
    what it reached on are different facts and only one of them is the hop count.
    """
    by_pair: dict[tuple[str, str], object] = {}
    for a in snapshot.arrows:
        by_pair.setdefault((a.src_slot, a.dst_slot), a)
        by_pair.setdefault((a.dst_slot, a.src_slot), a)

    adj: dict[str, list[str]] = {}
    for e in block.edges:
        adj.setdefault(e.u, []).append(e.v)
        adj.setdefault(e.v, []).append(e.u)

    out: dict[str, tuple[int, tuple[Hop, ...]]] = {}
    queue: deque[tuple[str, int, tuple[Hop, ...]]] = deque()
    for sid in sorted(seeds & set(block.slots)):
        out[sid] = (0, ())
        queue.append((sid, 0, ()))
    while queue:
        cur, hops, path = queue.popleft()
        for nxt in sorted(adj.get(cur, ())):
            if nxt in out:
                continue
            arrow = by_pair.get((cur, nxt))
            rec = snapshot.slots.get(nxt)
            step = Hop(
                kind=getattr(arrow, "kind", "?"),
                tier=getattr(getattr(arrow, "tier", None), "name", "EXTRACTION"),
                provisional=bool(getattr(arrow, "provisional", True)),
                to_slot=nxt, to_chart=rec.chart if rec else "?",
                to_nu=_display(rec.nu) if rec else nxt[:16])
            out[nxt] = (hops + 1, path + (step,))
            queue.append((nxt, hops + 1, path + (step,)))
    return out


def _display(nu: str) -> str:
    """Strip the chart tag for READING. Addressing keeps it; this never feeds an address."""
    if nu.startswith("\x01"):
        end = nu.find("\x01", 1)
        if end != -1:
            return nu[end + 1:]
    return nu


def relax(text: str, snapshot: CorpusSnapshot, chart: str = "english",
          seeds_from: set[str] | None = None,
          extra_arrows: list | None = None) -> Relaxation:
    """Apply the typed text as a soft constraint and report what the field did.

    Settlement runs twice per affected block — corpus alone, then corpus plus bias — and the
    difference is the response. Nothing branches on whether the bias's address was already
    present: that determines whether the graph couples it, which is a structural fact the
    result reports, not a gate on whether the field is consulted at all.
    """
    out = Relaxation()
    deltas = bias_deltas(text, chart)
    out.bias_slots = tuple(d.slot for d in deltas)
    if snapshot.empty:
        out.silence = ("the corpus is empty — there is no field to perturb. This is a "
                       "passthrough and is reported as one.")
        return out
    if not deltas:
        out.silence = "the typed text produced no addressable claim, so there is no bias."
        return out

    # Where the bias attaches. By default its own address — which is only ever right when
    # the typed text already exists verbatim. `seeds_from` carries the ATTACHMENT the
    # proposer accepted, which is how a bias reaches a corpus that does not contain it
    # word for word. Either way the seeds are addresses, and everything after this point
    # travels declared arrows only.
    seeds = set(seeds_from) if seeds_from else {d.slot for d in deltas}
    out.bias_in_field = tuple(sorted(seeds & set(snapshot.slots)))
    if extra_arrows:
        # The attachment arrows themselves, laid over the read view so the perturbation can
        # travel them. They are EXTRACTION tier and are not written anywhere.
        snapshot = with_arrows(snapshot, list(snapshot.arrows) + list(extra_arrows))

    # WHERE THE PUSH IS APPLIED. Keyed by the typed claim's own address, the bias only ever
    # lands when the typed text already exists verbatim — the slot is otherwise absent from
    # every block and the perturbation is silently applied to nothing. When the proposer has
    # ATTACHED the input to corpus claims, the push belongs on those claims: that is what the
    # correspondence asserts, and it is the whole point of proposing one.
    raw_bias = evidence_from_deltas(deltas)
    summed = [0.0] * NBV
    for vec in raw_bias.values():
        for i, x in enumerate(vec):
            summed[i] += x
    if seeds_from:
        bias = {sid: [c * BIAS_WEIGHT for c in summed] for sid in seeds}
    else:
        bias = {s: [c * BIAS_WEIGHT for c in vec] for s, vec in raw_bias.items()}

    for block in _blocks_touching(snapshot, seeds):
        if len(block.slots) > BLOCK_CAP:
            out.blocks_skipped += 1
            continue
        base_ev = _corpus_evidence(snapshot, block.slots)
        priors = lexicon_prior(block.slots)
        biased_ev = {s: list(v) for s, v in base_ev.items()}
        for sid, vec in bias.items():
            if sid in block.slots:
                target = biased_ev.setdefault(sid, [0.0] * NBV)
                for i, x in enumerate(vec):
                    target[i] += x

        before = settle(block, base_ev, priors, READ_BETA)
        after = settle(block, biased_ev, priors, READ_BETA)
        out.blocks_settled += 1
        out.slots_considered += len(block.slots)

        paths = _paths_from(block, seeds, snapshot)
        for sid in block.slots:
            p0, p1 = before.p.get(sid), after.p.get(sid)
            if p0 is None or p1 is None:
                continue
            shift = sum(abs(a - b) for a, b in zip(p0, p1))
            if shift <= MOVED_EPS:
                continue
            reach = paths.get(sid)
            if reach is None:
                # Moved but unreachable over declared edges. It cannot be compiled, because
                # the compiled input must show HOW the bias got there and there is no path
                # to show. Counted below as considered, never emitted as a fact.
                continue
            rec = snapshot.slots.get(sid)
            if rec is None:
                continue
            out.moved.append(Moved(
                slot=sid, chart=rec.chart, type=rec.type, nu=rec.nu, value=rec.value,
                tier=rec.tier, contested=sid in snapshot.contested, shift=shift,
                before=tuple(p0), after=tuple(p1), path=reach[1], hops=reach[0]))

    out.moved.sort(key=lambda m: (-m.shift, m.hops, m.slot))
    if len(out.moved) > MOVED_CAP:
        out.moved_dropped = len(out.moved) - MOVED_CAP
        out.moved = out.moved[:MOVED_CAP]

    if not out.moved:
        out.silence = _why_silent(out, snapshot)
    return out


def _why_silent(out: Relaxation, snapshot: CorpusSnapshot) -> str:
    """Name the structural reason nothing moved. "No result" is not an explanation."""
    if not out.bias_in_field:
        return (f"nothing in the field responded. The typed text addressed "
                f"{len(out.bias_slots)} claim(s), none of which this corpus carries, so the "
                f"bias joined the coupling graph with no declared arrow touching it and had "
                f"nothing to propagate through. That is a fact about the corpus, not a "
                f"failed search: no words were compared.")
    if out.blocks_settled == 0:
        return (f"nothing in the field responded: {len(out.bias_in_field)} biased address(es) "
                f"are in the corpus but every block containing them exceeded the "
                f"{BLOCK_CAP}-slot settling cap ({out.blocks_skipped} skipped).")
    return (f"the field was perturbed and did not move. {len(out.bias_in_field)} biased "
            f"address(es) sit in {out.blocks_settled} settled block(s) covering "
            f"{out.slots_considered} slot(s), and no slot's settled distribution shifted by "
            f"more than {MOVED_EPS:g} — the corpus's own evidence outweighs a bias of "
            f"{BIAS_WEIGHT}, which is what a soft constraint is supposed to do.")
