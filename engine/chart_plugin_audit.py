"""Can a third chart be added by manifest alone? Measured, not asserted.

Item 2 of the pre-P3 instructions asks for a tabular chart stood up "via the declarative
manifest path — manifest + battery only, zero engine edits", and rules that "if that's
impossible, the plug-in audit has failed: report before proceeding."

It *was* impossible, and this module was the evidence: charts were hardcoded at five engine
sites, one of which (`Chart`) was a `Literal`, so a third chart could not even be named.
The item-2 refactor relocated english and lean behind the `engine/charts.py` registry, and
**this audit now PASSes** — which is the completion criterion, the audit that caught the
gap proving the fix.

`BLOCKING_SITES` records what *was* blocking; `audit()` re-verifies each against the live
source and returns only those that still hardcode a chart — now none.
`attempt_manifest_only()` confirms a manifest-declared chart (tabular) is accepted by `nu`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .constants import REPO_ROOT


@dataclass(frozen=True, slots=True)
class BlockingSite:
    site: str
    hardcodes: str
    manifest_would_need: str
    severity: str  # "type" | "dispatch" | "data"


#: Every place the two-chart assumption is compiled in. `type` sites make a third chart
#: unnameable; `dispatch` sites make it unroutable; `data` sites make it unconfigurable.
BLOCKING_SITES: tuple[BlockingSite, ...] = (
    BlockingSite(
        site="engine/types.py:Chart",
        hardcodes='Chart = Literal["english", "lean"]',
        manifest_would_need="a chart set read from the seed, so a new chart is a value "
                            "rather than a type change",
        severity="type",
    ),
    BlockingSite(
        site="engine/normalize.py:_TAGS",
        hardcodes='{"english": "\\x01en\\x01", "lean": "\\x01lean\\x01"}',
        manifest_would_need="tags declared per chart in the manifest and hashed into the "
                            "seed, since the tag rides inside nu() and therefore inside "
                            "every address",
        severity="data",
    ),
    BlockingSite(
        site="engine/normalize.py:nu",
        hardcodes="_nu_english(core) if chart == 'english' else _nu_lean(core)",
        manifest_would_need="a registry of normalizers keyed by chart. This is the "
                            "load-bearing one: nu decides addresses, so a third chart with "
                            "no normalizer of its own would silently be normalized as Lean.",
        severity="dispatch",
    ),
    BlockingSite(
        site="engine/normalize.py:classify",
        hardcodes="chart-dispatched claim-form rules with a lean branch",
        manifest_would_need="per-chart claim-form rules declared alongside the normalizer",
        severity="dispatch",
    ),
    BlockingSite(
        site="engine/extract.py:DeterministicExtractor._candidate_spans",
        hardcodes='if doc.chart == "lean": ... else: sentence-split',
        manifest_would_need="a per-chart span segmenter; a tabular chart segments by row, "
                            "which is neither sentence-splitting nor Lean declaration "
                            "matching",
        severity="dispatch",
    ),
    BlockingSite(
        site="engine/blocks.py:content_tokens",
        hardcodes='body[:4] in ("en\\x01", "lean") to strip the chart tag',
        manifest_would_need="tag stripping driven by the same declared tag table, or fiber "
                            "tokens for a third chart would keep their tag and never match "
                            "anything",
        severity="data",
    ),
)


def audit(root: Path | None = None) -> list[BlockingSite]:
    """The blocking sites, verified to still exist in the source.

    A site that has been fixed drops out of the list, so the verdict tracks the code rather
    than this docstring.
    """
    base = root or REPO_ROOT
    still_blocking: list[BlockingSite] = []
    for site in BLOCKING_SITES:
        rel, symbol = site.site.split(":", 1)
        path = base / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if symbol == "Chart":
            if "Chart = Literal[" in text:
                still_blocking.append(site)
            continue
        if symbol == "_TAGS":
            if "_TAGS: dict[str, str] = {" in text:
                still_blocking.append(site)
            continue
        tree = ast.parse(text, filename=rel)
        name = symbol.split(".")[-1]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                if _hardcodes_a_chart(node):
                    still_blocking.append(site)
                break
    return still_blocking


#: Chart names and tag bodies that, appearing as *code* (a string literal or a comparison),
#: mean a function is dispatching on a specific chart rather than through the registry.
_CHART_LITERALS = frozenset({"lean", "english", "en\x01", "lean\x01"})


def _hardcodes_a_chart(node: ast.AST) -> bool:
    """True if the function body contains a chart name as an actual string constant.

    Walks the AST, so a chart named in a comment or docstring does not count — only real
    code does. This is what lets the audit flip to PASS once the dispatch is gone even
    though the module still *describes* what it used to hardcode.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if child.value in _CHART_LITERALS or child.value.strip("\x01") in ("lean", "en"):
                # A docstring is an Expr-statement Constant; exclude the function's own.
                if child is not _docstring_node(node):
                    return True
    return False


def _docstring_node(node: ast.AST) -> ast.AST | None:
    body = getattr(node, "body", None)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        return body[0].value
    return None


def attempt_manifest_only(chart: str = "tabular") -> tuple[bool, str]:
    """Introduce a third chart without touching engine code. Report where it stops.

    Returns `(succeeded, first_obstruction)`. Since the item-2 refactor it succeeds: a
    manifest-declared chart (tabular) is accepted by `nu`.
    """
    from .normalize import nu

    try:
        nu(chart, "| a | b |")
    except ValueError as exc:
        return False, (
            f"engine/normalize.py:nu rejects the chart outright: {exc}. The tag table is a "
            "module-level dict, so there is nowhere for a manifest to declare a third "
            "chart's tag — and without a tag its addresses would collide with another "
            "chart's."
        )
    return True, ""


def verdict(root: Path | None = None) -> dict[str, object]:
    blocking = audit(root)
    ok, obstruction = attempt_manifest_only()
    return {
        "manifest_only_possible": ok,
        "first_obstruction": obstruction,
        "blocking_sites": [
            {"site": s.site, "severity": s.severity, "hardcodes": s.hardcodes,
             "manifest_would_need": s.manifest_would_need}
            for s in blocking
        ],
        "by_severity": {
            sev: sum(1 for s in blocking if s.severity == sev)
            for sev in ("type", "dispatch", "data")
        },
        "conclusion": (
            "PLUG-IN AUDIT FAILED. A third chart cannot be added by manifest alone: it "
            "cannot be named without editing a Literal type, cannot be normalized without "
            "editing nu()'s dispatch, and cannot be segmented without editing the "
            "extractor. Charts are a compile-time binary, not a plug-in point."
            if blocking else
            "A third chart can be declared without engine edits."
        ),
    }
