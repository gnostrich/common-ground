"""THE GATE THAT LICENSES ANSWER-FIRST — by RESOLVING CITATIONS, never by comparing text.

WHAT THIS REPLACED, AND WHY IT HAD TO GO. The first version of this module took the answer's
words, took the prompt's words, and reported the set difference:

    loose = sorted(words(sentence) - ground - LICENSED)

That is term overlap. `seed/OBJECT-AMENDED.md` records "Term overlap in the ANSWER path" as
DELETED, and this module reintroduced it inside the referee — the one place it does most
damage, because a similarity mechanism grading an answer launders similarity into a warrant.
It also did not work: five of six acceptance responses came back RED, every conviction was on
connective prose (`system`, `indicates`, `for example`), and no answer had imported anything.
The reply to that was a second lexical tier and a hand-tuned word list, which is the other
ledgered failure — refining a wrong mechanism instead of asking the diagram whether it can
work. Both are deleted. Nothing in this file tokenizes, lowercases, stems or compares text.

THE STRUCTURAL VERSION, which is the same trick used everywhere else in this codebase. The
compiled input already enumerates every object the answer may rest on, and `engine.inbound`
now prints an INTEGER on each of those lines — `[1] MOVED …`, `[7] BEARS ON …`. The grammar
requires every sentence to end citing at least one of those integers. This module then does
one thing: it reads the integers out of each sentence and asks whether they are in the set
that was emitted. Integer membership. Exact, mechanical, and with no notion of resemblance
anywhere in it.

HONEST NEGATIVES HAVE A LEGAL FORM, because they cannot have a positive one. A sentence that
says "the relation between X and Y is not measured here" rests on the trace LACKING something,
so no [n] can carry it, and the first version of this checker marked every such sentence RED
forever. Three of eleven sentences in a live answer were exactly this. Absence claims are half
of what makes the instrument honest — an engine that can only say what it found is an engine
that will always find something — so the grammar gives them a marker instead of a conviction:

  [0]          asserted absent across the WHOLE trace. Legal only when there IS a trace: over
               an empty citable set the honest sentence is the silence statement, not a
               negative about nothing.
  [0:3,7]      asserted absent from those lines specifically. The indices resolve exactly as a
               positive citation does — a scoped negative is checkable in the same way.
  [0gap] etc.  asserted absent BECAUSE THE FIELD SAYS SO, naming which structural fact
               licenses it. Each warrant resolves against a real number or flag in the
               relaxation record, so a sentence claiming the field reports a gap when it
               reports none is RED. This is the strongest of the three and the only one that
               can convict an invented negative.

(The marker is written U+2205 EMPTY SET in the prompt and the page; the ASCII form above is
this docstring avoiding a non-ASCII character in source prose.)

FOUR WAYS TO FAIL, all structural:
  UNCITED     — a sentence carries no citation and no absence marker. It rests on nothing.
  UNRESOLVED  — a sentence cites a number that was never emitted.
  VACUOUS     — a whole-trace absence claim over an empty trace: a negative about nothing.
  UNWARRANTED — an absence claim naming a structural warrant the field does not report.

THE TRACE-SET IS STATED, because a checker that convicts correct answers by leaving evidence
out of its own trace is convicting them twice. Citable objects are, exactly: every MOVED claim
(with its full nu-string), every CORRESPONDENCE attachment, and every BEARS-ON attachment.
Attachment-supplied text IS in the set. Nothing else is citable — not the region description,
not the boundary condition, not the field-status line — because none of those is a claim the
answer can rest on.

WHAT THIS DOES NOT CHECK, so the green is not read as more than it is. A citation says the
sentence CLAIMS to rest on line [n]; it does not verify that line [n] entails the sentence.
A model can cite honestly and reason wrongly, and this catches neither. What it catches is
the failure that put the prose last: a sentence resting on nothing in the field. That is
importation, it is now structurally visible, and calling this an entailment check would be an
overclaim of exactly the kind gate 10 exists to stop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: A citation is a bracketed integer. This regex matches numbers, not words — there is
#: deliberately no tokenizer in this module to reach for.
#: A CITATION IS A LABEL, not an integer. The label space is the region's own — a chart letter
#: and an index, `[e1]`, `[l45]` — and it survives end-to-end: the medium sees it, the extractor
#: reads it, and this checker verifies against it, with no renumbering step in between.
#:
#: THE ANTI-SIMILARITY ARGUMENT SURVIVES, RESTATED. It used to read "resolution is integer
#: membership, no text is compared". It now reads: RESOLUTION IS EXACT MEMBERSHIP IN A DECLARED
#: LABEL SET. That is the same property — a label is in the set or it is not, there is no
#: partial match, no nearest neighbour and no distance — and integers were never the safer
#: case: `engine/region._ARROW_RE` records a real defect where `1.0 -same_claim-> 2` matched the
#: `1` out of `1.0`, so a bare-number grammar had the substring hazard and it fired. The label
#: form carries one thing the integer did not: the chart, which the medium needs when relating
#: across languages, and which makes a tag/chart disagreement a decidable second check.
#:
#: The bare-integer form is still read, so a field emitted before the collapse still resolves.
#: A CITATION BRACKET, INCLUDING THE COMMA-SEPARATED SERIALIZATION. `[e40, e21]` is the same
#: structure as `[e40][e21]` written with a different delimiter, and the medium writes it
#: unprompted.
#:
#: THE RULING, and the reason widening here is not a loosening. Each token inside the bracket
#: still resolves by EXACT MEMBERSHIP in the declared label set or voids — resolve-or-void is
#: untouched, no similarity is introduced, and nothing partial is matched. What is accepted is a
#: serialization variant of an unambiguous structure. The grammar's job was never to test
#: obedience to punctuation; it is to make lies unwritable and structure extractable, and a
#: comma-separated list lies about nothing and extracts exactly. The precedent is the arrow
#: parser, which accepts `e1 -kind-> l45` and `[e1] -kind-> [l45]` for the same reason.
#:
#: MEASURED: a live run returned five violations on a five-of-five receipted answer, every one
#: of them this delimiter. Convicting a correct answer over a comma is row 523's cousin — a rule
#: enforced at a strictness the task never needed.
#:
#: The first token must be label-shaped, so `[∅]`, `[∅rel]` and `[!]` are not swallowed. Later
#: tokens are read whatever they look like, deliberately: a non-label inside the bracket must
#: come back UNRESOLVED rather than be silently dropped, or the widening would have introduced
#: leniency instead of punctuation.
#: NO ALPHABETIC RUN, and that constraint shaped the pattern. The first version wrote the
#: trailing tokens as `[A-Za-z0-9_]+`, which is a word matcher however it got there, and the
#: standing anti-similarity control refused it — correctly. The tokens after the first comma are
#: therefore matched STRUCTURALLY, as "not a closing bracket", the same device `_ABSENT` already
#: uses, and are split apart in `cited` rather than by the regex. The first token must still be
#: label-shaped, which is what keeps `[∅:e3,e7]` and `[!]` out of this pattern entirely.
_CITE_LIST = re.compile(r"\[([a-z]?\d+(?:\s*,[^\]]*)?)\]")


def cited(text: str) -> list[str]:
    """Every label a sentence claims to rest on, in order, both serializations.

    ONE PARSER, so "did this turn cite anything" and "did the referee see a citation" cannot
    disagree — `engine.dialogue` reads through this function rather than keeping its own.
    """
    out: list[str] = []
    for m in _CITE_LIST.finditer(text or ""):
        for part in m.group(1).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out

#: An absence marker: bare, index-scoped, or warrant-named. Same shape, same bracket, and the
#: only thing read out of it is integers and a name from a CLOSED list.
#: THE SCOPED ABSENCE TAKES LABELS TOO. `_CITE` and `_CITE_RUN` were widened to `[a-z]?\d+`
#: and this one was missed, so `[∅:e3,e7]` was invisible to it and an honest, correctly scoped
#: negative naming two tagged lines came back UNCITED — the opposite of resolve-or-void's
#: intent, convicting the careful answer and passing the vague one.
#:
#: The warrant group stays `[a-z_]+` because a warrant is a NAME from a closed list, not a
#: label, and the scope group is separated from it by the colon that must precede a scope.
_ABSENT = re.compile(r"\[\u2205(?::([a-z\d,\s]+))?([a-z_]+)?\]")

#: Sentence boundary. Splitting decides WHERE a sentence ends; the only thing done with the
#: sentence afterwards is reading its brackets.
#: A run of citation tokens: [4], [∅gap], [!]. Used to decide where a sentence ENDS, never
#: to compare anything.
_CITE_RUN = re.compile(r"\s*(?:\[(?:[a-z]?\d+(?:\s*,[^\]]*)?|∅[^\]]*|!)\])+")

#: A line too short to assert anything. Requiring a citation on "Yes." produces noise.
MIN_SENTENCE_CHARS = 25

#: THE CLOSED VOCABULARY OF STRUCTURAL WARRANTS. Each name maps to a predicate over the
#: relaxation and attachment records — a real number or flag the field reported. A warrant
#: outside this list does not resolve, exactly as an index outside the emitted set does not.
#: Adding one means adding the predicate that decides it, which is what keeps this a grammar
#: rather than a vocabulary of excuses.
WARRANTS: dict[str, str] = {
    "gap": "no declared correspondence carried the perturbation further "
           "(no moved row was reached over an arrow)",
    "cap": "one or more blocks exceeded the settling cap, so their contents are unmeasured",
    "cut": "the moved list was cut at its least-responsive end and the remainder is unshown",
    "attach": "nothing attached: the medium drew no arrow to the boundary condition",
    "anchor": "the region could not be aimed — no declared arrow to aim it at",
    "indiscriminate": "the medium attached to essentially everything it was shown, so the "
                      "attachment carries no information about which claims are meant",
    "void": "lines came back VOID and were discarded, so what they held is unmeasured",
}


def warrants_held(compiled: dict) -> set[str]:
    """Which structural warrants the FIELD ACTUALLY REPORTS, read off the record.

    Every one of these is a count or a flag the relaxation and the perturbation already carry.
    Nothing is inferred and no text is read: a warrant is held or it is not.
    """
    rel = compiled.get("relaxation") or {}
    att = compiled.get("attachment") or {}
    rows = rel.get("rows") or []
    held: set[str] = set()
    if rows and not any((r.get("hops") or 0) > 0 for r in rows):
        held.add("gap")
    if not rows and (rel.get("responded") is False or compiled.get("conditioned") is False):
        held.add("gap")
    if (rel.get("blocks_skipped") or 0) > 0:
        held.add("cap")
    if (rel.get("moved_dropped") or 0) > 0:
        held.add("cut")
    if not (att.get("attachment") or att.get("proposed") or []):
        held.add("attach")
    if att.get("unanchored"):
        held.add("anchor")
    if ((att.get("discrimination") or {}).get("red")):
        held.add("indiscriminate")
    if (att.get("void") or 0) > 0:
        held.add("void")
    return held


@dataclass
class Welded:
    """A sentence relating objects no arrow joins.

    THE MEASURED FAILURE: "certified positivity relates to mode spectrum measurement [21]" —
    two co-present claims fused by a conjunction, each half correctly cited, the relation
    between them declared nowhere. The citation grammar could not see it, because it checks
    that every claim is SHOWN and never that an asserted relation between two of them exists.
    Same failure class as the fiber repair, one level up: asserting structure the declarations
    do not license.

    THE CHECK IS CONSERVATIVE AND SAYS SO. Co-citing two objects in one sentence is treated as
    asserting a relation between them, because a checker cannot read the sentence to find out.
    The escape is not silence — it is [0rel], which says in the grammar that the relation is
    not in the field. Splitting the sentence also works, and is usually what was meant.
    """

    sentence: str
    numbers: list
    kind: str = "welded"

    def render(self) -> str:
        return (f"WELDED {sorted(self.numbers)} — no arrow joins these :: "
                f"{self.sentence.strip()[:160]}")


@dataclass
class Uncontested:
    """A sentence citing a contested object without carrying [!]."""

    sentence: str
    numbers: list
    kind: str = "uncontested"

    def render(self) -> str:
        return (f"UNCONTESTED {sorted(self.numbers)} — the field holds more than one value "
                f":: {self.sentence.strip()[:160]}")


@dataclass
class Uncited:
    """A sentence resting on nothing that was shown."""

    sentence: str
    kind: str = "uncited"

    def render(self) -> str:
        return f"UNCITED :: {self.sentence.strip()[:160]}"


@dataclass
class Unresolved:
    """A sentence citing a number that was never emitted."""

    sentence: str
    numbers: list[int]
    kind: str = "unresolved"

    def render(self) -> str:
        return f"UNRESOLVED {sorted(self.numbers)} :: {self.sentence.strip()[:160]}"


@dataclass
class Vacuous:
    """A whole-trace absence claim made over an empty trace."""

    sentence: str
    kind: str = "vacuous"

    def render(self) -> str:
        return f"VACUOUS (nothing was shown to be absent from) :: {self.sentence.strip()[:160]}"


@dataclass
class Unwarranted:
    """An absence claim naming a structural fact the field does not report."""

    sentence: str
    warrant: str
    kind: str = "unwarranted"

    def render(self) -> str:
        return (f"UNWARRANTED [{self.warrant}] — the field does not report it :: "
                f"{self.sentence.strip()[:160]}")


@dataclass
class Verdict:
    """`ok` is every failure list empty.

    `checked` says how many sentences were looked at, so a verdict on an empty answer cannot
    read as a pass. `asserted_absent` is counted separately from `cited` because an instrument
    whose answers are all positives is a different instrument from one that reports what it
    could not find, and the operator should be able to see which one this is.
    """

    uncited: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)
    vacuous: list = field(default_factory=list)
    unwarranted: list = field(default_factory=list)
    welded: list = field(default_factory=list)
    uncontested: list = field(default_factory=list)
    checked: int = 0
    cited: int = 0
    asserted_absent: int = 0
    citable: int = 0
    resolved: list = field(default_factory=list)
    warrants: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.uncited or self.unresolved or self.vacuous or self.unwarranted
                    or self.welded or self.uncontested)

    @property
    def violations(self) -> list[dict]:
        out = []
        for v in (self.uncited + self.unresolved + self.vacuous + self.unwarranted
                  + self.welded + self.uncontested):
            out.append({"kind": v.kind, "sentence": v.sentence,
                        "numbers": sorted(getattr(v, "numbers", []) or []),
                        "warrant": getattr(v, "warrant", "")})
        return out

    def as_record(self) -> dict:
        return {"ok": self.ok, "checked": self.checked, "cited": self.cited,
                "asserted_absent": self.asserted_absent, "citable": self.citable,
                "resolved": sorted(set(self.resolved)), "warrants": sorted(set(self.warrants)),
                "method": "citation-resolution", "violations": self.violations}


def arrow_index(compiled: dict) -> tuple[dict, set]:
    """(arrow number -> the pair it joins, the set of joined pairs). Read off the citations."""
    joins, joined = {}, set()
    for c in (compiled.get("citations") or []):
        if c.get("kind") != "arrow":
            continue
        pair = tuple(sorted(str(x) for x in (c.get("joins") or ())))
        if len(pair) == 2:
            joins[str(c["n"])] = pair
            joined.add(pair)
    return joins, joined


def group_of(compiled: dict) -> dict:
    """object number -> the declared group it belongs to. Ungrouped objects get their own."""
    out = {}
    for c in (compiled.get("citations") or []):
        if c.get("kind") == "arrow":
            continue
        n = str(c["n"])
        out[n] = str(c.get("group") or f"~{n}")
    return out


def contested_numbers(compiled: dict) -> set:
    """Objects the field holds more than one value for."""
    return {str(c["n"]) for c in (compiled.get("citations") or []) if c.get("contested")}


def citable_numbers(compiled: dict) -> set[int]:
    """The integers `engine.inbound` actually emitted. The whole trace-set, nothing implied."""
    return {str(c["n"]) for c in (compiled.get("citations") or []) if c.get("n")}


def sentences(answer: str) -> list[str]:
    """Split on terminal punctuation, KEEPING each sentence's trailing citations.

    A regex split could not do this. Models write "…forms. [4][32] It also…", and splitting on
    the full stop made the trailing bracket its own sentence — counted as uncited — while the
    sentence it belonged to lost its citation. Both halves wrong from one split, and widening
    the separator to swallow the brackets deleted them instead. So this scans: a sentence ends
    at its terminator PLUS any run of citation tokens that follows it, which is where the
    author put them.

    Fragments below `MIN_SENTENCE_CHARS` are scaffolding, not assertions.
    """
    text = answer or ""
    out, start, i = [], 0, 0
    while i < len(text):
        if text[i] in ".!?":
            j = i + 1
            while j < len(text) and text[j] in "\"')]":
                j += 1
            m = _CITE_RUN.match(text, j)
            if m:
                j = m.end()
            rest = text[j:]
            if not rest.strip() or re.match(r"\s+[A-Z\"\'(\[]", rest) or rest.startswith("\n\n"):
                out.append(text[start:j])
                start = j
                i = j
                continue
        i += 1
    if text[start:].strip():
        out.append(text[start:])
    return [s for s in out if len(s.strip()) >= MIN_SENTENCE_CHARS]


def check_answer(answer: str, compiled: dict) -> Verdict:
    """Read the brackets, resolve them against what was emitted. No text is compared."""
    valid = citable_numbers(compiled)
    held = warrants_held(compiled) | {"rel"}
    joins, joined = arrow_index(compiled)
    contested = contested_numbers(compiled)
    groups = group_of(compiled)
    v = Verdict(citable=len(valid))
    for sentence in sentences(answer):
        v.checked += 1
        nums = cited(sentence)
        absences = _ABSENT.findall(sentence)

        if absences:
            v.asserted_absent += 1
            for scoped, warrant in absences:
                if warrant:
                    v.warrants.append(warrant)
                    if warrant not in held:
                        v.unwarranted.append(Unwarranted(sentence, warrant))
                    continue
                if scoped:
                    scope = [x for x in scoped.replace(" ", "").split(",") if x]
                    bad = [n for n in scope if n not in valid]
                    if bad:
                        v.unresolved.append(Unresolved(sentence, bad))
                    else:
                        v.resolved.extend(scope)
                    continue
                if not valid:
                    v.vacuous.append(Vacuous(sentence))
        if nums:
            v.cited += 1
            bad = [n for n in nums if n not in valid]
            if bad:
                v.unresolved.append(Unresolved(sentence, bad))
            v.resolved.extend(n for n in nums if n in valid)

            # THE WELD RULE. Co-citing two objects in one sentence is treated as asserting a
            # relation between them, because a checker cannot read the sentence to find out.
            # It is licensed by citing the ARROW that states the relation, or by [∅rel]
            # which says in the grammar that the field does not have one. Splitting the
            # sentence also works and is usually what was meant.
            objects = sorted({n for n in nums if n in valid and n not in joins})
            if len(objects) > 1 and not any(n in joins for n in nums) \
                    and not any(w == "rel" for _, w in absences):
                # DIFFERENT GROUPS, not merely two objects. Co-citing two faces of one
                # quotient asserts no relation the field lacks — the quotient IS the declared
                # relation between them, which is what a fiber means. The rule fires only
                # where the sentence spans groups the field never joined, and the first
                # version without this distinction convicted a correct multi-citation.
                spans = {groups.get(n, f"~{n}") for n in objects}
                covered = all(tuple(sorted((a, b))) in joined
                              for i, a in enumerate(objects) for b in objects[i + 1:])
                if len(spans) > 1 and not covered:
                    v.welded.append(Welded(sentence, objects))

            # THE CONTEST RULE. A contested object cited without [!] is a contest resolved in
            # prose, which is the one thing the field explicitly refuses to do itself.
            hot = [n for n in nums if n in contested]
            if hot and "[!]" not in sentence:
                v.uncontested.append(Uncontested(sentence, hot))
        elif not absences:
            v.uncited.append(Uncited(sentence))
    return v
