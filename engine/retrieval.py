"""RETRIEVAL: which existing claims to put in front of the model. Not addressing, not a claim.

`engine/inbound.py` is emphatic that landing is EXACT — a span lands on a slot iff
`hash(nu(surface), type)` matches one already in the corpus, with no nearest-neighbour search
and no threshold. That is right, and nothing here weakens it. But the read path conflated two
different things under that one rule, and the cost was a window that answered every real
question with "NO FIELD TO CONDITION ON".

The distinction this module draws:

**Addressing is identity.** Two claims are the same claim or they are not, and the answer is a
hash. A similarity score can never make two addresses one; that is the fiber relation this
build deleted on purpose, and it stays deleted.

**Retrieval is navigation.** Which of the corpus's already-addressed claims should be shown?
That question asserts nothing. It creates no address, declares no correspondence, enters no
delta, and cannot promote. Every claim it surfaces still carries its OWN exact address, its
own warrant tier and its own contest status — retrieval only decides the order they are read
in. Grepping a library is not a claim about the books.

So the compiled field gains a second, separately-labelled section, and the labelling is the
whole safety property:

    LANDED    — this span IS this claim. Exact, gate 1.
    RETRIEVED — this claim shares terms with what you typed. It is NOT what you typed, and
                nothing here asserts it corresponds to it.

`tests/test_retrieval.py` plants against the failure that matters: a retrieved slot reported
as a landing, or `conditioned=True` where nothing landed exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .corpus_state import CorpusSnapshot

#: Words that carry no discriminating signal. Deliberately small and English-only: a large
#: hand-tuned list is a model of language pretending to be a constant, and every word removed
#: here is a word the operator can no longer search for.
STOPWORDS = frozenset("""
a an the and or but if then else of in on at to for with by from as is are was were be been
being this that these those it its i me my we our you your they them their he she his her
what which who whom whose how why when where do does did done have has had can could will
would shall should may might must not no nor so than too very just about into over under
""".split())

#: A term must be at least this long to count. One- and two-character tokens match everywhere.
MIN_TERM = 3

#: How many claims retrieval may surface. The compiled field is read by a model with a finite
#: window, and a hundred loosely-related claims condition worse than a dozen close ones.
DEFAULT_LIMIT = 14

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def terms(text: str) -> list[str]:
    """The query's discriminating words, lowercased, in order, deduplicated.

    Identifiers are split on underscores AND on camelCase humps as well as kept whole, so a
    question about "order book" reaches `OrderBook` and `order_book` without either side
    having to guess the other's spelling.
    """
    out: list[str] = []
    seen: set[str] = set()
    for raw in _WORD.findall(text):
        pieces = [raw]
        pieces.extend(raw.split("_"))
        pieces.extend(re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", raw))
        for piece in pieces:
            low = piece.lower()
            if len(low) < MIN_TERM or low in STOPWORDS or low in seen:
                continue
            seen.add(low)
            out.append(low)
    return out


@dataclass(frozen=True, slots=True)
class Retrieved:
    """One existing claim, selected for reading. It is NOT a landing and never becomes one."""

    slot: str
    chart: str
    type: str
    nu: str
    value: str
    tier: str
    contested: bool
    matched: tuple[str, ...]                   # which query terms this claim actually contains
    score: float

    def as_record(self) -> dict[str, object]:
        from .inbound import display

        return {"slot": self.slot[:16], "chart": self.chart, "value": self.value,
                "tier": self.tier, "contested": self.contested,
                "matched": list(self.matched), "score": round(self.score, 3),
                "nu_display": display(self.nu)[:300],
                "relation_to_query": "TERM OVERLAP ONLY — not an address match, not a "
                                     "declared correspondence"}


def retrieve(text: str, snapshot: CorpusSnapshot, chart: str = "",
             limit: int = DEFAULT_LIMIT, exclude: frozenset[str] = frozenset()) -> list[Retrieved]:
    """Claims whose surface shares discriminating terms with the query.

    Scoring is deliberately legible rather than clever: the fraction of query terms present,
    with a mild preference for shorter surfaces so a whole README does not outrank the one
    sentence that says the thing. There is no embedding, no learned weight and no threshold
    that would need tuning — every retrieved claim can be explained by naming the words it
    shares, and `matched` carries exactly that so the page can show it.

    `chart` biases rather than filters: a question typed in the english chart should still be
    able to see the Go function it is about, since crossing charts is the point of the engine.
    """
    query = terms(text)
    if not query or snapshot.empty:
        return []
    wanted = set(query)
    scored: list[Retrieved] = []
    for sid, rec in snapshot.slots.items():
        if sid in exclude:
            continue
        surface = rec.nu.lower()
        matched = tuple(t for t in query if t in surface)
        if not matched:
            continue
        coverage = len(matched) / len(wanted)
        if coverage < 2 / len(wanted) and len(wanted) > 2:
            continue                    # a single common word is not a reason to surface a claim
        # Shorter surfaces say the thing; longer ones merely contain it.
        brevity = 1.0 / (1.0 + len(rec.nu) / 400.0)
        bias = 1.08 if (chart and rec.chart == chart) else 1.0
        scored.append(Retrieved(
            slot=sid, chart=rec.chart, type=rec.type, nu=rec.nu, value=rec.value,
            tier=rec.tier, contested=sid in snapshot.contested, matched=matched,
            score=coverage * brevity * bias))
    scored.sort(key=lambda r: (-r.score, -len(r.matched), r.slot))
    return _spread(_dedupe(scored), limit)


def _dedupe(scored: list[Retrieved]) -> list[Retrieved]:
    """One row per surface.

    Distinct addresses can carry the same nu at different types — `def f(...)` as both a
    `define` and an `assert`, say — and the corpus holds the same sentence from more than one
    document. They are genuinely different claims, so this does NOT merge them in the corpus;
    it only declines to spend two of fourteen reading slots showing the same words twice.
    """
    out, seen = [], set()
    for r in scored:
        if r.nu in seen:
            continue
        seen.add(r.nu)
        out.append(r)
    return out


def _spread(scored: list[Retrieved], limit: int) -> list[Retrieved]:
    """Take the best, but not all from one chart.

    Straight top-N returned fourteen English sentences for a corpus that holds six charts,
    which is the opposite of what an atlas is for. One pass round-robins across charts, then
    the remainder fills by score.
    """
    if len(scored) <= limit:
        return scored
    by_chart: dict[str, list[Retrieved]] = {}
    for r in scored:
        by_chart.setdefault(r.chart, []).append(r)
    out: list[Retrieved] = []
    while len(out) < limit:
        added = False
        for chart in sorted(by_chart):
            queue = by_chart[chart]
            if queue:
                out.append(queue.pop(0))
                added = True
                if len(out) >= limit:
                    break
        if not added:
            break
    return out
