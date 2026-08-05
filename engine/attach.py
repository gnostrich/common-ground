"""How a BIAS reaches the field. It is proposed and gated, exactly like every other arrow.

The defect this fixes was inherited, not designed. Gate 1 says two CLAIMS are the same claim
iff `hash(nu(surface), type)` agrees, and that is right. A bias is not a claim, and how a bias
attaches to the field was never specified — so the implementation reused the addressing rule
because it was the rule that was there. The consequence: typed text that did not already exist
verbatim in the corpus attached to nothing, propagated nowhere, and the window reported that a
69,000-slot corpus had not responded. Correct under the rule it inherited, and the wrong rule.

Attachment is a CORRESPONDENCE. The typed claim and a corpus claim either correspond or they
do not, and that question already has a mechanism: the same proposer, the same prompt, the
same three kinds, with `none` legal and expected. So:

    typed text -> addressed like any claim (gate 1, unchanged)
               -> the proposer is asked which corpus claims it corresponds to
               -> accepted proposals are Correspondences at EXTRACTION tier
               -> those attachment points are handed to `engine/relax` as seeds
               -> everything downstream travels declared arrows only

No string is ever compared. The proposer reads two claims and judges; superficial word overlap
is explicitly `none` in its instructions, and a bias that attaches to nothing is a field that
genuinely did not respond rather than a search that missed.

**Which candidates it is shown, and why that is not selection by another name.** The corpus is
too large to ask about exhaustively, so candidates are ordered — and the ordering is by
DECLARED DEGREE, the number of correspondences already touching a slot. That is a property of
the arrow graph, not of any text: it compares nothing, it reads no surface, and it prefers the
claims a perturbation could actually travel from, since a slot no arrow touches can only ever
report that nothing moved. What the budget does not reach is COUNTED and reported as
unmeasured, never as absent.

**Attachment is cross-chart, and that is constitutional rather than incidental.** A
correspondence between two claims in one chart is refused by `engine/correspondence`, because
exact addressing already owns intra-chart identity and an intra-chart arrow would reintroduce
similarity by the back door. So a claim typed in the english chart attaches to lean, python,
go, tabular or conversation claims, and reaches english claims through them. That is the
engine working as specified, not a limitation of this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .correspondence import Correspondence
from .corpus_state import CorpusSnapshot
from .extract import DeterministicExtractor
from .holes import Hole
from .propose_correspondence import PROPOSE_SYSTEM, parse_answers, render_candidates
from .types import Document, WarrantTier

#: Candidate pairs per call. The daemon's batch; kept the same so the prompt the attachment
#: proposer sees is the prompt the corpus proposer sees, down to the shape of the body.
BATCH = 12

#: Calls one attachment may spend. A question is interactive, so this is a latency and cost
#: budget, and what it does not reach is reported as unmeasured rather than treated as none.
CALL_BUDGET = 4

#: Attachment enters at EXTRACTION, like every LM proposal. It cannot ground and cannot clamp.
ATTACH_TIER = WarrantTier.EXTRACTION


@dataclass(frozen=True, slots=True)
class Attachment:
    """One proposed bridge from the typed input into the corpus, accepted or not."""

    kind: str                                 # same_claim | refines | instance_of | none
    dst_slot: str
    dst_chart: str
    dst_nu: str
    evidence: str
    tier: str = ATTACH_TIER.name

    @property
    def accepted(self) -> bool:
        return self.kind != "none"

    def as_record(self) -> dict[str, object]:
        return {"kind": self.kind, "accepted": self.accepted, "tier": self.tier,
                "to": self.dst_slot[:16], "chart": self.dst_chart,
                "nu": self.dst_nu[:220], "evidence": self.evidence[:400]}


@dataclass(slots=True)
class AttachResult:
    """What the proposer said about the typed input, in full. The bridge, not just the result."""

    typed_slot: str = ""
    typed_chart: str = ""
    typed_nu: str = ""
    proposed: list[Attachment] = field(default_factory=list)
    considered: int = 0                       # candidate pairs actually asked about
    available: int = 0                        # candidates the corpus offered
    calls: int = 0
    budget_exhausted: bool = False
    error: str = ""

    @property
    def accepted(self) -> list[Attachment]:
        return [a for a in self.proposed if a.accepted]

    @property
    def seeds(self) -> set[str]:
        """Where the bias actually attached. `engine/relax` takes these as its starting set.

        This module proposes attachment and does nothing else. Gate 10 caught an earlier
        wording here that described this file as performing the settling, which it does not;
        the check was right, and the phrasing changed rather than the check.

        Note for anyone tempted to quote the offending sentence back into a docstring: the
        check cannot distinguish a phrase asserted from a phrase quoted, and it should not
        try. Naming the defect without reproducing its words is the cheaper discipline.
        """
        return {a.dst_slot for a in self.accepted}

    def arrows(self, typed_slot: str) -> list[Correspondence]:
        """Accepted attachments as real Correspondence objects, at extraction tier."""
        from . import EngineError

        out = []
        for a in self.accepted:
            try:
                out.append(Correspondence(
                    src_chart=self.typed_chart, src_slot=typed_slot,
                    dst_chart=a.dst_chart, dst_slot=a.dst_slot, kind=a.kind,
                    tier=ATTACH_TIER, proposer="lm", prompt_hash="attach",
                    evidence=(a.evidence,)))
            except EngineError:
                continue          # refused (intra-chart, self-pair) — skipped, never coerced
        return out

    def as_record(self) -> dict[str, object]:
        return {"typed_slot": self.typed_slot[:16], "typed_chart": self.typed_chart,
                "proposed": [a.as_record() for a in self.proposed],
                "accepted": len(self.accepted), "considered": self.considered,
                "available": self.available, "calls": self.calls,
                "budget_exhausted": self.budget_exhausted, "error": self.error,
                "note": ("Attachment is a PROPOSED correspondence at extraction tier, judged "
                         "by the same proposer and the same prompt the corpus arrows use. "
                         "`none` is legal and expected; nothing here is promoted.")}


def _degree(snapshot: CorpusSnapshot) -> dict[str, int]:
    """Declared arrows touching each slot. Structure, not text — nothing is compared."""
    out: dict[str, int] = {}
    for a in snapshot.arrows:
        out[a.src_slot] = out.get(a.src_slot, 0) + 1
        out[a.dst_slot] = out.get(a.dst_slot, 0) + 1
    return out


def candidates(snapshot: CorpusSnapshot, typed_chart: str, typed_type: str,
               limit: int) -> list[tuple[str, object]]:
    """Corpus claims to ask about, most-connected first.

    Two filters, both structural. Type compatibility, because a correspondence relates claims
    of the same form. And a different chart, because a correspondence IS cross-chart — asking
    about an intra-chart pair would produce a proposal the engine then refuses to build.
    """
    degree = _degree(snapshot)
    rows = [(sid, rec) for sid, rec in snapshot.slots.items()
            if rec.chart != typed_chart and rec.type == typed_type]
    rows.sort(key=lambda kv: (-degree.get(kv[0], 0), kv[0]))
    return rows[:limit]


def attach(text: str, snapshot: CorpusSnapshot, transport, chart: str = "english",
           call_budget: int = CALL_BUDGET) -> AttachResult:
    """Ask the proposer where this input attaches. Its answer, in full, is the return value.

    `transport(system, user) -> (raw, usage)` is the same callable the daemon uses, so an
    attachment call is indistinguishable from a corpus call at the wire.
    """
    out = AttachResult()
    deltas = list(DeterministicExtractor("inbound", "typed").extract(
        Document("inbound", chart, text, "typed")))
    if not deltas or snapshot.empty:
        out.error = ("the typed text produced no addressable claim" if not deltas
                     else "the corpus is empty")
        return out

    d = deltas[0]
    out.typed_slot, out.typed_chart, out.typed_nu = d.slot, chart, d.nu

    pool = candidates(snapshot, chart, d.type, limit=BATCH * call_budget)
    out.available = sum(1 for _, rec in snapshot.slots.items()
                        if rec.chart != chart and rec.type == d.type)
    if not pool:
        out.error = (f"no corpus claim is both type-compatible ({d.type}) and in a different "
                     f"chart, so there is no legal correspondence to propose")
        return out

    for start in range(0, len(pool), BATCH):
        if out.calls >= call_budget:
            out.budget_exhausted = True
            break
        chunk = pool[start:start + BATCH]
        holes = [Hole(src_chart=chart, src_slot=d.slot, src_nu=d.nu,
                      dst_chart=rec.chart, dst_slot=sid, dst_nu=rec.nu,
                      type=d.type, restatement=0)
                 for sid, rec in chunk]
        try:
            raw, _usage = transport(PROPOSE_SYSTEM, render_candidates(holes))
        except Exception as exc:                     # a dead call is reported, never silent
            out.error = f"{type(exc).__name__}: {exc}"
            break
        out.calls += 1
        out.considered += len(holes)
        for outcome in parse_answers(raw, holes):
            out.proposed.append(Attachment(
                kind=outcome.kind, dst_slot=outcome.hole.dst_slot,
                dst_chart=outcome.hole.dst_chart, dst_nu=outcome.hole.dst_nu,
                evidence=outcome.evidence))

    # Compared against `available`, NOT against `len(pool)`. The pool is ALREADY truncated to
    # the budget, so comparing with it asks "did we ask about everything we decided to ask
    # about" — which is always yes, and would have reported a budget-limited search as a
    # complete one. The question is whether every type-compatible candidate was reached.
    if out.considered < out.available and not out.error:
        out.budget_exhausted = True
    return out
