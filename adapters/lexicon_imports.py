"""The five lexicon imports, in the order the SPEC fixes.

    1. Mathlib dump        (pinned commit)   pre-bound: formal face + gloss together
    2. Convention table    (file hash)       pre-fibered sense-splits + bridges
    3. nLab alias scrape   (scrape date)     synonym edges and aliases, NOT authority
    4. Repo pre-minted     (D5 file hashes)  domain senses, by authorship provenance
    5. WordNet general     (version)         LAST, gap-fill

Order matters: later imports must not shadow earlier ones. `import_all` runs them in
`SOURCE_ORDER` and refuses any other sequence, so the ordering is a property of the code
rather than of the caller remembering.

An unresolved pin does not fake a result. The importer records the source as BLOCKED and
moves on, and null cell (vi) reports the coverage that produces.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine import EngineError
from engine.constants import SOURCE_BETA, SOURCE_ORDER, convention_table
from engine.hashing import sha256_text
from engine.seed_lock import IMPORTER_SCRIPT_FILES, importer_script_hash  # noqa: F401  (re-exported for callers)
from engine.lexicon import (
    Bridge,
    Face,
    Registry,
    Sense,
    SynonymEdge,
    make_sense,
    tokens,
)
from engine.rmap import render_batch, segments
from engine.types import Document

#: Leading function words dropped when deriving a lemma from a rendered face.
_LEMMA_SKIP = {"is", "has", "the", "a", "an", "of", "to", "in", "on", "for", "non", "not"}

_LEAN_DECL = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+|nonrec\s+|scoped\s+|local\s+)*"
    r"(?:theorem|lemma|def|abbrev|structure|class|instance|inductive)\s+([^\s:({\[]+)\s*(.*)$",
    re.MULTILINE,
)


@dataclass(slots=True)
class ImportResult:
    source: str
    status: str  # "imported" | "blocked"
    added: int = 0
    edges: int = 0
    bridges: int = 0
    pin: str | None = None
    detail: str = ""
    stats: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "source": self.source, "status": self.status, "added": self.added,
            "edges": self.edges, "bridges": self.bridges, "pin": self.pin,
            "detail": self.detail, "stats": self.stats,
        }


def lemma_of(english_face: str) -> str:
    """Primary lemma of a rendered face: first content token that is not a function word."""
    toks = [t for t in re.split(r"[^0-9A-Za-z]+", english_face.casefold()) if t]
    for tok in toks:
        if tok not in _LEMMA_SKIP and len(tok) > 1:
            return tok
    return toks[0] if toks else english_face.casefold()


# --- 1. Mathlib -------------------------------------------------------------------


def import_mathlib(registry: Registry, dump_path: str | Path | None, commit: str | None) -> ImportResult:
    """Names + type signatures + docstrings + namespace-as-taxonomy.

    These arrive **pre-bound** — the formal face and its gloss come together — which makes
    them the highest-quality entries, so they are imported first and own their addresses.

    Faces are rendered in one batch by `rmap.render_batch`, which sorts first, so the
    rendering depends on the *set* of declarations and not on directory walk order. That
    is what makes a re-run byte-identical (SPEC §3).
    """
    if dump_path is None or commit is None:
        return ImportResult(
            "mathlib", "blocked",
            detail="D8 unresolved: no pinned Mathlib dump path and commit. "
                   "KICKOFF §7.5 forbids a live pull during a run; only a pinned dump hashes cleanly.",
        )

    path = Path(dump_path)
    if not path.exists():
        raise EngineError(f"mathlib dump not found: {path}")

    decls = _read_mathlib(path)
    faces = render_batch([d["name"] for d in decls])

    added = 0
    for decl in sorted(decls, key=lambda d: d["name"]):
        name = decl["name"]
        face = faces[name]
        registry.add(
            make_sense(
                lemma=lemma_of(face),
                english_face=face,
                source="mathlib",
                type_sig=decl.get("type"),
                # namespace-as-taxonomy: the path segments are the frames.
                frames=[s.casefold() for s in segments(name)[:-1]] or ["mathlib"],
                formal_faces=[Face(chart="lean", surface=name, kind="formal")],
                gloss=decl.get("doc", ""),
                # A docstring is an authored gloss; the FACE is still rendered by us.
                face_warrant="rendered",
            )
        )
        added += 1

    return ImportResult("mathlib", "imported", added=added, pin=commit,
                        detail=f"{added} declarations at commit {commit[:12]}")


def _read_mathlib(path: Path) -> list[dict[str, Any]]:
    """Accept a JSON dump, or a directory of .lean files as a fallback."""
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return list(payload.get("declarations", []))

    out: list[dict[str, Any]] = []
    for lean in sorted(path.rglob("*.lean")):
        namespace = ".".join(lean.relative_to(path).with_suffix("").parts)
        text = lean.read_text(encoding="utf-8", errors="replace")
        for match in _LEAN_DECL.finditer(text):
            short, rest = match.group(1), match.group(2).strip()
            out.append({
                "name": f"{namespace}.{short}",
                "type": rest.split(":=")[0].strip() or None,
                "doc": "",
            })
    return out


# --- 2. Convention table ----------------------------------------------------------


def import_convention_table(registry: Registry, table: Mapping[str, Any] | None = None) -> ImportResult:
    """Hand-seeded polysemy pathologies as PRE-FIBERED sense-splits, with declared bridges.

    Lands before any corpus ingestion, so the splits are in place the first time a
    document mentions "compact" and there is never a window in which one undifferentiated
    sense absorbs both readings.

    A `formal_faces` entry here is a *candidate* Mathlib binding. It is kept only if the
    Mathlib import already produced that name; otherwise it is dropped and counted, rather
    than inventing a binding that no dump backs.
    """
    data = dict(table or convention_table())
    known_formal = {
        f.surface for core in registry.cores() for f in core.formal_faces
    }
    known_short = {s.split(".")[-1]: s for s in known_formal}

    added = 0
    dropped: list[str] = []
    id_map: dict[str, str] = {}

    for entry in data.get("entries", []):
        lemma = entry["lemma"]
        for sense in entry.get("senses", []):
            faces: list[Face] = []
            for candidate in sense.get("formal_faces", []):
                resolved = candidate if candidate in known_formal else known_short.get(candidate)
                if resolved:
                    faces.append(Face(chart="lean", surface=resolved, kind="formal"))
                else:
                    dropped.append(candidate)
            # The table labels each sense with the tier it actually belongs to. A
            # hand-seeded *general-English* sense is still general English — importing
            # it at convention tier would give it convention-tier authority and make it
            # invisible to the shadowing check in null cell (vii), which asks precisely
            # whether a general sense ever wins a technical context.
            declared = sense.get("source_beta", "convention")
            built = make_sense(
                lemma=lemma,
                english_face=sense["english_face"],
                source=declared if declared in SOURCE_BETA else "convention",
                type_sig=sense.get("type_sig"),
                frames=sense.get("frames", []),
                formal_faces=faces,
                gloss=sense.get("gloss", ""),
                face_warrant="authored",
                sense_id=sense["sense_id"],
            )
            registry.add(built)
            id_map[sense["sense_id"]] = built.sense_id
            added += 1

    bridges = 0
    for entry in data.get("entries", []):
        for bridge in entry.get("bridges", []):
            registry.bridges.append(
                Bridge(
                    from_sense=id_map.get(bridge["from"], bridge["from"]),
                    to_sense=id_map.get(bridge["to"], bridge["to"]),
                    statement=bridge["statement"],
                    chart=bridge.get("chart", "english"),
                    status=bridge.get("status", "declared"),
                    formal=bridge.get("formal"),
                )
            )
            bridges += 1

    pin = sha256_text(json.dumps(data, sort_keys=True, ensure_ascii=False))
    return ImportResult(
        "convention", "imported", added=added, bridges=bridges, pin=pin,
        detail=f"{added} senses, {bridges} bridges, "
               f"{len(dropped)} unresolved formal-face candidates dropped",
        stats={"status": data.get("status", ""), "dropped_formal_candidates": sorted(set(dropped))},
    )


# --- 3. nLab ----------------------------------------------------------------------


def import_nlab(registry: Registry, scrape_path: str | Path | None, scrape_date: str | None) -> ImportResult:
    """Aliases and redirects as synonym edges, at curated-tier source_beta.

    nLab glosses are perspectival, so this imports **edges and aliases, not authority**:
    no gloss from this source is ever attached as a sense's authoritative reading. An
    alias that resolves to nothing already in the registry gets a minimal English-only
    sense so it is at least addressable — coverage without authority.
    """
    if scrape_path is None or scrape_date is None:
        return ImportResult(
            "nlab", "blocked",
            detail="D8 unresolved: no pinned nLab scrape path and date.",
        )

    path = Path(scrape_path)
    if not path.exists():
        raise EngineError(f"nLab scrape not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    index = registry.lemma_index()

    added = 0
    edges = 0
    for group in sorted(payload.get("aliases", []), key=lambda g: g.get("canonical", "")):
        canonical = group.get("canonical", "")
        names = [canonical, *group.get("aliases", [])]
        resolved: list[str] = []

        for name in names:
            hits = index.get(lemma_of(name), [])
            match = next(
                (s for s in hits if s.display.english_face.casefold() == name.casefold()), None
            )
            if match is not None:
                resolved.append(match.sense_id)
                continue
            built = make_sense(
                lemma=lemma_of(name),
                english_face=name,
                source="nlab",
                frames=group.get("frames", ["general"]),
                gloss="",  # deliberately empty: nLab contributes no authority
                notes=f"nLab alias of {canonical!r}",
                face_warrant="authored",
            )
            registry.add(built)
            index = registry.lemma_index()
            resolved.append(built.sense_id)
            added += 1

        for i in range(len(resolved)):
            for j in range(i + 1, len(resolved)):
                _attach_edge(registry, resolved[i], resolved[j], 0.8, "nlab")
                edges += 1

    return ImportResult("nlab", "imported", added=added, edges=edges, pin=scrape_date,
                        detail=f"{added} alias senses, {edges} synonym edges @ {scrape_date}")


def _attach_edge(registry: Registry, a: str, b: str, weight: float, source: str) -> None:
    """Attach a synonym edge to sense `a`, rebuilding the immutable sense in place."""
    for lemma, entry in registry.entries.items():
        for i, sense in enumerate(entry.senses):
            if sense.sense_id != a:
                continue
            core = sense.core
            if any(e.to_sense == b for e in core.synonym_edges):
                return
            import dataclasses

            new_core = dataclasses.replace(
                core,
                synonym_edges=core.synonym_edges
                + (SynonymEdge(from_sense=a, to_sense=b, weight=weight, source=source),),
            )
            senses = list(entry.senses)
            senses[i] = Sense(core=new_core, display=sense.display)
            registry.entries[lemma] = dataclasses.replace(entry, senses=tuple(senses))
            return


# --- 4. Repo pre-minted -----------------------------------------------------------

_GLOSSARY_LINE = re.compile(r"^\s*[-*+]\s+\*{0,2}(?P<term>[^*:]+?)\*{0,2}\s*[—:-]\s+(?P<gloss>.+)$")


def import_preminted(registry: Registry, documents: Sequence[Document]) -> ImportResult:
    """D5 files: domain senses at high warrant by authorship provenance.

    **Never merged into imported general senses** (SPEC §2): these get `source="preminted"`
    and their own sense ids, so a project term that happens to collide with a WordNet
    lemma stays a separate sense rather than being absorbed.
    """
    if not documents:
        return ImportResult(
            "preminted", "blocked",
            detail="D5 unresolved: seed/LEXICON/preminted/ holds no files.",
        )

    added = 0
    for doc in documents:
        for line in doc.text.splitlines():
            match = _GLOSSARY_LINE.match(line)
            if not match:
                continue
            term = match.group("term").strip()
            if not term or len(term) > 80:
                continue
            registry.add(
                make_sense(
                    lemma=lemma_of(term),
                    english_face=term,
                    source="preminted",
                    frames=["common_ground", "ledger"],
                    gloss=match.group("gloss").strip(),
                    notes=f"preminted:{doc.meta.get('path', doc.doc_id)}",
                    face_warrant="authored",
                )
            )
            added += 1

    return ImportResult("preminted", "imported", added=added,
                        pin=",".join(sorted(d.meta.get("sha256", "")[:12] for d in documents)),
                        detail=f"{added} domain senses from {len(documents)} pre-minted file(s)")


# --- 5. WordNet -------------------------------------------------------------------


def import_wordnet(registry: Registry, path: str | Path | None, version: str | None) -> ImportResult:
    """General English, LAST, gap-fill.

    Every WordNet sense is added as a distinct sense — the collision policy never
    suppresses and never merges. What stops a general sense shadowing a technical one is
    *selection* (frames plus a `source_beta` prior too small to overturn frame evidence),
    which is exactly what null cell (vii) tests. Suppressing them here instead would hide
    the shadowing risk rather than defusing it.
    """
    if path is None or version is None:
        return ImportResult(
            "wordnet", "blocked",
            detail="D8 unresolved: no pinned WordNet path and version.",
        )

    p = Path(path)
    if not p.exists():
        raise EngineError(f"WordNet dump not found: {p}")

    payload = json.loads(p.read_text(encoding="utf-8"))
    before = {lemma for lemma in registry.entries}

    added = 0
    gap_fill = 0
    for entry in sorted(payload.get("entries", []), key=lambda e: e["lemma"]):
        lemma = entry["lemma"]
        if lemma not in before:
            gap_fill += 1
        for i, sense in enumerate(entry.get("senses", [])):
            registry.add(
                make_sense(
                    lemma=lemma,
                    english_face=sense.get("english_face", lemma),
                    source="general",
                    frames=["general"],
                    gloss=sense.get("gloss", ""),
                    notes=f"wordnet:{version}:{i}",
                    face_warrant="authored",
                )
            )
            added += 1

    return ImportResult(
        "wordnet", "imported", added=added, pin=version,
        detail=f"{added} general senses ({gap_fill} lemmas previously uncovered) @ {version}",
        stats={"gap_fill_lemmas": gap_fill, "coexisting_lemmas": len(payload.get("entries", [])) - gap_fill},
    )


# --- orchestration ----------------------------------------------------------------


def import_all(
    pins: Mapping[str, Any],
    preminted_docs: Sequence[Document] = (),
) -> tuple[Registry, list[ImportResult]]:
    """Run all five imports in the fixed order. Every batch is a logged seed event."""
    registry = Registry()
    results: list[ImportResult] = []

    runners = {
        "mathlib": lambda: import_mathlib(registry, pins.get("mathlib_dump"), pins.get("mathlib_commit")),
        "convention": lambda: import_convention_table(registry),
        "nlab": lambda: import_nlab(registry, pins.get("nlab_scrape"), pins.get("nlab_scrape_date")),
        "preminted": lambda: import_preminted(registry, preminted_docs),
        "general": lambda: import_wordnet(registry, pins.get("wordnet_path"), pins.get("wordnet_version")),
    }

    for source in SOURCE_ORDER:
        runner = runners.get(source)
        if runner is None:
            raise EngineError(f"no importer registered for source {source!r}")
        result = runner()
        results.append(result)
        registry.import_log.append(result.as_record())

    return registry, results
