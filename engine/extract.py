"""k-extractor: documents -> typed, warranted, addressed candidate deltas.

Gate 3 is enforced by construction. `Extractor.extract()` is the only public entry point,
it is not overridden by any subclass, and it stamps `WarrantTier.EXTRACTION` on every
delta it builds. Subclasses supply spans via `_spans()` and never touch a `Warrant`, so
there is no code path by which extraction provenance could ground.

Two implementations:

- `DeterministicExtractor` — offline, rule-based, hash-seeded. This is what the null
  battery and every dry run use. It has no network dependency, so a run's addressing and
  settlement are reproducible from the seed hash without an API key.
- `AnthropicExtractor` — the real k=3 arm from D4. Refuses to construct unless live
  extraction is explicitly enabled *and* a spend cap is set, so leaving D4's spend cap
  blank keeps it off rather than defaulting it to unlimited.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from . import EngineError
from .constants import BVALUES
from .hashing import DRNG
from .normalize import address, classify
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
        if doc.chart == "lean":
            matches = list(_LEAN_DECL_RE.finditer(doc.text))
            out: list[tuple[str, str]] = []
            for i, m in enumerate(matches):
                end = matches[i + 1].start() if i + 1 < len(matches) else len(doc.text)
                chunk = doc.text[m.start() : end].strip()
                if chunk:
                    out.append((chunk, f"decl:{i}"))
            return out

        out = []
        for i, raw in enumerate(_SENTENCE_RE.split(doc.text)):
            span = raw.strip()
            if len(span.split()) >= 3:
                out.append((span, f"sent:{i}"))
        return out

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
        rng = DRNG("extract", self.extractor_id, self.prompt_id, doc.content_hash)
        for surface, locator in self._candidate_spans(doc):
            keep_draw = rng.random()
            jitter = rng.uniform(-0.12, 0.12)
            # Selectivity shifts which marginal spans each extractor keeps.
            if keep_draw < self.selectivity:
                continue
            lowered = surface.casefold()
            value, base = self._value_for(lowered)
            yield Span(
                surface=surface,
                type=classify(doc.chart, surface),
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


class AnthropicExtractor(Extractor):
    """The live k=3 arm. Off unless explicitly enabled with a spend cap (D4).

    Both conditions are required, and neither has a permissive default: an unset
    `COMMON_GROUND_ENABLE_LLM` keeps it off, and an unset spend cap keeps it off even if
    the flag is set. D4's spend cap being blank therefore blocks live extraction rather
    than silently meaning "no limit".
    """

    ENABLE_ENV = "COMMON_GROUND_ENABLE_LLM"

    def __init__(
        self,
        extractor_id: str,
        prompt_id: str,
        model: str,
        prompt_text: str,
        spend_cap_usd: float | None,
        max_tokens: int = 16000,
    ) -> None:
        if os.environ.get(self.ENABLE_ENV, "").strip().lower() not in {"1", "true", "yes", "on"}:
            raise EngineError(
                f"live extraction is off: set {self.ENABLE_ENV}=1 to enable it. "
                "The offline DeterministicExtractor is what P0-P2 and the null battery use."
            )
        if spend_cap_usd is None:
            raise EngineError(
                "D4 spend cap is unresolved. Live extraction refuses to run without an "
                "explicit cap; an unset cap is not an unlimited cap."
            )
        super().__init__(extractor_id, prompt_id)
        self.model = model
        self.prompt_text = prompt_text
        self.spend_cap_usd = float(spend_cap_usd)
        self.max_tokens = max_tokens
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic  # imported lazily so the offline path needs no SDK
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise EngineError(
                    "the anthropic SDK is not installed; live extraction is unavailable"
                ) from exc
            self._client = anthropic.Anthropic()
        return self._client

    def _spans(self, doc: Document) -> Iterable[Span]:
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.prompt_text,
            output_config={"format": {"type": "json_schema", "schema": _EXTRACTION_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    # The document's *identity* is deliberately not in the prompt. A
                    # doc_id here would let the model's reading depend on what the file
                    # was called, so the same text under two labels could extract
                    # differently — the live-path form of the defect the offline seeding
                    # carried. Identity labels evidence in `Provenance`; it never reaches
                    # anything that generates.
                    "content": (
                        f"chart: {doc.chart}\ncontent: {doc.content_hash[:16]}"
                        f"\n\n---\n{doc.text}"
                    ),
                }
            ],
        )
        if response.stop_reason == "refusal":
            raise EngineError(
                f"extraction refused for doc {doc.doc_id}; the run's k-coverage is "
                "incomplete and the result must not be treated as a full extraction"
            )
        text = next((b.text for b in response.content if b.type == "text"), "")
        payload = json.loads(text)
        for i, claim in enumerate(payload.get("claims", [])):
            yield Span(
                surface=claim["surface"],
                type=claim["type"],
                value=claim["value"],
                confidence=float(claim["confidence"]),
                locator=claim.get("locator") or f"claim:{i}",
            )


def build_k_extractors(decisions: dict, offline: bool = True) -> list[Extractor]:
    """Construct the k=3 bank described by D4.

    Offline is the default everywhere in P0-P2. The three offline extractors are given
    distinct ids and distinct selectivity so that they disagree the way three real
    (model, prompt) pairs would, rather than agreeing trivially.
    """
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

    from .constants import SEED_DIR

    cap = decisions.get("D4", {}).get("spend_cap_usd")
    out: list[Extractor] = []
    for spec in specs:
        prompt_path = SEED_DIR / "PROMPTS" / f"{spec['prompt']}.md"
        out.append(
            AnthropicExtractor(
                extractor_id=spec["id"],
                prompt_id=spec["prompt"],
                model=spec["model"],
                prompt_text=prompt_path.read_text(encoding="utf-8"),
                spend_cap_usd=cap,
            )
        )
    return out


def slots_from_deltas(deltas: Sequence[Delta]):
    """Distinct slots referenced by a delta set, as Slot objects."""
    from .types import Slot

    seen: dict[str, Slot] = {}
    for d in deltas:
        if d.slot not in seen:
            seen[d.slot] = Slot(id=d.slot, nu=d.nu, type=d.type, chart=d.chart)
    return [seen[k] for k in sorted(seen)]
