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
  MOVE 3, its morphisms. A GLOSS is a `same_claim` arrow from an operator-chart term to a
          medium-chart sense. Same three kinds, same inlet, EXTRACTION tier, source-tagged,
          born aging. No new mechanism anywhere.
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

#: A gloss arrow is `same_claim`: this operator term MEANS this medium-side concept. It is not
#: `refines` (a gloss adds no precision) and not `instance_of` (a sense is not an instance).
GLOSS_KIND = "same_claim"

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
    """One medium-chart sense for one operator term, with the model that produced it."""

    term: Term
    text: str                          # the medium's canonical statement of the concept
    model: str                         # WHICH medium said it — glosses are per-medium
    status: str = PROPOSED
    #: Metric deltas from the validation run, signed so the direction is unambiguous.
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
        return {"term": self.term.as_record(), "text": self.text, "model": self.model,
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


GLOSS_SYSTEM = (
    "You are being asked for ONE GLOSS. Below are several claims that a reconciliation "
    "engine has already established express the SAME PROPOSITION, carried across different "
    "charts (English prose, Lean, Python, Go, tables, conversation). They are one concept "
    "written several ways.\n\n"
    "State that concept in YOUR OWN canonical terms — the vocabulary you would naturally use "
    "for it. One sentence. No examples, no restatement of the claims, no hedging, no "
    "preamble. If several senses are possible, give the one these claims actually pick out.\n\n"
    "This is a translation table entry, not an answer: you are recording how you read this "
    "concept, so that later prompts using the operator's word for it can be checked against "
    "your reading of it."
)


def gloss_prompt(term: Term) -> str:
    """The term's defining claims, VERBATIM. Nothing is trimmed on the way into a prompt."""
    from .inbound import display

    lines = [f"THE SAME PROPOSITION, carried in {len(term.charts)} chart(s) "
             f"({', '.join(term.charts)}), stated {term.size} way(s):"]
    for i, (nu, slot) in enumerate(zip(term.claims, term.members), start=1):
        rec_chart = term.charts[0] if len(term.charts) == 1 else "?"
        lines.append(f"[{i}] {display(nu)}")
    lines.append("")
    lines.append("ONE GLOSS. One sentence, your own canonical terms.")
    return "\n".join(lines)


def extract_gloss(term: Term, transport, model: str) -> Gloss:
    """One relaxation per term. Resolve-or-void: an unusable reply is a FAILED gloss, not a
    silently dropped one — an absent gloss and a refused gloss are different facts."""
    try:
        raw, usage = transport(GLOSS_SYSTEM, gloss_prompt(term))
    except Exception as exc:
        return Gloss(term=term, text="", model=model, status=FAILED,
                     note=f"the gloss call failed: {type(exc).__name__}: {exc}")
    served = str((usage or {}).get("model") or model)
    text = " ".join((raw or "").split("\n")).strip()
    if not text:
        return Gloss(term=term, text="", model=served, status=FAILED,
                     note="the medium returned no gloss for this term")
    return Gloss(term=term, text=text, model=served, status=PROPOSED)


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


def glossary_block(glosses: list, serving: str, present: set, cites: list, Citable) -> list[str]:
    """The GLOSSARY, numbered into the same citation stream as everything else.

    Only VALIDATED glosses are emitted, and a gloss validated on another medium is emitted as
    a LEAD with that stated — never silently promoted across media and never silently dropped.
    """
    usable = [g for g in glosses
              if g.for_medium(serving) in (VALIDATED, LEAD)
              and (not present or g.term.fiber_id in present)]
    if not usable:
        return []
    lines = [
        "GLOSSARY — how the medium now serving reads the operator's load-bearing terms. Each "
        "gloss is a same_claim arrow from a term this corpus already carries (a fiber: one "
        "proposition written across several charts) to that medium's own canonical sense of "
        "it. A gloss is about the INTERFACE and never about truth: it conditions how the "
        "claims below are read and it is not itself a claim about the world.",
    ]
    for g in usable:
        state = g.for_medium(serving)
        n = len(cites) + 1
        cites.append(Citable(n=n, kind="gloss", chart=MEDIUM_CHART, slot=g.term.fiber_id,
                             nu=g.text))
        mark = "" if state == VALIDATED else (
            f" [LEAD — validated on {g.model}, not on the medium now serving; "
            f"treat as unconfirmed]")
        lines.append(f"[{n}] GLOSS ({'+'.join(g.term.charts)}) {g.text}{mark}")
    return lines


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
        out.append(Gloss(term=term, text=str(rec.get("text", "")),
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
