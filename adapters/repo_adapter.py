"""Repo intake: walk a repository, route each file to a chart, hold it as reference-tier,
or shelve it.

Dispatch is a seed-declared language manifest (`seed/LANGUAGES.json`, read through
`adapters/language_registry.py`) — never an `if ext == ...` chain in this file, the same
plug-in shape `engine/charts.py` gives charts. Three destinations, first match wins,
nothing silently dropped: `RepoIntakeReport.counts()` carries every file the walk saw.

- **chart-worthy** -> a `Document` on the language's declared chart, ready for the same
  extractor/normalizer/segmenter pipeline every other document goes through.
- **reference-tier** -> HELD. Recorded (path, hash, reason) but no `Document` is built.
  Ingesting reference-tier content as English claims *about* the code is future work (see
  seed/DECISIONS.md's REPO_INTAKE ledger entry); this adapter does not do it, so a v0 run
  cannot silently absorb prose-about-code at EXTRACTION tier under cover of "repo intake."
- **shelf** -> skipped. Hashed for the report; content is never read into anything —
  binaries are not decoded as text even to discard them.

This module never ingests the operator's real repositories; it is proven against
`tests/fixtures/mixed_repo/`. Real-repo ingestion is a separate, later, explicitly
authorized step (seed/DECISIONS.md REPO_INTAKE).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from engine.charts import is_chart
from engine.hashing import sha256_file
from engine.types import Document

from engine.router import route

from .language_registry import (CHART_WORTHY, CONTENT_CLASSIFIED, LanguageSpec,
                                classify_path)

#: Directories never walked into. `.git` is history, not content; the others are
#: machine-generated dependency trees that would otherwise dwarf the repo's own code.
EXCLUDE_DIRS: frozenset[str] = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache",
})


@dataclasses.dataclass(frozen=True, slots=True)
class WalkedFile:
    """One file's routing verdict. `document` is populated only for chart-worthy files —
    a reference-tier or shelf row carries its hash and reason but never its bytes as text.
    """

    path: str                    # posix path relative to the repo root
    classification: str          # "chart-worthy" | "reference-tier" | "shelf"
    chart: str | None
    reason: str
    rule: str
    sha256: str
    document: Document | None = None


@dataclasses.dataclass(slots=True)
class RepoIntakeReport:
    repo: str
    files: tuple[WalkedFile, ...]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.files:
            out[f.classification] = out.get(f.classification, 0) + 1
        return out

    def by_chart(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.files:
            if f.classification == "chart-worthy":
                out[f.chart or "?"] = out.get(f.chart or "?", 0) + 1
        return out

    def to_documents(self) -> list[Document]:
        """Only chart-worthy files reach here. Reference-tier and shelf never do."""
        return [f.document for f in self.files if f.document is not None]

    def held(self) -> tuple[WalkedFile, ...]:
        """Reference-tier files: content HELD, not ingested. See module docstring."""
        return tuple(f for f in self.files if f.classification == "reference-tier")

    def shelved(self) -> tuple[WalkedFile, ...]:
        return tuple(f for f in self.files if f.classification == "shelf")

    def header(self) -> str:
        parts = [f"{k}={v}" for k, v in sorted(self.counts().items())]
        return "repo-intake: " + ", ".join(parts) if parts else "repo-intake: (empty)"


def walk_repo(repo_root: str | Path, repo_name: str) -> RepoIntakeReport:
    """Walk `repo_root` and classify every file. Raises on a manifest/registry drift —
    a language routed to a chart that `seed/CHARTS.json` never registered — rather than
    silently misrouting it, since that would be a slot address nobody could compute.
    """
    root = Path(repo_root)
    if not root.is_dir():
        raise ValueError(f"repo not found: {root}")

    paths = sorted(
        p for p in root.rglob("*")
        if p.is_file() and not (EXCLUDE_DIRS & set(p.relative_to(root).parts))
    )

    files: list[WalkedFile] = []
    for p in paths:
        rel = p.relative_to(root).as_posix()
        spec = classify_path(p.name)
        digest = sha256_file(p)
        doc: Document | None = None

        if spec.classification in (CHART_WORTHY, CONTENT_CLASSIFIED):
            if spec.classification == CHART_WORTHY and not is_chart(spec.chart):
                raise ValueError(
                    f"seed/LANGUAGES.json routes {rel!r} to chart {spec.chart!r}, which is "
                    "not registered in seed/CHARTS.json — a manifest drift, not a silent "
                    "misroute"
                )
            text = p.read_text(encoding="utf-8", errors="replace")
            # ONE routing path. `engine.router.route` reads the same manifest for the
            # extension and then applies the content rules a `content-classified` file needs
            # — including the span-level verbatim split, so a README with a usage example
            # contributes its prose instead of being shelved whole.
            routed = route(f"repo:{repo_name}:{rel}", text, "repo_adapter")
            doc = routed.document
            if doc is not None:
                doc.meta.update({"repo": repo_name, "path": rel, "sha256": digest})
                spec = LanguageSpec(spec.classification, doc.chart, spec.reason, spec.rule)

        files.append(WalkedFile(
            path=rel, classification=spec.classification, chart=spec.chart,
            reason=spec.reason, rule=spec.rule, sha256=digest, document=doc,
        ))

    return RepoIntakeReport(repo=repo_name, files=tuple(files))
