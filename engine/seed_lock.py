"""SEED.lock: the manifest, the seed hash, and the gate-4 tripwire.

The lock is a sha256 over every seed file, every prompt, the pinned toolchain versions,
and the constants. The seed hash is the hash of that manifest. Everything downstream —
every run record, every null battery, every floor read — is keyed to it.

Two refusals live here:

- `build()` refuses while any decision in `seed/DECISIONS.json` is unresolved. KICKOFF
  section 7.1 says to refuse past P0 with any blank, and this is where that becomes
  mechanical rather than a matter of the operator remembering.
- `verify()` recomputes every hash and fails on drift. CI runs it on every push, which is
  the "toolchain hashes tripwired in CI" half of gate 4.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import GateViolation
from .constants import (
    C,
    DECISIONS_PATH,
    SEED_DIR,
    SEED_LOCK_PATH,
    decisions as load_decisions,
)
from .hashing import hash_obj, sha256_file

#: Files under seed/ that are hashed. Everything except the lock itself, so that writing
#: the lock does not change the thing the lock is a hash of.
_EXCLUDED = {"SEED.lock"}

_BLANK_MARKERS = ("____", "UNRESOLVED", "DECISION-REQUIRED")


def seed_files() -> list[Path]:
    return sorted(
        p
        for p in SEED_DIR.rglob("*")
        if p.is_file() and p.name not in _EXCLUDED and not p.name.startswith(".")
    )


def unresolved_decisions(decisions: dict[str, Any] | None = None) -> list[str]:
    """Decision ids that are not fully resolved.

    Reads the machine-readable `seed/DECISIONS.json`. `partial` counts as unresolved: D4
    with a bound extractor bank but a blank spend cap is not a decision that has been
    made.
    """
    d = decisions if decisions is not None else load_decisions()
    out: list[str] = []
    for key in sorted(k for k in d if k.startswith("D")):
        status = str(d[key].get("status", "")).lower()
        if status != "resolved":
            out.append(f"{key}:{status or 'missing'}")
    return out


def blank_markers_in_decisions_md() -> list[str]:
    """Lines in seed/DECISIONS.md still carrying a literal blank.

    Checked alongside the JSON so the human record and the machine record cannot silently
    diverge — a `____` left in the prose is a decision someone still owes.
    """
    md = SEED_DIR / "DECISIONS.md"
    if not md.exists():
        return ["seed/DECISIONS.md missing"]
    hits: list[str] = []
    for i, line in enumerate(md.read_text(encoding="utf-8").splitlines(), start=1):
        if any(marker in line for marker in _BLANK_MARKERS):
            hits.append(f"{i}: {line.strip()[:100]}")
    return hits


#: Files whose content determines the lexicon registry. Hashed into SEED.lock as
#: `importer_script_hash` (LEXICON SPEC §3): editing any of them changes what the
#: importer produces, which moves addresses, which is plastic under gate 4.
IMPORTER_SCRIPT_FILES: tuple[str, ...] = (
    "adapters/lexicon_imports.py",
    "engine/lexicon.py",
    "engine/rmap.py",
)


def importer_script_hash() -> str:
    from .constants import REPO_ROOT

    parts = []
    for rel in IMPORTER_SCRIPT_FILES:
        path = REPO_ROOT / rel
        parts.append(sha256_file(path) if path.exists() else "missing")
    return hash_obj({"files": list(IMPORTER_SCRIPT_FILES), "hashes": parts})


def lexicon_pins(decisions: dict[str, Any]) -> dict[str, Any]:
    """The five pins LEXICON SPEC §3 requires, plus the probe fixture.

    The convention table and shadow probes live under `seed/` and are therefore already
    hashed file-by-file, but they are named here too so a reader of the lock can see the
    lexicon's inputs in one place without diffing the file map.
    """
    from .constants import CONVENTION_TABLE_PATH, SHADOW_PROBES_PATH

    d8 = decisions.get("D8", {})
    return {
        "mathlib_commit": d8.get("mathlib_commit"),
        "nlab_scrape_date": d8.get("nlab_scrape_date"),
        "wordnet_version": d8.get("wordnet_version"),
        "convention_table_sha256": (
            sha256_file(CONVENTION_TABLE_PATH) if CONVENTION_TABLE_PATH.exists() else None
        ),
        "shadow_probes_sha256": (
            sha256_file(SHADOW_PROBES_PATH) if SHADOW_PROBES_PATH.exists() else None
        ),
        "importer_script_hash": importer_script_hash(),
    }


def build_manifest(decisions: dict[str, Any] | None = None, provisional: bool = False) -> dict[str, Any]:
    d = decisions if decisions is not None else load_decisions()
    files = {
        str(p.relative_to(SEED_DIR)).replace("\\", "/"): sha256_file(p) for p in seed_files()
    }
    return {
        "lexicon_pins": lexicon_pins(d),
        "schema": "common-ground/seed-lock/v0",
        "lock_status": "provisional" if provisional else "locked",
        "files": files,
        "constants": C,
        "toolchain": {
            "lean": d.get("D6", {}).get("lean"),
            "python": d.get("D6", {}).get("python"),
            "python_running": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "third_party_runtime_deps": d.get("D6", {}).get("third_party_runtime_deps", []),
        },
        "charts": d.get("D2", {}).get("charts"),
        "extractors": d.get("D4", {}).get("extractors"),
    }


def manifest_hash(manifest: dict[str, Any]) -> str:
    return hash_obj(manifest)


@dataclass(slots=True)
class LockState:
    seed_hash: str
    provisional: bool
    manifest: dict[str, Any]


def build(force: bool = False) -> LockState:
    """Write seed/SEED.lock. Refuses while any decision is unresolved."""
    d = load_decisions()
    pending = unresolved_decisions(d)
    blanks = blank_markers_in_decisions_md()
    if (pending or blanks) and not force:
        detail = []
        if pending:
            detail.append("unresolved decisions: " + ", ".join(pending))
        if blanks:
            detail.append(f"{len(blanks)} blank marker(s) in seed/DECISIONS.md")
        raise GateViolation(
            4,
            "SEED.lock not written — " + "; ".join(detail)
            + ". KICKOFF section 7.1: refuse to proceed past P0 with any blank.",
        )

    manifest = build_manifest(d, provisional=False)
    seed_hash = manifest_hash(manifest)
    payload = {"seed_hash": seed_hash, "manifest": manifest}
    SEED_LOCK_PATH.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return LockState(seed_hash=seed_hash, provisional=False, manifest=manifest)


def load() -> LockState | None:
    if not SEED_LOCK_PATH.exists():
        return None
    payload = json.loads(SEED_LOCK_PATH.read_text(encoding="utf-8"))
    return LockState(
        seed_hash=payload["seed_hash"], provisional=False, manifest=payload["manifest"]
    )


def current() -> LockState:
    """The seed hash to key this run to.

    With a lock present, that is the locked hash. Without one, a *provisional* hash is
    computed over the same manifest with `lock_status: "provisional"`, so it can never
    collide with a real lock hash. A provisional hash is enough to run P0 diagnostics and
    the always-runnable null cells; it is not enough to read a floor, because gate 5
    compares the battery's hash to the run's and the phases refuse to advance without a
    written lock.
    """
    locked = load()
    if locked is not None:
        return locked
    manifest = build_manifest(provisional=True)
    return LockState(seed_hash=manifest_hash(manifest), provisional=True, manifest=manifest)


def verify() -> tuple[bool, list[str]]:
    """Gate 4 tripwire. Recompute every hash and compare against the written lock."""
    locked = load()
    if locked is None:
        return False, ["seed/SEED.lock is absent"]

    problems: list[str] = []
    recomputed = build_manifest(provisional=False)

    old_files: dict[str, str] = locked.manifest.get("files", {})
    new_files: dict[str, str] = recomputed["files"]

    for path in sorted(set(old_files) | set(new_files)):
        before, after = old_files.get(path), new_files.get(path)
        if before is None:
            problems.append(f"added without a seed-morphism: seed/{path}")
        elif after is None:
            problems.append(f"removed without a seed-morphism: seed/{path}")
        elif before != after:
            problems.append(f"content drift: seed/{path} ({before[:12]} -> {after[:12]})")

    if locked.manifest.get("constants") != recomputed["constants"]:
        problems.append("CONSTANTS.json drifted from the lock")

    old_pins = locked.manifest.get("lexicon_pins", {})
    new_pins = recomputed["lexicon_pins"]
    for key in sorted(set(old_pins) | set(new_pins)):
        if old_pins.get(key) != new_pins.get(key):
            problems.append(
                f"lexicon pin drift: {key} ({old_pins.get(key)} -> {new_pins.get(key)})"
            )

    old_tc = dict(locked.manifest.get("toolchain", {}))
    new_tc = dict(recomputed["toolchain"])
    # The *running* interpreter is recorded, not pinned; a different CI runner patch
    # version is not drift. The pinned values are.
    old_tc.pop("python_running", None)
    new_tc.pop("python_running", None)
    if old_tc != new_tc:
        problems.append(f"toolchain drift: {old_tc} -> {new_tc}")

    recomputed_hash = manifest_hash(recomputed)
    if recomputed_hash != locked.seed_hash and not problems:
        problems.append(
            f"seed hash drift with no identified cause: {locked.seed_hash[:12]} -> {recomputed_hash[:12]}"
        )

    return (not problems), problems
