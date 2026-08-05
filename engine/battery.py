"""THE STANDING BATTERY on the perturbation path. Not an acceptance test — a gate.

Three pinned inputs (`seed/BATTERY.json`), one pinned paraphrase pair, and four properties
that must hold on every deployed build. It exists because the perturbation path has failed
four distinct ways in one week, each of which looked like working software from the outside:

  * the field never consulted at all — an extractor gate bounced the input before the call
  * a silent zero — "nothing moved", with no way to tell a decline from a filter
  * a cliff — one phrasing answered in full, a near-identical one answered with nothing
  * two mechanisms — the window on a candidate list, the sampler on regions

FOUR PROPERTIES, and which half of each is mechanism:

  NO SILENT ZERO   — every input yields a conditioned region OR a trace saying which question
                     was put, how many objects were seated, and what came back. Pure
                     mechanism, gated hermetically.
  GRADED           — attachment strength ordered sharp > question > vague. The MEDIUM supplies
                     the grade; the mechanism's job is to carry it without flattening it, and
                     that half is gated hermetically by holding the medium's answers fixed in
                     shape and varying only the KIND. The live ordering needs the live medium
                     and is measured by `run_live`.
  STATEFUL         — the same input against a corpus with one more arrow must compile
                     differently. Pure mechanism.
  ONE CODE PATH    — the perturb path and the walk share the region implementation, and no
                     candidate-list iteration exists anywhere. Pure mechanism, checked
                     structurally rather than by inspection.

`run_live` runs the same battery against the real corpus and the real medium, so a deployed
build reports its own grading rather than being trusted to have it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .corpus_state import CorpusSnapshot
from .perturb import Perturbation, perturb, relax_from
from .region import BEARS_ON

BATTERY_PATH = Path(__file__).resolve().parent.parent / "seed" / "BATTERY.json"

#: Verdicts. RED is a deploy blocker; the battery states which property failed and why.
GREEN, RED = "GREEN", "RED"


def load_battery(path: Path | str = BATTERY_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass(slots=True)
class Reading:
    """One pinned input's result. Everything the four properties are judged from."""

    id: str
    text: str
    consulted: bool = False
    conditioned: bool = False
    seated: int = 0
    attached: int = 0
    bears_on: int = 0
    corresponds: int = 0
    extracted: int = 0
    moved: int = 0
    reached: int = 0                          # moved through a declared arrow, not biased directly
    region_id: str = ""
    #: Declared arrows per corpus object in the region this input was put into. The structural
    #: quantity the curve is testing: a richer field should mean a denser diagram to complete.
    density: float = 0.0
    trace: dict = field(default_factory=dict)
    error: str = ""

    @property
    def tightness(self) -> tuple:
        """How TIGHT this input's attachment is, as an orderable key.

        Correspondence-kind attachments rank above `bears_on` because they assert a
        proposition-level relation; among equals, fewer attachment points is tighter, since a
        bias that attaches to everything has localized nothing. The key is deliberately
        crude — the battery asserts an ORDER, not a magnitude, and a magnitude here would be a
        number nobody could defend.
        """
        return (1 if self.corresponds else 0, -self.attached if self.attached else 0)

    def as_record(self) -> dict[str, object]:
        return {"id": self.id, "text": self.text, "consulted": self.consulted,
                "conditioned": self.conditioned, "seated": self.seated,
                "attached": self.attached, "bears_on": self.bears_on,
                "corresponds": self.corresponds, "extracted": self.extracted,
                "moved": self.moved, "reached": self.reached, "region": self.region_id,
                "density": round(self.density, 4), "trace": self.trace, "error": self.error}


@dataclass(slots=True)
class BatteryReport:
    """The verdict, per property, with the reason. A bare GREEN would be worth nothing."""

    readings: list[Reading] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)

    @property
    def verdict(self) -> str:
        return RED if any(v == RED for v in self.properties.values()) else GREEN

    def as_record(self) -> dict[str, object]:
        return {"verdict": self.verdict, "properties": dict(self.properties),
                "reasons": dict(self.reasons),
                "readings": [r.as_record() for r in self.readings]}


def read_one(text: str, ident: str, snapshot: CorpusSnapshot, transport,
             chart: str = "english") -> Reading:
    """Run one pinned input all the way through and record what the path did."""
    r = Reading(id=ident, text=text)
    p: Perturbation = perturb(text, snapshot, transport, chart)
    r.consulted = p.consulted
    r.seated = p.members
    r.region_id = p.region_id
    r.error = p.error
    r.trace = p.trace()
    objects = max(1, p.members - 1)
    r.density = (len(p.region.declared) / objects) if p.region else 0.0
    r.attached = len(p.attachment)
    r.bears_on = sum(1 for a in p.attachment if a.kind == BEARS_ON)
    r.corresponds = r.attached - r.bears_on
    r.extracted = len(p.extracted)
    if p.seeds:
        rel = relax_from(p, text, snapshot, chart)
        r.moved = len(rel.moved)
        r.reached = sum(1 for m in rel.moved if m.hops > 0)
        r.conditioned = bool(rel.moved)
    return r


def check_no_silent_zero(readings: list[Reading]) -> tuple[str, str]:
    """A zero is legal. A zero nobody can account for is not."""
    for r in readings:
        if r.conditioned:
            continue
        if not r.consulted and not r.error:
            return RED, (f"{r.id!r} produced nothing and the medium was never called, with no "
                         f"error to explain it — a filter in front of the field, which is the "
                         f"defect this property exists for")
        if not r.trace.get("seated"):
            return RED, f"{r.id!r} produced nothing and seated no objects, with no trace"
    return GREEN, ("every input either conditioned the field or carried a trace naming the "
                   "question put, the objects seated, and what came back")


def check_graded(readings: list[Reading]) -> tuple[str, str]:
    """sharp strictly tightest, vague loosest, question between. Order, never magnitude."""
    by_id = {r.id: r for r in readings}
    try:
        sharp, question, vague = by_id["sharp"], by_id["question"], by_id["vague"]
    except KeyError as exc:
        return RED, f"the battery is missing input {exc}"
    shapes = {(r.corresponds > 0, r.bears_on > 0, r.attached) for r in (sharp, question, vague)}
    if len(shapes) == 1:
        return RED, ("all three inputs produced the same attachment shape — a path that "
                     "answers a sharp claim, a question and a bare topic identically is not "
                     "reading them, and that is what a lookup looks like")
    if vague.corresponds and not sharp.corresponds:
        return RED, ("the bare topic drew correspondence-kind attachments where the sharp "
                     "claim drew none: a topic asserts nothing and cannot correspond, so the "
                     "grading is inverted")
    if not (sharp.tightness >= question.tightness >= vague.tightness):
        return RED, (f"attachment strength is not ordered: sharp={sharp.tightness} "
                     f"question={question.tightness} vague={vague.tightness}")
    return GREEN, (f"ordered sharp={sharp.tightness} >= question={question.tightness} >= "
                   f"vague={vague.tightness}")


def check_no_cliff(a: Reading, b: Reading) -> tuple[str, str]:
    """Near-identical phrasings must not be full-response versus nothing."""
    if a.consulted != b.consulted:
        return RED, ("one paraphrase reached the medium and the other did not — something "
                     "exact is gating the path")
    live = [x for x in (a, b) if x.conditioned]
    if len(live) == 1:
        return RED, (f"{live[0].id!r} conditioned the field and its paraphrase produced "
                     f"nothing: a cliff on near-identical wording")
    return GREEN, ("both paraphrases were put to the medium and neither fell off a cliff "
                   "relative to the other")


def check_stateful(before: Reading, after: Reading) -> tuple[str, str]:
    """A field that gained an arrow must compile differently for the same input."""
    same = (before.region_id == after.region_id and before.moved == after.moved
            and before.reached == after.reached and before.extracted == after.extracted)
    if same:
        return RED, ("the same input compiled identically against a corpus that had gained an "
                     "arrow — the response is frozen with respect to the field, which means "
                     "it is not coming from the field")
    return GREEN, (f"the added arrow changed the compilation: moved {before.moved}->"
                   f"{after.moved}, reached {before.reached}->{after.reached}")


def check_one_code_path(root: Path | str | None = None) -> tuple[str, str]:
    """No second attachment mechanism. Checked structurally, not by reading the diff.

    Two things must hold and both are decidable: the deleted module must stay deleted, and the
    perturb path must go out on `engine.region`'s prompt and renderer rather than on any of
    its own. A candidate-list mechanism reintroduced under a new name would have to import a
    different prompt or build its own body, and both show here.
    """
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    if (base / "engine" / "attach.py").exists():
        return RED, "engine/attach.py is back — the candidate-list loop was reintroduced"
    body = (base / "engine" / "perturb.py").read_text(encoding="utf-8")
    for marker in ("REGION_SYSTEM", "render_region", "parse_region", "residuals"):
        if marker not in body:
            return RED, (f"the perturb path no longer uses {marker} — it has stopped sharing "
                         f"the sampler's region implementation")
    for banned in ("BATCH", "CALL_BUDGET", "call_budget", "render_candidates"):
        if banned in body:
            return RED, f"candidate-list vocabulary {banned!r} is back on the perturb path"
    for rel in ("engine/inbound.py", "ui/current.py"):
        text = (base / rel).read_text(encoding="utf-8")
        if "engine.attach" in text or "from .attach import" in text:
            return RED, f"{rel} still reaches for the deleted loop"
    return GREEN, ("the perturb path uses engine.region's prompt, renderer, parser and "
                   "reading discipline; the candidate-list loop is absent")


def run(snapshot: CorpusSnapshot, transport, chart: str = "english",
        battery: dict | None = None, extra_arrow=None) -> BatteryReport:
    """Run the whole battery. `extra_arrow` is the arrow landed between the two state reads."""
    spec = battery or load_battery()
    report = BatteryReport()
    for item in spec["inputs"]:
        report.readings.append(read_one(item["text"], item["id"], snapshot, transport, chart))

    v, why = check_no_silent_zero(report.readings)
    report.properties["no_silent_zero"], report.reasons["no_silent_zero"] = v, why
    v, why = check_graded(report.readings)
    report.properties["graded"], report.reasons["graded"] = v, why

    pair = spec["paraphrase_pair"]
    a = read_one(pair["a"], "paraphrase_a", snapshot, transport, chart)
    b = read_one(pair["b"], "paraphrase_b", snapshot, transport, chart)
    report.readings += [a, b]
    v, why = check_no_cliff(a, b)
    report.properties["no_cliff"], report.reasons["no_cliff"] = v, why

    if extra_arrow is not None:
        from .corpus_state import with_arrows

        sharp = next(i for i in spec["inputs"] if i["id"] == "sharp")
        before = next(r for r in report.readings if r.id == "sharp")
        grown = with_arrows(snapshot, list(snapshot.arrows) + [extra_arrow])
        after = read_one(sharp["text"], "sharp_after", grown, transport, chart)
        report.readings.append(after)
        v, why = check_stateful(before, after)
    else:
        v, why = RED, "statefulness was not measured — no arrow was landed between the reads"
    report.properties["stateful"], report.reasons["stateful"] = v, why

    v, why = check_one_code_path()
    report.properties["one_code_path"], report.reasons["one_code_path"] = v, why
    return report


#: The longitudinal sample's cadence. t0, then weekly.
SAMPLE_EVERY_DAYS = 7


@dataclass(slots=True)
class Sample:
    """ONE POINT ON THE CURVE. Does daemon time turn into perturbation richness?

    The claim the daemon is running on is that hours spent extracting arrows make the window
    better — that a corpus with more structure answers a typed input more richly. That is a
    claim about a TREND, and a trend needs a series measured the same way each time, which is
    what the pinned battery is for. Two numbers per point:

      * ATTACHMENTS FOUND — how many arrows the medium drew to the boundary condition, summed
        over the three pinned inputs. Directly the thing the window delivers.
      * MEAN REGION ARROW-DENSITY — declared arrows per object, averaged over the battery's
        regions. The structural quantity the first number is supposed to depend on. Logging
        both is the point: if attachments rise while density is flat, the gain came from the
        model and not from the corpus, and the daemon's hours are not what bought it.

    Recorded with the corpus's own size so a rise cannot be read as growth when it was
    ingestion. A curve that does not move is a real answer about the daemon.
    """

    at: str                                    # ISO date; passed in, never read from a clock
    attachments: dict = field(default_factory=dict)      # input id -> arrows drawn to the bias
    attachments_total: int = 0
    bears_on_total: int = 0
    corresponds_total: int = 0
    mean_arrow_density: float = 0.0            # declared arrows per object, over the regions
    regions: int = 0
    corpus_slots: int = 0
    corpus_arrows: int = 0
    verdict: str = ""

    def as_record(self) -> dict[str, object]:
        return {"record": "battery", "at": self.at, "attachments": dict(self.attachments),
                "attachments_total": self.attachments_total,
                "bears_on_total": self.bears_on_total,
                "corresponds_total": self.corresponds_total,
                "mean_arrow_density": round(self.mean_arrow_density, 4),
                "regions": self.regions, "corpus_slots": self.corpus_slots,
                "corpus_arrows": self.corpus_arrows, "verdict": self.verdict,
                "note": ("Attachment quality on the PINNED battery. A rise in attachments "
                         "without a rise in arrow-density did not come from the daemon.")}


def sample_from(report: BatteryReport, snapshot: CorpusSnapshot, at: str,
                densities: list[float] | None = None) -> Sample:
    """Reduce a battery run to one point on the curve."""
    pinned = {"sharp", "question", "vague"}
    rows = [r for r in report.readings if r.id in pinned]
    s = Sample(at=at, verdict=report.verdict)
    s.attachments = {r.id: r.attached for r in rows}
    s.attachments_total = sum(r.attached for r in rows)
    s.bears_on_total = sum(r.bears_on for r in rows)
    s.corresponds_total = sum(r.corresponds for r in rows)
    dens = densities if densities is not None else [r.density for r in rows]
    s.regions = len(dens)
    s.mean_arrow_density = (sum(dens) / len(dens)) if dens else 0.0
    s.corpus_slots = len(snapshot.slots)
    s.corpus_arrows = len(snapshot.arrows)
    return s


def log_sample(sample: Sample, path: str | Path | None = None) -> None:
    """Append one point to the WALK LOG, tagged so a reader can tell it from a step.

    It goes in the walk's own log rather than beside it because it is the same question the
    walk is asking, measured from the other end: the walk records what the sampler found, and
    this records whether any of it reached the window. Step records predate the `record` key,
    so a reader must treat its absence as `step`.
    """
    from .walk import WALK_PATH

    p = Path(path or WALK_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(sample.as_record(), sort_keys=True) + "\n")
        fh.flush()


def curve(path: str | Path | None = None) -> list[dict]:
    """The series, oldest first. Steps are skipped; only battery points come back."""
    from .walk import WALK_PATH

    p = Path(path or WALK_PATH)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("record") == "battery":
            out.append(row)
    return sorted(out, key=lambda r: r.get("at", ""))


def due(at: str, path: str | Path | None = None,
        every_days: int = SAMPLE_EVERY_DAYS) -> bool:
    """Is a new point due? True at t0 — an empty curve is always due."""
    from datetime import date

    series = curve(path)
    if not series:
        return True
    try:
        last = date.fromisoformat(series[-1]["at"])
        now = date.fromisoformat(at)
    except (ValueError, KeyError):
        return True
    return (now - last).days >= every_days


def run_live(key: str | None = None, chart: str = "english") -> BatteryReport:
    """The battery against the REAL corpus and the REAL medium, with the PINNED wording.

    This is the half the suite cannot gate. The hermetic controls hold the medium fixed and
    check that the mechanism carries a grade without flattening it; only a live run can say
    whether the grade is there at all — whether this model, on this corpus, actually answers a
    sharp claim more tightly than a bare topic.

    Statefulness is measured with a REAL arrow: the first arrow the medium extracts from the
    sharp input's own region is laid over the read view for the second read. That is a genuine
    change to the field rather than a synthetic one, and if the medium extracts nothing the
    property reports unmeasured rather than passing.
    """
    from ui.current import _region_transport, corpus_snapshot

    transport = _region_transport(key)
    if transport is None:
        r = BatteryReport()
        for k in ("no_silent_zero", "graded", "no_cliff", "stateful", "one_code_path"):
            r.properties[k] = RED
            r.reasons[k] = "no model is configured, so the live battery could not be run"
        return r
    snapshot = corpus_snapshot(reload=True)
    spec = load_battery()
    sharp = next(i for i in spec["inputs"] if i["id"] == "sharp")
    probe = perturb(sharp["text"], snapshot, transport, chart)
    extra = probe.extracted[0] if probe.extracted else None
    return run(snapshot, transport, chart, battery=spec, extra_arrow=extra)
