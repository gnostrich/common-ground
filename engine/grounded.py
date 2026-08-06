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

TWO WAYS TO FAIL, both structural:
  UNCITED     — a sentence carries no citation at all. It rests on nothing that was shown.
  UNRESOLVED  — a sentence cites a number that was never emitted. It rests on something that
                does not exist.

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

#: A citation is a bracketed integer. This is the only regular expression in the module and
#: it matches numbers, not words — there is deliberately no tokenizer here to reach for.
_CITE = re.compile(r"\[(\d+)\]")

#: Sentence boundary. Splitting is not matching: this decides WHERE a sentence ends, and the
#: only thing done with the sentence afterwards is reading its bracketed integers.
_SENT = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z\"'(\[])|\n{2,}")

#: A line that is scaffolding rather than a proposition — a bare heading or a fragment too
#: short to assert anything. Requiring a citation on "Yes." produces noise, not rigour.
MIN_SENTENCE_CHARS = 25


@dataclass
class Uncited:
    """A sentence resting on nothing that was shown."""

    sentence: str

    def render(self) -> str:
        return f"UNCITED :: {self.sentence.strip()[:160]}"


@dataclass
class Unresolved:
    """A sentence citing a number that was never emitted."""

    sentence: str
    numbers: list[int]

    def render(self) -> str:
        return (f"UNRESOLVED {sorted(self.numbers)} :: {self.sentence.strip()[:160]}")


@dataclass
class Verdict:
    """`ok` is both failure lists empty. `checked` says how many sentences were looked at, so
    a verdict on an empty answer cannot read as a pass, and `citable` says how large the set
    was — a green against an empty citable set means the answer cited nothing because there
    was nothing, which is a different fact and is reported as one."""

    uncited: list[Uncited] = field(default_factory=list)
    unresolved: list[Unresolved] = field(default_factory=list)
    checked: int = 0
    cited: int = 0
    citable: int = 0
    resolved: list[int] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.uncited and not self.unresolved

    @property
    def violations(self) -> list[dict]:
        return ([{"kind": "uncited", "sentence": u.sentence, "numbers": []}
                 for u in self.uncited]
                + [{"kind": "unresolved", "sentence": u.sentence, "numbers": sorted(u.numbers)}
                   for u in self.unresolved])

    def as_record(self) -> dict:
        return {"ok": self.ok, "checked": self.checked, "cited": self.cited,
                "citable": self.citable, "resolved": sorted(set(self.resolved)),
                "method": "citation-resolution",
                "violations": self.violations}


def citable_numbers(compiled: dict) -> set[int]:
    """The integers `engine.inbound` actually emitted. The whole trace-set, nothing implied."""
    return {int(c["n"]) for c in (compiled.get("citations") or []) if c.get("n")}


def sentences(answer: str) -> list[str]:
    """Split on terminal punctuation. Fragments below `MIN_SENTENCE_CHARS` are scaffolding."""
    return [s for s in _SENT.split(answer or "")
            if len(s.strip()) >= MIN_SENTENCE_CHARS]


def check_answer(answer: str, compiled: dict) -> Verdict:
    """Read the citations, resolve them against what was emitted. No text is compared."""
    valid = citable_numbers(compiled)
    v = Verdict(citable=len(valid))
    for sentence in sentences(answer):
        v.checked += 1
        nums = [int(m) for m in _CITE.findall(sentence)]
        if not nums:
            v.uncited.append(Uncited(sentence))
            continue
        v.cited += 1
        bad = [n for n in nums if n not in valid]
        if bad:
            v.unresolved.append(Unresolved(sentence, bad))
        v.resolved.extend(n for n in nums if n in valid)
    return v
