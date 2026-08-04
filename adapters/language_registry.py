"""The repo-intake language registry: a seed-declared manifest, not an `if ext == ...`
chain.

`repo_adapter.py` needs to know, for an arbitrary file in an arbitrary repo, whether it is
chart-worthy (routed straight to a `Document` on its chart), reference-tier (held —
counted and hashed, no `Document`, no ingestion), or shelf (skipped, hashed only). That
decision lives in `seed/LANGUAGES.json`, loaded here, mirroring exactly the shape
`engine/charts.py` gives the chart manifest itself: data in the seed, a thin loader in
code, no dispatch logic hardcoded anywhere that has to be edited to add a row.

Adding a new chart-worthy language later touches no code in this file or in
`repo_adapter.py`: (1) a chart manifest row plus behavior functions, `engine/charts.py`'s
own pattern; (2) one row here pointing the extension at that chart's name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from engine.constants import SEED_DIR

LANGUAGES_PATH = SEED_DIR / "LANGUAGES.json"

_CLASSES = frozenset({"chart-worthy", "reference-tier", "shelf"})


@dataclass(frozen=True, slots=True)
class LanguageRule:
    match: str              # "filename" | "extension"
    pattern: str
    classification: str     # one of _CLASSES
    chart: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class LanguageSpec:
    """The verdict for one file: classification, destination chart (if any), why, and
    which manifest rule (or "default") decided it — carried through so a caller can report
    "held for reason X" rather than just "held"."""

    classification: str
    chart: str | None
    reason: str
    rule: str


@lru_cache(maxsize=1)
def _load() -> tuple[tuple[LanguageRule, ...], tuple[LanguageRule, ...], LanguageSpec]:
    payload = json.loads(LANGUAGES_PATH.read_text(encoding="utf-8"))
    filename_rules: list[LanguageRule] = []
    extension_rules: list[LanguageRule] = []
    seen_patterns: set[tuple[str, str]] = set()

    for row in payload["rules"]:
        cls = row["class"]
        if cls not in _CLASSES:
            raise ValueError(f"language rule {row!r}: class {cls!r} not one of {sorted(_CLASSES)}")
        if cls == "chart-worthy" and not row.get("chart"):
            raise ValueError(f"language rule {row!r}: chart-worthy row names no chart")
        match = row["match"]
        if match not in ("filename", "extension"):
            raise ValueError(f"language rule {row!r}: match must be 'filename' or 'extension'")
        pattern = row["pattern"].lower() if match == "extension" else row["pattern"]
        key = (match, pattern)
        if key in seen_patterns:
            raise ValueError(f"duplicate language rule for {match}={pattern!r}")
        seen_patterns.add(key)
        rule = LanguageRule(match=match, pattern=pattern, classification=cls,
                            chart=row.get("chart"), reason=row["reason"])
        (filename_rules if match == "filename" else extension_rules).append(rule)

    default_row = payload["default"]
    if default_row["class"] not in _CLASSES:
        raise ValueError(f"default class {default_row['class']!r} not one of {sorted(_CLASSES)}")
    default_spec = LanguageSpec(classification=default_row["class"], chart=default_row.get("chart"),
                                reason=default_row["reason"], rule="default")
    return tuple(filename_rules), tuple(extension_rules), default_spec


def classify_path(name: str) -> LanguageSpec:
    """Classify a file by its name. Filename-exact rules win over extension rules — a
    lockfile named `*.json` is `shelf`, not the generic `.json` reference-tier rule — the
    same "most specific, first match wins" convention `engine/router.py` uses.
    """
    filename_rules, extension_rules, default_spec = _load()
    for rule in filename_rules:
        if name == rule.pattern:
            return LanguageSpec(rule.classification, rule.chart, rule.reason, f"filename:{rule.pattern}")
    suffix = Path(name).suffix.lower()
    for rule in extension_rules:
        if suffix == rule.pattern:
            return LanguageSpec(rule.classification, rule.chart, rule.reason, f"extension:{rule.pattern}")
    return default_spec


def all_rules() -> tuple[LanguageRule, ...]:
    filename_rules, extension_rules, _ = _load()
    return filename_rules + extension_rules


def chart_worthy_charts() -> frozenset[str]:
    """Every chart named by a chart-worthy rule — used to cross-check against
    `engine/charts.py:chart_names()` so a manifest drift (a language routed to a chart that
    was never registered) is caught structurally rather than by a silent misroute."""
    return frozenset(r.chart for r in all_rules() if r.classification == "chart-worthy" and r.chart)
