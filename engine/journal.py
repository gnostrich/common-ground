"""The proposal journal — append-only, fsync'd, readable at any time.

A background process that silently accumulates structure is how this becomes NELL. The
journal is the answer to that: it is the daemon's **entire durable memory**, it is written
before anything is believed, and it is a plain JSONL file the operator can `tail` mid-run.
Nothing the proposer knows lives anywhere else — not the asked set, not the arrows, not the
cost. Delete the journal and the daemon has amnesia; that is the intended property.

Four record kinds, and no fifth:

- ``ask``            one candidate pair shown to the proposer, and the answer it gave —
                     including ``none``, which is *information about the corpus* and is
                     recorded exactly as durably as an arrow.
- ``call``           one LM request: candidate count, outcome, tokens, and the provider's
                     own reported cost. Also the rate limiter's clock (see below).
- ``contradiction``  composition implied a pair the proposer already answered otherwise.
                     Never silently dropped, never auto-resolved.
- ``halt``           the loop stopped, and why. A halt is a record, not a log line.

**Resume is replay, not restore.** On startup the daemon re-enters every recorded arrow
through `FastTape.propose` — the one inlet — rather than un-pickling a tape. The write-path
assertion in `tests/test_inlet.py` therefore still covers the resumed state, and a journal
line can never introduce structure the inlet would have refused.

**Timestamps are operational only.** ``t`` exists so the operator can see when something
happened and so the rate limiter can count calls in a window. It is never an input to an
address, a random stream, or a value — gate 7. `tests/test_continuous.py` plants that defect
and asserts the check catches it.
"""

from __future__ import annotations

from .decompose import decompose as _decompose

import json
import os
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

ASK = "ask"
CALL = "call"
CONTRADICTION = "contradiction"
HALT = "halt"

#: Answers that are arrows. Anything else recorded as an answer is a `none`.
_NONE = "none"


def pair_key(src_slot: str, dst_slot: str) -> str:
    """The DIRECTED key. `A->B` and `B->A` are different questions.

    A correspondence is a directed morphism and its reverse is a separate claim with a
    separate address (GATES 9), so "already asked" must be directed too — otherwise the
    daemon would answer the reverse question by assuming symmetry, which is exactly what
    `correspondence.asymmetries` exists to refuse.
    """
    return f"{src_slot}>{dst_slot}"


@dataclass(frozen=True, slots=True)
class Recorded:
    """One answered candidate, as replayed off disk."""

    src_chart: str
    src_slot: str
    dst_chart: str
    dst_slot: str
    type: str
    answer: str
    evidence: str
    relation: str
    proposer: str
    prompt_hash: str

    @property
    def is_arrow(self) -> bool:
        return self.answer != _NONE


class Journal:
    """Append-only JSONL. Index is built by replaying the file; there is no other state."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.answers: dict[str, str] = {}          # directed pair key -> answer kind
        self.arrows: list[Recorded] = []
        self.calls: list[float] = []               # call timestamps, for the rate window
        self.spend: float = 0.0                    # provider-reported cost, summed
        self.spend_reported: int = 0               # calls whose cost the provider reported
        self.tokens_in = 0
        self.tokens_out = 0
        self.counts: Counter = Counter()
        self.contradictions: list[dict] = []
        self._replay()
        self._fh = self.path.open("a", encoding="utf-8")

    # --- reading ------------------------------------------------------------------

    def _replay(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    self.counts["corrupt_lines"] += 1
                    continue                      # a torn tail line is skipped, not guessed
                self._index(rec)

    def _index(self, rec: dict) -> None:
        kind = rec.get("kind")
        self.counts[kind] += 1
        if kind == ASK:
            key = pair_key(rec.get("src_slot", ""), rec.get("dst_slot", ""))
            answer = str(rec.get("answer", _NONE))
            self.answers[key] = answer
            self.counts[f"answer:{answer}"] += 1
            if answer != _NONE:
                self.arrows.append(Recorded(
                    src_chart=rec.get("src_chart", ""), src_slot=rec.get("src_slot", ""),
                    dst_chart=rec.get("dst_chart", ""), dst_slot=rec.get("dst_slot", ""),
                    type=rec.get("type", "assert"), answer=answer,
                    evidence=rec.get("evidence", ""), relation=rec.get("relation", ""),
                    proposer=rec.get("proposer", "lm"), prompt_hash=rec.get("prompt_hash", ""),
                ))
        elif kind == CALL:
            self.calls.append(float(rec.get("t", 0.0)))
            self.tokens_in += int(rec.get("tokens_in", 0) or 0)
            self.tokens_out += int(rec.get("tokens_out", 0) or 0)
            cost = rec.get("cost")
            if cost is not None:
                self.spend += float(cost)
                self.spend_reported += 1
            if not rec.get("ok", True):
                self.counts["call_errors"] += 1
        elif kind == CONTRADICTION:
            self.contradictions.append(rec)

    def asked(self, src_slot: str, dst_slot: str) -> bool:
        return pair_key(src_slot, dst_slot) in self.answers

    def answer_for(self, src_slot: str, dst_slot: str) -> str | None:
        return self.answers.get(pair_key(src_slot, dst_slot))

    def calls_since(self, cutoff: float) -> int:
        """How many LM calls landed at or after `cutoff`. The rate limiter's only input."""
        return sum(1 for t in self.calls if t >= cutoff)

    def totals(self) -> dict[str, object]:
        """The running totals the operator reads. Cost is REPORTED, never estimated."""
        by_kind = {k.split(":", 1)[1]: v for k, v in self.counts.items()
                   if k.startswith("answer:")}
        n_calls = len(self.calls)
        # OI-30. TWO DENOMINATORS LIVED HERE and neither named the gap between them: `asked`
        # is derived from the ANSWER counters and `calls` from the call log, so a call that
        # produced no parseable answer — a refusal, a truncation, a malformed reply — was
        # counted in one and not the other, and nothing said so. `call_errors` names part of
        # it; the rest was invisible. A known cause absorbing an unknown one, in the totals
        # the operator reads to decide whether the daemon is working.
        _answered = sum(by_kind.values())
        _errors = self.counts.get("call_errors", 0)
        calls_decomposed = _decompose(
            "lm_calls", n_calls,
            {"produced an answer": min(_answered, n_calls),
             "errored": min(_errors, max(0, n_calls - min(_answered, n_calls)))},
            unit="call")
        return {
            "asked": _answered,
            "answers": by_kind,
            # WHAT EVERY CALL DID, and what nothing here accounts for. Reported beside the
            # raw counters rather than replacing them: the counters are what other code
            # reads, and this is what a reader needs to know they are not the whole story.
            "calls_by_outcome": calls_decomposed,
            "arrows": sum(v for k, v in by_kind.items() if k != _NONE),
            "none": by_kind.get(_NONE, 0),
            "none_rate": (by_kind.get(_NONE, 0) / sum(by_kind.values())
                          if by_kind else 0.0),
            "contradictions": len(self.contradictions),
            "calls": n_calls,
            "call_errors": self.counts.get("call_errors", 0),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost": round(self.spend, 6),
            "cost_coverage": (f"{self.spend_reported}/{n_calls} calls reported a cost"
                              if n_calls else "no calls yet"),
            "halts": self.counts.get(HALT, 0),
        }

    def tail(self, n: int = 40) -> list[dict]:
        """The last `n` records, for the operator's window. Reads the file, not the index."""
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()[-n:]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    # --- writing ------------------------------------------------------------------

    def _write(self, rec: dict) -> dict:
        rec = {"t": round(time.time(), 3), **rec}
        self._fh.write(json.dumps(rec, sort_keys=True) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())      # readable at any time, and survives a kill
        self._index(rec)
        return rec

    def record_ask(self, *, src_chart: str, src_slot: str, dst_chart: str, dst_slot: str,
                   type: str, answer: str, evidence: str, relation: str,
                   proposer: str, prompt_hash: str, tier: str,
                   region_id: str = "", model: str = "") -> dict:
        """One answered candidate. `region_id` identifies the CO-PRESENT SET it was named in.

        Without it, re-confirmation cannot be told from re-measurement. An arrow named twice
        in the same assembly is one observation counted twice; independence is what makes a
        re-confirmation evidence. The journal previously stored the answer and not the
        context, so 1,426 apparent re-confirmations could not be checked at all — the same
        defect as logging a drift count without the drifting triple.
        """
        rec = {
            "kind": ASK, "src_chart": src_chart, "src_slot": src_slot,
            "dst_chart": dst_chart, "dst_slot": dst_slot, "type": type,
            "answer": answer, "evidence": evidence[:300], "relation": relation,
            "proposer": proposer, "prompt_hash": prompt_hash, "tier": tier,
        }
        if region_id:
            rec["region_id"] = region_id
        if model:
            # THE SERVED MODEL, not the requested one. `openrouter/auto` routed 448 of 465
            # calls to a lite model that repeats 35x and never emits `same_claim`, and
            # nothing in the record said so — the arrows it produced are indistinguishable
            # from any other after the fact. A model selector is a mechanism parameter, so
            # which model actually answered belongs in the evidence, not in a log line.
            rec["model"] = model
        return self._write(rec)

    def record_admission(self, admission) -> dict:
        """One K decision at a boundary site, with the evidence it was computed FROM.

        THE PHASING CONDITION, in code. The in-graph hyperedge comes after the suite, but this
        record carries the full evidence from the very first promotion: the Hankel value, the
        second-FDT floor, the conservative-check result, and the RESIDUAL SET. The later edge
        renders this record; it never reconstructs it.

        Evidence not captured at admission time cannot be recovered afterwards, and a record
        without its residual set is a weight flip with a note attached — decision B silently
        degraded to decision A. That is the failure this signature exists to prevent, which is
        why it takes the whole `Admission` and not a handful of scalars.
        """
        from . import EngineError

        rec = admission.as_record()
        if not rec.get("residuals"):
            raise EngineError(
                "an admission must carry the residual set it was computed from. Without it "
                "the promotion is unexplainable after the fact and the in-graph edge would "
                "have nothing to render.")
        return self._write(rec)

    def record_call(self, *, candidates: int, ok: bool, tokens_in: int = 0,
                    tokens_out: int = 0, cost: float | None = None,
                    model: str = "", error: str = "") -> dict:
        return self._write({
            "kind": CALL, "candidates": candidates, "ok": ok, "tokens_in": tokens_in,
            "tokens_out": tokens_out, "cost": cost, "model": model, "error": error[:200],
        })

    def record_contradiction(self, *, src_slot: str, dst_slot: str, implied: str,
                             recorded: str, via: Sequence[str], note: str) -> dict:
        return self._write({
            "kind": CONTRADICTION, "src_slot": src_slot, "dst_slot": dst_slot,
            "implied": implied, "recorded": recorded, "via": list(via), "note": note,
        })

    def record_halt(self, reason: str, detail: object = None) -> dict:
        return self._write({"kind": HALT, "reason": reason, "detail": detail})

    # --- the committable half -------------------------------------------------------

    @staticmethod
    def restore_from_ledger(journal_path: str | Path, ledger_path: str | Path) -> int:
        """Rebuild a lost journal from the committed, hash-redacted ledger.

        The working journal is gitignored — it quotes the corpus verbatim — so a container
        reclaim destroys it, and with it every record of which pairs have been asked. The
        daemon then re-asks thousands of pairs it has already paid for. The REDACTED ledger is
        committed and survives, and it keeps every field the resume path actually needs: the
        directed pair, the answer, the kind, the call timestamps. Only the quoted evidence was
        replaced by a hash.

        So a restore loses the quotations and keeps the memory. That is the right trade: the
        evidence is re-derivable from the corpus, and the spend is not.

        Refuses to overwrite an existing journal. A live journal is always the better record,
        and clobbering it with an older checkpoint is the one way this could destroy the thing
        it exists to protect.
        """
        target, source = Path(journal_path), Path(ledger_path)
        if target.exists():
            return 0
        if not source.exists():
            return 0
        target.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with source.open("r", encoding="utf-8") as src, target.open("w", encoding="utf-8") as dst:
            for line in src:
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    continue
                dst.write(line if line.endswith("\n") else line + "\n")
                n += 1
        return n

    def export_redacted(self, path: str | Path) -> dict[str, int]:
        """Write the journal WITHOUT the quoted corpus, so it can live in the repository.

        The full journal cannot be committed and that is not a formality: its `evidence`
        field is the proposer quoting Lean source and repo prose verbatim, which is the
        operator's private corpus. But `evidence` is the only field that carries corpus text,
        and it is *explanatory* — nothing in resume depends on it. What resume needs is which
        directed pair was asked and what came back, and those are slot HASHES and a verdict.

        So the quote is replaced by its content hash. The record stays complete and
        verifiable — anyone holding the corpus can recompute the hash and confirm the quote —
        while the repository holds no corpus text. This is the difference between a container
        reclaim costing time and costing 737 answered pairs, which is what it cost once.
        """
        from .hashing import sha256_text

        counts = {"records": 0, "redacted": 0}
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            for line in (self.path.read_text(encoding="utf-8").splitlines()
                         if self.path.exists() else ()):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for field in ("evidence", "note", "error", "detail"):
                    value = rec.get(field)
                    if isinstance(value, str) and value:
                        rec[field] = f"sha256:{sha256_text(value)[:16]}"
                        counts["redacted"] += 1
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                counts["records"] += 1
        return counts

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass
