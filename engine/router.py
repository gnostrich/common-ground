"""Ingestion routing (item 3): a raw artifact -> a chart, a verbatim pin, or the shelf.

Everything that enters a run passes through here first, and every artifact ends up in
exactly one place with a logged reason and a count. Nothing is silently dropped: the report
header carries the tally, so "we ingested X and shelved Y for reason Z" is a fact on the
page rather than an inference.

The rules, in order (first match wins):

1. **fenced blocks -> verbatim SPANS, lifted out and pinned by content hash**; the prose
   around them is routed on its own merits. A stack trace is not a claim and an extractor
   over it would manufacture b-values from noise — but neither is a README's usage section
   forfeit because it sits beside one. Verbatim is a property of a span, and a fence is a
   delimiter the author wrote. A document that is *entirely* fenced blocks, or whose prose
   residue still reads as log/trace (those have no delimiter — a stated limitation), is a
   whole verbatim artifact.
2. **`.lean` -> Lean chart, always.** Gate 3 governs GROUNDING, not entry, so a Lean file
   enters on the strength of being Lean, at extraction tier.
3. **Elaboration decides CLAMP ELIGIBILITY only.** It is an *injected* predicate; with no
   pinned toolchain (D6 unresolved) the default cannot verify, so the slot enters
   `NOT clamp-eligible` — present and readable, grounding nothing.
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
CONVERSATION = "conversation"
VERBATIM = "verbatim-artifact"
SHELF = "shelf"

_FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)
#: A complete fenced block: an opening fence, its body, and a CLOSING fence of the same kind.
#: The backreference is what makes it a span rather than a guess — the block's extent is
#: written in the document by its author, not inferred.
_FENCE_BLOCK_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[^\n]*\n.*?^[ \t]{0,3}\1[ \t]*$",
                             re.DOTALL | re.MULTILINE)
#: A fence opened and never closed runs to the end of the document. Same delimiter, one end.
_OPEN_FENCE_RE = re.compile(r"^[ \t]{0,3}(?:`{3,}|~{3,})[^\n]*\n.*\Z", re.DOTALL | re.MULTILINE)
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\)|^\s+at .+:\d+\)?$", re.MULTILINE)
_LOG_LINE_RE = re.compile(r"^\s*\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d|^(DEBUG|INFO|WARN|ERROR|FATAL)\b", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$", re.MULTILINE)
_INLINE_MATH_RE = re.compile(r"\$[^$\n]+\$|\\\([^\n]*?\\\)")

#: A Lean declaration docstring (`/-- ... -/`) and a module/section doc (`/-! ... -/`).
#: These are natural-language STATEMENTS about the declaration they precede — the most
#: perfectly co-located prose that can exist, since they sit ON the declaration.
_LEAN_DOCSTRING_RE = re.compile(r"/--(.*?)-/", re.DOTALL)
_LEAN_SECTION_DOC_RE = re.compile(r"/-!(.*?)-/", re.DOTALL)
#: The declaration a docstring is attached to: Lean convention puts the doc immediately
#: before its declaration, so the head that follows is the one being documented.
_NEXT_DECL_RE = re.compile(
    r"\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+"
    r"|nonrec\s+|scoped\s+|local\s+)*"
    r"(theorem|lemma|def|abbrev|structure|class|instance|inductive|axiom)\s+([^\s:({\[]+)")


@dataclass(frozen=True, slots=True)
class RoutedDoc:
    name: str
    destination: str
    reason: str
    content_hash: str
    document: Document | None = None   # None for verbatim/shelf — not sent to extractors
    math_tokens: tuple[str, ...] = ()  # opaque hashes of inline math preserved from prose
    #: Content hashes of the fenced blocks lifted out of this document. They are pinned as
    #: artifacts of record and never extracted; the prose around them is routed normally.
    verbatim_spans: tuple[str, ...] = ()
    #: English documents derived from a Lean file's docstrings. ADDITIVE: they are extra
    #: claims in the English chart and do not touch the Lean document or its address.
    companions: tuple[Document, ...] = ()


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
        """Only the documents that reached a chart. Verbatim and shelved are excluded.

        Includes docstring companions: a Lean docstring is an English claim about the
        declaration it sits on, so it reaches the English chart alongside the Lean document.
        """
        out: list[Document] = []
        for r in self.routed:
            if r.document is not None:
                out.append(r.document)
            out.extend(r.companions)
        return out


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


def _is_log_or_trace(text: str) -> bool:
    """The verbatim signals that have no span delimiter. See `split_verbatim`."""
    return bool(_TRACEBACK_RE.search(text) or _LOG_LINE_RE.search(text))


def split_verbatim(text: str) -> tuple[str, tuple[str, ...]]:
    """Separate a document's PROSE from its fenced blocks. Span-level, not document-level.

    Verbatim is a property of a SPAN, not of a document. The old rule shelved an entire
    artifact if it contained a single fence, which on the real repositories discarded 226 of
    742 markdown files — 2.21M characters of prose, to avoid extracting 225k characters of
    code. The prose it discarded is exactly the prose most likely to bridge: a README's usage
    section is the natural-language statement of what the code beside it does.

    A fenced block is used as the delimiter because it *is* one: the author wrote where the
    code starts and where it stops, so removing it is reading the document's own markup, not
    inferring an extent. Each removed block is pinned by content hash and returned, so it is
    still an artifact of record — it is simply not run through an extractor.

    Log lines and stack traces get NO span treatment here, and that is a stated limitation
    rather than an oversight: they carry no delimiter, so their extent would have to be
    guessed, and a guessed extent is the kind of threshold this build removes rather than
    adds. A document whose prose residue still reads as log/trace stays a whole artifact.
    On the real corpus that residue is **one document of 227**.
    """
    pinned: list[str] = []

    def _pin(match: re.Match) -> str:
        pinned.append(sha256_text(match.group())[:16])
        return "\n"

    prose = _FENCE_BLOCK_RE.sub(_pin, text)
    if _FENCE_RE.search(prose):        # an opening fence that was never closed
        prose = _OPEN_FENCE_RE.sub(_pin, prose)
    return prose, tuple(pinned)


def _is_conversation(text: str) -> bool:
    """A transcript: >=3 speaker-attributed turns across >=2 distinct speakers.

    Requiring two speakers and three turns keeps ordinary prose with a stray "Name:" colon
    from reading as a conversation, while a real dialogue routes to the conversation chart.
    """
    from .conversation import parse_transcript

    turns = parse_transcript(text)
    return len(turns) >= 3 and len({t.speaker for t in turns}) >= 2


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

    Returns (False, reason). The file still enters the Lean chart — gate 3 is about what may
    GROUND, not about what may be read — but it enters NOT clamp-eligible, so nothing it says
    is backed by a kernel receipt the engine does not have.
    """
    return False, "no pinned Lean toolchain (D6 unresolved); elaboration unverified"


def lean_docstrings(name: str, text: str, source: str = "repo_docs") -> list[Document]:
    """A Lean file's docstrings, as ENGLISH claims attached to their declaration.

    `/-- ... -/` documents the declaration that follows it (Lean convention), so the derived
    English document's id names that declaration: `<file>#doc:<declaration>`. `/-! ... -/` is a
    section/module doc with no single owner, so it is attributed to the file.

    This is ADDITIVE and NON-PLASTIC. The Lean document and its address are untouched — `nu`
    still strips docstrings from the Lean surface, so every Lean slot id is byte-identical
    before and after. What changes is that 293k characters of prose which used to be discarded
    at the boundary now enter the English chart, carrying provenance that points at the exact
    declaration they describe. That provenance is what makes them co-located at DECLARATION
    granularity — tighter than any directory.
    """
    out: list[Document] = []
    for match in _LEAN_DOCSTRING_RE.finditer(text):
        body = match.group(1).strip()
        if not body:
            continue
        owner = _NEXT_DECL_RE.match(text, match.end())
        decl = owner.group(2) if owner else ""
        doc_id = f"{name}#doc:{decl}" if decl else f"{name}#doc@{match.start()}"
        doc = Document(doc_id, ENGLISH, _nfc(body), source)
        doc.meta["lean_file"] = name
        if decl:
            doc.meta["declaration"] = decl
            doc.meta["declaration_head"] = owner.group(1)
        out.append(doc)
    for match in _LEAN_SECTION_DOC_RE.finditer(text):
        body = match.group(1).strip()
        if not body:
            continue
        doc = Document(f"{name}#sectiondoc@{match.start()}", ENGLISH, _nfc(body), source)
        doc.meta["lean_file"] = name
        out.append(doc)
    return out


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

    # 1. Verbatim is a property of a SPAN. Fenced blocks are lifted out and pinned by hash;
    #    what remains is the document's prose and is routed on its own merits. A file that is
    #    nothing but fenced blocks, or whose residue still reads as log/trace (no delimiter
    #    exists for those), is a whole artifact and is shelved as one — with its spans pinned.
    #    (A .lean file is code too, but it has its own elaboration route below.)
    pinned: tuple[str, ...] = ()
    if not is_lean_file:
        normalized, pinned = split_verbatim(normalized)
        if pinned and not normalized.strip():
            # It had fenced blocks and nothing else. An EMPTY document has no spans and is
            # not an artifact; it falls through to the shelf where it belongs.
            return RoutedDoc(name, VERBATIM, "entirely fenced/code — pinned, not extracted",
                             raw_hash, verbatim_spans=pinned)
        if _is_log_or_trace(normalized):
            return RoutedDoc(name, VERBATIM,
                             "log/trace — pinned, not extracted (no span delimiter exists)",
                             raw_hash, verbatim_spans=pinned)

    # 2/3. Lean is keyed on the .lean extension (per the spec). A prose file that merely
    #      mentions "lemma" is prose, not Lean — the content heuristic false-fired on
    #      table headers, so routing to Lean is extension-only.
    if is_lean_file:
        # GATES sentence 3 governs GROUNDING, not chart ENTRY: "Only top-tier warrants
        # ground (clamp-eligible): Lean kernel-accept under pinned toolchain". A `.lean`
        # file therefore enters the Lean chart on the strength of being Lean, at extraction
        # tier, and elaboration decides only whether it may later CLAMP.
        #
        # This used to shelf every non-elaborating file, justified as "a Lean-chart slot
        # that was never kernel-checked would be a grounding claim the engine cannot back".
        # That conflated entry with grounding — `adapters/lean_corpus.py` had it right all
        # along ("refuses to emit clamps while D6 is unresolved, and emits documents only"),
        # and the Aristotle corpus proves it: 12,041 Lean slots at extraction tier, D6
        # unresolved, zero clamps. The one line cost 407 GitHub .lean files their chart.
        elaborates, reason = (lean_elaborates or _default_lean_elaborates)(normalized)
        document = Document(name, LEAN, normalized, source)
        companions = tuple(lean_docstrings(name, normalized, source))
        if elaborates:
            return RoutedDoc(name, LEAN, "elaborates; clamp-eligible", raw_hash, document,
                             companions=companions)
        return RoutedDoc(name, LEAN, f"extraction tier, NOT clamp-eligible: {reason}",
                         raw_hash, document, companions=companions)

    # 3.5. Speaker-attributed transcript -> conversation chart. Checked before tables/prose
    #      because a dialogue is neither, and its speaker turns are the segmentation unit.
    if _is_conversation(normalized):
        return RoutedDoc(name, CONVERSATION, "speaker-attributed transcript", raw_hash,
                         Document(name, CONVERSATION, normalized, source),
                         verbatim_spans=pinned)

    # 4/5. Markdown tables: well-formed -> tabular; malformed -> prose, tagged.
    shape = _table_shape(normalized)
    if shape == "well-formed":
        return RoutedDoc(name, TABULAR, "well-formed table", raw_hash,
                         Document(name, TABULAR, normalized, source), verbatim_spans=pinned)
    if shape == "malformed":
        prose, tokens = _tokenize_math(normalized)
        return RoutedDoc(name, ENGLISH, "malformed-table -> prose", raw_hash,
                         Document(name, ENGLISH, prose, source), tuple(tokens),
                         verbatim_spans=pinned)

    # 6. Prose -> English, with inline math preserved as opaque tokens.
    if normalized.strip():
        prose, tokens = _tokenize_math(normalized)
        return RoutedDoc(name, ENGLISH, "prose", raw_hash,
                         Document(name, ENGLISH, prose, source), tuple(tokens),
                         verbatim_spans=pinned)

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
