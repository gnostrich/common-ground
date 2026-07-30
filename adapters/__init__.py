"""Corpus adapters: source -> Document (and, for Lean, kernel clamps).

An adapter's job is to produce documents and provenance. It does not decide warrants for
claims — that is `engine/extract.py`, which stamps `EXTRACTION` on everything it emits
(gate 3). The two exceptions are structural, not editorial: `repo_docs` may raise a
document's tier to `PREMINTED` or `REPO_DOC` because the *source* is what confers that
tier, and `lean_corpus` may emit a `Clamp` because a kernel receipt is a fact about the
toolchain rather than a reading of a sentence.
"""

from .claude_export import load_claude_export
from .lean_corpus import KernelReceipt, load_lean_corpus
from .lexicon_imports import ImportResult, import_all
from .repo_docs import load_preminted, load_repo_docs

__all__ = [
    "load_claude_export",
    "load_lean_corpus",
    "load_preminted",
    "load_repo_docs",
    "KernelReceipt",
    "import_all",
    "ImportResult",
]
