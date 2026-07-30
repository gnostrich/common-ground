"""nu per chart, claim-form classification, and the slot hasher.

Gate 1: `slot_id(nu, type)` takes exactly the two arguments the gate names and reads no
engine state. `nu` is chart-indexed and emits the chart as a control-character tag inside
its own output, so the chart rides along inside `nu(surface)` and the hash signature stays
`hash(nu(surface), type)` verbatim.

Idempotence (null cell i) is exact rather than empirical: step 2 of the core normalization
deletes every C0/C1 control character from the input, so a raw surface can never contain a
chart tag, and stripping a leading tag on re-entry is unambiguous.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from .constants import (
    LEAN_CLAIM_HEADS,
    LEAN_DEFINE_HEADS,
    MARKERS_CONDITIONAL,
    MARKERS_DEFINITIONAL,
    MARKERS_DEONTIC,
)
from .hashing import join_hash
from .types import Chart, ClaimForm

TAG_OPEN = "\x01"
_TAGS: dict[str, str] = {"english": "\x01en\x01", "lean": "\x01lean\x01"}
_TAG_RE = re.compile(r"^\x01[a-z]+\x01")

# C0 and C1 control characters, which the tag is drawn from and which no legitimate
# surface needs.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_WS_RE = re.compile(r"\s+")

_TYPOGRAPHIC = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u2014": "-", "\u2015": "-", "\u2212": "-",
    "\u2026": "...", "\u00a0": " ", "\u202f": " ", "\u2007": " ",
}

_MD_INLINE_RE = re.compile(r"[*_`~]+")
_MD_LINE_PREFIX_RE = re.compile(r"^\s*(?:#{1,6}\s+|>\s+|[-*+]\s+|\d+[.)]\s+)", re.MULTILINE)
_LATEX_DELIM_RE = re.compile(r"\\[()\[\]]|\$+")
_TERMINAL_PUNCT_RE = re.compile(r"[.?!;,:\s]+$")

_LEAN_LINE_COMMENT_RE = re.compile(r"--[^\n]*")


def _strip_tag(s: str) -> str:
    return _TAG_RE.sub("", s, count=1) if s.startswith(TAG_OPEN) else s


def _strip_lean_block_comments(s: str) -> str:
    """Remove balanced /- ... -/ blocks, honouring nesting.

    Lean block comments nest, so a regex would mis-handle `/- a /- b -/ c -/`. Scan
    instead; an unterminated block is treated as running to end of input, which is what
    the elaborator would report as an error anyway.
    """
    out: list[str] = []
    depth = 0
    i = 0
    n = len(s)
    while i < n:
        if s.startswith("/-", i):
            depth += 1
            i += 2
        elif s.startswith("-/", i) and depth > 0:
            depth -= 1
            i += 2
        else:
            if depth == 0:
                out.append(s[i])
            i += 1
    return "".join(out)


def _lean_head(s: str) -> str:
    """First token of the declaration, ignoring common modifiers."""
    modifiers = {
        "private", "protected", "noncomputable", "partial", "unsafe",
        "@[simp]", "nonrec", "scoped", "local",
    }
    for token in s.split():
        t = token.strip()
        if not t or t.startswith("@[") or t in modifiers:
            continue
        return t
    return ""


def _cut_at_top_level_assign(s: str) -> str:
    """Cut at the first `:=` that is not inside brackets.

    Used for claim heads only: the proof term is not part of a statement's address
    (proof irrelevance), but a definition's body *is* its content and is retained.
    """
    depth = 0
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in "([{⟨":
            depth += 1
        elif c in ")]}⟩":
            depth = max(0, depth - 1)
        elif depth == 0 and s.startswith(":=", i):
            return s[:i]
        i += 1
    return s


#: Same alternation as the multiline prefix rule, anchored to the start of the string.
#: Applied after whitespace collapse — see the fixed-point note in `_nu_english`.
_MD_LEADING_RE = re.compile(r"^\s*(?:#{1,6}\s+|>\s+|[-*+]\s+|\d+[.)]\s+)")


def _nu_english(core: str) -> str:
    s = _CONTROL_RE.sub("", core)
    s = unicodedata.normalize("NFKC", s)
    for src, dst in _TYPOGRAPHIC.items():
        s = s.replace(src, dst)
    s = _MD_LINE_PREFIX_RE.sub("", s)
    s = _MD_INLINE_RE.sub("", s)
    s = _LATEX_DELIM_RE.sub("", s)
    s = s.casefold()
    s = _WS_RE.sub(" ", s).strip()

    # Fixed point, and not optional. The multiline pass above runs before whitespace
    # collapse, so a marker that only *becomes* line-initial once the collapse removes
    # what preceded it survives the first pass and is stripped on the second — which
    # breaks idempotence, and therefore breaks addressing. Iterating here to a fixed
    # point after the collapse closes that gap. Found by the cell-(i) fuzzer on input
    # '*#\nr\t\x00\x01m -> $_\n=': the '*' was removed as an inline marker, promoting
    # '#' to line-initial on re-entry.
    while True:
        stripped = _MD_LEADING_RE.sub("", s).lstrip()
        if stripped == s:
            break
        s = stripped

    s = _TERMINAL_PUNCT_RE.sub("", s)
    return s


def _nu_lean(core: str) -> str:
    s = _CONTROL_RE.sub("", core)
    s = unicodedata.normalize("NFKC", s)
    s = _strip_lean_block_comments(s)
    s = _LEAN_LINE_COMMENT_RE.sub("", s)
    if _lean_head(s) in LEAN_CLAIM_HEADS:
        s = _cut_at_top_level_assign(s)
    s = _WS_RE.sub(" ", s).strip()
    # Deliberately no casefold: Lean is case-sensitive and `Cone` != `cone`.
    return s


def nu(chart: Chart, surface: str) -> str:
    """Normalize a surface for the given chart. Idempotent, total, pure."""
    if chart not in _TAGS:
        raise ValueError(f"unknown chart {chart!r}")
    core = _strip_tag(surface)
    body = _nu_english(core) if chart == "english" else _nu_lean(core)
    return _TAGS[chart] + body


def slot_id(normalized: str, type_: ClaimForm) -> str:
    """Gate 1. sha256(nu(surface), type). No engine state, ever."""
    return join_hash(normalized, type_)


def address(chart: Chart, surface: str, type_: ClaimForm) -> tuple[str, str]:
    """Convenience: returns (slot_id, nu)."""
    n = nu(chart, surface)
    return slot_id(n, type_), n


def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
    return any(needle in haystack for needle in needles)


def classify(chart: Chart, surface: str) -> ClaimForm:
    """Assign a claim-form. Ordered rules, first match wins (seed/TYPES.md).

    Operates on the normalized surface so that classification and addressing cannot
    disagree — a pair that collides on `nu` must also collide on `type`, or the
    paraphrase suite's known-same pairs would fail for a reason that has nothing to do
    with normalization.
    """
    n = nu(chart, surface)
    body = n[len(_TAGS[chart]) :]

    if chart == "lean":
        head = _lean_head(body)
        if head in LEAN_DEFINE_HEADS:
            return "define"
        if head in LEAN_CLAIM_HEADS:
            return "conditional" if _has_explicit_binder(body) else "assert"
        # A Lean fragment with no recognised head is still a claim about the code.
        return "assert"

    if _contains_any(body, MARKERS_DEONTIC):
        return "normative"
    if _contains_any(body, MARKERS_CONDITIONAL):
        return "conditional"
    if _contains_any(body, MARKERS_DEFINITIONAL):
        return "define"
    return "assert"


def _has_explicit_binder(body: str) -> bool:
    """True if a Lean declaration binds at least one hypothesis before the final colon.

    `theorem f (h : P) : Q` is a conditional; `theorem f : Q` is an assert. Detected by
    the presence of a bracketed binder group between the declaration name and the
    top-level colon that opens the statement.
    """
    depth = 0
    for i, c in enumerate(body):
        if c in "([{⟨":
            if depth == 0:
                # A binder group opens before we reached a top-level colon.
                return True
            depth += 1
        elif c in ")]}⟩":
            depth = max(0, depth - 1)
        elif c == ":" and depth == 0:
            # Reached the statement colon with no binder group seen.
            return False
    return False
