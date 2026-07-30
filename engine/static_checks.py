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
