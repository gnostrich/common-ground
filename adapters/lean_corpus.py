"""Lean sources -> Lean-chart documents, with kernel receipts as clamps.

Gate 3 admits Lean kernel-accept as a grounding warrant **under the pinned toolchain**.
The qualifier is the whole content of the gate: a kernel receipt from an unpinned or
unknown toolchain grounds nothing, because there is nothing fixed that it is a receipt
*of*. So `load_lean_corpus` refuses to emit clamps while D6 is unresolved, and emits
documents only.

Per KICKOFF section 7.5, this reads the D3 dump directory. It does not pull live during a
run: a live pull is unpinned by construction and cannot hash cleanly.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from engine import EngineError
from engine.hashing import sha256_file
from engine.normalize import address, classify
from engine.types import Clamp, Document, Warrant, WarrantTier

_DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+|nonrec\s+|scoped\s+|local\s+)*"
    r"(theorem|lemma|example|axiom|def|abbrev|structure|class|instance|inductive|notation)\s+([^\s:({\[]+)",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class KernelReceipt:
    """Evidence that the pinned toolchain elaborated a file without error."""

    file: str
    file_sha256: str
    toolchain: str
    accepted: bool
    detail: str


def load_lean_corpus(
    dump_dir: str | Path,
    lean_toolchain: str | None,
) -> tuple[list[Document], list[KernelReceipt]]:
    """Load .lean files from the D3 dump. Receipts require a pinned toolchain."""
    root = Path(dump_dir)
    if not root.is_dir():
        raise EngineError(f"lean corpus dump directory not found: {root}")

    files = sorted(p for p in root.rglob("*.lean") if p.is_file())
    docs = [
        Document(
            doc_id=f"lean:{p.relative_to(root).as_posix()}",
            chart="lean",
            text=p.read_text(encoding="utf-8", errors="replace"),
            source="lean_corpus",
            meta={"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)},
        )
        for p in files
    ]

    receipts: list[KernelReceipt] = []
    if lean_toolchain:
        receipts = [_elaborate(p, root, lean_toolchain) for p in files]

    return docs, receipts


def _elaborate(path: Path, root: Path, toolchain: str) -> KernelReceipt:
    """Re-elaborate one file under the pinned toolchain.

    A failure to *run* the toolchain is recorded as `accepted=False` with the reason, not
    raised. A missing toolchain is a fact about the environment; treating it as an
    exception would tempt a caller to catch it and proceed as though the file had been
    checked.
    """
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", str(path)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        accepted = proc.returncode == 0
        detail = "" if accepted else (proc.stderr or proc.stdout)[:500]
    except FileNotFoundError:
        accepted, detail = False, "lake not on PATH; no kernel receipt available"
    except subprocess.TimeoutExpired:
        accepted, detail = False, "elaboration timed out after 600s"

    return KernelReceipt(
        file=path.name,
        file_sha256=sha256_file(path),
        toolchain=toolchain,
        accepted=accepted,
        detail=detail,
    )


def clamps_from_receipts(
    documents: Sequence[Document],
    receipts: Sequence[KernelReceipt],
    lean_toolchain: str | None,
) -> list[Clamp]:
    """Turn accepted receipts into clamps on the declarations they certify.

    Refuses outright while D6 is unresolved. This is the single place in the codebase
    that constructs a `KERNEL`-tier warrant, and it will not do so without a pinned
    toolchain string to name in the warrant's detail.
    """
    if not lean_toolchain:
        raise EngineError(
            "D6 Lean toolchain is unresolved; kernel-accept cannot ground (gate 3 admits "
            "kernel-accept *under the pinned toolchain*). Read the version from the "
            "certified-positivity lake-manifest and record it in seed/DECISIONS.json."
        )

    accepted = {r.file for r in receipts if r.accepted}
    out: list[Clamp] = []

    for doc in documents:
        name = Path(doc.meta.get("path", doc.doc_id)).name
        if name not in accepted:
            continue
        for match in _DECL_RE.finditer(doc.text):
            head = match.group(1)
            if head not in ("theorem", "lemma", "axiom"):
                # Only propositions carry a truth value a kernel receipt can ground.
                # Definitions elaborate too, but "this definition type-checks" is not a
                # claim that some proposition is true.
                continue
            end = doc.text.find(":=", match.end())
            statement = doc.text[match.start() : end if end != -1 else len(doc.text)]
            slot, _ = address("lean", statement, classify("lean", statement))
            out.append(
                Clamp(
                    slot=slot,
                    value="T",
                    warrant=Warrant(
                        tier=WarrantTier.KERNEL,
                        detail=f"lean kernel-accept; toolchain={lean_toolchain}; file={name}",
                    ),
                )
            )
    return out
