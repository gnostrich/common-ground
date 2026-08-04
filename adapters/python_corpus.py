"""Python sources -> Python-chart documents, with CI-green test receipts as clamps.

Mirrors `lean_corpus.py`'s shape exactly. GATES.md sentence 3 names two grounding tiers by
name: "Lean kernel-accept under pinned toolchain; CI-green test receipts." This module is
the second one. A receipt here is not asserted: it comes from actually *running* the
corpus's own stdlib `unittest` suite in a subprocess and reading back which test functions
passed — the replayable floor "Python via AST + tests" names. AST supplies the deterministic
structural segmenter (`engine/extract.py:_segment_python`); tests supply the grounding.

Only a `test_*`-discovered method that a green run reports `ok` for is clamp-eligible, and
only the function whose test passed is clamped — never the module, never a plain function
that merely happens to sit beside a passing test. Nothing here can construct a KERNEL-tier
warrant; `WarrantTier.CI_RECEIPT` is the only tier this module is capable of naming.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from engine import EngineError
from engine.hashing import sha256_file
from engine.normalize import address, classify
from engine.types import Clamp, Document, Warrant, WarrantTier


@dataclass(frozen=True, slots=True)
class TestReceipt:
    """Evidence that the repo's own stdlib-unittest suite ran a test function green."""

    file: str      # posix path relative to the corpus root, as the runner reported it
    qualname: str  # "Class.method", or "method" for a module-level test function
    outcome: str   # "pass" | "fail" | "error" | "skip"
    detail: str = ""


def load_python_corpus(dump_dir: str | Path) -> list[Document]:
    """Load `.py` files from a repo dump. Test files are ordinary python-chart documents
    too — a test function is Python source like any other; its clamp eligibility is
    decided by whether a receipt names it, not by which file it lives in.
    """
    root = Path(dump_dir)
    if not root.is_dir():
        raise EngineError(f"python corpus dump directory not found: {root}")

    files = sorted(
        p for p in root.rglob("*.py")
        if p.is_file() and "__pycache__" not in p.parts
    )
    return [
        Document(
            doc_id=f"python:{p.relative_to(root).as_posix()}",
            chart="python",
            text=p.read_text(encoding="utf-8", errors="replace"),
            source="python_corpus",
            meta={"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)},
        )
        for p in files
    ]


# The runner is a standalone, pure-stdlib script executed in a *subprocess* — never
# imported into this process — so that a broken or hostile test module in the corpus
# cannot corrupt this adapter's own interpreter state, and so a hung test cannot hang the
# caller past the subprocess timeout below. It discovers every test via
# `unittest.TestLoader.discover` (the same discovery `python -m unittest discover` uses),
# runs each individually, and prints one JSON object per line — it asserts nothing about
# the result itself, only reports.
_RUNNER_SCRIPT = r"""
import json, sys, unittest

root = sys.argv[1]
loader = unittest.TestLoader()
suite = loader.discover(start_dir=root, pattern="test_*.py")


def flatten(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            yield from flatten(t)
        else:
            yield t


for case in flatten(suite):
    cls = type(case).__name__
    method = getattr(case, "_testMethodName", "")
    result = unittest.TestResult()
    case.run(result)
    if result.errors:
        outcome, detail = "error", result.errors[0][1][:300]
    elif result.failures:
        outcome, detail = "fail", result.failures[0][1][:300]
    elif result.skipped:
        outcome, detail = "skip", result.skipped[0][1][:300]
    else:
        outcome, detail = "pass", ""
    try:
        file = sys.modules[type(case).__module__].__file__ or ""
    except Exception:
        file = ""
    print(json.dumps({"cls": cls, "method": method, "file": file,
                       "outcome": outcome, "detail": detail}))
"""


def run_test_receipts(
    dump_dir: str | Path,
    python_executable: str | None = None,
    timeout: int = 600,
) -> list[TestReceipt]:
    """Actually run the corpus's `unittest` suite and report per-test outcomes.

    Runs in a fresh subprocess of `python_executable` (default: the interpreter running
    this process — D6's pinned Python, never a guessed one) so the adapter's own process is
    never polluted by the corpus's module state. A discovery or import error in the corpus
    is not raised here: it surfaces as an empty receipt list plus non-empty stderr, which
    the caller can log, mirroring `lean_corpus._elaborate`'s "record, don't raise" stance
    on the *toolchain*'s own reported outcome.
    """
    root = Path(dump_dir)
    if not root.is_dir():
        raise EngineError(f"python corpus dump directory not found: {root}")
    exe = python_executable or sys.executable
    # Resolve to an absolute path before handing it to the subprocess: `cwd=root` changes
    # the child's working directory, so a *relative* argv would be re-resolved against
    # that new cwd and silently point somewhere else (or nowhere).
    abs_root = root.resolve()

    try:
        proc = subprocess.run(
            [exe, "-c", _RUNNER_SCRIPT, str(abs_root)],
            cwd=abs_root, capture_output=True, text=True, timeout=timeout, check=False,
        )
        stdout = proc.stdout
    except subprocess.TimeoutExpired:
        stdout = ""

    receipts: list[TestReceipt] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            rel = Path(row["file"]).resolve().relative_to(root.resolve()).as_posix()
        except (ValueError, OSError):
            rel = row["file"]
        cls, method = row.get("cls", ""), row.get("method", "")
        qualname = f"{cls}.{method}" if cls and cls != "_ErrorHolder" else method
        receipts.append(TestReceipt(file=rel, qualname=qualname,
                                    outcome=row["outcome"], detail=row.get("detail", "")))
    return receipts


def clamps_from_receipts(
    documents: Sequence[Document],
    receipts: Sequence[TestReceipt],
) -> list[Clamp]:
    """Turn passing test receipts into CI_RECEIPT clamps on the test function they certify.

    The single place in the codebase that constructs a `CI_RECEIPT`-tier warrant from a
    Python source. Only a receipt with `outcome == "pass"` clamps, and only the specific
    test *function* it names — found by walking that document's own AST for a matching
    `def`, never guessed by name alone across files, mirroring
    `lean_corpus.clamps_from_receipts` restricting to the declarations a receipt's file
    actually contains.
    """
    by_path = {d.meta.get("path", ""): d for d in documents}
    out: list[Clamp] = []
    for r in receipts:
        if r.outcome != "pass":
            continue
        doc = by_path.get(r.file)
        if doc is None:
            continue
        method = r.qualname.rsplit(".", 1)[-1]
        node = _find_function(doc.text, method)
        if node is None:
            continue
        span = ast.get_source_segment(doc.text, node)
        if not span:
            continue
        slot, _ = address("python", span, classify("python", span))
        out.append(Clamp(
            slot=slot, value="T",
            warrant=Warrant(tier=WarrantTier.CI_RECEIPT,
                            detail=f"unittest green; test={r.qualname}; file={r.file}"),
        ))
    return out


def _find_function(text: str, name: str) -> ast.AST | None:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None
