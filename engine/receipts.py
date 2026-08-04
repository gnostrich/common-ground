"""Test receipts: the only thing in a code chart that GROUNDS.

Gate 3 names two grounding warrants — "Lean kernel-accept under pinned toolchain; CI-green
test receipts". The Lean half has been unreachable since D6 (no pinned toolchain), so every
Lean slot in this corpus sits at EXTRACTION with zero clamps. The code charts can reach the
second half: a passing test is a receipt, and a receipt is `CI_RECEIPT` tier, which is
clamp-eligible.

**A receipt is not a proposal, so it does not come through the inlet.** `FastTape.propose`
refuses a clamp-eligible warrant by construction — "warrant rises at the gate, never at the
inlet" — so receipts are emitted as `Clamp` objects applied at settlement. That is not a
workaround; it is the two-door architecture doing what it says.

**Three things a receipt is not, each refused rather than approximated:**

- *A test that did not run is not a receipt.* No toolchain, no receipt; every slot stays at
  EXTRACTION. That is the "extraction tier otherwise" branch, and it is the normal case.
- *A failing or skipped test is not a receipt.* Only `pass` counts. A skip is an absence of
  evidence and is recorded as one.
- *A test whose name does not resolve EXACTLY to a declaration is not a receipt.* The
  mapping is a naming convention the language communities actually hold — Go's `TestFoo`
  tests `Foo`, pytest's `test_foo` tests `foo` — and it is applied as an exact key lookup
  against the declarations the segmenter found. If `TestFoo` has no `Foo`, there is no
  receipt for anything. Nearest-match here would be the similarity defect wearing a
  test runner's clothes.

What a receipt grounds is narrow and worth stating plainly: that the declaration's tests
passed under the runner, on this machine, at this commit. It is not a proof of the
declaration's English restatement, and it clamps the declaration's own slot only.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .types import Clamp, Warrant, WarrantTier

#: `TestFoo` / `TestFoo_Bar` -> `Foo`. Go's convention, and `go test` enforces the prefix.
_GO_TEST_RE = re.compile(r"^Test([A-Z]\w*?)(?:_\w+)?$")
#: `test_foo` / `test_foo_when_bar` -> the longest prefix that names a real declaration.
_PY_TEST_RE = re.compile(r"^test_(\w+)$")

RUNNERS = ("go", "pytest")


@dataclass(frozen=True, slots=True)
class Receipt:
    """One passing test, and the declaration it names."""

    runner: str
    test: str
    declaration: str
    package: str
    duration: float = 0.0

    def as_record(self) -> dict[str, object]:
        return {"runner": self.runner, "test": self.test, "declaration": self.declaration,
                "package": self.package}


@dataclass(slots=True)
class RunReport:
    """What a runner actually did. An unavailable runner is a REPORTED fact, not a zero."""

    runner: str
    available: bool
    ran: bool = False
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    receipts: list[Receipt] = None            # type: ignore[assignment]
    unmapped: list[str] = None                # type: ignore[assignment]
    note: str = ""

    def __post_init__(self) -> None:
        if self.receipts is None:
            self.receipts = []
        if self.unmapped is None:
            self.unmapped = []

    def as_record(self) -> dict[str, object]:
        return {"runner": self.runner, "available": self.available, "ran": self.ran,
                "passed": self.passed, "failed": self.failed, "skipped": self.skipped,
                "receipts": len(self.receipts), "unmapped_tests": len(self.unmapped),
                "note": self.note}


def _tool_available(cmd: str) -> bool:
    try:
        subprocess.run([cmd, "version" if cmd == "go" else "--version"],
                       capture_output=True, timeout=30)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def go_receipts(repo_root: str | Path, declarations: set[str],
                timeout: int = 900) -> RunReport:
    """Run `go test -json ./...` and keep the PASSES whose names resolve to a declaration."""
    if not _tool_available("go"):
        return RunReport("go", available=False,
                         note="go is not installed; every go slot stays at EXTRACTION")
    root = Path(repo_root)
    if not any(root.rglob("*_test.go")):
        return RunReport("go", available=True, ran=False, note="no *_test.go in this tree")
    # `go test ./...` only means anything from a MODULE root. Running it at a repository
    # root that merely contains a module reports zero tests and zero failures — which reads
    # exactly like a green run with no tests, and is the most dangerous shape a
    # zero can have here. Every go.mod in the tree is a module root; each is run.
    modules = sorted({m.parent for m in root.rglob("go.mod")
                      if "node_modules" not in m.parts and "vendor" not in m.parts})
    if not modules:
        return RunReport("go", available=True, ran=False,
                         note="*_test.go present but no go.mod: not a module, cannot run")

    report = RunReport("go", available=True, ran=True)
    report.note = f"modules: {', '.join(str(m.relative_to(root)) or '.' for m in modules)}"
    stdout = ""
    for module in modules:
        try:
            proc = subprocess.run(
                ["go", "test", "-json", "-count=1", "./..."], cwd=str(module),
                capture_output=True, text=True, timeout=timeout,
                env={"PATH": "/usr/local/go/bin:/usr/bin:/bin", "HOME": str(Path.home()),
                     "GOFLAGS": "-mod=mod", "GOCACHE": "/tmp/gocache", "GOPATH": "/tmp/gopath"})
            stdout += proc.stdout
        except subprocess.TimeoutExpired:
            report.note += f" | {module.name} exceeded {timeout}s (its receipts are absent)"
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        action, test = event.get("Action"), event.get("Test")
        if not test:
            continue
        if action == "fail":
            report.failed += 1
        elif action == "skip":
            report.skipped += 1
        elif action == "pass":
            report.passed += 1
            match = _GO_TEST_RE.match(test)
            decl = match.group(1) if match else ""
            if decl and decl in declarations:
                report.receipts.append(Receipt("go", test, decl, event.get("Package", "")))
            else:
                report.unmapped.append(test)
    return report


def pytest_receipts(repo_root: str | Path, declarations: set[str],
                    timeout: int = 900) -> RunReport:
    """Run pytest and keep the PASSES whose names resolve to a declaration.

    `--junitxml` because it is the one machine-readable format pytest emits without a
    plugin, and parsing the human report would mean guessing at its formatting.
    """
    import xml.etree.ElementTree as ET

    if not _tool_available("pytest"):
        return RunReport("pytest", available=False,
                         note="pytest is not installed; every python slot stays at EXTRACTION")
    root = Path(repo_root)
    if not (any(root.rglob("test_*.py")) or any(root.rglob("*_test.py"))):
        return RunReport("pytest", available=True, ran=False, note="no test files in this tree")

    # Same lesson as go: pytest run from the wrong directory collects nothing or fails to
    # import, and either way produces a zero that looks like a result. The project root is
    # where the packaging metadata is; failing that, the parent of the tests directory.
    projects = sorted({m.parent for name in ("pyproject.toml", "setup.py", "setup.cfg")
                       for m in root.rglob(name)
                       if ".venv" not in m.parts and "node_modules" not in m.parts})
    if not projects:
        projects = sorted({t.parent.parent if t.parent.name in ("tests", "test") else t.parent
                           for t in list(root.rglob("test_*.py")) + list(root.rglob("*_test.py"))
                           if ".venv" not in t.parts})
    report = RunReport("pytest", available=True, ran=True)
    report.note = f"roots: {', '.join(str(p.relative_to(root)) or '.' for p in projects)}"
    cases = []
    for project in projects:
        out = Path("/tmp") / f"junit-{abs(hash(str(project)))}.xml"
        out.unlink(missing_ok=True)
        try:
            subprocess.run(["pytest", "-q", "--no-header", "-p", "no:cacheprovider",
                            f"--junitxml={out}", "."],
                           capture_output=True, text=True, timeout=timeout, cwd=str(project))
        except subprocess.TimeoutExpired:
            report.note += f" | {project.name} exceeded {timeout}s (its receipts are absent)"
            continue
        if out.exists():
            cases.extend(ET.parse(out).getroot().iter("testcase"))
            out.unlink(missing_ok=True)
    if not cases:
        report.ran = False
        report.note += " | no test cases collected"
        return report
    for case in cases:
        name = case.get("name", "")
        if case.find("failure") is not None or case.find("error") is not None:
            report.failed += 1
            continue
        if case.find("skipped") is not None:
            report.skipped += 1
            continue
        report.passed += 1
        match = _PY_TEST_RE.match(name)
        decl = _resolve_python(match.group(1), declarations) if match else ""
        if decl:
            report.receipts.append(Receipt("pytest", name, decl, case.get("classname", "")))
        else:
            report.unmapped.append(name)
    return report


def _resolve_python(stem: str, declarations: set[str]) -> str:
    """`test_foo_when_bar` -> `foo_when_bar`, else `foo_when`, else `foo`, else nothing.

    Longest-prefix against the declarations that EXIST, so the resolution is an exact lookup
    at every step and simply fails when no prefix names a real declaration. It never picks a
    closest match: pytest's convention is that the name is a prefix of what is tested plus a
    description of the case, and a prefix that names nothing is not evidence about anything.
    """
    parts = stem.split("_")
    for cut in range(len(parts), 0, -1):
        candidate = "_".join(parts[:cut])
        if candidate in declarations:
            return candidate
    return ""


def declarations_from_deltas(deltas, chart: str) -> dict[str, str]:
    """declaration name -> slot id, from the locators the segmenter wrote.

    The segmenter already recorded which declaration each span is (`func:Book.Match`,
    `def:positive`), so the mapping is read off the corpus rather than re-derived. A method's
    bare name is registered too, because a Go test for `Book.Match` is conventionally
    `TestMatch`.
    """
    out: dict[str, str] = {}
    for d in deltas:
        if d.chart != chart:
            continue
        locator = d.provenance.locator
        if ":" not in locator:
            continue
        name = locator.split(":", 1)[1]
        out.setdefault(name, d.slot)
        if "." in name:
            out.setdefault(name.rsplit(".", 1)[1], d.slot)
    return out


def clamps_from_receipts(receipts: Sequence[Receipt],
                         slot_of: dict[str, str]) -> list[Clamp]:
    """Turn receipts into CLAMPS — the gate door, not the inlet door.

    `Clamp.__post_init__` refuses a warrant that is not clamp-eligible, so this cannot
    produce a grounded assignment from anything weaker than a receipt whatever it intends.
    The value is `T`: a green test says the declaration behaves as its tests state.
    """
    out: list[Clamp] = []
    seen: set[str] = set()
    for r in receipts:
        slot = slot_of.get(r.declaration)
        if slot is None or slot in seen:
            continue
        seen.add(slot)
        out.append(Clamp(slot=slot, value="T", warrant=Warrant(
            tier=WarrantTier.CI_RECEIPT,
            detail=f"{r.runner} receipt: {r.test} passed for {r.declaration}")))
    return out
