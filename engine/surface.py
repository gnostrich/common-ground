"""The usable surface (item A): a report + a query surface over a fixture run.

This is the first thing you can open. It runs the real pipeline — ingest -> address ->
prior -> block -> settle -> meter — over a synthetic four-chart corpus and renders the
result two ways (markdown + a self-contained HTML page you can open in a browser), plus a
small query surface so you can interrogate it: slots, contested blocks, cross-chart
correspondences, the conversation proposal->verdict ledger, and the holonomy floors.

It is a **view, not an extension**. It reads the object; it adds no base, no measure, no
morphism — which is exactly why it carries no three-moves registry entry. The belonging
audit is about what extends the object; a report observes it.

Everything here is synthetic. No corpus is read, nothing is promoted, and the floors are the
*shape* of an eventual verdict on fixtures — never a verdict on the real corpus, which stays
held on D5. `build_report()` says so on the page.
"""

from __future__ import annotations

import html
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

import json

from . import seed_lock
from .conversation import ProposalVerdict, proposal_verdict_ledger
from .constants import BETA_ARMS, SEED_DIR, shadow
from .extract import build_k_extractors
from .pipeline import Ledger, build_ledger, run_meter
from .router import route_all
from .types import Delta, Document


# ---- the fixture corpus: one document per chart, routed through the front-end ----

_PROSE = (
    "Positivity is preserved under composition. "
    "The cone is positive. However, the cone is not positive in the degenerate case. "
    "If the kernel accepts, the statement is certified."
)
_TABLE = (
    "| lemma | status |\n"
    "|---|---|\n"
    "| comp_pos | proved |\n"
    "| add_pos | open |\n"
)
_DIALOGUE = (
    "Alice: The cone is positive under composition.\n"
    "Bob: Yes, agreed, the cone stays positive under composition.\n"
    "Alice: The spectral radius equals the largest eigenvalue.\n"
    "Carol: No, that is wrong; the spectral radius is the maximum modulus eigenvalue.\n"
    "Bob: The transfer defect is first order in the perturbation.\n"
    "Alice: More precisely, the transfer defect is first order only to leading order.\n"
)
_LEAN = (
    "theorem comp_pos (f g : Cone) : IsPositive (f ∘ g) := by simp\n"
    "theorem add_pos (f g : Cone) : IsPositive (f + g)"
)


def fixture_documents() -> tuple[list[Document], dict[str, int]]:
    """Route the fixtures. English/tabular/conversation come through the router; the Lean
    doc is added directly, because real Lean routing is gated on D6 (elaboration) and would
    otherwise shelf — the fixture stands in for a kernel-checked source.
    """
    report = route_all([
        ("claims.md", _PROSE),
        ("table.md", _TABLE),
        ("dialogue.md", _DIALOGUE),
    ])
    docs = report.to_charts()
    docs.append(Document("thm.lean", "lean", _LEAN, "lean_corpus"))
    routing = report.counts()
    routing["lean (fixture, D6-gated in prod)"] = 1
    return docs, routing


# ---- the report ----

@dataclass(slots=True)
class SlotView:
    chart: str
    type: str
    value: str          # modal b-value across this slot's deltas
    nu: str


@dataclass(slots=True)
class Correspondence:
    charts: tuple[str, ...]
    nus: tuple[str, ...]
    block: str


@dataclass(slots=True)
class ArmResult:
    beta: float
    loops: int
    mean_floor: float
    q95: float
    second_fdt_floor: float
    certificates: tuple[str, ...]
    no_cycle_support: tuple[str, ...]


@dataclass(slots=True)
class Report:
    routing: dict[str, int]
    ledger_summary: dict[str, int]
    slots: list[SlotView]
    correspondences: list[Correspondence]
    contested: list[str]
    arms: list[ArmResult]
    translator_drift: float | None
    verdicts: list[ProposalVerdict]
    status: dict[str, str]

    def by_chart(self) -> dict[str, int]:
        c: Counter = Counter(s.chart for s in self.slots)
        return dict(sorted(c.items()))


def _modal_value(slot_id: str, deltas: Sequence[Delta]) -> str:
    votes: Counter = Counter()
    for d in deltas:
        if d.slot == slot_id:
            votes[d.value] += d.confidence
    if not votes:
        return "-"
    return sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _correspondences(ledger: Ledger) -> list[Correspondence]:
    """Fibers whose slots span two or more charts — the inter-chart agreements/contests."""
    block_of = {s: b.id for b in ledger.blocks for s in b.slots}
    nu_of = {s.id: s.nu for s in ledger.slots}
    chart_of = ledger.chart_of
    out: list[Correspondence] = []
    for fib in ledger.fibers:
        members = list(getattr(fib, "slots", getattr(fib, "members", ())))
        charts = tuple(sorted({chart_of[m] for m in members if m in chart_of}))
        if len(charts) >= 2:
            out.append(Correspondence(
                charts=charts,
                nus=tuple(nu_of.get(m, m)[:48] for m in members),
                block=block_of.get(members[0], "-"),
            ))
    return out


def build_report() -> Report:
    docs, routing = fixture_documents()
    extractors = build_k_extractors(_d4(), offline=True)
    ledger = build_ledger(docs, extractors)

    lock = seed_lock.current()
    arms: list[ArmResult] = []
    drift: float | None = None
    for beta in BETA_ARMS:
        result, _warm, cold = run_meter(ledger, beta, lock.seed_hash, shadow())
        certs = tuple(sorted({s.certificate for s in cold.values()}))
        arms.append(ArmResult(
            beta=beta,
            loops=len(result.measurements),
            mean_floor=result.mean_floor(),
            q95=float(result.surrogate.get("q95", 0.0)),
            second_fdt_floor=float(result.surrogate.get("second_fdt_floor", 0.0)),
            certificates=certs,
            no_cycle_support=tuple(result.no_cycle_support),
        ))
        if drift is None:
            drift = _drift(result)

    slots = [
        SlotView(chart=s.chart, type=s.type,
                 value=_modal_value(s.id, ledger.deltas), nu=s.nu)
        for s in ledger.slots
    ]
    contested = [b.id for b in ledger.contested_blocks]
    verdicts = proposal_verdict_ledger(_DIALOGUE)

    status = {
        "phase": "P0-P2 (fixtures only)",
        "P3": "HELD on D5 (STATEMENTS.md / pre-minted files) — floors below are on "
              "SYNTHETIC fixtures, not a verdict on the real corpus",
        "charts": ", ".join(sorted(self_charts())),
        "gates": "gate6 / gate7 / faithfulness / probes / three-moves all green",
        "mint (K)": "INERT — the conversation ledger is produced, nothing is promoted",
    }
    return Report(
        routing=routing,
        ledger_summary=ledger.summary(),
        slots=slots,
        correspondences=_correspondences(ledger),
        contested=contested,
        arms=arms,
        translator_drift=drift,
        verdicts=verdicts,
        status=status,
    )


def self_charts() -> tuple[str, ...]:
    from .charts import chart_names
    return chart_names()


def _d4() -> dict:
    path = SEED_DIR / "DECISIONS.json"
    if path.exists():
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("D4", {}).get("extractors"):
            return d
    # Fixture fallback: a self-contained k=3 offline bank so the surface runs even before
    # DECISIONS.json is fully wired.
    return {"D4": {"extractors": [
        {"id": "k0", "model": "modelA", "prompt": "extract_v1"},
        {"id": "k1", "model": "modelA", "prompt": "extract_v2"},
        {"id": "k2", "model": "modelB", "prompt": "extract_v1"},
    ]}}


def _drift(result) -> float | None:
    fn = getattr(result, "translator_drift", None)
    if callable(fn):
        try:
            return float(fn())
        except Exception:
            return None
    return None


# ---- the query surface ----

def query(report: Report, selector: str, arg: str | None = None) -> list[str]:
    """Interrogate a report. Selectors: slots | contested | verdicts | floors |
    correspondences | chart <name> | find <term>."""
    sel = selector.lower()
    if sel == "slots":
        return [f"{s.chart:<12} {s.type:<11} {s.value}  {s.nu[:60]}" for s in report.slots]
    if sel == "contested":
        return report.contested or ["(no contested blocks in the fixture)"]
    if sel == "verdicts":
        return [f"{v.verdict:<10} {v.proposer}->{v.decided_by or '-'}  {v.proposal[:60]}"
                for v in report.verdicts]
    if sel == "floors":
        return [f"beta={a.beta}: loops={a.loops} floor={a.mean_floor:.8f} "
                f"q95={a.q95:.8f} 2ndFDT={a.second_fdt_floor:.8f} certs={a.certificates}"
                for a in report.arms]
    if sel == "correspondences":
        return [f"{'+'.join(c.charts)} @ {c.block}: {' | '.join(c.nus)}"
                for c in report.correspondences] or ["(no cross-chart fibers in the fixture)"]
    if sel == "chart":
        return [f"{s.type:<11} {s.value}  {s.nu[:60]}"
                for s in report.slots if s.chart == (arg or "")] or [f"(no slots for {arg!r})"]
    if sel == "find":
        term = (arg or "").casefold()
        return [f"{s.chart:<12} {s.value}  {s.nu[:60]}"
                for s in report.slots if term in s.nu.casefold()] or [f"(no slot matches {arg!r})"]
    raise ValueError(f"unknown query {selector!r}; try: slots contested verdicts floors "
                     "correspondences 'chart <name>' 'find <term>'")


# ---- rendering ----

def render_markdown(report: Report) -> str:
    L = report.ledger_summary
    lines = [
        "# common-ground — fixture report",
        "",
        f"**{report.status['P3']}**",
        "",
        "## Routing (ingestion front-end)",
        "",
        "| destination | n |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(report.routing.items())],
        "",
        "## Object at a glance",
        "",
        "| quantity | n |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in L.items()],
        f"| charts in play | {len(report.by_chart())} |",
        "",
        "## Slots by chart",
        "",
        "| chart | n |", "|---|---|",
        *[f"| {c} | {n} |" for c, n in report.by_chart().items()],
        "",
        "## Cross-chart correspondences (fibers spanning >=2 charts)",
        "",
        *([f"- **{'+'.join(c.charts)}** @ {c.block}: {' | '.join(c.nus)}"
           for c in report.correspondences] or ["_(none in this fixture)_"]),
        "",
        "## Holonomy floors (per beta arm) — SYNTHETIC",
        "",
        "| beta | loops | mean floor | q95 | 2nd-FDT | certificates |",
        "|---|---|---|---|---|---|",
        *[f"| {a.beta} | {a.loops} | {a.mean_floor:.8f} | {a.q95:.8f} | "
          f"{a.second_fdt_floor:.8f} | {', '.join(a.certificates) or '-'} |" for a in report.arms],
        "",
        f"translator drift (measured vs declared shadow): "
        f"{report.translator_drift if report.translator_drift is not None else 'n/a'}",
        "",
        "## Conversation ledger — proposal -> verdict (p_fast content; K inert)",
        "",
        "| verdict | proposer | decided by | proposal |",
        "|---|---|---|---|",
        *[f"| {v.verdict} | {v.proposer} | {v.decided_by or '-'} | {v.proposal} |"
          for v in report.verdicts],
        "",
        "## Status",
        "",
        *[f"- **{k}**: {v}" for k, v in report.status.items()],
        "",
    ]
    return "\n".join(lines)


_CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#e3e3e3;--acc:#2a6;--card:#fafafa}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#e8e8e8;--mut:#9aa;--line:#2a2f36;--acc:#5db98b;--card:#1b1e24}}
:root[data-theme=dark]{--bg:#14161a;--fg:#e8e8e8;--mut:#9aa;--line:#2a2f36;--acc:#5db98b;--card:#1b1e24}
:root[data-theme=light]{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#e3e3e3;--acc:#2a6;--card:#fafafa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:2rem}
.wrap{max-width:960px;margin:0 auto}h1{font-size:1.5rem;margin:0 0 .2rem}
h2{font-size:1.05rem;margin:2rem 0 .6rem;color:var(--acc)}
.note{background:var(--card);border-left:3px solid var(--acc);padding:.7rem 1rem;border-radius:4px;color:var(--mut)}
table{border-collapse:collapse;width:100%;margin:.3rem 0;font-size:13.5px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:.35rem .6rem;text-align:left;white-space:nowrap}
th{background:var(--card)}code,.nu{font-family:ui-monospace,Menlo,monospace;font-size:12.5px}
.v{font-weight:600}.accepted{color:var(--acc)}.rejected{color:#d5566b}.sharpened{color:#c98a2a}.open{color:var(--mut)}
.grid{display:flex;gap:1.2rem;flex-wrap:wrap}.grid table{flex:1;min-width:260px}
footer{margin-top:2rem;color:var(--mut);font-size:12px;border-top:1px solid var(--line);padding-top:.8rem}
"""


def _t(rows: list[list[str]], head: list[str]) -> str:
    h = "".join(f"<th>{html.escape(c)}</th>" for c in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"


def render_html(report: Report) -> str:
    L = report.ledger_summary
    routing = _t([[html.escape(k), str(v)] for k, v in sorted(report.routing.items())],
                 ["destination", "n"])
    glance = _t([[k, str(v)] for k, v in L.items()], ["quantity", "n"])
    bychart = _t([[c, str(n)] for c, n in report.by_chart().items()], ["chart", "n"])
    corr = ("".join(f"<li><b>{'+'.join(c.charts)}</b> @ {html.escape(c.block)}: "
                    f"<span class=nu>{html.escape(' | '.join(c.nus))}</span></li>"
                    for c in report.correspondences)
            or "<li><i>none in this fixture</i></li>")
    floors = _t([[str(a.beta), str(a.loops), f"{a.mean_floor:.8f}", f"{a.q95:.8f}",
                  f"{a.second_fdt_floor:.8f}", html.escape(", ".join(a.certificates) or "-")]
                 for a in report.arms],
                ["beta", "loops", "mean floor", "q95", "2nd-FDT", "certs"])
    verd = _t([[f"<span class='v {v.verdict}'>{v.verdict}</span>", html.escape(v.proposer),
                html.escape(v.decided_by or "-"), html.escape(v.proposal)]
               for v in report.verdicts],
              ["verdict", "proposer", "decided by", "proposal"])
    slots = _t([[html.escape(s.chart), html.escape(s.type), f"<span class=v>{html.escape(s.value)}</span>",
                 f"<span class=nu>{html.escape(s.nu[:70])}</span>"] for s in report.slots],
               ["chart", "type", "b", "nu"])
    status = "".join(f"<li><b>{html.escape(k)}</b>: {html.escape(v)}</li>"
                     for k, v in report.status.items())
    drift = report.translator_drift
    return f"""<div class="wrap">
<h1>common-ground — fixture report</h1>
<p class="note">{html.escape(report.status['P3'])}</p>
<h2>Routing (ingestion front-end)</h2>{routing}
<div class="grid"><div><h2>Object at a glance</h2>{glance}</div>
<div><h2>Slots by chart</h2>{bychart}</div></div>
<h2>Cross-chart correspondences</h2><ul>{corr}</ul>
<h2>Holonomy floors per beta arm <small>(synthetic)</small></h2>{floors}
<p class="note">translator drift (measured vs declared shadow): {drift if drift is not None else 'n/a'}</p>
<h2>Conversation ledger — proposal &rarr; verdict <small>(p_fast; K inert)</small></h2>{verd}
<h2>Slots</h2>{slots}
<h2>Status</h2><ul>{status}</ul>
<footer>Synthetic fixtures only. No corpus was read; nothing was promoted. Floors are the
shape of an eventual verdict, not a verdict. P3 held on D5.</footer>
</div>"""


def html_page(report: Report) -> str:
    return (f"<!doctype html><html><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>common-ground — fixture report</title><style>{_CSS}</style></head>"
            f"<body>{render_html(report)}</body></html>")
