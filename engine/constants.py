"""SEED.lock-scope constants, loaded from seed/CONSTANTS.json.

Nothing in the engine may hardcode a value that lives in CONSTANTS.json. The JSON is
hashed into SEED.lock; a constant duplicated in Python would drift silently past the
gate-4 tripwire.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = REPO_ROOT / "seed"
RUNS_DIR = REPO_ROOT / "runs"
REPORTS_DIR = REPO_ROOT / "reports"
REGISTRY_DIR = REPO_ROOT / "registry"

CONSTANTS_PATH = SEED_DIR / "CONSTANTS.json"
DECISIONS_PATH = SEED_DIR / "DECISIONS.json"
SHADOW_PATH = SEED_DIR / "shadow.json"
PARAPHRASE_PATH = SEED_DIR / "paraphrase_suite.json"
SEED_LOCK_PATH = SEED_DIR / "SEED.lock"


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


C: dict[str, Any] = _load(CONSTANTS_PATH)

# --- settlement -------------------------------------------------------------------
LAMBDA: float = float(C["lambda"])
LAMBDA2: float = float(C["lambda2"])
ETA: float = float(C["eta"])
SETTLE_GRAD_TOL: float = float(C["settle_grad_tol"])
SETTLE_MAX_ITERS: int = int(C["settle_max_iters"])
SETTLE_MAX_BACKTRACKS: int = int(C["settle_max_backtracks"])

# --- fibers and casting -----------------------------------------------------------
FIBER_CAP: int = int(C["fiber_cap"])
CAST_T2_START: float = float(C["cast_t2_start"])
CAST_T2_END: float = float(C["cast_t2_end"])
CAST_T2_DECAY: float = float(C["cast_t2_decay"])

# --- mint tape (LOGGED ONLY; mint is OFF) -----------------------------------------
HANKEL_WINDOW: int = int(C["hankel_window"])
MINT_THRESHOLD_MULTIPLE: float = float(C["mint_threshold_multiple"])
MINT_ENABLED: bool = bool(C["mint_enabled"])

# --- ontology ---------------------------------------------------------------------
BVALUES: tuple[str, ...] = tuple(C["bvalues"])
NBV: int = len(BVALUES)
BVALUE_INDEX: dict[str, int] = {v: i for i, v in enumerate(BVALUES)}
CHARTS: tuple[str, ...] = tuple(C["charts"])
CLAIM_FORMS: tuple[str, ...] = tuple(C["claim_forms"])

# --- protocol arms ----------------------------------------------------------------
BETA_ARMS: tuple[float, ...] = tuple(float(b) for b in C["beta_arms"])
SURROGATE_TRIALS: int = int(C["surrogate_trials"])
SURROGATE_QUANTILE: float = float(C["surrogate_quantile"])
PRIOR_DROPOUT_RATE: float = float(C["prior_dropout_rate"])
PRIOR_DROPOUT_TRIALS: int = int(C["prior_dropout_trials"])
NULL_FUZZ_SAMPLES: int = int(C["null_fuzz_samples"])

# --- fiber construction (a prior; gate 2 confines it to energy) -------------------
FIBER_TOKEN_PREFIX: int = int(C["fiber"]["token_prefix"])
FIBER_INTRA_THRESHOLD: float = float(C["fiber"]["intra_chart_jaccard_threshold"])
FIBER_CROSS_THRESHOLD: float = float(C["fiber"]["cross_chart_jaccard_threshold"])
STOPWORDS: frozenset[str] = frozenset(C["fiber"]["stopwords"])

# --- markers (part of the addressing function; plastic under gate 4) --------------
MARKERS_DEONTIC: tuple[str, ...] = tuple(C["markers"]["deontic"])
MARKERS_CONDITIONAL: tuple[str, ...] = tuple(C["markers"]["conditional"])
MARKERS_DEFINITIONAL: tuple[str, ...] = tuple(C["markers"]["definitional"])
LEAN_DEFINE_HEADS: tuple[str, ...] = tuple(C["lean_define_heads"])
LEAN_CLAIM_HEADS: tuple[str, ...] = tuple(C["lean_claim_heads"])

# Numerical floor for probabilities. Keeps log(p) finite in the entropic mirror map.
EPS: float = 1e-12


def decisions() -> dict[str, Any]:
    """Read seed/DECISIONS.json fresh. Not cached: the lock builder checks it late."""
    return _load(DECISIONS_PATH)


def shadow() -> dict[str, Any]:
    return _load(SHADOW_PATH)


def paraphrase_suite() -> dict[str, Any]:
    return _load(PARAPHRASE_PATH)
