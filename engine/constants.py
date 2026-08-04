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

# --- casting ----------------------------------------------------------------------
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
#: The chart set is declared in seed/CHARTS.json (the manifest) — the single source of
#: truth since the item-2 plug-in refactor. This is kept as a convenience re-export, read
#: from the manifest rather than from CONSTANTS.json so the two cannot drift.
def _chart_names() -> tuple[str, ...]:
    import json
    payload = json.loads((SEED_DIR / "CHARTS.json").read_text(encoding="utf-8"))
    return tuple(row["name"] for row in payload["charts"])


CHARTS: tuple[str, ...] = _chart_names()
CLAIM_FORMS: tuple[str, ...] = tuple(C["claim_forms"])

# --- protocol arms ----------------------------------------------------------------
#: Verification budget multipliers. NOT temperatures.
BETA_ARMS: tuple[float, ...] = tuple(float(b) for b in C["beta_arms"])
SURROGATE_TRIALS: int = int(C["surrogate_trials"])
SURROGATE_QUANTILE: float = float(C["surrogate_quantile"])
PRIOR_DROPOUT_RATE: float = float(C["prior_dropout_rate"])
PRIOR_DROPOUT_TRIALS: int = int(C["prior_dropout_trials"])
#: Double-edge-swap passes per edge in the R4 null rewire (PREREG-AMENDMENT-2).
REWIRE_PASSES: int = int(C["rewire_passes"])
#: Null MAD below which a loop's permutation scale is degenerate and it falls
#: back to raw leave-one-out pooling (PREREG-AMENDMENT-3 studentization repair).
STUDENTIZE_MIN_SCALE: float = float(C["studentize_min_scale"])
#: Optional non-word normalization stage (item 4). OFF by default; flipping it
#: on is a seed edit (gate 4) because it moves prose addresses.
SPELLCHECK_ENABLED: bool = bool(C.get("spellcheck", {}).get("enabled", False))
NULL_FUZZ_SAMPLES: int = int(C["null_fuzz_samples"])
SINGLE_DOC_TOLERANCE: float = float(C["single_doc_tolerance"])
DUPLICATE_RESIDUE_TOLERANCE: float = float(C["duplicate_residue_tolerance"])

# --- lexicon ----------------------------------------------------------------------
# NB: `source_beta` is the lexicon source-authority tier. The meter's `beta` is the
# VERIFICATION BUDGET (arms 1x/4x). Two unrelated quantities; KICKOFF and the lexicon
# addendum both call theirs "beta", so this codebase keeps them apart by name.
LEX: dict[str, Any] = C["lexicon"]
SOURCE_ORDER: tuple[str, ...] = tuple(LEX["source_order"])
SOURCE_BETA: dict[str, float] = {k: float(v) for k, v in LEX["source_beta"].items()}
SELECT_W_FRAME: float = float(LEX["select"]["w_frame"])
SELECT_W_TYPE: float = float(LEX["select"]["w_type"])
SELECT_W_NEIGHBOUR: float = float(LEX["select"]["w_neighbour"])
#: Retained in CONSTANTS.json for the record; NOT used by `select_sense`.
#: source_beta reaches F through `lexicon.fiber_prior_weights`, as energy.
SELECT_W_SOURCE_BETA: float = float(LEX["select"]["w_source_beta"])
SELECT_W_LEMMA: float = float(LEX["select"]["w_lemma"])
SELECT_MARGIN: float = float(LEX["select"]["margin"])
RMAP_ABBREVIATIONS: dict[str, str] = dict(LEX["rmap_abbreviations"])
FRAME_CUES: dict[str, tuple[str, ...]] = {
    k: tuple(v) for k, v in LEX["frame_cues"].items()
}

LEXICON_DIR = SEED_DIR / "LEXICON"
CONVENTION_TABLE_PATH = LEXICON_DIR / "convention_table.json"
SHADOW_PROBES_PATH = LEXICON_DIR / "shadow_probes.json"


def convention_table() -> dict[str, Any]:
    return _load(CONVENTION_TABLE_PATH)


def shadow_probes() -> dict[str, Any]:
    return _load(SHADOW_PROBES_PATH)


# Fiber membership is EXACT declared correspondence (engine/correspondence.py), not a
# similarity threshold, so there are no fiber-similarity constants: the `fiber` block and
# `fiber_cap` were removed from seed/CONSTANTS.json in the same seed-morphism.

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
