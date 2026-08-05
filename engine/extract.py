"""k-extractor: documents -> typed, warranted, addressed candidate deltas.

Gate 3 is enforced by construction. `Extractor.extract()` is the only public entry point,
it is not overridden by any subclass, and it stamps `WarrantTier.EXTRACTION` on every
delta it builds. Subclasses supply spans via `_spans()` and never touch a `Warrant`, so
there is no code path by which extraction provenance could ground.

Two implementations:

- `DeterministicExtractor` — offline, rule-based, hash-seeded. This is what the null
  battery and every dry run use. It has no network dependency, so a run's addressing and
  settlement are reproducible from the seed hash without an API key.
  extraction is explicitly enabled *and* a spend cap is set, so leaving D4's spend cap
  blank keeps it off rather than defaulting it to unlimited.
"""

from __future__ import annotations

import ast

import json
import os
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from . import EngineError
from .constants import BVALUES
from .hashing import DRNG
from .charts import chart_spec
from .normalize import address, classify, nu
from .types import BValue, ClaimForm, Delta, Document, Provenance, Warrant, WarrantTier

#: A span as produced by a concrete extractor. The warrant is deliberately absent.
@dataclass(frozen=True, slots=True)
class Span:
    surface: str
    type: ClaimForm
    value: BValue
    confidence: float
    locator: str


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_LEAN_DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+|nonrec\s+|scoped\s+|local\s+)*"
    r"(?:theorem|lemma|example|axiom|def|abbrev|structure|class|instance|inductive|notation)\b",
    re.MULTILINE,
)

def _segment_prose(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i, raw in enumerate(_SENTENCE_RE.split(text)):
        span = raw.strip()
        if len(span.split()) >= 3:
            out.append((span, f"sent:{i}"))
    return out


def _segment_lean(text: str) -> list[tuple[str, str]]:
    """One span per declaration, locator `<head>:<name>` — the NAME, not the position.

    This used to emit `decl:<i>`, an ordinal. That made the Lean chart the only code chart
    whose declaration name had to be re-derived downstream (`holes_by_declaration` called
    `faces.declarations` on the surface to get it back), which is why hole enumeration could
    only ever be written for Lean. Python and Go already reported `def:name` / `func:Name`.
    All three now report the same shape, so a declaration key is readable from provenance in
    exactly one way for every code chart.

    The locator is provenance — a fact about where the claim was found — not part of the
    address (gate 1) and not an input to any key (gate 7), so no slot id moves.
    """
    from .faces import declarations

    matches = list(_LEAN_DECL_RE.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.start():end].strip()
        if not chunk:
            continue
        named = next(iter(declarations(chunk)), None)
        out.append((chunk, f"{named[0]}:{named[1]}" if named else f"decl:{i}"))
    return out


def _segment_tabular(text: str) -> list[tuple[str, str]]:
    """One candidate span per data row. Alignment rows and the header are skipped.

    A markdown table's first non-separator row is its header — column names, not a claim —
    so it is dropped; every subsequent row is a candidate. The raw row text is the span, so
    nu-for-tabular canonicalizes it downstream and raw bytes stay the provenance target.
    """
    rows = [ln for ln in re.split(r"[\r\n]+", text) if ln.strip()]
    data_rows = [r for r in rows if not _TABLE_SEP_ROW_RE.match(r)]
    out: list[tuple[str, str]] = []
    for i, raw in enumerate(data_rows[1:], start=1):   # [1:] drops the header row
        span = raw.strip()
        if span:
            out.append((span, f"row:{i}"))
    return out


def _segment_conversation(text: str) -> list[tuple[str, str]]:
    """One candidate span per speaker-attributed claim; the speaker rides in the locator.

    Delegates to the conversation module's transcript parser (which has no engine deps, so
    importing it here makes no cycle). This is the third leg of the plug-in seam for the
    `conversation` behavior — no dispatch edit, just a registered segmenter.
    """
    from .conversation import segment_conversation

    return segment_conversation(text)



#: A Go top-level declaration head. `func (r *T) M(...)` is a method; the receiver type is
#: part of the name, because `T.M` and `U.M` are different declarations.
_GO_DECL_RE = re.compile(
    r"^(?:func\s+(?:\(\s*\w+\s+\*?(?P<recv>\w+)\s*\)\s*)?(?P<fn>\w+)"
    r"|type\s+(?P<ty>\w+)"
    r"|(?:const|var)\s+(?P<cv>\w+))",
    re.MULTILINE)


def _segment_go(text: str) -> list[tuple[str, str]]:
    """One candidate span per top-level declaration, head to the next head.

    Go's own parser is not available here — the engine is stdlib-only and shelling out to
    `go` would make segmentation depend on a toolchain being installed, the same objection
    `_nu_go` records. So this segments the way `_segment_lean` does: on declaration heads at
    column zero, which Go's formatting guarantees for top-level declarations because gofmt
    puts them there. Nested closures are not spanned separately, the same simplification
    `_segment_lean` makes for a Lean declaration's internal `have`s.

    A method's locator carries its receiver (`func:T.M`), because `T.M` and `U.M` are
    different declarations and a locator that conflated them would attribute one's evidence
    to the other.
    """
    heads = [m for m in _GO_DECL_RE.finditer(text) if m.start() == 0 or text[m.start() - 1] == "\n"]
    out: list[tuple[str, str]] = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        span = text[m.start():end].strip()
        if not span:
            continue
        if m.group("fn"):
            name = f"{m.group('recv')}.{m.group('fn')}" if m.group("recv") else m.group("fn")
            kind = "func"
        elif m.group("ty"):
            name, kind = m.group("ty"), "type"
        else:
            name, kind = m.group("cv"), "const"
        out.append((span, f"{kind}:{name}"))
    return out


#: Per-chart span segmenters, keyed by the manifest's behavior id — the third leg of the
#: chart plug-in seam (normalizer and classifier are the other two, in engine/normalize.py).
def _segment_python(text: str) -> list[tuple[str, str]]:
    """One candidate span per top-level `def`/`class` and per method inside a class.

    Uses the real `ast` module — unlike `_nu_python`, this runs on a whole document that
    is a real file on disk (or, in a test, a deliberately-valid fixture), so a parse
    failure is a genuine malformed-source signal rather than adversarial fuzz. `ast.parse`
    is wrapped rather than left to raise: a corpus file with a syntax error yields zero
    candidate spans instead of crashing the extractor, which is the totality gate 1's
    idempotence check assumes of every stage downstream of `nu`.

    Granularity mirrors `_segment_lean`'s flat per-declaration spans: module-level
    functions/classes and one level of method inside a class, no deeper nesting (a nested
    closure is not spanned separately, same simplification `_segment_lean` makes for a
    Lean declaration's internal `have`s).
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []

    # `ast.get_source_segment` splits the WHOLE file into lines on every call, so a module
    # with n declarations costs O(n * len(text)). On the operator's repositories that made
    # ingest of 1,405 Python files take longer than the entire rest of the corpus. The line
    # table is built once here and sliced; the spans are byte-identical.
    lines = text.splitlines(keepends=True)

    def segment(node: ast.AST) -> str:
        lo = getattr(node, "lineno", 0)
        hi = getattr(node, "end_lineno", lo)
        if not lo:
            return ""
        return "".join(lines[lo - 1:hi]).strip()

    out: list[tuple[str, str]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qual = f"{prefix}.{child.name}" if prefix else child.name
                span = segment(child)
                if span:
                    kind = "class" if isinstance(child, ast.ClassDef) else "def"
                    out.append((span, f"{kind}:{qual}"))
                if isinstance(child, ast.ClassDef):
                    walk(child, qual)   # one level: methods, not nested closures

    walk(tree, "")
    return out


def _segment_correspondence(text: str) -> list[tuple[str, str]]:
    """One candidate span per correspondence claim — one arrow per line, whole and unsplit.

    A correspondence surface is atomic: splitting it would address half an arrow.
    """
    out: list[tuple[str, str]] = []
    for i, raw in enumerate(text.splitlines()):
        span = raw.strip()
        if span:
            out.append((span, f"arrow:{i}"))
    return out


_SEGMENTERS: dict[str, "Callable[[str], list[tuple[str, str]]]"] = {
    "prose": _segment_prose,
    "lean": _segment_lean,
    "tabular": _segment_tabular,
    "conversation": _segment_conversation,
    "correspondence": _segment_correspondence,
    "python": _segment_python,
    "go": _segment_go,
}

_TABLE_SEP_ROW_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")

_NEGATION = ("is not", "are not", "does not", "do not", "cannot", "never", "no ", "fails to")
_HEDGE = ("may ", "might ", "possibly", "we believe", "appears to", "conjecture", "unclear", "open question")
_CONTESTED = ("however", "on the other hand", "but also", "contested", "disputed", "we do not claim")


class Extractor:
    """Base class. `extract()` is final; subclasses implement `_spans()`."""

    def __init__(self, extractor_id: str, prompt_id: str) -> None:
        self.extractor_id = extractor_id
        self.prompt_id = prompt_id

    def _spans(self, doc: Document) -> Iterable[Span]:  # pragma: no cover - abstract
        raise NotImplementedError

    def extract(self, doc: Document) -> list[Delta]:
        """Build deltas from spans. Gate 3: the tier is stamped here and nowhere else."""
        warrant = Warrant(
            tier=WarrantTier.EXTRACTION,
            detail=f"extractor={self.extractor_id};prompt={self.prompt_id}",
        )
        out: list[Delta] = []
        for span in self._spans(doc):
            if span.value not in BVALUES:
                raise EngineError(f"extractor {self.extractor_id} emitted b-value {span.value!r}")
            slot, nu_value = address(doc.chart, span.surface, span.type)
            out.append(
                Delta(
                    slot=slot,
                    chart=doc.chart,
                    type=span.type,
                    value=span.value,
                    confidence=max(0.0, min(1.0, span.confidence)),
                    warrant=warrant,
                    provenance=Provenance(
                        source=doc.source,
                        doc_id=doc.doc_id,
                        locator=span.locator,
                        extractor_id=self.extractor_id,
                        content_hash=doc.content_hash,
                    ),
                    surface=span.surface,
                    nu=nu_value,
                )
            )
        return out


class DeterministicExtractor(Extractor):
    """Offline, rule-based, hash-seeded.

    The per-extractor RNG stream is what makes k=3 informative offline: three extractors
    with different ids draw different confidence jitter and different inclusion
    thresholds, so their disagreement is real variance rather than three copies of one
    reading. Null cell (iv) measures exactly that variance and voids the run if it is too
    large at this corpus scale.
    """

    def __init__(self, extractor_id: str, prompt_id: str, selectivity: float = 0.0) -> None:
        super().__init__(extractor_id, prompt_id)
        self.selectivity = selectivity

    def _candidate_spans(self, doc: Document) -> list[tuple[str, str]]:
        return _SEGMENTERS[chart_spec(doc.chart).behavior](doc.text)

    def _value_for(self, lowered: str) -> tuple[BValue, float]:
        if any(m in lowered for m in _CONTESTED):
            return "B", 0.55
        if any(m in lowered for m in _HEDGE):
            return "N", 0.5
        if any(m in lowered for m in _NEGATION):
            return "F", 0.7
        return "T", 0.8

    def _spans(self, doc: Document) -> Iterable[Span]:
        # Seeded on CONTENT, never on identity. Keying the inclusion draw to `doc.doc_id`
        # made extraction a function of what a document was *called*: the same text
        # re-ingested under a second provenance label drew a different sample and produced
        # deltas the original never did, which no deduplication can collapse. KICKOFF
        # section 4 requires re-ingestion to leave zero cold residue, and null cell (v)
        # correctly failed until this changed.
        #
        # The per-extractor stream that makes k=3 informative is untouched: `extractor_id`
        # and `prompt_id` still separate the three readers. What is removed is the one
        # component that let a label change what was read.
        for surface, locator in self._candidate_spans(doc):
            # GATES sentence 8: every slot-attributed property is computed over the slot's
            # ADDRESS SPAN. The stream is therefore keyed on the slot address — the hash of
            # (nu, type) — not on the whole document.
            #
            # Seeding on `doc.content_hash` and drawing in document order was UNFAITHFUL
            # SUBSTITUTION #3: editing a comment, or a DIFFERENT declaration, moved a slot's
            # confidence (measured 0.91832 -> 0.91440 on a byte-identical claim), and
            # inserting one declaration shifted every subsequent slot's draw. That is variance
            # driven by document COMPOSITION, which was never extractor noise. The k=3
            # ensemble's disagreement is preserved: `extractor_id` and `prompt_id` still
            # separate the three readers, so what dies is composition-variance only.
            span_type = classify(doc.chart, surface)
            slot_address, address_span = address(doc.chart, surface, span_type)
            rng = DRNG("extract", self.extractor_id, self.prompt_id, slot_address)
            keep_draw = rng.random()
            jitter = rng.uniform(-0.12, 0.12)
            # Selectivity shifts which marginal spans each extractor keeps.
            if keep_draw < self.selectivity:
                continue
            # The b-value is valued over `nu(chart, surface)` — the same normalized span
            # `classify` uses — so that valuation and addressing cannot disagree. Valuing the
            # raw segment was UNFAITHFUL SUBSTITUTION #2: the Lean segmenter runs a span from
            # one declaration head to the next, so proof bodies and trailing docstrings (often
            # prose about the NEXT declaration) reached the value. A stray "no "/"does not"/
            # "might" in a comment flipped a theorem to F/N and manufactured contest against
            # the identical statement in another file — 52 of 59 observed contests were
            # exactly this. The claim's truth-value must be a function of the claim's
            # identity, and the address span is that identity.
            value, base = self._value_for(address_span.casefold())
            yield Span(
                surface=surface,
                type=span_type,
                value=value,
                confidence=max(0.05, min(1.0, base + jitter)),
                locator=locator,
            )


_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "surface": {"type": "string"},
                    "type": {"type": "string", "enum": list(("assert", "define", "conditional", "normative"))},
                    "value": {"type": "string", "enum": list(BVALUES)},
                    "confidence": {"type": "number"},
                    "locator": {"type": "string"},
                },
                "required": ["surface", "type", "value", "confidence", "locator"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}


def build_k_extractors(decisions: dict, offline: bool = True) -> list[Extractor]:
    """Construct the k=3 bank described by D4. Deterministic extractors, always.

    `offline` is kept in the signature because every caller passes it explicitly and a
    silent signature change is the kind of thing that reads as working until it doesn't.
    It no longer selects anything: the live arm was an `AnthropicExtractor` and it is
    DELETED, not disabled. The operator's rule is that every LM call the engine makes goes
    through OpenRouter, and a dormant second provider in the extractor bank is a rule
    enforced by nobody calling it — which stops being true after one edit.

    Live LM extraction, when it returns, goes through `ui/lm.py:LMProposer`, which is the
    OpenRouter path and refuses a non-`sk-or-` key outright.
    """
    if not offline:
        raise EngineError(
            "live extraction was an Anthropic path and has been deleted. Every LM call "
            "goes through OpenRouter (ui/lm.py:LMProposer); there is no second provider."
        )
    specs = decisions.get("D4", {}).get("extractors", [])
    if not specs:
        raise EngineError("D4 declares no extractors")

    if offline:
        return [
            DeterministicExtractor(
                extractor_id=spec["id"],
                prompt_id=spec["prompt"],
                selectivity=0.05 * i,
            )
            for i, spec in enumerate(specs)
        ]



def slots_from_deltas(deltas: Sequence[Delta]):
    """Distinct slots referenced by a delta set, as Slot objects."""
    from .types import Slot

    seen: dict[str, Slot] = {}
    for d in deltas:
        if d.slot not in seen:
            seen[d.slot] = Slot(id=d.slot, nu=d.nu, type=d.type, chart=d.chart)
    return [seen[k] for k in sorted(seen)]
