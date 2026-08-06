"""The current: one inlet -> the engine settles -> one valve (K) deposits.

A `Current` is a live, accumulating fast tape. Every source enters it through the single
inlet `FastTape.propose`: me (a deterministic read of what I typed), the LM (Opus, in
parallel), and — a stub translator in front — another instance. After every submission the
engine re-settles the whole accumulated tape and the live gate K promotes what cleared
Hankel ∧ conservative into the slow corpus. Nothing reaches the tape except through the
inlet; nothing reaches the corpus except through K.

Accumulation is what lets the flow show: submit an English claim, then a Lean statement of
the same thing, and they fiber across charts, contest, raise a floor, and K deposits what
survives — the whole current in one window.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from engine import seed_lock
from engine.constants import BETA_ARMS, MINT_ENABLED, shadow
from engine.corpus_state import SNAPSHOT_PATH, CorpusSnapshot, with_arrows
from engine.inbound import compile_input
from engine.inlet import FastTape
from engine.mint_tape import MintController, read_tape, residual_stream
from engine.pipeline import ledger_from_deltas, run_meter
from engine.surface import report_from_ledger
from engine.types import Document

from .lm import LMClient, api_key, lm_available

#: The persisted read view over the real corpus. Loaded once, lazily, and never rebuilt in
#: the window — a request that rebuilt 620k deltas would be a request that never returned.
#: When the file is absent the window says the corpus is not loaded rather than answering
#: against an empty current and calling it the corpus.
_SNAPSHOT: CorpusSnapshot | None = None



def _journal_arrows() -> list:
    """The continuous proposer's arrows, read off its journal. Read-only, EXTRACTION tier.

    The daemon writes to its journal and the window reads it; there is no shared memory and
    no second account. An arrow it refuses to build (malformed, intra-chart) is skipped
    rather than coerced, exactly as `correspondences_from_deltas` does.
    """
    from engine import EngineError
    from engine.continuous import JOURNAL_PATH
    from engine.correspondence import Correspondence
    from engine.journal import Journal

    if not Path(JOURNAL_PATH).exists():
        return []
    journal = Journal(JOURNAL_PATH)
    try:
        out = []
        for rec in journal.arrows:
            try:
                out.append(Correspondence(
                    src_chart=rec.src_chart, src_slot=rec.src_slot,
                    dst_chart=rec.dst_chart, dst_slot=rec.dst_slot, kind=rec.answer,
                    proposer=rec.proposer, prompt_hash=rec.prompt_hash,
                    evidence=(rec.evidence,)))
            except EngineError:
                continue
        return out
    finally:
        journal.close()


def corpus_snapshot(reload: bool = False) -> CorpusSnapshot:
    """The corpus read view WITH the proposer's arrows laid over it.

    Reloaded on demand rather than cached forever, because the daemon is still running: a
    window that cached the arrow set at startup would show a frozen picture of a live process.
    """
    global _SNAPSHOT
    if _SNAPSHOT is None or reload:
        base = CorpusSnapshot.load(SNAPSHOT_PATH)
        _SNAPSHOT = with_arrows(base, _journal_arrows()) if not base.empty else base
    return _SNAPSHOT



def corpus_header() -> dict:
    """What the window must display so a missing corpus is never mistaken for an empty one."""
    from .build import stamp

    snap = corpus_snapshot()
    head = snap.header()
    head["path"] = SNAPSHOT_PATH
    from . import lm as _lm

    b = stamp()
    # PIN DRIFT, announced. An env var silently overrode the code pin and the deployed
    # window ran the lite model for hours while the code said otherwise. Configured and
    # served are different facts; the header now carries both and flags a mismatch.
    b["model_configured"] = _lm.OPENROUTER_MODEL
    b["model"] = _lm.LAST_SERVED
    b["model_drift"] = bool(_lm.LAST_SERVED
                            and _lm.LAST_SERVED != _lm.OPENROUTER_MODEL
                            and _lm.OPENROUTER_MODEL != "openrouter/auto")
    head["build"] = b
    if snap.empty:
        head["note"] = ("NO CORPUS LOADED — run `python3 proposerd.py build-snapshot`. "
                        "The window is answering from the typed current alone.")
    return head


def _modal(deltas) -> dict[str, str]:
    votes: dict[str, Counter] = {}
    for d in deltas:
        votes.setdefault(d.slot, Counter())[d.value] += d.confidence
    return {s: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for s, c in votes.items()}


class Current:
    """A live accumulating fast tape + its settled state and K deposits."""

    def __init__(self) -> None:
        self.tape = FastTape()
        self._conv: list[str] = []
        self._last_retention = None

    def reset(self) -> None:
        self.tape = FastTape()
        self._conv = []
        self._last_retention = None

    def propose_text(self, text: str, chart: str = "english", temperature: float = 0.3,
                     key: str | None = None, instance_id: str | None = None,
                     lm_transport=None) -> dict:
        """PERTURB-AND-RETAIN. Proposing and asking are one act with a persistence flag.

        THE BARE PROPOSE PATH IS DELETED, not deprecated. It ran the claim extractor and the
        LM proposer against a fresh Current that knew nothing about the corpus, so a proposed
        claim landed on the tape with no position in the field — while `ask` ran a region
        relaxation against the real one. Two mechanisms for one job, and the proposing half
        threw away the relaxation that could have situated what it was proposing.

        Now the SAME region call runs, and the flag decides what survives it. A proposed
        claim therefore arrives PRE-SITUATED: `[0|bias]` enters a region, the medium completes
        the diagram, and the correspondence-kind arrows it draws to the input are retained
        beside the claim as proposals. Everything retained is born subject to the
        event-quantized decay (D14), which is what stops the tape becoming a second corpus.

        WITH NO MODEL the input cannot be situated, and dropping it on the tape unsituated
        and calling that normal IS the removed organ. So that case is a stated degenerate of
        this one path — `perturb` returns an addressed input with an error, `commit` retains
        an isolated claim, and the result says so.
        """
        from engine.perturb import RETAIN, commit, perturb

        # ONE PATH. An instance is a SOURCE, not a second mechanism — it differs from `me`
        # by its source tag and by nothing else. The instance branch used to run the claim
        # extractor and a stub translator, which is the same raw drop the operator's own
        # branch did, so collapsing them is what "the two entry points become one box"
        # means rather than leaving the organ alive under another name.
        source = f"instance:{instance_id}" if instance_id else "me"
        transport = _region_transport(key) if lm_transport is None else lm_transport
        pert = perturb(text, corpus_snapshot(), transport, chart)
        retention = commit(pert, self.tape, RETAIN, source=source)
        lm_used = pert.consulted
        self._last_retention = retention
        if chart == "conversation":
            self._conv.append(text)
        out = self.state(lm_used=lm_used)
        if retention is not None:
            out["retention"] = retention.as_record()
        return out

    def state(self, lm_used: bool | None = None) -> dict:
        ledger = ledger_from_deltas(self.tape.deltas())
        report = report_from_ledger(ledger, conversation_text="\n".join(self._conv))

        controller = MintController(enabled=MINT_ENABLED)
        lock = seed_lock.current()
        result, _warm, cold = run_meter(ledger, BETA_ARMS[-1], lock.seed_hash, shadow())
        second_fdt = float(result.surrogate.get("second_fdt_floor", 0.0))
        modal = _modal(ledger.deltas)
        for block in ledger.blocks:
            settled = cold.get(block.id)
            if settled is None or not block.slots:
                continue
            reading = read_tape(residual_stream(settled), second_fdt)
            sid = block.slots[0]
            controller.consider(sid[:16], modal.get(sid, "T"), reading,
                                source=f"settled:{block.id[:8]}")

        return {
            "law": "One inlet. All proposers equal. Warrant conferred only at the gate.",
            "corpus_header": corpus_header(),
            "lm_available": bool(lm_used),
            "proposals_by_source": self.tape.by_source(),
            "proposals": [
                {"source": p.source_tag, "tier": p.tier.name, "chart": p.delta.chart,
                 "type": p.delta.type, "value": p.delta.value, "surface": p.delta.surface[:90]}
                for p in self.tape.entries
            ],
            "engine": report.to_dict(),
            "promotions": [pr.as_record() for pr in controller.log],
            "corpus": controller.corpus,
        }


def _region_transport(key: str | None):
    """The proposer's transport. The SAME one the daemon's sampler uses.

    Returns None with no key: a perturbation is a region completion, and without a model the
    bias can only attach at its own address — which the window then reports honestly rather
    than pretending the field was consulted.
    """
    from .lm import LMClient, api_key, lm_available, model_for

    resolved = api_key(key)
    if not lm_available(resolved):
        return None
    client = LMClient(resolved, model_for(resolved))

    def transport(system: str, user: str):
        return client.complete(system, user, 0.0, max_tokens=16000), dict(client.last_usage)

    return transport


def ask_the_corpus(question: str, chart: str = "english", key: str | None = None,
                   on_stage=None) -> dict:
    """Compile the LM's input FROM THE FIELD, and hand back both sides of the compilation.

    The answer is not retrieval-with-receipts and not a lookup. The typed question enters a
    REGION of the real corpus as one more object in the diagram, one call completes it, the
    arrows drawn to that object seed the corpus's energy as a soft constraint, and what the
    model receives is the region that moved — which is why the window shows the typed text and
    the compiled field side by side. When nothing moves, the compiler says so and names the
    structural reason; there is no second mechanism that produces words anyway.
    """
    compiled = compile_input(question, corpus_snapshot(), chart,
                             transport=_region_transport(key), on_stage=on_stage)
    out = compiled.as_record()

    # THE READING SURFACE. A view: the trace is unchanged and still in `compiled`, and the
    # surface is checked against it rather than trusted — a view's two failure modes are
    # showing what the measurement did not contain and dropping a warning it did.
    from engine.reading import check_faithful, read as read_surface

    surface = read_surface(compiled)
    out["surface"] = {
        "text": surface.render(),
        "entered": {"corresponds": surface.entered_corresponds,
                    "bears_on": surface.entered_bears_on,
                    "declined": surface.declined},
        "movers": [{"nu": m.nu, "chart": m.chart, "shift": round(m.shift, 4),
                    "hops": m.hops, "path": m.path, "contested": m.contested,
                    "tier": m.tier} for m in surface.movers],
        "field": surface.field_lines,
        "strength": surface.strength,
        "faithful": check_faithful(surface, compiled),
    }
    return out


def run_current(text: str, chart: str = "english", temperature: float = 0.3,
                key: str | None = None, instance_text: str = "", lm_transport=None) -> dict:
    """One-shot convenience (tests): a fresh current with one 'me' submission (+ optional
    instance), settled once."""
    cur = Current()
    first = cur.propose_text(text, chart=chart, temperature=temperature, key=key,
                             lm_transport=lm_transport)
    if instance_text.strip():
        cur.propose_text(instance_text, chart=chart, instance_id="B")
    out = cur.state(lm_used=lm_available(key))
    # The RETENTION travels with the result. Re-settling and dropping it would hide what
    # `/propose` actually did, which is the whole difference between the unified act and
    # the raw drop it replaced.
    if "retention" in first:
        out["retention"] = first["retention"]
    return out
