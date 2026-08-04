"""The extension -> chart map, as seed data. The other half of the chart plug-in contract.

`engine/charts.py` made a chart's *identity and behavior* declarative: a manifest row, plus
(if the behavior is new) a normalizer, a classifier and a segmenter. `chart_plugin_audit`
then reported PASS. It was measuring the wrong half.

Routing was still compiled in. `engine/router.py` decided Lean with
`name.endswith(".lean")` — a Python string literal — so a chart could be declared, tagged,
normalized, classified and segmented, and *still* have nothing route to it. That is the
seam this module closes: which chart an extension enters is now a row in
`seed/LANGUAGES.json`, read here, consulted by the router.

Four classes, and the third is the point:

- ``chart``     — enters the named chart on its extension alone, before any content rule.
- ``classify``  — content decides (transcript / table / prose). The default.
- ``reference`` — **read and counted, never ingested.** The engine has no chart for this
                  language. Saying so with a number is the honest form of a gap; walking
                  past the file in an `if ext in {...}` at the call site is not, and that
                  is precisely how 1,405 `.py` files became invisible without anything in
                  the system reporting a zero.
- ``shelf``     — skipped, hashed and counted only.

This module is data-only, like `engine/charts.py`: it imports nothing from the behavior
layer, so the router can import it without a cycle.
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import EngineError
from .constants import SEED_DIR

LANGUAGES_PATH = SEED_DIR / "LANGUAGES.json"

CHART = "chart"
CLASSIFY = "classify"
REFERENCE = "reference"
SHELF = "shelf"

#: The wildcard row's extension. Its class is the default for anything unlisted, and it is
#: written in the manifest rather than defaulted in code so that the default is auditable.
WILDCARD = "*"

_CLASSES = frozenset({CHART, CLASSIFY, REFERENCE, SHELF})


@dataclass(frozen=True, slots=True)
class LanguageRule:
    ext: str
    cls: str
    chart: str = ""
    why: str = ""
    filename: str = ""      # an exact basename rule; wins over any extension rule


@lru_cache(maxsize=1)
def rules() -> dict[str, LanguageRule]:
    """Every declared rule, keyed by lower-cased extension. Validated on load.

    A row whose class is `chart` must name a chart that `seed/CHARTS.json` declares: a
    manifest that could route to a chart which does not exist would be a manifest that lies,
    and the failure would show up as an address in an undeclared chart rather than as an
    error here.
    """
    from .charts import chart_names

    raw = json.loads(Path(LANGUAGES_PATH).read_text(encoding="utf-8"))
    declared = set(chart_names())
    out: dict[str, LanguageRule] = {}
    for row in raw.get("rules", ()):
        filename = str(row.get("filename", ""))
        ext = filename.lower() if filename else str(row.get("ext", "")).lower()
        cls = str(row.get("cls") or row.get("class", ""))
        if (not ext and not filename and "ext" not in row) or cls not in _CLASSES:
            raise EngineError(f"LANGUAGES.json: bad row {row!r}; class must be one of "
                              f"{sorted(_CLASSES)}")
        chart = str(row.get("chart", ""))
        if cls == CHART and chart not in declared:
            raise EngineError(
                f"LANGUAGES.json: {ext} routes to chart {chart!r}, which seed/CHARTS.json "
                f"does not declare (declared: {sorted(declared)})")
        out[ext] = LanguageRule(ext=ext, cls=cls, chart=chart, why=str(row.get("why", "")),
                                filename=filename)
    if WILDCARD not in out:
        raise EngineError(
            "LANGUAGES.json must declare a '*' row: the default has to be readable in the "
            "manifest, not hidden in the router")
    return out


def extension_of(name: str) -> str:
    """The artifact's extension, lower-cased. `''` when it has none.

    A document id may be `<repo>||<path>` or a chat message id like `claude||<uuid>:3`; the
    extension is taken from the last path segment only, so a dotted directory or a uuid with
    hyphens cannot masquerade as one.
    """
    tail = name.rpartition("||")[2] or name
    tail = posixpath.basename(tail.split("#", 1)[0])
    dot = tail.rfind(".")
    return tail[dot:].lower() if dot > 0 else ""


def basename_of(name: str) -> str:
    """The artifact's file name, for the FILENAME rules. `''` when it has none."""
    tail = name.rpartition("||")[2] or name
    return posixpath.basename(tail.split("#", 1)[0])


def rule_for(name: str) -> LanguageRule:
    """The rule governing this artifact. Falls back to the declared rows, never to code.

    Precedence, and each step is a manifest row rather than a branch here:

    1. an exact FILENAME rule (`package-lock.json`) — adopted from the repo-intake registry,
       because a generated lockfile is not classified by being JSON;
    2. the extension rule;
    3. the `""` row when the artifact has NO extension — a chat message id has no name to
       key on, so content decides, which is what the router always did;
    4. the `*` row for an extension nobody declared — SHELVED, because an undeclared
       extension is more likely a binary than prose and reading one manufactures claims.
    """
    table = rules()
    named = table.get(basename_of(name).lower())
    if named is not None and named.filename:
        return named
    ext = extension_of(name)
    hit = table.get(ext)
    if hit is not None:
        return hit
    return table.get("", table[WILDCARD]) if not ext else table[WILDCARD]


def report() -> list[dict[str, object]]:
    """The manifest as a table, for the audit and the report header."""
    return [{"ext": r.ext, "class": r.cls, "chart": r.chart, "why": r.why}
            for r in sorted(rules().values(), key=lambda r: (r.cls, r.ext))]
