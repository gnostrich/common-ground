"""KIND RE-ADJUDICATION: containment declared as identity, demoted to what it honestly is.

WHAT WAS MEASURED. 2,082 distinct `same_claim` pairs in the corpus. 2,013 of them — 96.7% —
join a code-chart definition to a sentence extracted from a docstring, and the provenance says
so: the prose slot's locator carries a `#doc:<Symbol>` fragment naming the symbol whose
docstring it came from. A definition and one sentence about it are not the same proposition.
The whole is not the same claim as each of its parts.

Individually, most of those declarations are defensible readings — a docstring sentence does
describe its function. What is not defensible is the KIND. `same_claim` is the only kind that
is `loop_eligible`, so it is the only kind that builds fibers, and a fiber is the transitive
closure of its declared pairs. Closure over a containment relation manufactures equivalences
nobody declared: if sentence S1 is "the same claim as" function F, and F is "the same claim
as" sentence S2, then S1 and S2 are one proposition — two different sentences of one
docstring, merged by a closure the composition table licenses and the data does not support.
Measured on the 120-member fiber: 6.1% declared coverage. 93.9% of what it asserted came from
closure alone.

`refines` is what containment honestly is, and it is not loop_eligible, so it does not close.

NOTHING IS DELETED. This is the quarantine pattern, fifth application. A demoted arrow keeps
its endpoints, its evidence, its proposer and its tier; it changes kind and carries the era
that demoted it. A genuine whole-restatement — a single-sentence docstring, a Lean-convention
docstring that restates the theorem — can RE-EARN `same_claim` by being confirmed through
region relaxation, arriving as a fresh declaration with a current-era tag. Demotion closes no
door; it stops one kind of reading from being asserted on the strength of another.

THE TEST IS STRUCTURAL AND READS NO CLAIM TEXT. It asks three questions of the provenance the
extractor already recorded: is one endpoint a code chart, does the other endpoint's locator
carry a docstring fragment, and do they name the same source document. No token is compared,
no similarity is computed, and `engine/referee_sweep` sweeps this module like any other.

THE PIGEONHOLE. If k > 1 sentences of ONE docstring each hold `same_claim` to ONE definition,
the declarations are over-determined on their face: at most one sentence can BE the
definition's proposition, so at least k-1 of them are containment however the rest is read.
That is a structural over-declaration, independent of what any sentence says, and it is RED if
it survives demotion.
"""

from __future__ import annotations

from dataclasses import dataclass

from .nonempty import census

#: `survivors()` LIVED HERE and was deleted. It walked the arrows, adjudicated each pair and
#: split them into kept and demoted — which is what `corpus_state._demote_containment` does,
#: with the live callers. Two implementations of one adjudication, one of them with no caller
#: and no control, free to drift from the other silently: the forbidden shape (Q5), and the
#: exact mechanism by which prose stops describing the code. One settlement, not two.

#: Charts whose slots are definitions rather than prose about definitions.
CODE_CHARTS = frozenset({"python", "go", "lean"})

#: The provenance fragment the extractor writes when a prose claim came from a docstring.
#: Declared by the extractor, not inferred here.
DOC_FRAGMENT = "#doc:"

#: What a demoted arrow becomes. `refines` is containment: the sentence sharpens the
#: definition's contract. It is NOT loop_eligible, so it does not close, which is the whole
#: point — closure over containment is what fabricated the fibers.
DEMOTED_KIND = "refines"

#: The era tag a demoted arrow carries, so a reader downstream can tell a demoted declaration
#: from one the proposer made as `refines` in the first place.
DOCSTRING_ERA = "docstring-demotion"

#: Statuses. A demoted arrow is a LEAD for its new kind — it was never declared `refines` by
#: anybody, it was re-read as one — and can be confirmed by ordinary region relaxation.
LEAD = "lead"


def doc_fragment(slot_rec) -> str:
    """The `file#doc:Symbol` locator, if this slot came from a docstring. Declared, not guessed."""
    for d in (getattr(slot_rec, "docs", None) or ()):
        text = str(d)
        if DOC_FRAGMENT in text:
            return text
    return ""


def source_file(slot_rec) -> str:
    docs = list(getattr(slot_rec, "docs", None) or ())
    return str(docs[0]).split("#")[0] if docs else ""


@dataclass(frozen=True, slots=True)
class Verdict:
    """One pair, adjudicated. Both branches carry a reason; neither is a bare boolean."""

    demote: bool
    reason: str
    cls: str = ""            # "same-file" | "cross-document" | ""
    symbol: str = ""         # the docstring locator, when there is one
    #: OI-24 AT THE FINEST GRAIN. `demote=False` used to mean two different things: this pair
    #: was read and is not containment, and this pair could not be read at all. The second is
    #: not a keep — it is an absence — and counting it as a keep is success on the empty set
    #: one pair at a time. A pair with an endpoint outside the snapshot is UNADJUDICATED.
    adjudicated: bool = True

    def as_record(self) -> dict[str, object]:
        return {"demote": self.demote, "reason": self.reason, "class": self.cls,
                "symbol": self.symbol, "adjudicated": self.adjudicated}


def adjudicate(src_rec, dst_rec) -> Verdict:
    """Is this `same_claim` a containment wearing an identity's kind?"""
    if src_rec is None or dst_rec is None:
        return Verdict(False, "an endpoint is not in this snapshot; nothing to read",
                       adjudicated=False)
    a, b = src_rec, dst_rec
    if b.chart in CODE_CHARTS and a.chart not in CODE_CHARTS:
        prose, code = a, b
    elif a.chart in CODE_CHARTS and b.chart not in CODE_CHARTS:
        prose, code = b, a
    else:
        return Verdict(False, "not a code-to-prose pair — outside the adjudicated class")
    frag = doc_fragment(prose)
    if not frag:
        return Verdict(False, "the prose endpoint did not come from a docstring: its "
                              "provenance carries no #doc: fragment")
    if source_file(prose) == source_file(code):
        return Verdict(True, "a definition and a sentence of its OWN docstring. The whole is "
                             "not the same claim as each of its parts; this is containment, "
                             "and containment is `refines`.",
                       cls="same-file", symbol=frag)
    return Verdict(True, "a docstring sentence from one source bridged to a definition in "
                         "ANOTHER. Nobody declared these are the same proposition about the "
                         "same thing, and the closure it feeds is weaker still.",
                   cls="cross-document", symbol=frag)


def pigeonhole(pairs, slots) -> dict:
    """Docstrings with k>1 sentences each claiming identity with ONE definition.

    At most one sentence of a docstring can BE the definition's proposition. k of them cannot,
    whatever any of them says — so k-1 are containment on the face of the declarations, with
    no reading of the text required. RED if any survives demotion.
    """
    counts: dict[tuple, int] = {}
    unadjudicated = 0
    for u, v in pairs:
        ru, rv = slots.get(u), slots.get(v)
        verdict = adjudicate(ru, rv)
        if not verdict.adjudicated:
            unadjudicated += 1
            continue
        if not verdict.demote or verdict.cls != "same-file":
            continue
        code = u if (rv is not None and rv.chart not in CODE_CHARTS) else v
        counts[(verdict.symbol, code)] = counts.get((verdict.symbol, code), 0) + 1
    over = {k: n for k, n in counts.items() if n > 1}
    return census("pigeonhole", pairs, {
        "docstrings": len(counts), "over_declared": len(over),
        "worst": max(counts.values()) if counts else 0,
        "excess_pairs": sum(n - 1 for n in over.values()),
        "unadjudicated_pairs": unadjudicated}, unit="same_claim pair")
