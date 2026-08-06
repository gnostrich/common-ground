"""THE HUMAN READING SURFACE. A view over the trace, derived from what the response IS.

The perturbation output is a faithful instrument trace — every slot, shift, hop, tier and
receipt — and it is unreadable by a person. This is not a summarizer bolted on top: the three
layers are read straight off what the object says a response is, in the order that makes the
response checkable.

  LAYER 1  WHERE YOU ENTERED — the attachments. Shown FIRST because everything downstream is
           conditioned on them: if the proposer read the input wrongly the whole response is
           wrong, and a person should see that in two seconds rather than after reading it.
  LAYER 2  WHAT ANSWERED — the strongest entries in the trace's moved list, cut at the shift
           KNEE rather than at a count. Entries with a nonzero hop count rank above zero-hop
           entries at equal shift: a hop is the field's contribution and a zero-hop entry is
           only proximity. This module computes neither; it reads both off `Relaxation` and
           orders the rendering to match what the object says a response is.

GATE 10, ON THIS FILE, TWICE — and the second time was self-inflicted. An earlier version of
this docstring asserted that the response consists of the claims propagation carried, which is
a propagation claim in a module that propagates nothing and calls none of the machinery that
would. The check caught it and was right: this file renders a list somebody else computed.

The rewrite then failed the same check, because it NAMED the offending phrase in order to
explain the fix. A static check cannot tell a phrase asserted from a phrase quoted, and it
should not try — so the discipline is to describe the defect without reproducing its words,
which is what this paragraph now does. The wording changed both times; the check did not.
  LAYER 3  WHAT IT MEANS FOR THE FIELD — one line each, rendered ONLY when the underlying
           fact exists. Never templated filler: a line that is always there stops being read.

NOTHING IS DELETED. The full trace remains, collapsed behind "show the trace". This is a VIEW
and takes no three-moves entry — but GATE 10 APPLIES TO ITS WORDING. The surface may not claim
a mechanism and may not attribute a mental state to the field; it renders measured facts in
plain words. `seed/SURFACE.json` pins the phrasings and lists the forbidden ones, because the
words are free choices and a surface whose words drift renders a different answer each release
from the same measurement, with nobody able to say which changed.

DISPLAY TRIM NEVER FEEDS COMPUTATION. `_trim` is called on the way to a string and nowhere
else; the nu-string that addresses, hashes and compares is always the full one. That is gate 8
discipline, and it is why trimming happens here rather than anywhere upstream.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SURFACE_PATH = Path(__file__).resolve().parent.parent / "seed" / "SURFACE.json"

#: Longest claim rendered inline. DISPLAY ONLY — see the module docstring.
DISPLAY_WIDTH = 200


def phrasings(path: Path | str = SURFACE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _trim(nu: str, width: int = DISPLAY_WIDTH) -> str:
    """Strip the chart tag and cut, FOR READING. Never on any path that computes."""
    if nu.startswith("\x01"):
        end = nu.find("\x01", 1)
        if end != -1:
            nu = nu[end + 1:]
    nu = nu.replace("\n", " ").strip()
    return nu if len(nu) <= width else nu[:width - 1].rstrip() + "…"


def knee(shifts: list[float]) -> int:
    """How many movers to show: cut at the largest RELATIVE drop, not at a count.

    A fixed k is a free constant and, worse, the wrong shape — a response with two strong
    entries and one with forty should not both show five. The knee is the largest ratio
    between consecutive sorted shifts, which is scale-free: it finds where the list stops
    being about the same thing, wherever that is.

    TWO CONDITIONS, and the second one is an admission. A gap must DOMINATE — be larger, in
    log space, than every other drop put together — and it must be at least an e-fold.

    Dominance alone is not enough, and finding that out is what this docstring is for. In
    [0.90, 0.85, 0.84] the first drop dominates the second by five to one, and cutting there
    would show one mover out of three that are plainly the same magnitude. In
    [0.90, 0.88, 0.01] the second drop dominates by two hundred to one and is a real cliff.
    Both have a dominant gap; as FRACTIONS of their list's range they are nearly identical
    (83% and 82%). No purely relative rule can separate them, because what separates them is
    absolute: 0.84 is a claim that moved and 0.01 is not.

    So there is exactly one absolute anchor here, and it is stated rather than buried: the
    drop must be at least one nat — a full factor of e. That is a canonical scale rather than
    a fitted one, and it is the only number in this module. Everything else compares the list
    against itself.

    Fewer than three entries cannot have a distinguished gap — there is nothing to distinguish
    it from — so the whole list shows. With no qualifying gap the list is one population and
    all of it shows, which is the honest reading of a flat distribution rather than a failure
    to cut.
    """
    import math

    if len(shifts) < 3:
        return len(shifts)
    drops: list[tuple[float, int]] = []
    for i in range(1, len(shifts)):
        prev, cur = shifts[i - 1], shifts[i]
        if cur <= 0:
            return i
        drops.append((math.log(prev / cur) if prev > cur else 0.0, i))
    if not drops:
        return len(shifts)
    biggest, at = max(drops)
    rest = sum(d for d, _ in drops) - biggest
    return at if (biggest > rest and biggest >= 1.0) else len(shifts)


@dataclass(slots=True)
class Mover:
    """One claim the field moved, as a person reads it."""

    nu: str                                   # trimmed — display only
    chart: str
    shift: float
    hops: int
    path: str = ""                            # the VIA chain, as chart-to-chart hops
    contested: bool = False
    tier: str = ""
    slot: str = ""                            # kept so the surface can be checked vs the trace

    @property
    def direct(self) -> bool:
        return self.hops == 0


@dataclass(slots=True)
class Reading:
    """The three layers, plus the trace they were read off."""

    entered_corresponds: list = field(default_factory=list)
    entered_bears_on: list = field(default_factory=list)
    declined: str = ""
    movers: list[Mover] = field(default_factory=list)
    field_lines: list[str] = field(default_factory=list)
    strength: str = ""
    trace: str = ""

    @property
    def conditioned(self) -> bool:
        return bool(self.movers)

    def render(self, p: dict | None = None) -> str:
        """The whole surface as text. The trace goes behind its toggle, never dropped."""
        p = p or phrasings()
        out: list[str] = [p["layer1"]["heading"]]

        if not (self.entered_corresponds or self.entered_bears_on):
            out.append("  " + (self.declined or p["layer1"]["declined"]))
        for nu, chart in self.entered_corresponds:
            out.append(f"  {p['layer1']['corresponds']} [{chart}] {nu}")
        for nu, chart in self.entered_bears_on:
            out.append(f"  {p['layer1']['bears_on']} [{chart}] {nu}")

        out += ["", p["layer2"]["heading"]]
        if not self.movers:
            out.append("  " + p["layer2"]["none"])
        for m in self.movers:
            how = p["layer2"]["direct"] if m.direct else f"{p['layer2']['reached']} {m.path}"
            line = f"  [{m.chart}] {m.nu}\n      {how}"
            if m.contested:
                line += f"  — {p['layer2']['contested']}"
            out.append(line)

        if self.field_lines:
            out += [""] + self.field_lines

        out += ["", f"({p['trace_toggle']})", self.trace]
        return "\n".join(out)


def _render_path(m) -> str:
    """The VIA chain as chart-to-chart hops. A person reads charts, not slot ids."""
    charts: list[str] = []
    for step in getattr(m, "path", ()) or ():
        for attr in ("src_chart", "dst_chart"):
            c = getattr(step, attr, None)
            if c and (not charts or charts[-1] != c):
                charts.append(c)
    return " → ".join(charts) if charts else f"{m.hops} declared hop(s)"


def read(compiled, p: dict | None = None) -> Reading:
    """Build the surface from a `CompiledInput`. Reads the trace; invents nothing.

    Every value rendered comes off `compiled` — the attachments from the perturbation, the
    movers from the relaxation. There is no path by which a claim reaches the surface without
    being in the trace, which is exactly what `check_faithful` asserts rather than assumes.
    """
    p = p or phrasings()
    out = Reading(trace=compiled.compiled)

    att = compiled.attachment
    if att is not None:
        from .region import BEARS_ON

        for a in att.attachment:
            row = (_trim(a.dst_nu), a.dst_chart)
            if a.kind == BEARS_ON:
                out.entered_bears_on.append(row)
            else:
                out.entered_corresponds.append(row)
        if not att.attachment:
            # CONSULTED AND DECLINED, with its trace — never bare silence.
            t = att.trace()
            out.declined = (p["layer1"]["declined"] + " "
                            + p["layer1"]["declined_detail"].format(
                                objects=t.get("corpus_objects", 0),
                                declared=t.get("declared_in", 0)))

    rel = compiled.relaxation
    if rel is not None and rel.moved:
        # Shift decides; a tie goes to the hop-reached entry. Propagation is the field's
        # contribution, direct touch is proximity, and the ranking says which is which.
        ranked = sorted(rel.moved, key=lambda m: (-m.shift, 1 if m.hops == 0 else 0))
        for m in ranked[:knee([x.shift for x in ranked])]:
            out.movers.append(Mover(
                nu=_trim(m.nu), chart=m.chart, shift=m.shift, hops=m.hops,
                path=_render_path(m), contested=m.contested,
                tier=getattr(m, "weakest_tier", "") or m.tier, slot=m.slot))

    out.field_lines, out.strength = _layer3(compiled, out, p)
    return out


def _tier_rank(tier: str) -> int:
    """Lower is weaker. Unknown sorts weakest — an unknown warrant is not a strong one."""
    order = ("EXTRACTION", "REPO_DOC", "PREMINTED", "AUTHORSHIP", "CI_RECEIPT", "KERNEL")
    return order.index(tier) if tier in order else -1


def _layer3(compiled, reading: Reading, p: dict) -> tuple[list[str], str]:
    """One line each, ONLY when the underlying fact exists.

    A templated line that is always present carries no information and teaches the reader to
    skip the block, so every line here is guarded by the fact it reports.
    """
    lines: list[str] = []

    # LAYER 3 READS THE WHOLE RELAXATION, not the movers layer 2 chose to show. It is "what
    # this means for the FIELD", and a contested block the knee happened to cut is still
    # contested — losing that warning because it ranked low is precisely the failure the
    # faithfulness control exists to prevent.
    rel = compiled.relaxation
    every = list(rel.moved) if rel is not None else []

    contested = [m for m in every if m.contested]
    if contested:
        lines.append(p["layer3"]["contested"].format(
            where="; ".join(f"[{m.chart}] {_trim(m.nu, 80)}" for m in contested[:3])))

    reached = [m for m in every if m.hops > 0]
    if reached:
        # The honest fragility: the minimum-warrant arrow the answer rests on.
        weakest = min(reached, key=lambda m: _tier_rank(
            getattr(m, "weakest_tier", "") or m.tier))
        tier = getattr(weakest, "weakest_tier", "") or weakest.tier
        lines.append(p["layer3"]["weakest"].format(
            arrow=f"[{weakest.chart}] {_trim(weakest.nu, 80)}", tier=tier or "unknown"))

    floor = getattr(compiled, "floor_status", "") or getattr(
        getattr(compiled, "relaxation", None), "floor_status", "")
    if floor:
        lines.append(p["layer3"]["floor"].format(floor=floor))

    strength = ""
    if reading.movers:
        strength = _strength(reading, p)
        lines.append(strength)
    return lines, strength


def _strength(reading: Reading, p: dict) -> str:
    """Response strength, DERIVED — so a reader need not read tiers to know how loud it was.

    Two already-measured inputs: how much distribution actually moved, and the weakest warrant
    under it. The split is on whether ANYTHING rested on better than extraction, which is a
    categorical fact rather than a tuned cutoff.
    """
    mass = sum(m.shift for m in reading.movers)
    reached = [m for m in reading.movers if not m.direct]
    all_extraction = all(_tier_rank(m.tier) <= _tier_rank("EXTRACTION")
                         for m in reading.movers)
    if not reached or (all_extraction and mass < 1.0):
        return p["layer3"]["faint"]
    return p["layer3"]["moderate"] if all_extraction else p["layer3"]["firm"]


def check_faithful(reading: Reading, compiled) -> list[str]:
    """SURFACE-FAITHFULNESS. Every claim shown is in the trace; no CONTESTED mark is lost.

    A surface is a view, and the two ways a view can lie are showing something the measurement
    did not contain and dropping a warning the measurement did. Both are checked, not trusted.
    """
    out: list[str] = []
    rel = compiled.relaxation
    moved = {m.slot: m for m in (rel.moved if rel else ())}
    for m in reading.movers:
        if m.slot not in moved:
            out.append(f"surface shows a claim that is not in the trace: {m.slot[:16]}")
        elif moved[m.slot].contested and not m.contested:
            out.append(f"surface dropped a CONTESTED mark the trace carries: {m.slot[:16]}")

    att = compiled.attachment
    if att is not None:
        shown = len(reading.entered_corresponds) + len(reading.entered_bears_on)
        if shown != len(att.attachment):
            out.append(f"surface shows {shown} attachment(s); the trace has "
                       f"{len(att.attachment)}")
    return out


def check_wording(p: dict | None = None) -> list[str]:
    """GATE 10 for the surface: it renders facts; it does not claim mechanisms or match."""
    p = p or phrasings()
    body = " ".join(str(v) for section in ("layer1", "layer2", "layer3")
                    for v in p[section].values()).lower()
    return [f"the surface says {bad!r}, which claims a mechanism or claims a match"
            for bad in p["forbidden"] if bad.lower() in body]
