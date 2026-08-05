"""The atlas: one page showing what is actually in the corpus and what has been bridged.

Every number on this page is read off disk at render time — the journal, the snapshot, the
candidate pool — and nothing is carried in the template. That is the whole design constraint.
An earlier version of this page was assembled by hand from numbers I had in front of me at
the time, which meant it was accurate exactly once and had no way of saying so afterwards.

Three sources, and the page names which figure came from which:

  * `runs/proposer.journal.jsonl` — every pair asked and every answer, including each `none`.
    Cost is the provider's reported figure summed, never an estimate.
  * `runs/corpus.snapshot`        — the read view: slots by chart, fibers, contested blocks.
  * `runs/pool.jsonl`             — the candidate pool, which is where the per-chart-pair
    census comes from. Declaration granularity is what the pool holds; the depth-1 subtree
    census is a separate measurement and is shown only if `runs/census.json` records it.

Where a source is missing the page says so in that section rather than dropping it, because
a section that vanishes looks identical to a section whose number is zero.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .constants import REPO_ROOT
from .corpus_state import SNAPSHOT_PATH, CorpusSnapshot, coverage_caveat

TEMPLATE_PATH = REPO_ROOT / "ui" / "atlas.html"
JOURNAL_PATH = REPO_ROOT / "runs" / "proposer.journal.jsonl"
POOL_PATH = REPO_ROOT / "runs" / "pool.jsonl"
CENSUS_PATH = REPO_ROOT / "runs" / "census.json"
STATUS_PATH = REPO_ROOT / "runs" / "proposer.status.json"

#: One hue per chart. Charts are disjoint by construction, so the colours can be too.
HUE = {
    "english": "#0E7C6B", "lean": "#7C3AED", "python": "#2563EB", "go": "#0891B2",
    "conversation": "#B45309", "tabular": "#BE185D", "correspondence": "#4B5563",
}
FALLBACK_HUE = "#6B7A88"

#: How many worked examples to show. Enough to read, few enough that the page stays a page.
N_EXAMPLES = 8

#: Each slot's surface is truncated to this in the embedded index. The page is one file with
#: no network access, so the whole corpus rides inside it; 12 MB of raw nu-strings against a
#: 16 MB ceiling leaves no room for the markup, and search works on the opening of a claim
#: far more often than on its tail. Truncated text is marked, never silently cut.
NU_BUDGET = 200

#: Arrows are NOT truncated. They are the thing the engine found, and reading half a bridge
#: is not reading it.
N_ARROW_SIDES = 2

_NONE = "none"


@dataclass(slots=True)
class Atlas:
    """Everything the page displays, read off disk. No figure is passed in."""

    slots: int = 0
    by_chart: dict[str, int] = field(default_factory=dict)
    floor: str = ""
    loops: int = 0
    fibers: int = 0
    contested: int = 0
    coverage: str = ""
    sources: dict[str, int] = field(default_factory=dict)
    asked: int = 0
    arrows: int = 0
    none: int = 0
    calls: int = 0
    call_errors: int = 0
    cost: float = 0.0
    answers: dict[str, int] = field(default_factory=dict)
    arrows_by_pair: dict[tuple[str, str], int] = field(default_factory=dict)
    asked_by_pair: dict[tuple[str, str], int] = field(default_factory=dict)
    pool_by_pair: dict[tuple[str, str], int] = field(default_factory=dict)
    pool_total: int = 0
    pool_position: int = 0
    subtree_by_pair: dict[tuple[str, str], int] = field(default_factory=dict)
    examples: list[dict] = field(default_factory=list)
    arrow_records: list[dict] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    running: bool = False
    reason: str = ""

    @property
    def none_rate(self) -> float:
        return self.none / self.asked if self.asked else 0.0


def _read_journal(atlas: Atlas, path: Path) -> None:
    """Replay the ledger. A truncated final line is expected — the writer fsyncs per record,
    so a reader that arrives mid-write sees a partial line and must skip it, not fail."""
    if not path.exists():
        atlas.missing.append("no proposer journal — nothing has been asked yet")
        return
    examples: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = rec.get("kind")
            if kind == "ask":
                answer = rec.get("answer", "")
                atlas.asked += 1
                atlas.answers[answer] = atlas.answers.get(answer, 0) + 1
                pair = (rec.get("src_chart", "?"), rec.get("dst_chart", "?"))
                atlas.asked_by_pair[pair] = atlas.asked_by_pair.get(pair, 0) + 1
                if answer and answer != _NONE:
                    atlas.arrows += 1
                    atlas.arrows_by_pair[pair] = atlas.arrows_by_pair.get(pair, 0) + 1
                    atlas.arrow_records.append(rec)
                    if rec.get("evidence"):
                        examples.append(rec)
                else:
                    atlas.none += 1
            elif kind == "call":
                atlas.calls += 1
                if not rec.get("ok", True):
                    atlas.call_errors += 1
                atlas.cost += float(rec.get("cost") or 0.0)
    atlas.cost = round(atlas.cost, 6)
    atlas.examples = _pick_examples(examples)


def _pick_examples(records: list[dict]) -> list[dict]:
    """The most recent arrow from each chart pair first, then fill from the tail.

    Taking the last N outright showed eight rows from whichever pair the daemon happened to
    be working through, which reads as though the engine only bridges one thing.
    """
    picked, seen = [], set()
    for rec in reversed(records):
        pair = (rec.get("src_chart"), rec.get("dst_chart"), rec.get("answer"))
        if pair not in seen:
            seen.add(pair)
            picked.append(rec)
    for rec in reversed(records):
        if len(picked) >= N_EXAMPLES:
            break
        if rec not in picked:
            picked.append(rec)
    return picked[:N_EXAMPLES]


def _read_pool(atlas: Atlas, path: Path) -> None:
    if not path.exists():
        atlas.missing.append("no candidate pool — run `proposerd.py build-pool`")
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            pair = tuple(sorted((rec.get("src_chart", "?"), rec.get("dst_chart", "?"))))
            atlas.pool_by_pair[pair] = atlas.pool_by_pair.get(pair, 0) + 1
            atlas.pool_total += 1


def _read_snapshot(atlas: Atlas, path: Path, arrows: Sequence | None = None) -> None:
    """The corpus read view, WITH the proposer's arrows laid over it if there are any.

    Without the overlay the page reports a corpus with zero arrows while the daemon has been
    finding them for hours — and, worse, reports the floor as a gap forever, because a cycle
    can only exist once arrows do. The floor is the one figure on this page that describes
    the engine rather than the corpus, so it has to be computed against the live graph.
    """
    snap = CorpusSnapshot.load(path)
    if snap.empty:
        atlas.missing.append("no corpus snapshot — run `proposerd.py build-snapshot`")
        atlas.coverage = coverage_caveat()
        return
    if arrows:
        from .corpus_state import with_arrows
        snap = with_arrows(snap, arrows)
    header = snap.header()
    atlas.slots = int(header["slots"])
    atlas.by_chart = dict(header["by_chart"])
    atlas.floor = str(header["floor"])
    atlas.loops = int(header["loops"])
    atlas.fibers = int(header["fibers"])
    atlas.contested = int(header["contested_slots"])
    atlas.coverage = str(header["coverage"])
    atlas.sources = dict(header["sources"])


def _read_census(atlas: Atlas, path: Path) -> None:
    """The depth-1 subtree census, if a run recorded one. Absent is stated, not implied."""
    if not path.exists():
        atlas.missing.append("no subtree census on disk — the depth-1 column is unmeasured "
                             "in this build (`proposerd.py census` records it)")
        return
    raw = json.loads(path.read_text(encoding="utf-8"))
    for key, n in (raw.get("subtree") or {}).items():
        a, _, b = key.partition("x")
        atlas.subtree_by_pair[tuple(sorted((a.strip(), b.strip())))] = int(n)


def _read_status(atlas: Atlas, path: Path) -> None:
    if not path.exists():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    atlas.running = bool(raw.get("running"))
    atlas.reason = str(raw.get("reason", ""))
    atlas.pool_position = int(raw.get("pool_position") or 0)


def _correspondences(atlas: Atlas) -> list:
    """The journal's arrows as Correspondence objects, for laying over the read view.

    An arrow the constructor refuses (malformed, intra-chart) is SKIPPED rather than coerced,
    exactly as the rest of the engine treats a claim it cannot type.
    """
    from . import EngineError
    from .correspondence import Correspondence

    out = []
    for rec in atlas.arrow_records:
        try:
            out.append(Correspondence(
                src_chart=rec.get("src_chart", ""), src_slot=rec.get("src_slot", ""),
                dst_chart=rec.get("dst_chart", ""), dst_slot=rec.get("dst_slot", ""),
                kind=rec.get("answer", ""), proposer=rec.get("proposer", "lm"),
                prompt_hash=rec.get("prompt_hash", ""),
                evidence=(rec.get("evidence", ""),)))
        except EngineError:
            continue
    return out


def gather(root: Path | None = None) -> Atlas:
    """Read every source. Missing ones are recorded on the Atlas, never silently skipped."""
    base = Path(root) if root else REPO_ROOT
    atlas = Atlas()
    # Journal first: the snapshot's floor is computed against the arrows, so the order is a
    # dependency, not a preference.
    _read_journal(atlas, base / "runs" / "proposer.journal.jsonl")
    _read_snapshot(atlas, base / SNAPSHOT_PATH, _correspondences(atlas))
    _read_pool(atlas, base / "runs" / "pool.jsonl")
    _read_census(atlas, base / "runs" / "census.json")
    _read_status(atlas, base / "runs" / "proposer.status.json")
    return atlas


# --- rendering ----------------------------------------------------------------------------

def _esc(text: object) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _clean_nu(nu: str) -> str:
    """Strip the \\x01 chart tags that ride inside every nu-string. They are part of the
    address, not part of what the author wrote, and they break the page's markup."""
    return " ".join(str(nu).replace("\x01", " ").split())


def _hue(chart: str) -> str:
    return HUE.get(chart, FALLBACK_HUE)


def _bars(atlas: Atlas) -> str:
    if not atlas.by_chart:
        return ('<p class="note">No corpus is loaded. Build one with '
                '<span class="mono">proposerd.py build-snapshot</span>.</p>')
    top = max(atlas.by_chart.values())
    rows = []
    for chart, n in sorted(atlas.by_chart.items(), key=lambda kv: -kv[1]):
        pct = 100.0 * n / top if top else 0.0
        rows.append(
            f'    <div class="chart" style="--hue:{_hue(chart)}">\n'
            f'      <div class="chart-head"><span class="chart-name">{_esc(chart)}</span>'
            f'<span class="chart-n">{n:,}</span></div>\n'
            f'      <div class="track"><div class="fill" style="width:{pct:.1f}%"></div></div>\n'
            f'    </div>')
    return "\n".join(rows)


def _bridges(atlas: Atlas) -> str:
    if not atlas.arrows_by_pair:
        return ('    <li class="bridge"><span class="pn">No arrow has been found yet. '
                'That is a state, not a failure — the ledger records every '
                '<span class="mono">none</span> too.</span></li>')
    top = max(atlas.arrows_by_pair.values())
    rows = []
    for (src, dst), n in sorted(atlas.arrows_by_pair.items(), key=lambda kv: -kv[1]):
        asked = atlas.asked_by_pair.get((src, dst), 0)
        rate = 100.0 * n / asked if asked else 0.0
        width = 100.0 * n / top if top else 0.0
        rows.append(
            f'    <li class="bridge">'
            f'<span class="dot" style="background:{_hue(src)}"></span>'
            f'<span class="pn">{_esc(src)} → {_esc(dst)}</span>'
            f'<span class="arrowline"><span class="al" style="width:{width:.1f}%"></span></span>'
            f'<span class="pc">{n:,}</span>'
            f'<span class="pn">of {asked:,} asked · {rate:.0f}%</span></li>')
    return "\n".join(rows)


def _census(atlas: Atlas) -> str:
    keys = set(atlas.pool_by_pair) | set(atlas.subtree_by_pair)
    if not keys:
        return ('        <tr><td colspan="3">No candidate pool on disk. '
                'Run <span class="mono">proposerd.py build-pool</span>.</td></tr>')
    rows = []
    for pair in sorted(keys, key=lambda p: -atlas.pool_by_pair.get(p, 0)):
        decl = atlas.pool_by_pair.get(pair)
        sub = atlas.subtree_by_pair.get(pair)
        decl_cell = (f'<td class="num strong">{decl:,}</td>' if decl
                     else '<td class="num dim">—</td>')
        sub_cell = (f'<td class="num">{sub:,}</td>' if sub
                    else '<td class="num dim">unmeasured</td>')
        rows.append(f'        <tr><td class="pair">{_esc(pair[0])} × {_esc(pair[1])}</td>'
                    f'{decl_cell}{sub_cell}</tr>')
    total_sub = sum(atlas.subtree_by_pair.values())
    rows.append(f'        <tr><td class="pair"><strong>total</strong></td>'
                f'<td class="num strong">{atlas.pool_total:,}</td>'
                f'<td class="num">{total_sub:,}</td></tr>' if total_sub else
                f'        <tr><td class="pair"><strong>total</strong></td>'
                f'<td class="num strong">{atlas.pool_total:,}</td>'
                f'<td class="num dim">unmeasured</td></tr>')
    return "\n".join(rows)


def _examples(atlas: Atlas) -> str:
    if not atlas.examples:
        return ('    <p class="note">No arrow carries evidence yet.</p>')
    out = []
    for rec in atlas.examples:
        kind = _esc(rec.get("answer", "?"))
        src, dst = _esc(rec.get("src_chart", "?")), _esc(rec.get("dst_chart", "?"))
        evidence = rec.get("evidence") or ""
        halves = str(evidence).split("TARGET", 1)
        left = _esc(_clean_nu(halves[0].replace("SOURCE", "", 1)))[:420]
        right = _esc(_clean_nu(halves[1] if len(halves) > 1 else ""))[:420]
        out.append(
            f'    <div class="ex">\n'
            f'      <header><span class="kind">{kind}</span>'
            f'<span class="route"><i>{src}</i> → <i>{dst}</i></span></header>\n'
            f'      <p class="side">{left or "—"}</p>\n'
            f'      <p class="side alt">{right or "—"}</p>\n'
            f'    </div>')
    return "\n".join(out)


def payload(atlas: Atlas, snapshot: CorpusSnapshot | None = None) -> dict:
    """The corpus itself, embedded so the page can be searched with no network at all.

    An artifact is one self-contained file behind a strict CSP: it cannot call back here, so
    either the corpus rides inside it or the page is a picture of the corpus rather than the
    corpus. This carries both — every arrow in full, and every slot with its surface truncated
    to `NU_BUDGET` and MARKED where it was cut, so a search that misses a long tail is a
    visible limit rather than a silent one.
    """
    snap = snapshot if snapshot is not None else CorpusSnapshot.load(REPO_ROOT / SNAPSHOT_PATH)
    slots = []
    for sid, rec in snap.slots.items():
        nu = _clean_nu(rec.nu)
        cut = len(nu) > NU_BUDGET
        slots.append([sid[:12], rec.chart, rec.type, nu[:NU_BUDGET] + ("…" if cut else "")])
    arrows = []
    for rec in atlas.arrow_records:
        evidence = str(rec.get("evidence") or "")
        halves = evidence.split("TARGET", 1)
        arrows.append([
            rec.get("src_chart", "?"), rec.get("dst_chart", "?"), rec.get("answer", "?"),
            _clean_nu(halves[0].replace("SOURCE", "", 1)),
            _clean_nu(halves[1] if len(halves) > 1 else ""),
        ])
    return {"slots": slots, "arrows": arrows, "nu_budget": NU_BUDGET,
            "truncated": sum(1 for s in slots if s[3].endswith("…"))}


def _floor_note(atlas: Atlas) -> str:
    """What the floor means RIGHT NOW, computed from the loop count rather than remembered.

    The template used to carry "the floor is a gap because no cycle has closed yet" as a flat
    sentence. It was true for weeks and then a cycle closed, which is the single most
    load-bearing event this engine can report — and the page would have gone on denying it.
    Same defect as the coverage caveat, same fix: derive it.
    """
    if atlas.loops:
        return (f"A cycle has closed: {atlas.loops:,} loop"
                f"{'' if atlas.loops == 1 else 's'} across {atlas.fibers:,} fibers, so the "
                f"floor is MEASURABLE for the first time rather than a gap. What it measures "
                f"is disagreement around a closed path — nothing is promoted by it, and "
                f"nothing has been.")
    return ("The floor is a gap because no cycle has closed yet; a number there would be "
            "reporting agreement where there is only absence.")


def render(atlas: Atlas, template: str | None = None) -> str:
    """Fill the template. Every placeholder is derived from `atlas`; none is a literal."""
    text = template if template is not None else TEMPLATE_PATH.read_text(encoding="utf-8")
    state = ("running — " + _esc(atlas.reason)) if atlas.running else _esc(
        atlas.reason or "stopped")
    missing = ("".join(f'<li>{_esc(m)}</li>' for m in atlas.missing)
               or "<li>every source read</li>")
    fills = {
        "{{SLOTS}}": f"{atlas.slots:,}",
        "{{ASKED}}": f"{atlas.asked:,}",
        "{{ARROWS}}": f"{atlas.arrows:,}",
        "{{NONE}}": f"{100 * atlas.none_rate:.0f}",
        "{{COST}}": f"{atlas.cost:.3f}",
        "{{FLOOR}}": _esc(atlas.floor or "no floor"),
        "{{CALLS}}": f"{atlas.calls:,}",
        "{{ERR}}": f"{atlas.call_errors:,}",
        "{{POOLPOS}}": f"{atlas.pool_position:,}",
        "{{NUBUDGET}}": f"{NU_BUDGET}",
        "{{FLOORNOTE}}": _floor_note(atlas),
        "{{POOLTOTAL}}": f"{atlas.pool_total:,}",
        "{{STATE}}": state,
        "{{COVERAGE}}": _esc(atlas.coverage),
        "{{MISSING}}": missing,
        "{{BARS}}": _bars(atlas),
        "{{BRIDGES}}": _bridges(atlas),
        "{{CENSUS}}": _census(atlas),
        "{{EXAMPLES}}": _examples(atlas),
    }
    for token, value in fills.items():
        text = text.replace(token, value)
    return text


def render_with_corpus(atlas: Atlas, snapshot: CorpusSnapshot | None = None,
                       template: str | None = None) -> str:
    """The page, plus the corpus embedded so its search box works with no network."""
    text = render(atlas, template)
    data = payload(atlas, snapshot)
    # `</script` inside a JSON string would close the tag early; the escape is the standard
    # one and is applied to the serialized text, not to the data, so nothing is altered.
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return text.replace("{{PAYLOAD}}", blob).replace(
        "{{TRUNCATED}}", f"{data['truncated']:,}")


def write(out_path: str | Path, root: Path | None = None,
          with_corpus: bool = True) -> dict[str, object]:
    atlas = gather(root)
    text = render_with_corpus(atlas) if with_corpus else render(atlas)
    out = Path(out_path)
    out.write_text(text, encoding="utf-8")
    return {"out": str(out), "bytes": out.stat().st_size, "slots": atlas.slots,
            "asked": atlas.asked, "arrows": atlas.arrows, "cost": atlas.cost,
            "missing": atlas.missing}
