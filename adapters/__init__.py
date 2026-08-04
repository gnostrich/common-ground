"""Corpus adapters: source -> Document (and, for Lean and Python, grounding clamps).

An adapter's job is to produce documents and provenance. It does not decide warrants for
claims — that is `engine/extract.py`, which stamps `EXTRACTION` on everything it emits
(gate 3). The exceptions are structural, not editorial: `repo_docs` may raise a document's
tier to `PREMINTED` or `REPO_DOC` because the *source* is what confers that tier;
`lean_corpus` may emit a `Clamp` because a kernel receipt is a fact about the toolchain
rather than a reading of a sentence; `python_corpus` may emit a `Clamp` for the same reason
about a CI-green test receipt (GATES.md sentence 3 names both grounding tiers). `repo_adapter`
routes an arbitrary repo's files to a chart, reference-tier hold, or the shelf via the
`seed/LANGUAGES.json` manifest — it produces no warrants of its own.
"""

from .claude_export import load_claude_export
from .lean_corpus import KernelReceipt, load_lean_corpus
from .lexicon_imports import ImportResult, import_all
from .python_corpus import TestReceipt, load_python_corpus, run_test_receipts
from .python_corpus import clamps_from_receipts as python_clamps_from_receipts
from .repo_adapter import RepoIntakeReport, WalkedFile, walk_repo
from .repo_docs import load_preminted, load_repo_docs

__all__ = [
    "load_claude_export",
    "load_lean_corpus",
    "load_preminted",
    "load_repo_docs",
    "load_python_corpus",
    "run_test_receipts",
    "python_clamps_from_receipts",
    "TestReceipt",
    "walk_repo",
    "RepoIntakeReport",
    "WalkedFile",
    "KernelReceipt",
    "import_all",
    "ImportResult",
]
