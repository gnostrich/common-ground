"""OI-5: CONDITIONAL LANGUAGE IN A RULING IS A TELL.

"as long as X" in a normative sentence is one of two things. Either X is a gate, in which case
the clause is redundant — the gate already refuses — or X is nothing, in which case the clause
is hope wearing the grammar of a constraint. Constraints are controls, not clauses, so a
conditional that cites no control is a ruling that has not been decided yet.

USE VERSUS MENTION, and it is not a technicality. OI-5's own statement contains the words "as
long as X", because it is quoting the phrase it forbids. A linter that could not tell quoting
from asserting would fire on the sentence that defines the rule — the same self-reference that
made an earlier key-exposure control fail the moment its assertion was written. A phrase inside
quotation marks or backticks is being MENTIONED. Everywhere else it is being USED.

WHAT COUNTS AS A CITATION is a closed, declared set: a gate number, an OI id, a D-decision id,
or a named control file. Not "a justification" — this cannot read prose and does not try. The
question it asks is narrow and decidable: does this sentence point at something that refuses?

SCOPE IS NORMATIVE TEXT ONLY. In code comments a conditional is ordinary description ("this
holds as long as the arrow exists" is a statement of fact about a mechanism). Running there
would produce noise, and a control that cries wolf is switched off by the person it protects.

THE RESIDUAL, CONFESSED — and it fired on the first real run. Mood is not detected. A
descriptive conditional in a normative document — a sentence stating how something behaved
rather than ruling what must happen — will be flagged. `seed/OBJECT-AMENDED.md` narrates the
mutually-concealing-defects case with "the control passed ... for as long as the emitter
stayed broken", which is history, not a ruling. That is a false positive this module cannot
remove without reading meaning, which is the mechanism this engine refuses everywhere.

SO THE EXEMPTION IS A NAMED LINE, NOT A CATEGORY. `KNOWN_DESCRIPTIVE` holds that one sentence
fragment verbatim. Dropping OBJECT-AMENDED.md from scope instead would have been the easy fix
and the wrong one: the document does contain rulings, and exempting the file to clear a hit in
its narrative is how a control gets defanged by the person it inconveniences. An allowlist
somebody can read in full is a cost that stays visible; a category exemption is not.
"""

from __future__ import annotations

import re

#: The tells. Deliberately short and specific: each is a construction that promises a future
#: condition rather than naming a present control. A longer list would be a heuristic.
TELLS = ("as long as", "so long as", "provided that", "provided we", "assuming that",
         "assuming we", "if it turns out", "unless and until", "once we have", "for now, ")

#: What a conditional may point at to be legitimate. A gate refuses; an OI is enforced; a D-id
#: is a recorded decision; a test file is a control. Anything else is prose.
_CITES = re.compile(r"\b(gate\s*\d+|OI-\d+|D\d+|tests?/[\w/]+\.py|seed/[\w.]+)\b", re.I)

#: Quotation marks and backticks. Inside them the phrase is MENTIONED, not used.
_QUOTED = re.compile(r"[\"“”`']([^\"“”`']{0,200})[\"“”`']")

#: DESCRIPTIVE conditionals, allowed one sentence at a time and never one file at a time. Each
#: entry is a verbatim fragment of a sentence that narrates history rather than ruling
#: anything, checked and recorded by a human. If this list grows past a handful, the linter is
#: wrong about its scope and the scope is what should change — not this list.
KNOWN_DESCRIPTIVE = (
    # seed/OBJECT-AMENDED.md, the mutually-concealing-defects narrative: a statement about how
    # long a broken control stayed undetected, not a condition on any ruling.
    "could never have detected content drift, for as long as the",
)


def sentences(text: str) -> list[str]:
    """Split on terminal punctuation and newlines. Crude on purpose: a finding names the
    sentence so a human can read it, and over-splitting only narrows the quoted context."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text or "") if s.strip()]


def mentioned(sentence: str, tell: str) -> bool:
    """Is every occurrence of `tell` inside quotes or backticks?"""
    spans = [m.span(1) for m in _QUOTED.finditer(sentence)]
    low = sentence.lower()
    for m in re.finditer(re.escape(tell), low):
        if not any(a <= m.start() and m.end() <= b for a, b in spans):
            return False
    return True


def findings(blobs: dict) -> list[dict]:
    """Conditional clauses in normative text that cite no control. {path: text} in, list out.

    A function over blobs rather than over the filesystem, so a control can run it on planted
    text and prove it fires — which is the only way to know a clean real result means anything.
    """
    out: list[dict] = []
    for path, text in blobs.items():
        for s in sentences(text):
            low = s.lower()
            for tell in TELLS:
                if tell not in low:
                    continue
                if mentioned(s, tell):
                    continue                      # quoted: the phrase is the subject, not the rule
                if _CITES.search(s):
                    continue                      # points at something that refuses
                if any(k in s for k in KNOWN_DESCRIPTIVE):
                    continue                      # recorded narrative, one sentence at a time
                out.append({"path": path, "tell": tell, "sentence": s[:240]})
                break
    return out
