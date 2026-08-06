"""THE MAP-VS-TERRITORY SWEEP: which controls check text where they claim to check behaviour.

THE LAW. A control that inspects source text instead of executing the path is testing the MAP,
not the territory. Any control asserting a RUNTIME property must exercise the runtime.

It is a law rather than an observation because the instances stopped being accidents. The
`/seed` endpoint raised on its first filesystem statement and returned nothing to any client,
while every control over it was green — each was a substring check over `inspect.getsource`,
so "returns 404 when unconfigured" was verified by finding the characters `404` in the file.
Before that, a JS syntax error killed the whole page with 887 server-side tests passing, and
the fix for THAT shipped a null dereference which parsed cleanly and threw on its first DOM
statement, because a parse check is still a check on the text.

WHAT THIS MODULE DOES AND DOES NOT DECIDE. It finds every test that reads source or file
text — that part is mechanical and exact. It does NOT decide which of those are wrong, because
the distinction is about what a control CLAIMS, not whether it opens a file:

  a control asserting a SOURCE property is right to read source — "this module contains no
    tokenizer", "no docstring claims a mechanism the call graph lacks", "the prompt names
    every warrant it will accept". Executing something would not check those, and converting
    one into a runtime check destroys the guard.
  a control asserting a RUNTIME property and reading source instead is the defect.

That judgement is carried in `seed/CONTROL-SWEEP.md`, produced by reading each control against
the property its class docstring says it defends. This module reports the population and the
registry's coverage of it, so a new source-reading control cannot appear unclassified.

THE BLIND SPOT, stated here because a sweep that hides its own limits is worse than none: a
control that DOES execute, with a fixture simpler than the thing it stands for, satisfies this
law and fails anyway. Three in one session — a stub with no `id` attribute that took a
fallback branch, a bound method that serialised as a method, and a source scan standing in for
an HTTP request. Executing is necessary and not sufficient.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

TESTS = Path(__file__).resolve().parent.parent / "tests"
TRIAGE = Path(__file__).resolve().parent.parent / "seed" / "CONTROL-SWEEP.md"

#: Calls that pull text out of a file or a live object's source. Finding one does not convict
#: the control; it puts it in the population that must be classified.
READERS = frozenset({"getsource", "getsourcelines", "getsourcefile",
                     "read_text", "read_bytes", "readlines"})


@dataclass(frozen=True)
class Control:
    file: str
    test: str
    line: int
    readers: tuple

    @property
    def key(self) -> str:
        return f"{self.file}::{self.test}"

    def render(self) -> str:
        return f"{self.file}:{self.line} {self.test}() reads {', '.join(self.readers)}"


def _class_of(tree: ast.AST, target: ast.FunctionDef) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and target in node.body:
            return node.name
    return ""


def source_reading_controls(tests_dir: Path | None = None) -> list[Control]:
    """Every test that reads source or file text. Mechanical, exact, and non-judgemental."""
    base = tests_dir or TESTS
    out: list[Control] = []
    for f in sorted(base.glob("test_*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test"):
                continue
            found = sorted({n.func.attr for n in ast.walk(node)
                            if isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Attribute)
                            and n.func.attr in READERS})
            if found:
                cls = _class_of(tree, node)
                out.append(Control(file=f.name,
                                   test=f"{cls}.{node.name}" if cls else node.name,
                                   line=node.lineno, readers=tuple(found)))
    return out


def classified_keys(triage: Path | None = None) -> set:
    """Which controls the triage document has actually ruled on."""
    p = triage or TRIAGE
    if not p.exists():
        return set()
    keys = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        if "::" not in line:
            continue
        # BY MARKDOWN CELL, not by tokenizing the line. A bare `.split()` inside a registered
        # guard is the forbidden shape whatever it happens to be doing, and `engine/
        # referee_sweep` was right to refuse it here rather than grant an exemption: the cell
        # boundary is the document's own declared structure, so reading it is reading a
        # grammar rather than manufacturing tokens.
        for cell in line.split("|"):
            cell = cell.strip().strip("`, ")
            if "::" in cell and " " not in cell:
                keys.add(cell)
    return keys


def unclassified(tests_dir: Path | None = None, triage: Path | None = None) -> list[Control]:
    """Source-reading controls the triage has not ruled on.

    A new one appearing unclassified is the thing this guards: the population is allowed to
    grow, and it is not allowed to grow silently.
    """
    known = classified_keys(triage)
    return [c for c in source_reading_controls(tests_dir) if c.key not in known]


def render(controls: list[Control]) -> str:
    if not controls:
        return "control sweep: every source-reading control is classified."
    return ("control sweep: UNCLASSIFIED source-reading controls\n"
            + "\n".join("  " + c.render() for c in controls))


if __name__ == "__main__":                                     # pragma: no cover
    pop = source_reading_controls()
    print(f"{len(pop)} source-reading control(s) in the suite")
    print(render(unclassified()))
