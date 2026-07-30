"""Static checks over the engine's own source. Backs null cell (viii).

The hub invariant says warrant must never flow through the English face. `SenseCore`
already makes that structurally true by not having the fields — but a future edit could
add them back, or an F-path module could reach through `Sense.display`. This module is
the tripwire for that: an AST walk asserting that no code on an F path so much as
*mentions* a display attribute.

"Gate 2, made grep-able at the lexicon layer" — but done on the AST rather than with a
text grep, so a match inside a comment or a docstring is not a false positive and a match
spelled across a line break is not a false negative.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from .constants import REPO_ROOT

#: Attributes that carry display strings. None may be read on an F path.
DISPLAY_ATTRS: frozenset[str] = frozenset({"english_face", "gloss", "notes", "display"})

#: Modules that construct or consume F. If a display string is reachable from any of
#: these, authority is flowing through the hub.
F_PATH_MODULES: tuple[str, ...] = (
    "engine/energy.py",
    "engine/settle.py",
    "engine/meter.py",
    "engine/cast.py",
    "engine/blocks.py",
    "engine/pipeline.py",
    "engine/mint_tape.py",
    "engine/linalg.py",
)

#: Functions that decide addressing or priors and therefore feed F, even though the
#: modules they live in are allowed to touch display elsewhere (for rendering).
F_FEEDING_FUNCTIONS: tuple[tuple[str, str], ...] = (
    ("engine/lexicon.py", "select_sense"),
    ("engine/lexicon.py", "q_edges"),
)


@dataclass(slots=True)
class Violation:
    file: str
    line: int
    attr: str
    context: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line} reads .{self.attr} in {self.context}"


@dataclass(slots=True)
class StaticCheckResult:
    violations: list[Violation] = field(default_factory=list)
    checked_files: int = 0
    checked_functions: int = 0
    core_fields: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.violations


def _read(rel: str, root: Path) -> ast.Module | None:
    path = root / rel
    if not path.exists():
        return None
    return ast.parse(path.read_text(encoding="utf-8"), filename=rel)


def _scan(node: ast.AST, rel: str, context: str) -> list[Violation]:
    out: list[Violation] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr in DISPLAY_ATTRS:
            out.append(Violation(rel, child.lineno, child.attr, context))
        # A string subscript would sidestep attribute access: sense["gloss"].
        elif isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Constant):
            if child.slice.value in DISPLAY_ATTRS:
                out.append(Violation(rel, child.lineno, str(child.slice.value), f"{context} (subscript)"))
    return out


def _find_function(tree: ast.Module, name: str) -> ast.AST | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def check_no_display_on_f_path(root: Path | None = None) -> StaticCheckResult:
    """Null cell (viii). Returns every violation found rather than the first."""
    base = root or REPO_ROOT
    result = StaticCheckResult()

    for rel in F_PATH_MODULES:
        tree = _read(rel, base)
        if tree is None:
            result.violations.append(Violation(rel, 0, "-", "module missing"))
            continue
        result.checked_files += 1
        result.violations.extend(_scan(tree, rel, "module"))

    for rel, func_name in F_FEEDING_FUNCTIONS:
        tree = _read(rel, base)
        if tree is None:
            result.violations.append(Violation(rel, 0, "-", "module missing"))
            continue
        func = _find_function(tree, func_name)
        if func is None:
            result.violations.append(Violation(rel, 0, "-", f"{func_name}() not found"))
            continue
        result.checked_functions += 1
        result.violations.extend(_scan(func, rel, f"{func_name}()"))

    result.core_fields = _sense_core_fields(base)
    for field_name in result.core_fields:
        if field_name in DISPLAY_ATTRS:
            result.violations.append(
                Violation("engine/lexicon.py", 0, field_name, "SenseCore field")
            )

    return result


def _sense_core_fields(root: Path) -> tuple[str, ...]:
    """Field names declared on SenseCore, read from the source rather than by import.

    Reading the AST means the check still reports something useful if importing the
    module is what broke.
    """
    tree = _read("engine/lexicon.py", root)
    if tree is None:
        return ()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SenseCore":
            return tuple(
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            )
    return ()


# --- gate 6: every statistical verdict is decided against a null ----------------------

#: Every site in the engine that builds or reads a statistical band, with its conformance
#: under GATES.md sentence 6.
#:
#: A band is *conforming* when its reference distribution is constructed under the
#: no-effect hypothesis the site is testing — a permutation, a rewire, a forced-consensus
#: ledger, an exact determinism argument. It is *non-conforming* when the reference is a
#: resample of the observation, because such a band moves with the thing it is supposed to
#: police.
#:
#: `role` is what the number does: `decides` means a verdict turns on it, `diagnostic`
#: means it is reported and nothing more. A non-conforming site is tolerable only as a
#: diagnostic.
GATE6_SITES: tuple[dict[str, object], ...] = (
    {
        "site": "engine/meter.py:surrogate_floor_distribution", "role": "diagnostic",
        "reference": "bootstrap resample of the observed loop floors",
        "conforming": False,
        "note": "The original defect. Retained because two amendments kept it as a legacy "
                "diagnostic for comparability; it decides nothing anywhere.",
    },
    {
        "site": "engine/meter.py:second_fdt_surrogate_floor", "role": "decides",
        "reference": "warm/cold label permutation, loop by loop",
        "conforming": True,
        "note": "Null under the no-effect hypothesis that the two arms are exchangeable. "
                "Decides R3 (PREREG-AMENDMENT-1) and floors the mint threshold.",
    },
    {
        "site": "engine/meter.py:loop_permutation_null", "role": "produces",
        "reference": "per-slot warm/cold assignment on one loop, holonomy recomputed",
        "conforming": True,
        "note": "A permutation null, but with only 2**k support — the all-cold assignment "
                "is the observed floor, so a loop can never exceed its own null. Produces "
                "draws; never thresholds on them directly. See pooled_loop_nulls.",
    },
    {
        "site": "engine/meter.py:pooled_loop_nulls", "role": "decides",
        "reference": "leave-one-out pool of the other loops' permutation draws",
        "conforming": True,
        "note": "The threshold R2 reads (PREREG-AMENDMENT-3). Pooling gives the null usable "
                "support; leave-one-out keeps a loop from inflating its own bar. Known "
                "limitation: loops are not exactly exchangeable with one another, so one "
                "loud loop raises everyone else's threshold.",
    },
    {
        "site": "engine/meter.py:within_noise", "role": "unused",
        "reference": "caller-supplied surrogate",
        "conforming": None,
        "note": "Dead helper: no call site. Conformance would inherit from whatever "
                "surrogate a caller passed, which is exactly the ambiguity sentence 6 "
                "exists to remove. Listed so a future caller has to classify itself.",
    },
    {
        "site": "engine/pipeline.py:_q95", "role": "diagnostic",
        "reference": "bootstrap, via surrogate_floor_distribution",
        "conforming": False,
        "note": "Populates MeterResult.surrogate['q95']. Reported on every run; no live "
                "decision reads it.",
    },
    {
        "site": "engine/pipeline.py:run_meter", "role": "produces",
        "reference": "n/a — computes both surrogates and stores them",
        "conforming": None,
        "note": "Producer, not a decision site. It populates MeterResult.surrogate with "
                "both the bootstrap q95 and the second-FDT floor; which of them decides "
                "anything is settled at the reading site.",
    },
    {
        "site": "engine/audit.py:ground_truth_rediscovery", "role": "decides",
        "reference": "per-loop second-FDT label permutation, pooled leave-one-out",
        "conforming": True,
        "note": "Found by this sweep rather than by hand, which is what the sweep is for, "
                "and amended by PREREG-AMENDMENT-3. It previously flagged at "
                "`floor > bootstrap q95`, miscalibrated in the STRICT direction — the "
                "opposite of R4's — since a larger floor raised the bar. The bootstrap "
                "flagging is retained as a reported diagnostic and decides nothing.",
    },
    {
        "site": "engine/audit.py:floor_verdict", "role": "decides",
        "reference": "second_fdt_surrogate_floor",
        "conforming": True,
        "note": "R3 after PREREG-AMENDMENT-1. The bootstrap band is read only to report a "
                "disagreement.",
    },
    {
        "site": "engine/audit.py:prior_insensitivity", "role": "decides",
        "reference": "dropout movement on a degree- and weight-marginal-preserving rewire",
        "conforming": True,
        "note": "R4 after PREREG-AMENDMENT-2, both arms. The superseded self-scaled band "
                "is reported as legacy_self_scaled_band and decides nothing.",
    },
    {
        "site": "engine/nulls.py:cell_iii_empty_corpus", "role": "decides",
        "reference": "exact zero",
        "conforming": True,
        "note": "No band at all. An empty corpus must produce a floor of exactly 0.0 — the "
                "degenerate no-effect null, and the strictest available.",
    },
    {
        "site": "engine/nulls.py:cell_iv_single_doc", "role": "decides",
        "reference": "consensus ledger floor (every block forced to its modal b-value)",
        "conforming": True,
        "note": "An intervention null under 'the document does not disagree with itself'. "
                "Replaced a bootstrap band that made the cell vacuous.",
    },
    {
        "site": "engine/nulls.py:cell_v_duplicate_source", "role": "decides",
        "reference": "DUPLICATE_RESIDUE_TOLERANCE (1e-12), a numerical tolerance",
        "conforming": True,
        "note": "Not a statistical band: the engine is deterministic, so a true duplicate "
                "moves the floor by exactly zero and the tolerance is float noise only.",
    },
    {
        "site": "engine/nulls.py:cell_ix_binding_sanity", "role": "decides",
        "reference": "fixed 5% failure rate, pre-registered in the LEXICON SPEC",
        "conforming": True,
        "note": "Conforming by not being data-derived rather than by being a null. A fixed "
                "pre-registered threshold cannot move with the observation, which is what "
                "sentence 6 forbids — but it is also not calibrated to anything, so it "
                "bounds a bug rate rather than testing a hypothesis.",
    },
    {
        "site": "engine/mint_tape.py:read_tape", "role": "diagnostic",
        "reference": "3x second_fdt_surrogate_floor",
        "conforming": True,
        "note": "Built on the conforming surrogate. Mint is OFF; the flag is logged and "
                "never acted on, so this decides nothing regardless.",
    },
)

#: Functions exempt from classification: they take a band as an argument or are the
#: primitive itself, so they have no reference distribution of their own.
_GATE6_EXEMPT: frozenset[str] = frozenset({"engine/hashing.py:quantile"})

_BAND_CALLS: frozenset[str] = frozenset({"quantile", "surrogate_floor_distribution"})


def _reads_a_band(node: ast.AST) -> bool:
    """True if this function builds a quantile/band or reads a surrogate band entry."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = child.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name in _BAND_CALLS:
                return True
            # `.surrogate.get("q95")` and friends.
            if (isinstance(fn, ast.Attribute) and fn.attr == "get"
                    and isinstance(fn.value, ast.Attribute) and fn.value.attr == "surrogate"
                    and child.args and isinstance(child.args[0], ast.Constant)
                    and child.args[0].value in ("q95", "second_fdt_floor")):
                return True
        if (isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Constant)
                and child.slice.value in ("q95", "second_fdt_floor")
                and isinstance(child.value, ast.Attribute) and child.value.attr == "surrogate"):
            return True
    return False


def check_gate6_classification(root: Path | None = None) -> StaticCheckResult:
    """Every band-building or band-reading function must be classified in GATE6_SITES.

    This is the sweep made permanent. Finding R4's miscalibration took noticing that the
    pattern behind two vacuous null cells might appear elsewhere — a discovery by accident.
    A new band added anywhere in `engine/` now fails this check until someone writes down
    what its reference distribution is and whether that reference is a null or a resample
    of the observation. The next one gets found by audit.

    It classifies rather than forbids. A non-conforming band is allowed to exist as a
    `diagnostic`; what is not allowed is an unexamined one.
    """
    base = root or REPO_ROOT
    result = StaticCheckResult()
    classified = {str(s["site"]) for s in GATE6_SITES} | _GATE6_EXEMPT

    for path in sorted((base / "engine").rglob("*.py")):
        rel = str(path.relative_to(base)).replace("\\", "/")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        result.checked_files += 1
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _reads_a_band(node):
                continue
            result.checked_functions += 1
            site = f"{rel}:{node.name}"
            if site not in classified:
                result.violations.append(
                    Violation(rel, node.lineno, "unclassified band", site)
                )
    return result


def gate6_report() -> list[dict[str, object]]:
    """GATE6_SITES with the non-conforming ones first. What the sweep prints."""
    return sorted(
        (dict(s) for s in GATE6_SITES),
        key=lambda s: (s["conforming"] is True, s["role"] != "decides", str(s["site"])),
    )
