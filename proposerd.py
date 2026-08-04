#!/usr/bin/env python3
"""proposerd — the continuous, global correspondence proposer.

    python3 proposerd.py build-pool          # assemble the GLOBAL pool once (slow, one-shot)
    python3 proposerd.py run                 # the daemon: runs until stopped or a gate reddens
    python3 proposerd.py status              # totals, gates, last records — safe any time
    python3 proposerd.py rate 20             # calls/hour, takes effect next batch
    python3 proposerd.py pause | resume | stop
    python3 proposerd.py cost-cap 5.0        # halt when provider-reported spend reaches this
    python3 proposerd.py contradictions      # every implied-vs-answered conflict, in full
    python3 proposerd.py measure-cross-repo  # the named gap, as a number

Corpus locations come from the environment and are never baked in, because the corpus is not
in this repository and must not become part of it:

    CG_LEAN_CORPUS     directory of the Lean corpus
    CG_CLAUDE_EXPORT   conversations.json from the Claude export
    CG_EXCLUSIONS      newline/space separated thread-id prefixes to EXCLUDE
    CG_REPO_ROOT       directory holding the GitHub checkouts (default /workspace)

If `CG_CLAUDE_EXPORT` is set but `CG_EXCLUSIONS` is not, the conversation corpus is REFUSED.
The exclusion list is the privacy decision; running without it would mean ingesting material
the operator has not cleared, and no amount of convenience justifies guessing at that.

The LM path is OpenRouter only (`ui/lm.py` has no other transport). Every claim this process
enters is EXTRACTION tier; it promotes nothing and confirms nothing.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.constants import decisions
from engine.continuous import (
    CONTROL_PATH,
    JOURNAL_PATH,
    POOL_PATH,
    STATUS_PATH,
    ContinuousProposer,
    Control,
    write_pool,
)
from engine.energy import dedupe_deltas
from engine.extract import build_k_extractors, slots_from_deltas
from engine.holes import holes_by_declaration, holes_by_subtree
from engine.journal import Journal
from engine.pipeline import ingest
from engine.router import RoutingReport, route

REPO_SKIP = {".git", "node_modules", ".lake", "build", ".cache", "__pycache__", ".venv"}
PROSE_EXT = {".md", ".txt", ".rst"}


# --- the union corpus -------------------------------------------------------------------

def _message_text(message: dict) -> str:
    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return text
    return "\n".join(b.get("text", "") for b in (message.get("content") or [])
                     if isinstance(b, dict) and b.get("type") == "text")


def conversation_docs() -> list:
    export = os.environ.get("CG_CLAUDE_EXPORT", "").strip()
    if not export:
        return []
    excl_raw = os.environ.get("CG_EXCLUSIONS", "").strip()
    if not excl_raw:
        raise SystemExit(
            "CG_CLAUDE_EXPORT is set but CG_EXCLUSIONS is not. The exclusion list is the "
            "privacy decision; this refuses to ingest conversations without it.")
    excluded = {p[:8] for p in excl_raw.split() if p.strip()}
    report = RoutingReport()
    for convo in json.load(open(export, encoding="utf-8")):
        uid = str(convo.get("uuid") or convo.get("id") or "")
        if uid[:8] in excluded:
            continue
        for i, msg in enumerate(convo.get("chat_messages") or convo.get("messages") or []):
            if str(msg.get("sender") or msg.get("role") or "") not in ("human", "assistant"):
                continue
            body = _message_text(msg)
            if body.strip():
                report.routed.append(route(f"claude||{uid}:{i}", body, "claude_export"))
    return report.to_charts()


def lean_corpus_docs() -> list:
    path = os.environ.get("CG_LEAN_CORPUS", "").strip()
    if not path or not Path(path).is_dir():
        return []
    from adapters.lean_corpus import load_lean_corpus

    docs, _ = load_lean_corpus(path, lean_toolchain=None)
    return docs


def repo_docs() -> tuple[list, list[str]]:
    root = Path(os.environ.get("CG_REPO_ROOT", "/workspace"))
    docs, names = [], []
    if not root.is_dir():
        return docs, names
    for repo_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        repo = repo_dir.name
        if repo.startswith(".") or repo == "common-ground":
            continue
        found = 0
        for dirpath, dirnames, filenames in os.walk(repo_dir):
            dirnames[:] = [d for d in dirnames if d not in REPO_SKIP]
            for filename in filenames:
                full = Path(dirpath) / filename
                ext = full.suffix.lower()
                if ext not in PROSE_EXT and ext != ".lean":
                    continue
                rel = str(full.relative_to(repo_dir)).replace(os.sep, "/")
                try:
                    text = full.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if not text.strip() or len(text) > 3_000_000:
                    continue
                routed = route(f"{repo}||{rel}", text, "repo")
                if routed.document is not None:
                    docs.append(routed.document)
                    found += 1
                docs.extend(routed.companions)
                found += len(routed.companions)
        if found:
            names.append(f"{repo}:{found}")
    return docs, names


def build_corpus():
    started = time.time()
    docs = conversation_docs() + lean_corpus_docs()
    repo, names = repo_docs()
    docs += repo
    print(f"docs={len(docs)}  repos=[{', '.join(names)}]  [{time.time() - started:.0f}s]",
          flush=True)
    deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
    slots = slots_from_deltas(deltas)
    print(f"deltas={len(deltas):,} slots={len(slots):,}  [{time.time() - started:.0f}s]",
          flush=True)
    return slots, deltas


# --- commands ----------------------------------------------------------------------------

def cmd_build_pool() -> None:
    pool = Path(POOL_PATH)
    if pool.exists():
        pool.unlink()
    slots, deltas = build_corpus()
    counts = {}
    counts["declaration"] = write_pool(
        pool, (h for v in holes_by_declaration(slots, deltas).values() for h in v),
        "declaration")
    for dst in ("english", "tabular", "conversation"):
        counts[f"subtree:{dst}"] = write_pool(
            pool, (h for v in holes_by_subtree(slots, deltas, dst_chart=dst,
                                               max_depth=1).values() for h in v),
            f"subtree:{dst}")
    total = sum(counts.values())
    print(json.dumps({"pool": str(pool), "total": total, "by_relation": counts,
                      "note": ("provenance relations do not cross a repository boundary; "
                               "cross-repo candidates come from composition. Run "
                               "`measure-cross-repo` for the size of that gap.")}, indent=2))


def cmd_measure_cross_repo() -> None:
    """The named gap, as a number: how many declaration names two repos share.

    This is a MEASUREMENT, not a relation. Nothing here proposes anything or widens the pool;
    it exists so the operator can rule on whether shared-identifier bounding is worth adding,
    with a count in hand instead of an intuition.
    """
    from engine.faces import declarations

    _, deltas = build_corpus()
    where: dict[str, set[str]] = defaultdict(set)
    for d in deltas:
        if d.chart != "lean":
            continue
        repo = d.provenance.doc_id.partition("||")[0]
        for _head, name in declarations(d.surface):
            where[name].add(repo)
            break
    shared = {n: sorted(r) for n, r in where.items() if len(r) > 1}
    print(json.dumps({
        "declaration_names": len(where),
        "shared_across_repos": len(shared),
        "share_rate": round(len(shared) / max(len(where), 1), 4),
        "examples": dict(list(sorted(shared.items()))[:15]),
        "ruling_required": ("shared-identifier bounding is NOT enabled. It would be a new "
                            "structural relation, and the standing instruction was to stop "
                            "adding candidate rules without a ruling."),
    }, indent=2))


def _openrouter_transport():
    from ui.lm import LMClient, _is_openrouter, model_for

    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not _is_openrouter(key):
        raise SystemExit("OPENROUTER_API_KEY (sk-or-...) required; there is no other path")
    client = LMClient(key, model_for(key))

    def transport(system: str, user: str) -> tuple[str, dict]:
        raw = client.complete(system, user, 0.0, max_tokens=8000)
        return raw, dict(client.last_usage)

    return transport, client.model


def cmd_run(max_batches: int | None) -> None:
    transport, model = _openrouter_transport()
    if not Path(POOL_PATH).exists():
        raise SystemExit(f"no pool at {POOL_PATH}; run `build-pool` first")
    control = Control.read(CONTROL_PATH)
    control.write(CONTROL_PATH)          # materialize it so the operator has a file to edit
    journal = Journal(JOURNAL_PATH)
    proposer = ContinuousProposer(journal, transport, prompt_hash="continuous")
    print(f"continuous proposer: model={model} rate={control.calls_per_hour}/h "
          f"journal={JOURNAL_PATH} control={CONTROL_PATH} status={STATUS_PATH}", flush=True)
    try:
        status = proposer.run(max_batches=max_batches)
    finally:
        journal.close()
    print(json.dumps({"batches": status.batches, "reason": status.reason,
                      "totals": status.totals}, indent=2))


def cmd_status() -> None:
    status = (json.loads(Path(STATUS_PATH).read_text(encoding="utf-8"))
              if Path(STATUS_PATH).exists() else {"note": "never run"})
    journal = Journal(JOURNAL_PATH)
    print(json.dumps({"status": status, "totals": journal.totals(),
                      "control": {k: v for k, v in vars(Control.read(CONTROL_PATH)).items()},
                      "recent": journal.tail(12)}, indent=2))
    journal.close()


def cmd_contradictions() -> None:
    journal = Journal(JOURNAL_PATH)
    print(json.dumps({"count": len(journal.contradictions),
                      "records": journal.contradictions}, indent=2))
    journal.close()


def _set(**changes) -> None:
    control = Control.read(CONTROL_PATH)
    for key, value in changes.items():
        setattr(control, key, value)
    control.write(CONTROL_PATH)
    print(json.dumps({k: v for k, v in vars(control).items() if k != "error"}, indent=2))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    command, rest = argv[0], argv[1:]
    if command == "build-pool":
        cmd_build_pool()
    elif command == "measure-cross-repo":
        cmd_measure_cross_repo()
    elif command == "run":
        cmd_run(int(rest[0]) if rest else None)
    elif command == "status":
        cmd_status()
    elif command == "contradictions":
        cmd_contradictions()
    elif command == "pause":
        _set(paused=True)
    elif command == "resume":
        _set(paused=False, stop=False)
    elif command == "stop":
        _set(stop=True)
    elif command == "rate":
        _set(calls_per_hour=int(rest[0]))
    elif command == "cost-cap":
        _set(max_cost=float(rest[0]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
