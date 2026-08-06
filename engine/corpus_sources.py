"""Where a corpus lives — the one seam between the mechanism and somebody's material.

Everything else in this engine is about *how* claims are addressed, charted and bridged.
None of it should know that a particular Lean corpus sits in a particular directory on a
particular machine, and until now `proposerd.py` did: three `CG_*` environment variables and
a hard-coded list of excluded conversation ids, which meant the mechanism could not be handed
to anyone else without handing over the shape of one person's disk.

So the pointer moves into a file the repository does not carry. `seed/CORPUS.example.json` is
the committed template; `corpus.local.json` is the real one and is gitignored. Fork this
repository, copy the template, point it at your own material, and nothing else changes.

**A source that is not there is REPORTED, not skipped.** `resolve()` returns every declared
source with a `present` flag and a reason, so a fork nobody has pointed anywhere says
"0 sources resolved" rather than ingesting nothing and printing a confident zero. That
distinction is the same one the router makes about held languages, for the same reason.

**An export must declare its exclusions.** A `claude_export` source with no `exclude` key is
REFUSED rather than defaulted to none. A personal archive contains material its owner never
meant to hand to an engine, and the failure mode of forgetting is that it has already been
read. Requiring the key makes leaving it empty a deliberate act.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import EngineError
from .constants import REPO_ROOT, SEED_DIR

#: The operator's own pointer file. Gitignored; never committed.
LOCAL_PATH = REPO_ROOT / "corpus.local.json"
#: The committed template a fork copies.
EXAMPLE_PATH = SEED_DIR / "CORPUS.example.json"

KINDS = frozenset({"repos", "lean_corpus", "claude_export", "files"})

DEFAULT_SKIP = (".git", "node_modules", ".lake", "build", ".cache", "__pycache__",
                ".venv", "dist")


@dataclass(frozen=True, slots=True)
class Source:
    """One declared corpus source, and whether it is actually there."""

    name: str
    kind: str
    path: str
    enabled: bool = True
    exclude: tuple[str, ...] = ()
    skip_dirs: tuple[str, ...] = DEFAULT_SKIP
    max_bytes: int = 3_000_000
    present: bool = False
    reason: str = ""

    def as_record(self) -> dict[str, object]:
        return {"name": self.name, "kind": self.kind, "enabled": self.enabled,
                "present": self.present, "reason": self.reason,
                "excluded_ids": len(self.exclude)}


def config_path() -> Path:
    """The pointer file in use: `$CG_CORPUS` if set, else `corpus.local.json`."""
    override = os.environ.get("CG_CORPUS", "").strip()
    return Path(override) if override else LOCAL_PATH


def resolve() -> list[Source]:
    """Every declared source, each marked present or not, with the reason.

    Raises only for a manifest that is *wrong* — an unknown kind, an export with no
    exclusion key. A source that is merely absent is returned with `present=False`, because
    "you have not plugged anything in yet" and "your manifest is malformed" are different
    facts and only the second is an error.
    """
    path = config_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EngineError(f"{path} is not valid JSON: {exc}") from exc

    out: list[Source] = []
    for row in raw.get("sources", ()):
        name = str(row.get("name") or row.get("path") or "?")
        kind = str(row.get("kind", ""))
        if kind not in KINDS:
            raise EngineError(f"{path}: source {name!r} has kind {kind!r}; "
                              f"legal kinds are {sorted(KINDS)}")
        if kind == "claude_export" and "exclude" not in row:
            raise EngineError(
                f"{path}: source {name!r} is a claude_export with no `exclude` key. It must "
                "be present even if empty — an archive contains material its owner never "
                "meant to hand to an engine, and the failure mode of forgetting is that it "
                "has already been read.")
        target = Path(str(row.get("path", "")))
        present = target.is_dir() if kind in ("repos", "lean_corpus") else target.is_file()
        out.append(Source(
            name=name, kind=kind, path=str(target),
            enabled=bool(row.get("enabled", True)),
            exclude=tuple(str(x) for x in row.get("exclude", ())),
            skip_dirs=tuple(row.get("skip_dirs", DEFAULT_SKIP)),
            max_bytes=int(row.get("max_bytes", 3_000_000)),
            present=present,
            reason="" if present else f"not found at {target}",
        ))
    return out


def active() -> list[Source]:
    """Sources that are both enabled and actually present."""
    return [s for s in resolve() if s.enabled and s.present]


def status() -> dict[str, object]:
    """What a fork sees before it has plugged anything in. Never a bare zero."""
    path = config_path()
    if not path.exists():
        return {"config": str(path), "configured": False, "sources": [],
                "note": (f"no corpus is plugged in. Copy {EXAMPLE_PATH.name} to "
                         f"{LOCAL_PATH.name} and point it at your own material; the file is "
                         "gitignored, so your paths never enter the repository.")}
    found = resolve()
    live = [s for s in found if s.enabled and s.present]
    return {
        "config": str(path), "configured": True,
        "sources": [s.as_record() for s in found],
        "active": len(live),
        "note": ("" if live else
                 "every declared source is disabled or missing — nothing would be ingested. "
                 "That is reported rather than run, because an empty corpus and an "
                 "unconfigured one produce the same zero."),
    }
