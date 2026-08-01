"""The chart registry: charts as a seed-declared manifest, not a compile-time literal.

Before this, a chart was a member of `Chart = Literal["english", "lean"]` and its tag was a
module constant, so a third chart could not be *named* without an engine edit — which the
plug-in audit (`engine/chart_plugin_audit.py`) caught. Now a chart is a row in
`seed/CHARTS.json`:

    {"name": "english", "tag": "en", "behavior": "prose"}

`name` is the chart id used throughout the engine. `tag` is the control-character tag `nu`
wraps every normalized surface in, so it rides inside every address — which is exactly why
it lives in the seed and is hashed into `SEED.lock` (gate 4) rather than sitting as a silent
code constant. `behavior` selects which normalizer / classifier / segmenter the chart uses;
those are code, keyed by behavior id in `normalize.py` and `extract.py`.

Adding a chart is therefore: one manifest row, plus (only if the behavior is new) a
normalizer, a classifier, and a segmenter registered under the behavior id. **No dispatch
edit** — there is no `if chart == ...` anywhere in the engine. That is the plug-in property
the audit demands, and the audit flips to PASS once it holds.

This module is data only. It imports nothing from the engine's behavior layer, so
`normalize.py` and `extract.py` can import *it* without a cycle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from .constants import SEED_DIR

CHARTS_PATH = SEED_DIR / "CHARTS.json"

TAG_OPEN = "\x01"


@dataclass(frozen=True, slots=True)
class ChartSpec:
    """One chart's declaration. Pure manifest data; behavior is keyed by `behavior`."""

    name: str
    tag_id: str        # the bare id, e.g. "en"; the wrapped tag is `\x01en\x01`
    behavior: str

    @property
    def tag(self) -> str:
        return f"{TAG_OPEN}{self.tag_id}{TAG_OPEN}"


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, ChartSpec], tuple[str, ...]]:
    payload = json.loads(CHARTS_PATH.read_text(encoding="utf-8"))
    specs: dict[str, ChartSpec] = {}
    order: list[str] = []
    seen_tags: dict[str, str] = {}
    for row in payload["charts"]:
        spec = ChartSpec(name=row["name"], tag_id=row["tag"], behavior=row["behavior"])
        if spec.name in specs:
            raise ValueError(f"duplicate chart {spec.name!r} in {CHARTS_PATH}")
        if not spec.tag_id.isalpha() or not spec.tag_id.islower():
            # The re-entry stripper is `^\x01[a-z]+\x01`; a tag outside that is unstrippable
            # and would break idempotence, hence addressing.
            raise ValueError(f"chart {spec.name!r}: tag {spec.tag_id!r} must be [a-z]+")
        if spec.tag_id in seen_tags:
            raise ValueError(
                f"chart {spec.name!r} reuses tag {spec.tag_id!r} of {seen_tags[spec.tag_id]!r}; "
                "two charts sharing a tag would collide on every address"
            )
        seen_tags[spec.tag_id] = spec.name
        specs[spec.name] = spec
        order.append(spec.name)
    return specs, tuple(order)


def chart_spec(name: str) -> ChartSpec:
    specs, _ = _load()
    try:
        return specs[name]
    except KeyError:
        raise ValueError(
            f"unknown chart {name!r}; declared charts are {', '.join(chart_names())}"
        ) from None


def chart_names() -> tuple[str, ...]:
    _, order = _load()
    return order


def is_chart(name: str) -> bool:
    specs, _ = _load()
    return name in specs


def tag_of(name: str) -> str:
    return chart_spec(name).tag
