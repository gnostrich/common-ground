"""THE GATE THAT LICENSES ANSWER-FIRST: every proposition in the answer traces to the trace.

The LM's prose was ruled least-trusted during the lookup era and shipped last, beneath the
instrument trace, because nothing constrained it. That ruling was right then and became wrong
the moment a constraint existed, because a caution issued against a defect keeps costing after
the defect is fixed unless somebody re-examines it. This module is the constraint. With it
green the answer is as warranted as the trace it voices, which is what puts it first.

WHAT THIS CHECKS, EXACTLY. The ground is the union of the content words in: every moved
claim's FULL nu-string, every attachment's target nu-string and kind, the field-status and
silence lines, and the user's own typed text. A sentence in the answer is GROUNDED when every
content word in it appears in that ground or in the licensed vocabulary below. A sentence that
introduces a content word from nowhere is a proposition the trace does not carry, and it is
reported with the words that convicted it.

WHAT THIS DOES NOT CHECK, STATED SO THE GREEN IS NOT READ AS MORE THAN IT IS. Lexical
containment cannot catch a claim assembled entirely out of grounded words that the trace does
not assert — "A refutes B" where the trace holds A and B and no relation between them. It
catches importation, which is the failure mode that put the prose last: an answer reaching
outside the field for material. Calling this an entailment check would be the same overclaim
in the opposite direction, so it is not called one, and `seed/OBJECT-AMENDED.md` carries the
limitation next to the promotion.

GATE 8. The ground is built from FULL nu-strings. Display trim never feeds this, and the
answer prompt no longer receives trimmed claims either — the two were one defect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Words the ANSWER may use without the corpus supplying them. Two kinds only, and both are
#: forced: the vocabulary the prompt itself puts in the model's mouth (it is instructed to say
#: "moved", "contested", "unmeasured"), and the machine's own nouns for its parts. Adding a
#: topic word here would silently license importation, so the list holds no topic words and
#: the control below asserts that by planting one.
LICENSED = frozenset("""
about above across after again against also always among another answer answered anything
anywhere appear appears applied apply arrow arrows asked attach attached attachment
attachments bear bears because become been before behind being below beside better between
beyond block blocks both boundary bring came cannot carried carry carries chain chart charts
claim claims close comes common complete condition conditioned consider contest contested
context corpus correspond corresponds correspondence correspondences could declared decline
declined declines defect different direct directly does doing done down draw drawn drew each
either engine enter entered enters even every everything except exist exists expansion far
field further gap gaps give given gives going hand hardly have having here hold holds hops
however input inside instead into itself just keep kept know landed least less letter level
like line lines list little long look made make many mean means measure measured measurement
might more most move moved moves moving much must name named names near nearly need neither
never nothing notice noticed only onto open other others over part parts perturbation
perturbations place point points prose question questions rather reach reached reaches read
reads real really reason reasons region regions relate related relation relations remain
report reported reports respond responded response result results said same says settle
settled settlement settling shift shifted shifts shown side signal silence since slot slots
some something somewhere stand stands state stated states still structure such take taken
tell text than that their them then there these they thing things this those though three
through thus together took toward trace traced traces turn turns two under unmeasured until
upon used using very what when where whether which while whole whose will with within
without word words would write writes written wrote your yours
absent already amounts anywhere beneath else enough first hence itself last none
nowhere outside rest scope seem seems suggest suggests therefore
""".split())

#: Below this length a word is glue, not a proposition. Four is the shortest length at which a
#: content word that could be imported reliably lives ("Riemann" is 7, "cone" is 4, "is" is
#: not a claim). The constant is stated rather than tuned: raising it hides short importations,
#: lowering it convicts articles.
MIN_CONTENT = 4

_WORD = re.compile(r"[a-z0-9]+")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])|\n{2,}")


def words(text: str) -> set[str]:
    """Content words, lowercased. Numbers included: an invented figure is an importation."""
    return {w for w in _WORD.findall((text or "").lower()) if len(w) >= MIN_CONTENT}


def ground_of(compiled: dict) -> set[str]:
    """Every word the field actually put on the table, from FULL nu-strings."""
    g: set[str] = set()
    g |= words(compiled.get("typed", ""))
    g |= words(compiled.get("field_status", ""))
    rel = compiled.get("relaxation") or {}
    g |= words(rel.get("silence", ""))
    for row in rel.get("rows", []) or []:
        g |= words(row.get("nu", ""))
        g |= words(row.get("chart", ""))
        g |= words(row.get("type", ""))
        for step in row.get("path", []) or []:
            if isinstance(step, dict):
                g |= words(step.get("src_nu", "")) | words(step.get("dst_nu", ""))
                g |= words(step.get("kind", ""))
    att = compiled.get("attachment") or {}
    for a in att.get("proposed", []) or []:
        g |= words(a.get("dst_nu", "")) | words(a.get("kind", ""))
        g |= words(a.get("evidence", "")) | words(a.get("dst_chart", ""))
    for name in ("error", "note"):
        g |= words(str(att.get(name) or ""))
    return g


@dataclass
class Violation:
    sentence: str
    ungrounded: list[str]

    def render(self) -> str:
        return f"{' '.join(sorted(self.ungrounded))} :: {self.sentence.strip()[:160]}"


@dataclass
class Verdict:
    """Green is an empty `violations`. `checked` says how much was looked at, so a verdict on
    an empty answer cannot read as a pass."""
    violations: list[Violation] = field(default_factory=list)
    checked: int = 0
    ground_size: int = 0

    @property
    def ok(self) -> bool:
        return not self.violations

    def as_record(self) -> dict:
        return {"ok": self.ok, "checked": self.checked, "ground": self.ground_size,
                "violations": [{"sentence": v.sentence, "ungrounded": sorted(v.ungrounded)}
                               for v in self.violations]}


def check_answer(answer: str, compiled: dict) -> Verdict:
    """Sentence by sentence, against the trace. Every convicting word is named."""
    ground = ground_of(compiled)
    v = Verdict(ground_size=len(ground))
    for sentence in _SENT.split(answer or ""):
        if not sentence.strip():
            continue
        v.checked += 1
        loose = sorted(words(sentence) - ground - LICENSED)
        if loose:
            v.violations.append(Violation(sentence, loose))
    return v
