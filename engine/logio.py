"""JSONL run logging on the KICKOFF section-6 schema.

Every record carries `seed_hash`. That is not decoration: a record without it cannot be
attributed to a seed, and gate 5 turns on comparing a null battery's seed hash to the one
a floor was read under.

    {t, phase, block_id?, F_before?, F_after?, cert, seed_hash, beta?, loop_id?,
     hol: {warm, cold}?, hankel_sv[]?, provenance}

Seed-morphism events use the same writer with `phase: "seed-morphism"` and carry
`sigma_summary`, `remap_count`, and `cold_anneal_ref`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from .constants import RUNS_DIR
from .types import SettledBlock


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(slots=True)
class RunLog:
    """Append-only JSONL writer for one run.

    `seq` is a monotone ordinal alongside the wall-clock `t`. The ordinal is what makes a
    log comparable across replays: two runs of the same seed produce the same sequence of
    records with the same ordinals, while their timestamps necessarily differ.
    """

    seed_hash: str
    phase: str
    path: Path
    _seq: int = field(default=0, init=False)

    @classmethod
    def open(cls, seed_hash: str, phase: str, runs_dir: Path | None = None) -> "RunLog":
        base = runs_dir or RUNS_DIR
        base.mkdir(parents=True, exist_ok=True)
        stamp = _now().replace(":", "").replace("-", "")
        path = base / f"{phase}-{seed_hash[:12]}-{stamp}.jsonl"
        return cls(seed_hash=seed_hash, phase=phase, path=path)

    def write(self, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            "t": _now(),
            "seq": self._seq,
            "phase": fields.pop("phase", self.phase),
            "seed_hash": self.seed_hash,
        }
        record.update({k: v for k, v in fields.items() if v is not None})
        self._seq += 1
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        return record

    # --- typed convenience writers ------------------------------------------------

    def settle_record(
        self,
        settled: SettledBlock,
        beta: float,
        provenance: str,
        **extra: Any,
    ) -> dict[str, Any]:
        return self.write(
            block_id=settled.block_id,
            F_before=settled.f_before,
            F_after=settled.f_after,
            cert=settled.certificate,
            beta=beta,
            iterations=settled.iterations,
            backtracks=settled.backtracks,
            grad_norm=settled.grad_norm,
            clamped=list(settled.clamped) or None,
            provenance=provenance,
            **extra,
        )

    def loop_record(
        self,
        loop_id: str,
        beta: float,
        warm: float,
        cold: float,
        shadow: float,
        floor: float,
        provenance: str,
        **extra: Any,
    ) -> dict[str, Any]:
        return self.write(
            loop_id=loop_id,
            beta=beta,
            hol={"warm": warm, "cold": cold},
            shadow=shadow,
            floor=floor,
            cert="monotone",
            provenance=provenance,
            **extra,
        )

    def tape_record(
        self,
        hankel_sv: Sequence[float],
        rank: int,
        mint_flag: bool,
        threshold: float,
        provenance: str,
        **extra: Any,
    ) -> dict[str, Any]:
        return self.write(
            phase="mint-tape",
            hankel_sv=list(hankel_sv),
            effective_rank=rank,
            mint_flag=mint_flag,
            mint_threshold=threshold,
            mint_enabled=False,
            cert="logged-only",
            provenance=provenance,
            **extra,
        )

    def seed_morphism(
        self,
        sigma_summary: str,
        remap_count: int,
        cold_anneal_ref: str,
        provenance: str = "seed",
    ) -> dict[str, Any]:
        """Gate 4. The only legitimate way for addresses to move."""
        return self.write(
            phase="seed-morphism",
            sigma_summary=sigma_summary,
            remap_count=remap_count,
            cold_anneal_ref=cold_anneal_ref,
            cert="monotone",
            provenance=provenance,
        )


def read_log(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def append_registry(entry: dict[str, Any], registry_path: Path) -> None:
    """Append to registry/REGISTRY.jsonl.

    KICKOFF section 7.2 requires the registry entry to be committed *before* the phase
    runs, so this is called by the CLI's pre-run step, not by the phase itself.
    """
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(entry)
    payload.setdefault("t", _now())
    with registry_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
