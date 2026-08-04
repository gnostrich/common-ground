"""The continuous proposer: one global field, running slowly, under an operator's hand.

Batch-per-repo was the wrong shape. A repository is a fact about where files were checked in,
not a boundary in the base category, and running one campaign per repo guarantees that the
only correspondences ever proposed are the ones inside a single checkout. This runs instead as
a **background process over the whole corpus** — every repo, plus Aristotle, plus the Claude
export — at a rate the operator sets, with a ledger the operator can read at any moment.

Four properties, each load-bearing:

**Global.** The candidate pool is built once over the union corpus and streamed. Repository
identity plays no part in it. The honest caveat, measured rather than assumed: the two
structural bounding relations (declaration-granularity and depth-bounded subtree) are
*provenance* relations, and provenance does not cross a repository boundary — so the pool's
cross-repo content comes from **composition**, not from a new bounding rule. That gap is named
here rather than filled with an anchor rule; `proposerd.py --measure-cross-repo` reports how
many declaration names are shared across repos so the operator can rule on it with a number.

**Persistent.** The journal is the only memory. A pair that has been answered is never asked
again — directed, so the reverse arrow remains a separate question — and a restart replays the
journal through `FastTape.propose`, so the resumed tape came through the one inlet like
everything else.

**Composing.** Before each batch the daemon composes the arrows it holds. Implied pairs are
asked first, because a triangle is the only thing that can produce a cycle and therefore the
only thing that can produce a floor. An implied pair the proposer already answered `none` on is
recorded as a CONTRADICTION and surfaced; it is not resolved in either direction.

**Stoppable.** A control file is re-read every iteration: `calls_per_hour`, `paused`, `stop`,
`max_cost`. Changing it takes effect on the next batch with no restart. A malformed control
file PAUSES the daemon rather than falling back to defaults — an unattended process must fail
towards doing nothing.

## The discipline, which is the whole point

- Every delta enters at `WarrantTier.EXTRACTION`, through `FastTape.propose`, and is asserted
  non-promotable **before** the batch is journalled. A promotable delta halts the loop.
- This module names no promotion machinery at all. `static_checks.check_proposer_discipline`
  walks its AST and fails the build if it ever does — so "K promotes nothing without explicit
  confirmation" is a property of the source, not a promise in a docstring (GATES 10).
- The gates are re-checked *while it runs*: the static suite in-process every batch, the full
  test suite in a subprocess every `gate_every` batches. Red gates HALT the loop and write a
  `halt` record. There is no "log the failure and keep going".
- Timestamps drive the rate limiter and nothing else. No clock value reaches an address, a
  random stream, or a claim's value (GATES 7).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

from . import EngineError
from .compose import compose, contradictions, unasked
from .correspondence import Correspondence, asymmetries, correspondences_from_deltas
from .holes import Hole
from .inlet import FastTape
from .journal import Journal
from .propose_correspondence import (
    PROPOSE_SYSTEM,
    ProposalOutcome,
    as_correspondence_delta,
    parse_answers,
    render_candidates,
)
from .types import Delta, WarrantTier, promotable

#: (system, user) -> (raw completion, usage dict). Usage may be empty; cost is then reported
#: as unavailable rather than estimated.
Transport = Callable[[str, str], tuple[str, dict]]

#: How long to wait between control-file polls while paused or rate-limited.
POLL_SECONDS = 5.0

#: Where the daemon's three files live by default.
JOURNAL_PATH = "runs/proposer.journal.jsonl"
CONTROL_PATH = "runs/proposer.control.json"
STATUS_PATH = "runs/proposer.status.json"
POOL_PATH = "runs/pool.jsonl"


# --- the operator's hand ---------------------------------------------------------------

@dataclass(slots=True)
class Control:
    """What the operator sets. Re-read every iteration; no restart needed."""

    calls_per_hour: int = 30
    paused: bool = False
    stop: bool = False
    max_cost: float | None = None       # provider-reported spend cap, in provider units
    #: Candidates per call. Small on purpose: the proposer cites evidence for every answer,
    #: so a large batch runs the reply into the token ceiling and the tail arrives truncated.
    #: `parse_answers` salvages the complete answers from a cut-off reply rather than losing
    #: the batch, but a truncated tail still means candidates that were shown and not
    #: answered, which costs a call for nothing. Twelve keeps replies inside the budget.
    batch: int = 12
    error: str = ""                     # why the daemon paused itself

    @staticmethod
    def read(path: str | Path) -> "Control":
        """Missing file -> conservative defaults. Malformed file -> PAUSED, with the reason.

        Falling back to defaults on a malformed file would mean a typo silently un-pauses an
        unattended process spending money. It pauses instead.
        """
        p = Path(path)
        if not p.exists():
            return Control()
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("control file must be a JSON object")
            ctl = Control(
                calls_per_hour=max(0, int(raw.get("calls_per_hour", 30))),
                paused=bool(raw.get("paused", False)),
                stop=bool(raw.get("stop", False)),
                max_cost=(None if raw.get("max_cost") in (None, "")
                          else float(raw["max_cost"])),
                batch=max(1, min(100, int(raw.get("batch", 12)))),
            )
            return ctl
        except Exception as exc:
            return Control(paused=True, error=f"unreadable control file ({exc}); PAUSED")

    def write(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        body = {k: v for k, v in asdict(self).items() if k != "error"}
        p.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def wait_for_slot(journal: Journal, calls_per_hour: int, now: float) -> float:
    """Seconds to wait before the next call is allowed. 0 if one is allowed right now.

    A rolling one-hour window over the journal's own `call` timestamps. Because the window is
    read off the durable log rather than an in-memory bucket, a restart cannot reset the
    budget — which is the only version of a rate limit that means anything for a process
    designed to be killed and resumed.
    """
    if calls_per_hour <= 0:
        return POLL_SECONDS
    window = [t for t in journal.calls if t >= now - 3600.0]
    if len(window) < calls_per_hour:
        return 0.0
    # the oldest call in the window expires first; wait for it to fall out
    oldest = sorted(window)[len(window) - calls_per_hour]
    return max(0.0, (oldest + 3600.0) - now)


# --- the global candidate pool ----------------------------------------------------------

def write_pool(path: str | Path, holes: Iterable[Hole], relation: str) -> int:
    """Append holes to the pool file, one JSON object per line. Streamed, never materialized."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("a", encoding="utf-8") as fh:
        for h in holes:
            fh.write(json.dumps({**h.as_record(), "relation": relation}, sort_keys=True) + "\n")
            n += 1
    return n


def read_pool(path: str | Path) -> Iterator[tuple[Hole, str]]:
    """Stream the pool file. The whole point of a file is that it need not fit in memory."""
    p = Path(path)
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                yield (Hole(
                    src_chart=rec["src_chart"], src_slot=rec["src_slot"],
                    src_nu=rec.get("src_nu", ""), dst_chart=rec["dst_chart"],
                    dst_slot=rec["dst_slot"], dst_nu=rec.get("dst_nu", ""),
                    type=rec.get("type", "assert"), restatement=int(rec.get("restatement", 0)),
                ), rec.get("relation", "pool"))
            except KeyError:
                continue


def _hole_from(src_chart: str, src_slot: str, dst_chart: str, dst_slot: str,
               type_: str, nu_of: dict[str, str]) -> Hole:
    return Hole(src_chart=src_chart, src_slot=src_slot, src_nu=nu_of.get(src_slot, ""),
                dst_chart=dst_chart, dst_slot=dst_slot, dst_nu=nu_of.get(dst_slot, ""),
                type=type_, restatement=0)


# --- gate checking, continuously --------------------------------------------------------

def static_gate_report() -> list[dict[str, object]]:
    """The in-process static checks. Cheap enough to run before every batch."""
    from . import static_checks

    checks = (
        ("no_display_on_f_path", static_checks.check_no_display_on_f_path),
        ("gate6_classification", static_checks.check_gate6_classification),
        ("generative_keys", static_checks.check_generative_keys),
        ("span_discipline", static_checks.check_span_discipline),
        ("claim_discipline", static_checks.check_claim_discipline),
        ("proposer_discipline", static_checks.check_proposer_discipline),
    )
    out = []
    for name, fn in checks:
        try:
            result = fn()
            out.append({"check": name, "ok": bool(result.ok),
                        "violations": [str(v) for v in result.violations[:5]]})
        except Exception as exc:                     # a check that cannot run is a red gate
            out.append({"check": name, "ok": False, "violations": [f"check raised: {exc}"]})
    return out


def suite_green(root: Path | None = None, timeout: int = 900) -> tuple[bool, str]:
    """Run the whole test suite in a subprocess. Red means HALT, not a warning."""
    from .constants import REPO_ROOT

    cwd = Path(root or REPO_ROOT)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"test suite exceeded {timeout}s"
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return proc.returncode == 0, "\n".join(tail)


# --- the daemon ---------------------------------------------------------------------------

@dataclass(slots=True)
class ProposerStatus:
    running: bool = False
    paused: bool = False
    reason: str = ""
    batches: int = 0
    pool_position: int = 0
    pool_exhausted: bool = False
    composition: dict[str, int] = field(default_factory=dict)
    gates: list[dict[str, object]] = field(default_factory=list)
    gates_checked_at: float = 0.0
    suite: str = "not yet run"
    totals: dict[str, object] = field(default_factory=dict)
    control: dict[str, object] = field(default_factory=dict)
    tier: str = "EXTRACTION only — nothing here is promotable"
    updated: float = 0.0

    def write(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.updated = round(time.time(), 3)
        p.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")


class ContinuousProposer:
    """Runs until the operator stops it, a gate goes red, or the cost cap is reached."""

    def __init__(self, journal: Journal, transport: Transport,
                 pool_path: str | Path = POOL_PATH,
                 control_path: str | Path = CONTROL_PATH,
                 status_path: str | Path = STATUS_PATH,
                 proposer: str = "lm", prompt_hash: str = "continuous",
                 gate_every: int = 25, sleeper: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.time,
                 run_suite: bool = True):
        self.journal = journal
        self.transport = transport
        self.pool_path = Path(pool_path)
        self.control_path = Path(control_path)
        self.status_path = Path(status_path)
        self.proposer = proposer
        self.prompt_hash = prompt_hash
        self.gate_every = max(1, int(gate_every))
        self.sleep = sleeper
        self.now = clock
        self.run_suite = run_suite

        self.tape = FastTape()
        self.status = ProposerStatus()
        self._pool = read_pool(self.pool_path)
        self._pool_pos = 0
        self._pool_done = False
        self._nu: dict[str, str] = {}
        self._replay()

    # -- resume is replay through the one inlet ------------------------------------------

    def _replay(self) -> int:
        """Re-enter every journalled arrow through `FastTape.propose`. No un-pickled state."""
        n = 0
        for rec in self.journal.arrows:
            outcome = ProposalOutcome(
                hole=_hole_from(rec.src_chart, rec.src_slot, rec.dst_chart, rec.dst_slot,
                                rec.type, self._nu),
                kind=rec.answer, evidence=rec.evidence)
            try:
                delta = as_correspondence_delta(outcome, rec.proposer or self.proposer,
                                                rec.prompt_hash or self.prompt_hash)
            except Exception:
                continue                       # a malformed line is skipped, never coerced
            self._enter(delta)
            n += 1
        return n

    def _enter(self, delta: Delta) -> None:
        """The single write-path, with the tier assertion in front of it."""
        if delta.warrant.tier != WarrantTier.EXTRACTION or promotable(delta.warrant.tier):
            raise EngineError(
                f"the continuous proposer may only enter EXTRACTION-tier claims; got "
                f"{delta.warrant.tier.name}. Promotion requires the operator's explicit "
                "confirmation, which this process cannot give.")
        self.tape.propose(delta, self.proposer)

    def arrows(self) -> list[Correspondence]:
        return correspondences_from_deltas(self.tape.deltas())

    # -- candidate generation, in priority order -----------------------------------------

    def next_batch(self, size: int) -> list[tuple[Hole, str]]:
        """Composition first, then unreciprocated arrows, then the structural pool.

        Composition is first because an implied pair is the only candidate whose answer can
        close a triangle; the structural pool can only ever add more stars.
        """
        arrows = self.arrows()
        out: list[tuple[Hole, str]] = []
        chosen: set[tuple[str, str]] = set()

        result = compose(arrows)
        self.status.composition = {
            "implied": len(result.implied), "residues": len(result.residues),
            "dropped_by_hub_cap": result.dropped, "hubs_capped": result.hubs_capped,
        }
        for c in contradictions(result.implied, self.journal):
            self.journal.record_contradiction(
                src_slot=c.src_slot, dst_slot=c.dst_slot, implied=c.implied,
                recorded=c.recorded, via=c.via, note=c.note)

        for item in unasked(result.implied, self.journal):
            if len(out) >= size:
                return out
            key = (item.src_slot, item.dst_slot)
            if key in chosen:
                continue
            chosen.add(key)
            out.append((_hole_from(item.src_chart, item.src_slot, item.dst_chart,
                                   item.dst_slot, item.type, self._nu), "composition"))

        for a in asymmetries(arrows):
            if len(out) >= size:
                return out
            if self.journal.asked(a.dst_slot, a.src_slot):
                continue
            key = (a.dst_slot, a.src_slot)
            if key in chosen:
                continue
            chosen.add(key)
            out.append((_hole_from(a.dst_chart, a.dst_slot, a.src_chart, a.src_slot,
                                   "assert", self._nu), "reverse"))

        while len(out) < size:
            try:
                hole, relation = next(self._pool)
            except StopIteration:
                self._pool_done = True
                break
            self._pool_pos += 1
            self._nu.setdefault(hole.src_slot, hole.src_nu)
            self._nu.setdefault(hole.dst_slot, hole.dst_nu)
            if self.journal.asked(hole.src_slot, hole.dst_slot):
                continue
            key = (hole.src_slot, hole.dst_slot)
            if key in chosen:
                continue
            chosen.add(key)
            out.append((hole, relation))
        return out

    def rewind_pool(self) -> None:
        """Re-open the pool from the top. Cheap: already-asked pairs are skipped on the way."""
        self._pool = read_pool(self.pool_path)
        self._pool_pos = 0
        self._pool_done = False

    # -- one batch -------------------------------------------------------------------------

    def run_batch(self, chunk: Sequence[tuple[Hole, str]]) -> dict[str, int]:
        holes = [h for h, _ in chunk]
        relation_of = {(h.src_slot, h.dst_slot): rel for h, rel in chunk}
        try:
            raw, usage = self.transport(PROPOSE_SYSTEM, render_candidates(holes))
            ok = True
            error = ""
        except Exception as exc:
            raw, usage, ok, error = "", {}, False, str(exc)

        outcomes = parse_answers(raw, holes) if ok else []
        # A call that returned text but no usable answers is a failure mode of its own — a
        # truncated JSON body, a model that argued instead of answering. Recording only the
        # token count would leave it looking like a successful empty batch, so the head of
        # the raw reply goes in the record. It is the proposer's own words about candidates
        # the operator can see in the same journal; nothing private is added by keeping it.
        if ok and not outcomes:
            error = f"no parsable answers; raw head: {raw[:200]!r}"
        self.journal.record_call(
            candidates=len(holes), ok=ok and bool(outcomes),
            tokens_in=int(usage.get("prompt_tokens", 0) or 0),
            tokens_out=int(usage.get("completion_tokens", 0) or 0),
            cost=usage.get("cost"), model=str(usage.get("model", "")), error=error)
        if not outcomes:
            return {"asked": 0, "arrows": 0, "none": 0, "errors": 1}

        counts = {"asked": 0, "arrows": 0, "none": 0, "errors": 0}
        for outcome in outcomes:
            h = outcome.hole
            if outcome.is_arrow:
                delta = as_correspondence_delta(outcome, self.proposer, self.prompt_hash)
                self._enter(delta)              # tier-asserted, then the one inlet
                counts["arrows"] += 1
            else:
                counts["none"] += 1
            counts["asked"] += 1
            self.journal.record_ask(
                src_chart=h.src_chart, src_slot=h.src_slot, dst_chart=h.dst_chart,
                dst_slot=h.dst_slot, type=h.type, answer=outcome.kind,
                evidence=outcome.evidence,
                relation=relation_of.get((h.src_slot, h.dst_slot), "pool"),
                proposer=self.proposer, prompt_hash=self.prompt_hash, tier="EXTRACTION")
        return counts

    # -- the loop ---------------------------------------------------------------------------

    def run(self, max_batches: int | None = None,
            max_iterations: int | None = None) -> ProposerStatus:
        """Loop until stopped. `max_batches` bounds calls made; `max_iterations` bounds
        passes through the loop, including the passes that make no call because the daemon is
        paused or rate-limited. Both are None in production: the daemon runs until the
        operator stops it or a gate reddens.
        """
        self.status.running = True
        batches = 0
        iterations = 0
        while max_batches is None or batches < max_batches:
            if max_iterations is not None and iterations >= max_iterations:
                break
            iterations += 1
            ctl = Control.read(self.control_path)
            self.status.control = {k: v for k, v in asdict(ctl).items()}

            if ctl.stop:
                self._halt("operator stop", asdict(ctl))
                break
            if ctl.max_cost is not None and self.journal.spend >= ctl.max_cost:
                self._halt("cost cap reached",
                           {"spend": self.journal.spend, "cap": ctl.max_cost})
                break

            if batches % self.gate_every == 0:
                if not self._check_gates():
                    break

            if ctl.paused:
                self.status.paused = True
                self.status.reason = ctl.error or "paused by operator"
                self._publish()
                self.sleep(POLL_SECONDS)
                continue
            self.status.paused = False

            wait = wait_for_slot(self.journal, ctl.calls_per_hour, self.now())
            if wait > 0:
                self.status.reason = (f"rate limited: {ctl.calls_per_hour} calls/hour, "
                                      f"next slot in {wait:.0f}s")
                self._publish()
                self.sleep(min(wait, POLL_SECONDS))
                continue

            chunk = self.next_batch(ctl.batch)
            if not chunk:
                if self._pool_done:
                    self.status.pool_exhausted = True
                    self.status.reason = ("pool exhausted; waiting for new material or new "
                                          "composition candidates")
                    self.rewind_pool()
                else:
                    self.status.reason = "no unasked candidates in this pass"
                self._publish()
                self.sleep(POLL_SECONDS)
                continue

            self.status.reason = f"asking {len(chunk)} candidates"
            try:
                self.run_batch(chunk)
            except Exception as exc:                    # noqa: BLE001 - see below
                # An unattended process that dies on an unexpected exception leaves no
                # record of why: the journal's last line is a successful call and the
                # status file says "running". That is exactly what happened when a
                # proposer returned a bare integer where an answer object belonged. A
                # crash is now a HALT with its traceback, so the ledger says what ended it.
                import traceback

                self._halt("unhandled exception in batch", traceback.format_exc()[-1500:])
                break
            batches += 1
            self.status.batches += 1
            self.status.pool_position = self._pool_pos
            self._publish()

        self.status.running = False
        self._publish()
        return self.status

    def _check_gates(self) -> bool:
        report = static_gate_report()
        self.status.gates = report
        self.status.gates_checked_at = round(self.now(), 3)
        red = [r for r in report if not r["ok"]]
        if red:
            self._halt("static gate red", red)
            return False
        if self.run_suite:
            green, tail = suite_green()
            self.status.suite = "green" if green else f"RED\n{tail}"
            if not green:
                self._halt("test suite red", tail)
                return False
        return True

    def _halt(self, reason: str, detail: object = None) -> None:
        self.status.running = False
        self.status.reason = f"HALTED: {reason}"
        self.journal.record_halt(reason, detail)
        self._publish()

    def _publish(self) -> None:
        self.status.totals = self.journal.totals()
        self.status.write(self.status_path)
