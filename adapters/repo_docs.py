"""README / STATEMENTS / docs -> English chart, with repo provenance.

Also the ingestion path for D5's pre-minted entries. The difference between a pre-minted
entry and an ordinary repo document is the warrant *tier* attached to the source, not the
extraction — both go through the same extractor bank, so a pre-minted file gets no special
reading, only a heavier energy weight. Neither tier is clamp-eligible (gate 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from engine import EngineError
from engine.constants import SEED_DIR
from engine.hashing import sha256_file
from engine.types import Delta, Document, Warrant, WarrantTier

_DOC_SUFFIXES = (".md", ".markdown", ".rst", ".txt")


def load_repo_docs(
    repo_root: str | Path,
    repo_name: str,
    include: Sequence[str] | None = None,
) -> list[Document]:
    """Load documentation files from a repository checkout."""
    root = Path(repo_root)
    if not root.is_dir():
        raise EngineError(f"repo not found: {root}")

    if include:
        paths = [root / rel for rel in include]
        missing = [str(p) for p in paths if not p.is_file()]
        if missing:
            raise EngineError(f"repo_docs: listed files missing: {missing}")
    else:
        paths = sorted(
            p
            for p in root.rglob("*")
            if p.is_file()
            and p.suffix.lower() in _DOC_SUFFIXES
            and ".git" not in p.parts
        )

    return [
        Document(
            doc_id=f"repo:{repo_name}:{p.relative_to(root).as_posix()}",
            chart="english",
            text=p.read_text(encoding="utf-8", errors="replace"),
            source="repo_docs",
            meta={
                "repo": repo_name,
                "path": p.relative_to(root).as_posix(),
                "sha256": sha256_file(p),
            },
        )
        for p in paths
    ]


def load_preminted(preminted_dir: str | Path | None = None) -> list[Document]:
    """Load D5 pre-minted files from seed/LEXICON/preminted/.

    Returns an empty list when the directory holds no entries, which is what makes null
    cell (iii) report BLOCKED. It does not raise: an empty pre-minted set is the current
    honest state of D5, not an error.
    """
    root = Path(preminted_dir) if preminted_dir else SEED_DIR / "LEXICON" / "preminted"
    if not root.is_dir():
        return []

    paths = sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in _DOC_SUFFIXES and p.name != "README.md"
    )
    return [
        Document(
            doc_id=f"preminted:{p.name}",
            chart="english",
            text=p.read_text(encoding="utf-8", errors="replace"),
            source="seed",
            meta={"preminted": "true", "path": p.name, "sha256": sha256_file(p)},
        )
        for p in paths
    ]


def retier(deltas: Sequence[Delta], tier: WarrantTier, detail: str) -> list[Delta]:
    """Re-stamp a delta set at a source-conferred tier.

    Guarded by an assertion rather than a comment: this function must never be used to
    manufacture a grounding warrant out of extraction provenance, so it refuses any
    clamp-eligible tier outright. Kernel clamps come from `lean_corpus`, and only from
    a receipt.
    """
    probe = Warrant(tier=tier, detail=detail)
    if probe.clamp_eligible:
        from engine import GateViolation

        raise GateViolation(
            3,
            f"retier() refuses tier {tier.name}: source-conferred tiers may not ground. "
            "A grounding warrant must come from a kernel receipt or a CI receipt.",
        )

    import dataclasses

    return [dataclasses.replace(d, warrant=probe) for d in deltas]
