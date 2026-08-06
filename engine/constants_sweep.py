"""OI-4's ENFORCEMENT: every constant is DERIVED, SWEPT, or CONFESSED — never picked.

The invariant existed and its control did not. The auditor invoked `tests.test_constants`, a
module that has never existed, and reported the failure as a FINDING rather than a pass —
which is the auditor working — but the check itself has never run once. An invariant with a
dead control is an invariant on paper.

THE THREE LEGAL PROVENANCES, and the rule is that a constant must claim one:

  DERIVED    forced by the object. `k/(k-1)` is fixed by the k=2 anchor where a fiber is one
             declared pair and freedom is zero. Aging's halving is scale-free. Coverage
             pressure is unwalked mass and self-extinguishes. No choice was made.
  SWEPT      measured across a range on fixed fixtures, found stable in a band, and pinned
             inside it WITH the sweep as its justification.
  CONFESSED  chosen, and SAID to be chosen, with the reason it has not been derived or swept
             and what would settle it. A confessed constant is honest; an unlabelled one is
             a number nobody can argue with because nobody can find its argument.

WHAT THIS SWEEP DOES. It reads every numeric module-level constant in `engine/` and checks it
against `seed/CONSTANTS.json`'s provenance map. A constant with no entry is UNMARKED — the
finding. It does not judge whether a derivation is good; it enforces that one is claimed,
which is the difference between an argument you can check and a number you cannot.

WHAT IT DELIBERATELY IGNORES: a value used once inside a function is a local, not a constant of
the object; and a constant whose name states its own provenance in the module docstring still
needs the seed entry, because a claim that lives only in prose is the thing gate 10 exists
against.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
SEED = ENGINE.parent / "seed" / "CONSTANTS.json"
PROVENANCE = ENGINE.parent / "seed" / "CONSTANT_PROVENANCE.json"

DERIVED, SWEPT, CONFESSED = "derived", "swept", "confessed"
LEGAL = (DERIVED, SWEPT, CONFESSED)

#: Names that are not constants of the object: loop bounds, display widths, string lengths in
#: renderers. Each is listed explicitly rather than matched by pattern, because a pattern
#: would quietly absorb the next real constant somebody names `MAX_` something.
NOT_OBJECT_CONSTANTS = frozenset({
    "DISPLAY_WIDTH", "HISTORY_DEPTH", "MIN_SENTENCE_CHARS", "MIN_CONTENT", "MIN_TERM",
    "MIN_PHRASE", "MAX_WORDS", "MAX_NOMINATED", "MAX_UPLOAD", "TOP_TERMS", "TOP_FIBERS",
    "TOP_LOOPS", "N_EXAMPLES", "HUBS", "HUB_CAP", "CHUNK", "MIN_FIBER", "MAX_TURNS",
})


@dataclass(frozen=True)
class Finding:
    module: str
    name: str
    value: str
    reason: str

    def render(self) -> str:
        return f"{self.module}:{self.name} = {self.value} — {self.reason}"


def _numeric(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return repr(node.value)
    if isinstance(node, ast.BinOp):
        # ARITHMETIC, EVALUATED. `ast.literal_eval` refuses multiplication — it allows only
        # +/- and then only for complex literals — so a constant written `2 * HANKEL_WINDOW`
        # or `64 * 1024` returned None and ESCAPED THE SWEEP ENTIRELY. A constant that is
        # computed is still a constant, and hiding from the sweep by arithmetic is exactly
        # the gap an unmarked number would use.
        left, right = _numeric(node.left), _numeric(node.right)
        if left is None or right is None:
            return None
        try:
            op = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
                  ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
                  ast.FloorDiv: lambda a, b: a // b, ast.Pow: lambda a, b: a ** b}[type(node.op)]
            return repr(op(ast.literal_eval(left), ast.literal_eval(right)))
        except Exception:
            return None
    return None


def constants(root: Path | None = None) -> list[tuple[str, str, str]]:
    """(module, NAME, value) for every module-level numeric constant in the engine."""
    base = root or ENGINE
    out: list[tuple[str, str, str]] = []
    for f in sorted(base.glob("*.py")):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            targets = []
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets, value = [node.target.id], node.value
            else:
                continue
            v = _numeric(value) if value is not None else None
            if v is None:
                continue
            for name in targets:
                if name.isupper() and name not in NOT_OBJECT_CONSTANTS:
                    out.append((f.name, name, v))
    return out


def provenance() -> dict:
    if not PROVENANCE.exists():
        return {}
    return json.loads(PROVENANCE.read_text(encoding="utf-8")).get("constants", {})


def unmarked(root: Path | None = None) -> list[Finding]:
    """Constants claiming no provenance, and entries claiming an illegal one."""
    known = provenance()
    out: list[Finding] = []
    for module, name, value in constants(root):
        entry = known.get(name)
        if entry is None:
            out.append(Finding(module, name, value,
                               "no provenance: a constant must claim derived, swept or "
                               "confessed, or it is a number nobody can argue with"))
        elif entry.get("provenance") not in LEGAL:
            out.append(Finding(module, name, value,
                               f"provenance {entry.get('provenance')!r} is not one of "
                               f"{LEGAL}"))
        elif not str(entry.get("why", "")).strip():
            out.append(Finding(module, name, value,
                               "provenance claimed with no argument — a label is not a "
                               "derivation"))
    return out


def render(findings: list[Finding]) -> str:
    if not findings:
        return "constants sweep: every engine constant claims a provenance."
    return ("constants sweep: UNMARKED constants\n"
            + "\n".join("  " + f.render() for f in findings))


if __name__ == "__main__":                                     # pragma: no cover
    found = unmarked()
    print(f"{len(constants())} engine constant(s)")
    print(render(found))
    raise SystemExit(1 if found else 0)
