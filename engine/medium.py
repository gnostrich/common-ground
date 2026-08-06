"""THE MEDIUM CHART: the last silent translation, made declared and gated.

Every prompt this system sends performs a translation nobody extracted. The operator writes
"floor", "current", "settling", "grain", "gate"; the medium reads those words through its own
priors, and some fraction of every interaction defect — indiscriminate attachment, ignored
intra-chart constraints, an answer saying nothing moved over twenty-four movers — is the
medium parsing operator terms in the wrong sense. Until it is extracted, LM interaction is a
lookup into an unaligned dictionary.

CATEGORICALLY, before any code:
  MOVE 1, a new base. `medium` is a chart — the LM's conceptual vocabulary as a modality,
          registered in seed/CHARTS.json like every other, behavior `prose` because a gloss is
          prose. Reusing the behavior rather than minting a fourth normalizer is the seam
          working as designed.
  MOVE 3, its morphisms. A GLOSS IS A SPAN, not an arrow: the operator's term is the APEX and
          several TYPED LEGS run from it into distinct medium-chart concepts. Same three
          kinds, same inlet, EXTRACTION tier, source-tagged, born aging. No new mechanism.

A GLOSS IS NOT ONE SENTENCE, AND THE FIRST VERSION OF THIS MODULE SAID IT WAS. It emitted one
`same_claim` arrow per term — the term MEANS this sentence — and that shape is wrong twice
over. An operator's term is CONDENSED; the medium's coverage of the same ground is
DISTRIBUTED across several of its own concepts. A single sentence forces that decompression
into paraphrase, where it is unstructured and uncheckable, instead of leaving it as morphism
structure where it is neither. And `same_claim` is the one kind a leg may never be: asserting
the term IS the concept is exactly the flattening being corrected.

THEN THE WHOLE THING COLLAPSED INTO A PRESENTATION FIX, which is where it should have started.
The decompression is not something a model produces AND it is not something this module needs
to store: it is the corpus's own fiber structure, which was in the snapshot the entire time
and was being FLATTENED AWAY on the way into the prompt. `_relaxed_block` rendered a numbered
list of claims, so a medium shown a pile attached to the pile — 59 of 59 on the measured run —
because a list offers nothing more precise to attach to than "one of these". Grouping the
compiled sheet by fiber, with each group headed by the shared proposition and followed by the
declared arrows leaving it, IS the span. Live structure, formatted honestly, no glossary
stored and no call made.

SO THIS MODULE IS THE IRREDUCIBLE RESIDUE. One optional cached line per fiber: the terminal
arrow — "name the one concept in your vocabulary this is" — a LABEL and nothing else. The
medium never generates content and never supplies structure; it names an endpoint the corpus
already built. Confabulation risk is one word sitting beside the verbatim claims it names,
where a wrong one is visible rather than woven in, and the behavioural control already covers
it. Everything else that lived here — spans as storage, a glossary block as a table, legs
generated per term — is gone, because the grouping does it.

THE SPAN PREDICTS THE FLAT VERSION'S OWN TABLE, which is the argument for it. Measured on four
fixtures, one flat gloss per term improved discrimination sharply on the structural question
(0.797 -> 0.186) and degraded it to the limit case on the vague input (0.949 -> 1.000). A span
explains both without an extra assumption: where the medium had no binding at all, any binding
helps; where it already had too many things to attach to, one more undifferentiated blob of
prose is one more attachable object. Typed legs give the binding somewhere specific to land
instead of one more surface to land on.
  This is the CONTENTS of T_{operator -> LM}. The export sheet was that morphism's first
  instance — the claims carried across. This is the translation table itself.

TERM SELECTION IS STRUCTURAL, AND A TERM IS A FIBER. There is no word counting here and no
frequency heuristic, because there is no tokenizer in this file at all — `engine/referee_sweep`
would refuse one and would be right. A `same_claim` fiber IS an operator term: a set of claims
across several charts that the corpus has already declared to express ONE proposition. The
load-bearing vocabulary is precisely the vocabulary that already carries arrows, and the fiber
is that fact in structural form. Its members, verbatim, are the term's defining claims.

THE GATE IS BEHAVIOURAL, NOT JUDGED. A gloss's warrant is its measured effect on the medium's
own behaviour, never the medium's opinion of its own gloss. A fixed set of past-failing
perturbations runs twice — with the glossary and without — and a gloss survives only if
attachment discrimination improves or citation compliance rises WITH NO METRIC WORSENING.
Anything else decays by the ordinary aging events. The medium's self-description is a
proposal; what that description does to the medium is the warrant.

THE FIREWALL IS CONSTITUTIONAL. Medium-chart claims are about the INTERFACE, never about
truth. A gloss never enters content settlement, never contests an operator claim, and never
reaches K's candidate set. It is conditioning-relevant and corpus-inert — the same containment
shape `bears_on` has, and for the same reason: something real and useful that is structurally
unable to become a belief. `tests/test_medium.py` plants a gloss in both forbidden places.

PER-MEDIUM, which is the quarantine pattern's fourth application. A gloss is tagged with the
model that produced it. Validated on one medium it is a FACT for that medium and a LEAD for
any other, exactly as a lite-era arrow is a lead for the pinned era and a keyword-era verdict
is a lead for the adjacency era.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MEDIUM_CHART = "medium"

#: THE LEGAL LEG KINDS, enumerated. Each carries a different facet of the compression:
#:   refines      the term is a sharper case of this concept — the concept is the genus.
#:   instance_of  the term names a particular occurrence of this concept.
#:   bears_on     the term is ABOUT this concept without asserting a relation to it.
#: `same_claim` is deliberately ABSENT. A `same_claim` leg says the term IS the concept, which
#: collapses the span back to the flat gloss this replaced. A response naming it is VOID, and
#: `tests/test_medium.py` plants exactly that.
LEG_KINDS = ("refines", "instance_of", "bears_on")



#: Terms taken per extraction round. Stated rather than tuned: the first validation table is
#: reported before scaling, so this is the size of that first table, not a permanent cap.
TOP_TERMS = 20

#: A fiber smaller than this is a pair, and a pair is a single arrow — not a term.
MIN_FIBER = 3

#: Statuses a gloss can hold. `proposed` has been extracted and not yet validated; `validated`
#: improved a metric with none worsening; `failed` did not and decays; `lead` was validated on
#: a different medium than the one now serving.
PROPOSED, VALIDATED, FAILED, LEAD = "proposed", "validated", "failed", "lead"

#: What the validation run measures. Both are EXISTING metrics with their invariance already
#: asserted elsewhere — attachment discrimination is deduped by target slot, citation
#: compliance counts sentences not words. No new metric ships here, per the standing rule.
METRICS = {
    "discrimination": "attachment fraction of the region — LOWER is more selective",
    "citation": "share of sentences carrying a resolvable citation — HIGHER is better",
}


@dataclass(frozen=True, slots=True)
class Term:
    """An operator term, in the only structural form one has: the fiber that carries it."""

    fiber_id: str
    charts: tuple[str, ...]
    members: tuple[str, ...]          # slot addresses
    claims: tuple[str, ...]           # the defining claims, VERBATIM

    @property
    def size(self) -> int:
        return len(self.members)

    def as_record(self) -> dict[str, object]:
        return {"fiber_id": self.fiber_id, "charts": list(self.charts),
                "size": self.size, "claims": list(self.claims)}


@dataclass
class Gloss:
    """One cached line: the medium's name for one fiber. The residue, and nothing more."""

    term: Term
    label: str = ""                    # ONE concept name. The only thing a model produces.
    model: str = ""                    # WHICH medium named it — labels are per-medium
    status: str = PROPOSED
    deltas: dict = field(default_factory=dict)
    note: str = ""

    @property
    def validated(self) -> bool:
        return self.status == VALIDATED

    def for_medium(self, serving: str) -> str:
        """Status AS SEEN BY the model now serving. Cross-medium, a fact becomes a lead."""
        if self.status != VALIDATED:
            return self.status
        return VALIDATED if serving == self.model else LEAD

    def as_record(self) -> dict[str, object]:
        return {"term": self.term.as_record(), "label": self.label, "model": self.model,
                "status": self.status, "deltas": dict(self.deltas), "note": self.note}


def terms_from(snapshot, top: int = TOP_TERMS, min_size: int = MIN_FIBER) -> list[Term]:
    """The load-bearing vocabulary, read off the fiber structure. No text is inspected.

    Ranked by chart span first and member count second: a proposition carried in four charts
    is more load-bearing than one carried by more claims inside a single chart, because the
    cross-chart span is what makes the term a TRANSLATION rather than a repetition.
    """
    slots = getattr(snapshot, "slots", None) or {}
    out: list[Term] = []
    for fib in (getattr(snapshot, "fibers", None) or []):
        members = tuple(fib)
        if len(members) < min_size:
            continue
        charts, claims = [], []
        for slot in members:
            rec = slots.get(slot)
            if rec is None:
                continue
            charts.append(getattr(rec, "chart", "?"))
            claims.append(getattr(rec, "nu", "") or "")
        if not claims:
            continue
        out.append(Term(fiber_id=members[0], charts=tuple(sorted(set(charts))),
                        members=members, claims=tuple(claims)))
    out.sort(key=lambda t: (-len(t.charts), -t.size, t.fiber_id))
    return out[:top]


LABEL_SYSTEM = (
    "Name ONE CONCEPT. Below are claims from somebody's corpus that a reconciliation engine "
    "has established express the SAME PROPOSITION, carried across different charts.\n\n"
    "Reply with the name of the one concept in YOUR OWN canonical vocabulary that this "
    "proposition is. A noun phrase. Nothing else — no sentence, no explanation, no "
    "restatement, no hedging, no quotation marks.\n\n"
    "You are labelling an endpoint, not writing a gloss. The claims themselves travel to the "
    "reader verbatim and grouped; this label is one line on top of them. If nothing in your "
    "vocabulary fits, reply with the single word NONE — a wrong label sits next to the claims "
    "it names and will be seen, and an invented one is worse than an absent one."
)

#: A label longer than this is a sentence, and a sentence is the thing this design removed.
#: Overlong replies are VOID with the reason, not truncated into something that looks like a
#: label — trimming a paragraph into a noun phrase would manufacture the very thing refused.
MAX_LABEL_CHARS = 80

#: The DECLARED decline sentinel, enumerated in every spelling accepted. Compared by exact
#: membership rather than by folding the reply's case: this module holds no text operation of
#: any kind, so `engine/referee_sweep` and the tokenizer control stay true by construction
#: rather than by an exemption.
_DECLINES = frozenset({"NONE", "None", "none", "NONE.", "None.", "none."})


def label_prompt(term: Term) -> str:
    from .inbound import display

    return ("THE SAME PROPOSITION, carried in "
            f"{len(term.charts)} chart(s) ({', '.join(term.charts)}):\n"
            + "\n".join(f"  {display(c)}" for c in term.claims[:4])
            + "\n\nONE CONCEPT NAME.")


def label_fiber(term: Term, transport, model: str) -> Gloss:
    """One hop, terminal. Resolve-or-void: a sentence is discarded, never trimmed to fit."""
    try:
        raw, usage = transport(LABEL_SYSTEM, label_prompt(term))
    except Exception as exc:
        return Gloss(term=term, model=model, status=FAILED,
                     note=f"the label call failed: {type(exc).__name__}: {exc}")
    served = str((usage or {}).get("model") or model)
    text = (raw or "").replace("\n", " ").replace("\r", " ").strip().strip('"\'')
    if not text:
        return Gloss(term=term, model=served, status=FAILED,
                     note="the medium returned no label")
    if text in _DECLINES:
        return Gloss(term=term, model=served, status=FAILED,
                     note="the medium declined: no concept in its vocabulary fits")
    if len(text) > MAX_LABEL_CHARS:
        return Gloss(term=term, model=served, status=FAILED,
                     note=(f"the reply was {len(text)} chars — a sentence, not a concept "
                           f"name. VOID rather than truncated: trimming it would manufacture "
                           f"a label"))
    return Gloss(term=term, label=text, model=served, status=PROPOSED)


def validate(gloss: Gloss, without: dict, with_: dict) -> Gloss:
    """THE BEHAVIOURAL GATE. Two runs of the same fixed perturbations; the deltas decide.

    Survives iff at least one metric IMPROVED and NONE worsened. A gloss that helps one thing
    while hurting another is not a gain with a cost — it is unvalidated, because a translation
    that trades attachment quality for citation compliance has not aligned anything.

    `without` and `with_` are `{"discrimination": float, "citation": float}` measured on the
    same fixture set. Discrimination is better when LOWER (a selective attachment touches
    less of the region); citation is better when HIGHER.
    """
    d_disc = float(with_.get("discrimination", 0.0)) - float(without.get("discrimination", 0.0))
    d_cite = float(with_.get("citation", 0.0)) - float(without.get("citation", 0.0))
    gloss.deltas = {"discrimination": round(d_disc, 4), "citation": round(d_cite, 4)}

    improved = (d_disc < 0) or (d_cite > 0)
    worsened = (d_disc > 0) or (d_cite < 0)
    if improved and not worsened:
        gloss.status = VALIDATED
        gloss.note = ("measured on the fixture set: "
                      + ", ".join(f"{k} {v:+.4f}" for k, v in gloss.deltas.items()))
    else:
        gloss.status = FAILED
        gloss.note = ("no metric improved without another worsening — "
                      + ", ".join(f"{k} {v:+.4f}" for k, v in gloss.deltas.items())
                      + ". The medium's self-description is a proposal; its effect is the "
                        "warrant, and this one had none.")
    return gloss


#: The label cache, keyed by fiber id. One line per fiber, the terminal arrow only.
_LABELS: dict[str, "Gloss"] = {}
_LOADED = False


def fiber_label(fiber_id: str, serving: str = "") -> str:
    """The medium's one-concept name for a fiber, IF one is cached and validated.

    Returns "" when there is none, which is the ordinary case and not a failure: the fiber
    grouping in `engine/inbound._relaxed_block` carries the decompression on its own, and this
    line is a convenience on top of it. A label that is a LEAD for the serving medium is
    returned marked, never bare — a cross-medium label presented as this medium's reading
    would be the quarantine pattern broken at the point it matters.
    """
    global _LOADED
    if not _LOADED:
        _LOADED = True
        try:
            for g in load_glosses():
                _LABELS[g.term.fiber_id] = g
        except Exception:
            pass
    g = _LABELS.get(fiber_id)
    if g is None:
        return ""
    state = g.for_medium(serving) if serving else LEAD
    if state == VALIDATED:
        return g.label
    if state == LEAD and g.label:
        return f"{g.label} [LEAD — labelled on {g.model}, not on the medium now serving]"
    return ""


# ---- THE FIREWALL ------------------------------------------------------------------------
#
# A gloss is real, useful, and structurally unable to become a belief. Two doors have to stay
# shut, and neither can be held shut by a convention: content settlement, and K's candidate
# set. `bears_on` has exactly this shape and it is the precedent being followed, not a new
# containment invented for this chart.

#: Charts whose claims may enter CONTENT settlement. `medium` is absent, and its absence is
#: the firewall — a positive list refuses a new chart by default, where a deny-list would
#: admit one the day somebody forgot to add it.
CONTENT_CHARTS = frozenset({"english", "lean", "tabular", "conversation", "correspondence",
                            "python", "go"})


def is_interface_claim(chart: str) -> bool:
    """True for a claim about the INTERFACE rather than about the world."""
    return chart == MEDIUM_CHART


def admits_to_content(chart: str) -> bool:
    """May a claim in this chart enter content settlement? Positive list, no exceptions."""
    return chart in CONTENT_CHARTS


def firewall_violations(*, settled_charts=(), k_candidates=()) -> list[str]:
    """RED conditions, named. Both doors checked in one place so a caller cannot check one.

    `settled_charts` is every chart present in a settlement round; `k_candidates` is every
    candidate K is considering. A medium-chart claim in either is a constitutional breach and
    is reported as one — not filtered out quietly, because a firewall that silently drops
    what it should refuse cannot be distinguished from a firewall that is not running.
    """
    out: list[str] = []
    for chart in settled_charts:
        if is_interface_claim(chart):
            out.append("a medium-chart gloss reached CONTENT SETTLEMENT: a claim about how "
                       "the interface reads a word would be contesting claims about the "
                       "world, which is the one thing this chart may never do")
    for cand in k_candidates:
        chart = getattr(cand, "chart", None) or (cand.get("chart") if isinstance(cand, dict)
                                                 else None)
        if is_interface_claim(str(chart)):
            out.append("a medium-chart gloss reached K'S CANDIDATE SET: a gloss promoted "
                       "into the slow corpus would be knowledge conferred on a translation "
                       "note, and warrant rises only at the gate for claims about the world")
    return out


# ---- PERSISTENCE -------------------------------------------------------------------------

GLOSSARY_PATH = "runs/glossary.jsonl"


def load_glosses(path: str = GLOSSARY_PATH) -> list:
    """Validated glosses from disk. A missing file is an empty glossary, never an error.

    A record with no `status` is read as PROPOSED, never as validated: the same rule
    `engine/staleness` and `engine/conversation` apply, because a tag that defaults forward
    launders exactly what the tag exists to hold back.
    """
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        t = rec.get("term") or {}
        term = Term(fiber_id=str(t.get("fiber_id", "")),
                    charts=tuple(t.get("charts") or ()),
                    members=tuple(t.get("members") or ()),
                    claims=tuple(t.get("claims") or ()))
        out.append(Gloss(term=term, label=str(rec.get("label", "")),
                         model=str(rec.get("model", "")),
                         status=str(rec.get("status") or PROPOSED),
                         deltas=dict(rec.get("deltas") or {}),
                         note=str(rec.get("note", ""))))
    return out


def save_glosses(glosses: list, path: str = GLOSSARY_PATH) -> None:
    import json
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(g.as_record()) for g in glosses) + "\n",
                 encoding="utf-8")
