"""Ingestion routing (item 3): a raw artifact -> a chart, a verbatim pin, or the shelf.

Everything that enters a run passes through here first, and every artifact ends up in
exactly one place with a logged reason and a count. Nothing is silently dropped: the report
header carries the tally, so "we ingested X and shelved Y for reason Z" is a fact on the
page rather than an inference.

The rules, in order (first match wins):

1. **fenced code block / log / stack trace -> verbatim-artifact.** Pinned by content hash,
   **not extracted** — a stack trace is not a claim, and running an extractor over it would
   manufacture b-values from noise.
2. **`.lean` that elaborates -> Lean chart.** Elaboration is an *injected* predicate; with
   no pinned Lean toolchain (D6 unresolved) the default cannot verify, so:
3. **`.lean` that does not elaborate -> shelf**, `elaboration-error`, counted separately
   from ordinary shelving so a broken proof is distinguishable from off-topic text.
4. **well-formed markdown table -> tabular chart.**
5. **malformed markdown table -> prose**, tagged `malformed-table`, so a table that failed
   to parse is still read rather than lost.
6. **prose -> English chart.** Inline math is replaced by opaque hashed tokens first (a
   known limitation: the engine does not read math, it preserves it as a stable token so it
   neither pollutes an address nor vanishes).
7. **everything else -> shelf**, `unclassified`, counted in the header.

NFC normalization is applied once at this boundary and pinned, so charts downstream see a
single Unicode normal form.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from .charts import is_chart
from .hashing import sha256_text
from .types import Document

# Destinations.
ENGLISH = "english"
LEAN = "lean"
TABULAR = "tabular"
VERBATIM = "verbatim-artifact"
SHELF = "shelf"

_FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\)|^\s+at .+:\d+\)?$", re.MULTILINE)
_LOG_LINE_RE = re.compile(r"^\s*\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d|^(DEBUG|INFO|WARN|ERROR|FATAL)\b", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$", re.MULTILINE)
_INLINE_MATH_RE = re.compile(r"\$[^$\n]+\$|\\\([^\n]*?\\\)")


@dataclass(frozen=True, slots=True)
class RoutedDoc:
    name: str
    destination: str
    reason: str
    content_hash: str
    document: Document | None = None   # None for verbatim/shelf — not sent to extractors
    math_tokens: tuple[str, ...] = ()  # opaque hashes of inline math preserved from prose


@dataclass(slots=True)
class RoutingReport:
    routed: list[RoutedDoc] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.routed:
            key = r.destination if r.destination != SHELF else f"shelf:{r.reason}"
            out[key] = out.get(key, 0) + 1
        return out

    def header(self) -> str:
        parts = [f"{k}={v}" for k, v in sorted(self.counts().items())]
        return "routing: " + ", ".join(parts) if parts else "routing: (empty)"

    def to_charts(self) -> list[Document]:
        """Only the documents that reached a chart. Verbatim and shelved are excluded."""
        return [r.document for r in self.routed if r.document is not None]


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _tokenize_math(text: str) -> tuple[str, list[str]]:
    """Replace inline math with opaque, content-stable hash tokens. Known limitation.

    The engine does not understand math; tokenizing keeps `$x^2$` from being read as prose
    (which would casefold and split it into meaningless slot tokens) while preserving it as
    a stable, addressable token so two documents sharing the same formula still collide.
    """
    tokens: list[str] = []

    def _sub(m: re.Match) -> str:
        h = sha256_text(m.group())[:12]
        tokens.append(h)
        return f" math_{h} "

    return _INLINE_MATH_RE.sub(_sub, text), tokens


def _is_verbatim(text: str) -> bool:
    return bool(_FENCE_RE.search(text) or _TRACEBACK_RE.search(text)
                or _LOG_LINE_RE.search(text))


def _table_shape(text: str) -> str:
    """"well-formed" | "malformed" | "none". A table needs a separator row and >=2 pipes."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    pipe_lines = [ln for ln in lines if ln.count("|") >= 2]
    if not pipe_lines:
        return "none"
    if not _TABLE_SEP_RE.search(text):
        return "malformed"   # table-ish pipes but no alignment row
    # Well-formed: header + separator + at least one data row, consistent-ish columns.
    non_sep = [ln for ln in pipe_lines if not _TABLE_SEP_RE.match(ln)]
    if len(non_sep) < 2:
        return "malformed"
    cols = [ln.count("|") for ln in non_sep]
    return "well-formed" if max(cols) - min(cols) <= 1 else "malformed"


def _default_lean_elaborates(text: str) -> tuple[bool, str]:
    """No pinned Lean toolchain (D6 unresolved), so elaboration cannot be verified.

    Returns (False, reason). This is deliberately conservative: an unverifiable proof is
    shelved with a reason, never waved through into the Lean chart, because a Lean-chart
    slot that was never kernel-checked would be a grounding claim the engine cannot back.
    """
    return False, "no pinned Lean toolchain (D6 unresolved); elaboration unverified"


def route(
    name: str,
    text: str,
    source: str = "repo_docs",
    *,
    lean_elaborates: Callable[[str], tuple[bool, str]] | None = None,
) -> RoutedDoc:
    """Classify one artifact. `name` carries the extension the router keys `.lean` on."""
    raw_hash = sha256_text(text)
    normalized = _nfc(text)
    is_lean_file = name.endswith(".lean")

    # 1. verbatim artifacts: code / logs / traces — pinned, never extracted.
    #    (A .lean file is code too, but it has its own elaboration route below.)
    if not is_lean_file and _is_verbatim(normalized):
        return RoutedDoc(name, VERBATIM, "code/log/trace — pinned, not extracted", raw_hash)

    # 2/3. Lean is keyed on the .lean extension (per the spec). A prose file that merely
    #      mentions "lemma" is prose, not Lean — the content heuristic false-fired on
    #      table headers, so routing to Lean is extension-only.
    if is_lean_file:
        elaborates, reason = (lean_elaborates or _default_lean_elaborates)(normalized)
        if elaborates:
            return RoutedDoc(name, LEAN, "elaborates", raw_hash,
                             Document(name, LEAN, normalized, source))
        return RoutedDoc(name, SHELF, f"elaboration-error: {reason}", raw_hash)

    # 4/5. Markdown tables: well-formed -> tabular; malformed -> prose, tagged.
    shape = _table_shape(normalized)
    if shape == "well-formed":
        return RoutedDoc(name, TABULAR, "well-formed table", raw_hash,
                         Document(name, TABULAR, normalized, source))
    if shape == "malformed":
        prose, tokens = _tokenize_math(normalized)
        return RoutedDoc(name, ENGLISH, "malformed-table -> prose", raw_hash,
                         Document(name, ENGLISH, prose, source), tuple(tokens))

    # 6. Prose -> English, with inline math preserved as opaque tokens.
    if normalized.strip():
        prose, tokens = _tokenize_math(normalized)
        return RoutedDoc(name, ENGLISH, "prose", raw_hash,
                         Document(name, ENGLISH, prose, source), tuple(tokens))

    # 7. Everything else (empty / unclassifiable) -> shelf.
    return RoutedDoc(name, SHELF, "unclassified", raw_hash)


def route_all(
    artifacts: list[tuple[str, str]],
    source: str = "repo_docs",
    *,
    lean_elaborates: Callable[[str], tuple[bool, str]] | None = None,
) -> RoutingReport:
    """Route `(name, text)` artifacts and return the report with per-destination counts."""
    report = RoutingReport()
    for name, text in artifacts:
        report.routed.append(route(name, text, source, lean_elaborates=lean_elaborates))
    return report
