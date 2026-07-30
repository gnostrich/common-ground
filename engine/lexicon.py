"""The lexicon registry: one hub, per-chart faces.

## The hub invariant, as a type boundary

`SenseCore` is the F-visible projection of a sense. It carries `english_slot` — the
*hash*, which is the address — and **has no `english_face` field at all**. The strings
live on `SenseDisplay`, which nothing on an F path can reach.

That is the difference between a convention and a gate. "Don't read the gloss" is a
convention; "the gloss is not a field of the object F sees" is enforceable, and null cell
(viii) enforces it with a static AST check over the F-path modules.

    SenseCore     english_slot, type_sig, frames, formal_faces, synonym_edges,
                  source, source_beta        -> may enter F
    SenseDisplay  english_face, gloss, notes, face_warrant
                                             -> display only, never enters F

## Sense selection

By typed context — frames and slot neighbourhood — per SPEC §2. Deliberately **not** by
gloss text: that would route authority back through the hub. When the context does not
decide, `select_sense` returns an honest fiber including `abstain` rather than picking.
A coin flip here is a seed bug.

## Merging

Never at import time. `merge_senses` raises: merging is plastic and mint-gated, and mint
is OFF at v0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal, Mapping, Sequence

from . import EngineError, GateViolation
from .constants import (
    FRAME_CUES,
    SELECT_MARGIN,
    SELECT_W_FRAME,
    SELECT_W_LEMMA,
    SELECT_W_NEIGHBOUR,
    SELECT_W_SOURCE_BETA,
    SELECT_W_TYPE,
    SOURCE_BETA,
    SOURCE_ORDER,
)
from .hashing import canonical_json, hash_obj, join_hash
from .normalize import address, nu
from .types import Chart, QEdge

FaceWarrant = Literal["authored", "rendered"]

_TOKEN = re.compile(r"[^0-9A-Za-z]+")


# --- faces --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Face:
    """A surface in one chart. `surface` is stored VERBATIM — never normalized.

    Mathlib names keep their case and their namespace path (SPEC §3). Normalization
    happens downstream in `nu`, at addressing time, and does not write back here.
    """

    chart: Chart
    surface: str
    kind: Literal["formal", "english"]

    def as_record(self) -> dict[str, object]:
        return {"chart": self.chart, "surface": self.surface, "kind": self.kind}


@dataclass(frozen=True, slots=True)
class SynonymEdge:
    """An equivalence prior between senses. Enters F as energy only (gate 2)."""

    from_sense: str
    to_sense: str
    weight: float
    source: str

    def as_record(self) -> dict[str, object]:
        return {
            "from_sense": self.from_sense,
            "to_sense": self.to_sense,
            "weight": self.weight,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class Bridge:
    """A declared relation between senses, checkable where formal.

    `status="checkable"` carries a Lean statement that a kernel receipt could ground.
    `status="declared-none"` records that two senses share a name and nothing else — that
    the absence of a bridge is itself the content, so nobody later infers one.
    """

    from_sense: str
    to_sense: str
    statement: str
    chart: Chart
    status: Literal["checkable", "declared", "declared-none"]
    formal: str | None = None


# --- the two halves of a sense ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SenseCore:
    """F-visible projection. NOTE: no `english_face`, no `gloss` — by construction."""

    sense_id: str
    lemma: str
    english_slot: str  # hash of the English face. The address, not the string.
    type_sig: str | None
    frames: tuple[str, ...]
    formal_faces: tuple[Face, ...]
    synonym_edges: tuple[SynonymEdge, ...]
    source: str
    source_beta: float

    def as_record(self) -> dict[str, object]:
        return {
            "sense_id": self.sense_id,
            "lemma": self.lemma,
            "english_slot": self.english_slot,
            "type_sig": self.type_sig,
            "frames": list(self.frames),
            "formal_faces": [f.as_record() for f in self.formal_faces],
            "synonym_edges": [e.as_record() for e in self.synonym_edges],
            "source": self.source,
            "source_beta": self.source_beta,
        }


@dataclass(frozen=True, slots=True)
class SenseDisplay:
    """Display only. Never enters F. Null cell (viii) checks nothing on an F path reads this."""

    english_face: str
    gloss: str = ""
    notes: str = ""
    face_warrant: FaceWarrant = "authored"

    def as_record(self) -> dict[str, object]:
        return {
            "english_face": self.english_face,
            "gloss": self.gloss,
            "notes": self.notes,
            "face_warrant": self.face_warrant,
        }


@dataclass(frozen=True, slots=True)
class Sense:
    core: SenseCore
    display: SenseDisplay

    @property
    def sense_id(self) -> str:
        return self.core.sense_id

    def as_record(self) -> dict[str, object]:
        return {"core": self.core.as_record(), "display": self.display.as_record()}


@dataclass(frozen=True, slots=True)
class Entry:
    entry_id: str
    lemma: str
    senses: tuple[Sense, ...]

    def as_record(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "lemma": self.lemma,
            "senses": [s.as_record() for s in sorted(self.senses, key=lambda x: x.sense_id)],
        }


# --- keys ---------------------------------------------------------------------------


def sense_key(lemma: str, type_sig: str | None, source: str, primary_formal: str = "") -> str:
    """Senses are keyed by (lemma, type_sig, source) plus the primary formal face.

    SPEC §2: never merge by string. Two imports contributing the same lemma produce two
    senses because their keys differ, and the key includes the primary formal face so
    that two Mathlib names sharing a type signature stay distinct too.
    """
    return join_hash("sense", lemma, type_sig or "", source, primary_formal)[:24]


def make_sense(
    lemma: str,
    english_face: str,
    *,
    source: str,
    type_sig: str | None = None,
    frames: Sequence[str] = (),
    formal_faces: Sequence[Face] = (),
    synonym_edges: Sequence[SynonymEdge] = (),
    gloss: str = "",
    notes: str = "",
    face_warrant: FaceWarrant = "authored",
    sense_id: str | None = None,
) -> Sense:
    """Build a sense. The English face is mandatory — SPEC §0a, enforced here."""
    if not english_face.strip():
        raise GateViolation(
            1,
            f"sense for lemma {lemma!r} from {source!r} has no English face. No entry may "
            "exist only in a formal chart; generate one with engine/rmap.py and mark it "
            "face_warrant='rendered'.",
        )
    if source not in SOURCE_BETA:
        raise EngineError(f"unknown lexicon source {source!r}; expected one of {SOURCE_ORDER}")

    slot, _ = address("english", english_face, "define")
    primary = formal_faces[0].surface if formal_faces else ""
    core = SenseCore(
        sense_id=sense_id or sense_key(lemma, type_sig, source, primary),
        lemma=lemma,
        english_slot=slot,
        type_sig=type_sig,
        frames=tuple(sorted(set(frames))),
        formal_faces=tuple(formal_faces),
        synonym_edges=tuple(synonym_edges),
        source=source,
        source_beta=SOURCE_BETA[source],
    )
    return Sense(core=core, display=SenseDisplay(english_face, gloss, notes, face_warrant))


# --- registry -----------------------------------------------------------------------


@dataclass(slots=True)
class Registry:
    """One registry. Per-chart faces. Canonically serializable, hence re-run identical."""

    entries: dict[str, Entry] = field(default_factory=dict)
    bridges: list[Bridge] = field(default_factory=list)
    import_log: list[dict[str, object]] = field(default_factory=list)

    # --- construction ---

    def add(self, sense: Sense) -> None:
        """Add a sense, never merging by string (SPEC §2)."""
        lemma = sense.core.lemma
        entry = self.entries.get(lemma)
        if entry is None:
            self.entries[lemma] = Entry(
                entry_id=join_hash("entry", lemma)[:16], lemma=lemma, senses=(sense,)
            )
            return
        if any(s.sense_id == sense.sense_id for s in entry.senses):
            return  # idempotent re-add of an identical sense
        self.entries[lemma] = Entry(
            entry_id=entry.entry_id, lemma=lemma, senses=entry.senses + (sense,)
        )

    # --- views ---

    @property
    def senses(self) -> list[Sense]:
        return [s for lemma in sorted(self.entries) for s in
                sorted(self.entries[lemma].senses, key=lambda x: x.sense_id)]

    def cores(self) -> list[SenseCore]:
        """The F-visible projection of the whole registry."""
        return [s.core for s in self.senses]

    def senses_for(self, lemma: str) -> list[Sense]:
        """Exact-entry lookup."""
        entry = self.entries.get(lemma)
        return sorted(entry.senses, key=lambda x: x.sense_id) if entry else []

    def lemma_index(self) -> dict[str, list[Sense]]:
        """Every sense indexed under every content token of its English face.

        An entry has one identity, but a lemma lookup should find every sense whose face
        contains that lemma — "integral kernel" has to be reachable from both `integral`
        and `kernel`, or the convention table's `kernel` split would never see it.
        """
        index: dict[str, list[Sense]] = {}
        for sense in self.senses:
            keys = set(tokens(sense.display.english_face)) | {sense.core.lemma}
            for key in keys:
                index.setdefault(key, []).append(sense)
        return index

    def candidates_for(self, lemma: str) -> list[SenseCore]:
        """F-visible candidates for a lemma, for `select_sense`."""
        return [s.core for s in self.lemma_index().get(lemma, [])]

    def by_english_slot(self) -> dict[str, list[SenseCore]]:
        index: dict[str, list[SenseCore]] = {}
        for core in self.cores():
            index.setdefault(core.english_slot, []).append(core)
        return index

    def bindings(self) -> dict[str, tuple[Face, ...]]:
        """english_slot -> formal faces. The round trip null cell (ix) exercises."""
        out: dict[str, list[Face]] = {}
        for core in self.cores():
            out.setdefault(core.english_slot, []).extend(core.formal_faces)
        return {k: tuple(v) for k, v in out.items()}

    def rendered_face_count(self) -> int:
        return sum(1 for s in self.senses if s.display.face_warrant == "rendered")

    # --- F-visible export ---

    def q_edges(self) -> list[QEdge]:
        """Synonym edges as equivalence priors, keyed on english_slot.

        Reads `core` only. Gate 2: these enter F as energy and can never clamp.
        """
        by_id = {c.sense_id: c for c in self.cores()}
        out: dict[tuple[str, str], QEdge] = {}
        for core in self.cores():
            for edge in core.synonym_edges:
                a, b = by_id.get(edge.from_sense), by_id.get(edge.to_sense)
                if a is None or b is None or a.english_slot == b.english_slot:
                    continue
                u, v = sorted((a.english_slot, b.english_slot))
                key = (u, v)
                prior = out.get(key)
                if prior is None or edge.weight > prior.weight:
                    out[key] = QEdge(u=u, v=v, weight=edge.weight, origin="lexicon")
        return [out[k] for k in sorted(out)]

    # --- serialization ---

    def as_record(self) -> dict[str, object]:
        return {
            "schema": "common-ground/registry/v0",
            "entries": [self.entries[k].as_record() for k in sorted(self.entries)],
            "bridges": [
                {
                    "from_sense": b.from_sense, "to_sense": b.to_sense,
                    "statement": b.statement, "chart": b.chart,
                    "status": b.status, "formal": b.formal,
                }
                for b in sorted(self.bridges, key=lambda x: (x.from_sense, x.to_sense))
            ],
            "import_log": self.import_log,
        }

    def serialize(self) -> str:
        """Canonical JSON. Re-run at the same pins is byte-identical (SPEC §3)."""
        return canonical_json(self.as_record())

    def digest(self) -> str:
        return hash_obj(self.as_record())

    def summary(self) -> dict[str, int]:
        by_source: dict[str, int] = {}
        for s in self.senses:
            by_source[s.core.source] = by_source.get(s.core.source, 0) + 1
        return {
            "entries": len(self.entries),
            "senses": len(self.senses),
            "bridges": len(self.bridges),
            "rendered_faces": self.rendered_face_count(),
            "q_edges": len(self.q_edges()),
            **{f"senses_{k}": v for k, v in sorted(by_source.items())},
        }


def merge_senses(*_args, **_kwargs) -> None:
    """Never at import time (SPEC §2). Plastic and mint-gated; mint is OFF at v0."""
    raise EngineError(
        "merging senses is a plastic, mint-gated operation driven by co-settlement "
        "evidence. It is never performed at import time, and mint is OFF at v0 "
        "(SEED.lock: mint_enabled=false). Two senses that look alike stay two senses."
    )


# --- frame inference and sense selection --------------------------------------------


def tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in _TOKEN.split(text.casefold()) if len(t) > 1)


def _compile_cues() -> dict[str, re.Pattern[str]]:
    """Word-boundary matchers, one per frame.

    Substring matching is wrong here and was a live bug: the `analysis` cue "norm" fired
    inside the word "normal", so "a perfectly normal Tuesday afternoon" was read as a
    passage about analysis. Boundaries are not a refinement, they are the difference
    between a cue table and a coincidence table.
    """
    out: dict[str, re.Pattern[str]] = {}
    for frame, cues in FRAME_CUES.items():
        if not cues:
            continue
        # `s?` before the closing boundary: prose says "closed sets" and
        # "neighbourhoods" where the cue is singular, and a boundary strict enough to
        # keep "norm" out of "normal" is also strict enough to keep "closed set" out of
        # "closed sets". Allowing exactly one trailing s buys back the plurals without
        # reopening the substring hole.
        out[frame] = re.compile(
            "|".join(rf"\b{re.escape(c)}s?\b" for c in sorted(cues, key=len, reverse=True))
        )
    return out


_CUE_PATTERNS = _compile_cues()


def infer_frames(text: str) -> frozenset[str]:
    """Frames a passage is speaking in, from the declared cue table.

    Cue phrases live in `seed/CONSTANTS.json` and are hashed into the lock. Returns
    `{"general"}` when nothing matches, which is the honest default: an absence of
    technical cues is evidence of a general context, not an absence of evidence.

    A cue must be *disambiguating*. The bare word being disambiguated is therefore never
    its own cue — "field" does not vote for `field_theory`, "ring" does not vote for
    `ring_theory` — because a term voting for its own technical reading would decide
    every probe in favour of the technical sense before any evidence was weighed.
    """
    low = text.casefold()
    hits = {frame for frame, pattern in _CUE_PATTERNS.items() if pattern.search(low)}
    return frozenset(hits) if hits else frozenset({"general"})


@dataclass(frozen=True, slots=True)
class SenseSelection:
    """Either a decision or an honest fiber. Never a coin flip."""

    lemma: str
    chosen: str | None
    fiber: tuple[str, ...]
    scores: tuple[tuple[str, float], ...]
    reason: str

    @property
    def decided(self) -> bool:
        return self.chosen is not None


ABSTAIN = "abstain"


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b) if inter else 0.0


def select_sense(
    lemma: str,
    candidates: Sequence[SenseCore],
    context_frames: Iterable[str],
    context_tokens: frozenset[str] = frozenset(),
    neighbour_slots: Iterable[str] = (),
) -> SenseSelection:
    """Choose a sense by typed context, or return a fiber including `abstain`.

    Scores from `frames`, `type_sig` tokens, slot-neighbourhood bindings, and a small
    `source_beta` prior — every input F-visible. **The gloss and the English face string
    are not read**, deliberately: selecting on them would route authority back through
    the hub, which is the thing the topology exists to prevent.

    The `source_beta` term is weighted so it can break a tie but cannot overturn frame
    evidence. That is what stops WordNet's general senses — imported last, and lowest
    beta — from shadowing a technical sense in a technical context (null cell vii).
    """
    if not candidates:
        return SenseSelection(lemma, None, (ABSTAIN,), (), "no candidate senses")

    frames = frozenset(context_frames)
    neighbours = frozenset(neighbour_slots)

    scored: list[tuple[str, float]] = []
    for core in candidates:
        score = SELECT_W_FRAME * _jaccard(frozenset(core.frames), frames)
        if core.type_sig:
            score += SELECT_W_TYPE * _jaccard(tokens(core.type_sig), context_tokens)
        if neighbours and core.english_slot in neighbours:
            score += SELECT_W_NEIGHBOUR
        # A sense whose lemma IS the queried word beats one that merely mentions it.
        # The lemma index is deliberately wide — "integral kernel" must be reachable
        # from both `integral` and `kernel` — and this is what keeps that width from
        # letting "degree of a field extension" outrank "field" for the word "field".
        if core.lemma == lemma:
            score += SELECT_W_LEMMA
        score += SELECT_W_SOURCE_BETA * core.source_beta
        scored.append((core.sense_id, score))

    scored.sort(key=lambda t: (-t[1], t[0]))

    if len(scored) == 1:
        return SenseSelection(lemma, scored[0][0], (scored[0][0],), tuple(scored), "sole candidate")

    top, second = scored[0], scored[1]
    if top[1] - second[1] >= SELECT_MARGIN:
        return SenseSelection(lemma, top[0], (top[0],), tuple(scored), "decided by typed context")

    return SenseSelection(
        lemma,
        None,
        (top[0], second[0], ABSTAIN),
        tuple(scored),
        f"undecidable from context: margin {top[1] - second[1]:.4f} < {SELECT_MARGIN}",
    )
