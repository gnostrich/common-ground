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
from engine.extract import DeterministicExtractor
from engine.inbound import compile_input
from engine.inlet import FastTape, stub_translator
from engine.mint_tape import MintController, read_tape, residual_stream
from engine.pipeline import ledger_from_deltas, run_meter
from engine.surface import report_from_ledger
from engine.types import Document

from .lm import LMClient, LMProposer, api_key, lm_available

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
    snap = corpus_snapshot()
    head = snap.header()
    head["path"] = SNAPSHOT_PATH
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

    def reset(self) -> None:
        self.tape = FastTape()
        self._conv = []

    def propose_text(self, text: str, chart: str = "english", temperature: float = 0.3,
                     key: str | None = None, instance_id: str | None = None,
                     lm_transport=None) -> dict:
        """Add a submission through the ONE inlet, then return the settled current."""
        lm_used = False
        if instance_id:
            # another instance — the same inlet, a stub translator in front.
            for d in DeterministicExtractor(f"inst-{instance_id}", "typed").extract(
                    Document(f"inst:{instance_id}", chart, text, "instance")):
                self.tape.propose(stub_translator(d, instance_id), f"instance:{instance_id}")
        else:
            # me (typing) — a source.
            for d in DeterministicExtractor("me", "typed").extract(
                    Document("me", chart, text, "typed")):
                self.tape.propose(d, "me")
            # the LM (Opus) — a source, in parallel, through the SAME inlet.
            if lm_available(key):
                client = LMClient(api_key(key), transport=lm_transport)
                for d in LMProposer("lm", "opus", client, temperature).extract(
                        Document("lm", chart, text, "lm")):
                    self.tape.propose(d, "lm")
                lm_used = True
        if chart == "conversation":
            self._conv.append(text)
        return self.state(lm_used=lm_used)

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


def ask_the_corpus(question: str, chart: str = "english") -> dict:
    """Compile the LM's input FROM THE FIELD, and hand back both sides of the compilation.

    The answer is not retrieval-with-receipts. The typed question is addressed like any other
    input (gate 1, exact), the addresses it LANDS ON supply the content, and what the model
    receives is the compiled field state — which is why the window shows the typed text and
    the compiled input side by side. When nothing lands, the compiler says
    "NO FIELD TO CONDITION ON" instead of quietly degrading into a plain prompt.
    """
    compiled = compile_input(question, corpus_snapshot(), chart)
    return compiled.as_record()


def run_current(text: str, chart: str = "english", temperature: float = 0.3,
                key: str | None = None, instance_text: str = "", lm_transport=None) -> dict:
    """One-shot convenience (tests): a fresh current with one 'me' submission (+ optional
    instance), settled once."""
    cur = Current()
    cur.propose_text(text, chart=chart, temperature=temperature, key=key, lm_transport=lm_transport)
    if instance_text.strip():
        cur.propose_text(instance_text, chart=chart, instance_id="B")
    return cur.state(lm_used=lm_available(key))
