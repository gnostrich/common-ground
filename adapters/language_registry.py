"""The repo-intake language registry — now a VIEW of the engine's one manifest.

This module arrived on `claude/repo-intake-adapter` with its own loader and its own schema
over `seed/LANGUAGES.json` (`chart-worthy` / `reference-tier` / `shelf`, filename rules, a
default row). The rebase onto HEAD found the collision that design implies: the router had
since been given the same job, wired into `engine/router.py` and reading the same filename,
with a different schema. One file, two readers, two rule vocabularies — and the operator's
ruling on exactly this was "wired into engine/router.py, not a parallel adapter path,
because a second intake path is a second set of rules to keep in agreement."

So the loader is gone and this is a translation layer over `engine.languages`. The mapping
is stated rather than implied:

    engine `chart`     -> "chart-worthy",     routed to that chart by extension alone
    engine `classify`  -> "content-classified", the router decides (transcript/table/prose)
    engine `reference` -> "reference-tier",   read and counted, never ingested
    engine `shelf`     -> "shelf"

`content-classified` is a class PR #3's schema did not have, and its absence was the real
incompatibility: that design routed a `.md` file to English on its extension, while the
router routes it on its content and can send it to the tabular or conversation chart
instead. Collapsing the two would have silently narrowed markdown to prose.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.languages import CHART, CLASSIFY, REFERENCE, SHELF, rule_for, rules

CHART_WORTHY = "chart-worthy"
CONTENT_CLASSIFIED = "content-classified"
REFERENCE_TIER = "reference-tier"
SHELVED = "shelf"

_CLASS_OF = {CHART: CHART_WORTHY, CLASSIFY: CONTENT_CLASSIFIED,
             REFERENCE: REFERENCE_TIER, SHELF: SHELVED}


@dataclass(frozen=True, slots=True)
class LanguageSpec:
    """The verdict for one file: classification, destination chart (if any), why, and rule."""
    classification: str
    chart: str
    reason: str
    rule: str


def classify_path(name: str) -> LanguageSpec:
    """Classify by the ENGINE's manifest. There is exactly one, and this reads it."""
    rule = rule_for(name)
    return LanguageSpec(
        classification=_CLASS_OF[rule.cls],
        chart=rule.chart,
        reason=rule.why or f"seed/LANGUAGES.json: {rule.ext} -> {rule.cls}",
        rule=f"extension:{rule.ext}",
    )


def all_rules() -> tuple[LanguageSpec, ...]:
    return tuple(
        LanguageSpec(classification=_CLASS_OF[r.cls], chart=r.chart,
                     reason=r.why or f"seed/LANGUAGES.json: {r.ext} -> {r.cls}",
                     rule=f"extension:{r.ext}")
        for r in sorted(rules().values(), key=lambda r: (r.cls, r.ext)))


def chart_worthy_charts() -> frozenset[str]:
    """Charts reachable by extension alone. `content-classified` files are not counted here:
    which chart they reach is a property of their content, not of their name."""
    return frozenset(r.chart for r in rules().values() if r.cls == CHART and r.chart)
