"""Does the snapshot still match the material it was built from?

The snapshot is a derived object: a pickle of slots, fibers and blocks computed from corpus
material at one moment. Nothing verified that the material had not moved since. On a rebuild
from re-cloned repositories that had advanced, three arrows in the journal referred to slots
the new snapshot no longer contained — they were dropped, correctly and silently, and the
only reason anyone knew is that a count changed by three.

That is the one sync surface the bones disclosure could not prove closed. Snapshot-wins is
the right resolution — the snapshot IS the read view — but it must be a VISIBLE resolution.
A stale snapshot answering questions about material that has changed underneath it is the
same failure class as a search reporting itself complete: correct mechanics, wrong claim.

THE DIGEST is over the material, not the snapshot: sha256 of the sorted `<filehash>  <relpath>`
lines, the algorithm the Aristotle corpus pin already uses. Recomputed on demand rather than
on every load, because walking a 528 MB tree is not free and a window that stalls to prove
its freshness has traded one honesty for another.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this touches mechanism --
MOVE: none. This is a VIEW-level integrity check over an existing derived artifact; it adds
no base, no measure and no morphism, and it decides nothing about warrant. It reports.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

#: Where the digest recorded at build time lives. Beside the snapshot, not inside it, so an
#: older snapshot without one is READABLE and simply reports `unknown` rather than failing.
DIGEST_PATH = "runs/corpus.snapshot.digest.json"

#: Files whose content is hashed. Everything the loader would ingest; nothing it shelves.
#: Kept deliberately wide — a narrower set could call a snapshot fresh while material it
#: actually read had changed.
SKIP_DIRS = frozenset({".git", "node_modules", ".lake", "build", ".cache",
                       "__pycache__", ".venv", "dist"})


@dataclass(frozen=True, slots=True)
class Staleness:
    """The verdict, with the reason. `unknown` is a third state and not a pass."""

    state: str                                 # fresh | stale | unknown
    recorded: str = ""
    observed: str = ""
    roots: tuple[str, ...] = ()
    files: int = 0
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.state == "fresh"

    def as_record(self) -> dict[str, object]:
        return {"state": self.state, "recorded": self.recorded[:16],
                "observed": self.observed[:16], "roots": list(self.roots),
                "files": self.files, "note": self.note}


def material_digest(roots) -> tuple[str, int]:
    """sha256 over sorted `<filehash>  <relpath>` lines. Same algorithm as the corpus pin."""
    lines: list[str] = []
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue
            lines.append(f"{h}  {p.relative_to(base)}")
    body = "\n".join(sorted(lines))
    return hashlib.sha256(body.encode("utf-8")).hexdigest(), len(lines)


def record(roots, path: str | Path = DIGEST_PATH) -> Staleness:
    """Called at snapshot build. Writes the digest of what was actually read."""
    digest, n = material_digest(roots)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"digest": digest, "files": n,
                             "roots": [str(r) for r in roots]}, indent=2) + "\n",
                 encoding="utf-8")
    return Staleness(state="fresh", recorded=digest, observed=digest,
                     roots=tuple(str(r) for r in roots), files=n,
                     note="recorded at snapshot build")


def check(path: str | Path = DIGEST_PATH) -> Staleness:
    """Recompute and compare. A missing digest is UNKNOWN, never fresh.

    An older snapshot predates this check and cannot be vouched for by it; saying so is the
    whole point. Reporting `unknown` as a pass would reintroduce silent snapshot-wins with an
    extra step.
    """
    p = Path(path)
    if not p.exists():
        return Staleness(state="unknown",
                         note="no digest was recorded when this snapshot was built, so its "
                              "freshness cannot be checked. Rebuild to establish one.")
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return Staleness(state="unknown", note="the recorded digest is unreadable")
    roots = tuple(rec.get("roots") or ())
    observed, n = material_digest(roots)
    if observed == rec.get("digest"):
        return Staleness(state="fresh", recorded=rec["digest"], observed=observed,
                         roots=roots, files=n, note="material matches the snapshot")
    return Staleness(
        state="stale", recorded=str(rec.get("digest", "")), observed=observed,
        roots=roots, files=n,
        note=(f"THE MATERIAL HAS CHANGED since this snapshot was built "
              f"({rec.get('files', '?')} files then, {n} now). The snapshot is still what "
              f"every answer is computed from — it does not silently lose — but it is "
              f"answering about material that has moved. Rebuild to resynchronise."))
