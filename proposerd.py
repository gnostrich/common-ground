#!/usr/bin/env python3
"""proposerd — the continuous, global correspondence proposer.

    python3 proposerd.py build-pool          # assemble the GLOBAL pool once (slow, one-shot)
    python3 proposerd.py build-snapshot      # the window's read view over the whole corpus
    python3 proposerd.py run                 # the daemon: runs until stopped or a gate reddens
    python3 proposerd.py sources             # what corpus is plugged in (or that none is)
    python3 proposerd.py atlas [out.html]    # ONE self-contained page: charts, arrows, search
    python3 proposerd.py census              # record the depth-1 subtree candidate count
    python3 proposerd.py status              # totals, gates, last records — safe any time
    python3 proposerd.py checkpoint          # write the REDACTED ledger, safe to commit
    python3 proposerd.py rate 20             # calls/hour, takes effect next batch
    python3 proposerd.py pause | resume | stop
    python3 proposerd.py cost-cap 5.0        # halt when provider-reported spend reaches this
    python3 proposerd.py contradictions      # every implied-vs-answered conflict, in full
    python3 proposerd.py measure-cross-repo  # the named gap, as a number

Where your corpus lives is declared in `corpus.local.json` — copy `seed/CORPUS.example.json`
and point it at your own material. That file is gitignored, so this repository can be forked,
shared or published while every corpus stays wherever its owner keeps it. NOTHING in the
engine names a path. `proposerd.py sources` prints what resolves, including what is missing,
so a fork nobody has pointed anywhere says so rather than ingesting nothing quietly.

A `claude_export` source must declare `exclude`, even if empty. An archive contains material
its owner never meant to hand to an engine, and the failure mode of forgetting is that it has
already been read.

The LM path is OpenRouter only (`ui/lm.py` has no other transport). Every claim this process
enters is EXTRACTION tier; it promotes nothing and confirms nothing.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.constants import decisions
from engine.corpus_sources import status as corpus_status
from engine.continuous import (
    CONTROL_PATH,
    LEDGER_PATH,
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
from engine.languages import REFERENCE, SHELF as SHELF_CLASS, rule_for
from engine.corpus_state import SNAPSHOT_PATH
from engine.journal import Journal
from engine.pipeline import ingest
from engine.router import RoutingReport, route

REPO_SKIP = {".git", "node_modules", ".lake", "build", ".cache", "__pycache__", ".venv"}


# --- the union corpus -------------------------------------------------------------------

def _message_text(message: dict) -> str:
    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return text
    return "\n".join(b.get("text", "") for b in (message.get("content") or [])
                     if isinstance(b, dict) and b.get("type") == "text")


def _docs_from_repos(src) -> tuple[list, dict]:
    """Every file under a checkout tree, classified by seed/LANGUAGES.json."""
    from collections import Counter

    root = Path(src.path)
    docs, held = [], Counter()
    for repo_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        repo = repo_dir.name
        if repo.startswith(".") or repo == "common-ground":
            continue
        for dirpath, dirnames, filenames in os.walk(repo_dir):
            dirnames[:] = [d for d in dirnames if d not in src.skip_dirs]
            for filename in filenames:
                full = Path(dirpath) / filename
                rel = str(full.relative_to(repo_dir)).replace(os.sep, "/")
                cls = rule_for(f"{repo}||{rel}").cls
                if cls in (REFERENCE, SHELF_CLASS):
                    held[cls] += 1
                    continue
                try:
                    if full.stat().st_size > src.max_bytes:
                        continue
                    text = full.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if not text.strip():
                    continue
                routed = route(f"{repo}||{rel}", text, "repo")
                if routed.document is not None:
                    docs.append(routed.document)
                docs.extend(routed.companions)
    return docs, dict(held)


def _docs_from_lean_corpus(src) -> tuple[list, dict]:
    from adapters.lean_corpus import load_lean_corpus

    docs, _ = load_lean_corpus(src.path, lean_toolchain=None)
    return docs, {}


def _docs_from_claude_export(src) -> tuple[list, dict]:
    """Conversations, minus the ids the source excludes. Exclusions are the source's own."""
    excluded = {p[:8] for p in src.exclude if str(p).strip()}
    report = RoutingReport()
    skipped = 0
    with open(src.path, encoding="utf-8") as fh:
        for convo in json.load(fh):
            uid = str(convo.get("uuid") or convo.get("id") or "")
            if uid[:8] in excluded:
                skipped += 1
                continue
            for i, msg in enumerate(convo.get("chat_messages") or convo.get("messages") or []):
                if str(msg.get("sender") or msg.get("role") or "") not in ("human", "assistant"):
                    continue
                body = _message_text(msg)
                if body.strip():
                    report.routed.append(route(f"claude||{uid}:{i}", body, "claude_export"))
    return report.to_charts(), {"excluded_conversations": skipped}


def _docs_from_files(src) -> tuple[list, dict]:
    docs = []
    for p in sorted(Path(src.path).parent.glob(Path(src.path).name)):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if text.strip():
            routed = route(f"{src.name}||{p.name}", text, src.name)
            if routed.document is not None:
                docs.append(routed.document)
            docs.extend(routed.companions)
    return docs, {}


LOADERS = {"repos": _docs_from_repos, "lean_corpus": _docs_from_lean_corpus,
           "claude_export": _docs_from_claude_export, "files": _docs_from_files}


def build_corpus():
    """Every ACTIVE source in the corpus manifest. No path is named in this file."""
    from engine.corpus_sources import active, status

    started = time.time()
    live = active()
    if not live:
        raise SystemExit(json.dumps(status(), indent=2))
    docs, notes = [], {}
    for src in live:
        got, held = LOADERS[src.kind](src)
        docs.extend(got)
        notes[src.name] = {"kind": src.kind, "docs": len(got), **held}
        print(f"  {src.name:28} {src.kind:14} {len(got):>6,} docs "
              f"[{time.time() - started:.0f}s]", flush=True)
    print(f"docs={len(docs)}  {json.dumps(notes)}  [{time.time() - started:.0f}s]", flush=True)
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


def cmd_build_snapshot() -> None:
    """The window's read view over the whole corpus, built DIRECTLY.

    Not through `ledger_from_deltas`: `Ledger.contested_blocks` scans every delta for every
    block, which on this corpus is ~1.1e11 comparisons and was killed after thirty minutes.
    The direct build is verified field-for-field against the ledger build in
    `tests/test_corpus_state.py` and on real repo subsets.
    """
    from engine.corpus_state import build_snapshot_direct, source_counts
    from engine.correspondence import correspondences_from_deltas

    started = time.time()
    slots, deltas = build_corpus()
    arrows = correspondences_from_deltas(deltas)
    snap = build_snapshot_direct(deltas, arrows, source_counts(deltas))
    snap.save(SNAPSHOT_PATH)
    print(json.dumps({"saved": SNAPSHOT_PATH, "seconds": round(time.time() - started, 1),
                      **snap.header()}, indent=2))


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


def cmd_census() -> None:
    """Record the depth-1 subtree candidate count per chart pair, to `runs/census.json`.

    Recorded rather than recomputed at render time: the enumeration is minutes over the full
    corpus, so a page that recomputed it would either be slow or would quietly show whatever
    it had cached without saying how old that was. Writing it to a file with a timestamp makes
    the age of the number part of the number.
    """
    from engine.holes import holes_by_subtree_all

    started = time.time()
    slots, deltas = build_corpus()
    subtree: dict[str, int] = {}
    for key, holes in holes_by_subtree_all(slots, deltas, max_depth=1).items():
        for hole in holes:
            pair = " x ".join(sorted((hole.src_chart, hole.dst_chart)))
            subtree[pair] = subtree.get(pair, 0) + 1
    out = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "measured_by": "engine.holes.holes_by_subtree_all(max_depth=1)",
        "elapsed_seconds": round(time.time() - started, 1),
        "note": ("Depth-1 subtree candidates per chart pair. A pair absent from this table "
                 "has NO candidates at that granularity — that is a measured zero, not a "
                 "gap in the measurement."),
        "subtree": dict(sorted(subtree.items(), key=lambda kv: -kv[1])),
    }
    Path("runs/census.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


def _openrouter_transport():
    from ui.lm import LMClient, _is_openrouter, model_for

    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not _is_openrouter(key):
        raise SystemExit("OPENROUTER_API_KEY (sk-or-...) required; there is no other path")
    client = LMClient(key, model_for(key))

    def transport(system: str, user: str) -> tuple[str, dict]:
        raw = client.complete(system, user, 0.0, max_tokens=16000)
        return raw, dict(client.last_usage)

    return transport, client.model


def cmd_run(max_batches: int | None) -> None:
    # A reclaim destroys the working journal (gitignored — it quotes the corpus). The
    # redacted ledger is committed and carries every field the resume path needs, so a
    # daemon starting with no journal rebuilds its memory rather than re-asking, and
    # re-paying for, thousands of pairs. Copy-if-absent: a live journal always wins.
    restored = Journal.restore_from_ledger(JOURNAL_PATH, LEDGER_PATH)
    if restored:
        print(f"restored {restored:,} records from {LEDGER_PATH} — the journal was lost, "
              f"the ledger was not", flush=True)
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


#: The committable ledger: the journal with every quoted span replaced by its hash.
LEDGER_PATH = "runs/proposer.ledger.jsonl"


def cmd_checkpoint() -> None:
    """Write the redacted ledger so the journal survives a container reclaim.

    The full journal quotes the corpus and stays out of the repository. This is the same
    record with the quotes hashed: enough to know what was asked and what was answered,
    which is everything resume needs, and no corpus text at all.
    """
    journal = Journal(JOURNAL_PATH)
    try:
        counts = journal.export_redacted(LEDGER_PATH)
        print(json.dumps({"ledger": LEDGER_PATH, **counts, **journal.totals()}, indent=2))
    finally:
        journal.close()


def cmd_status() -> None:
    status = (json.loads(Path(STATUS_PATH).read_text(encoding="utf-8"))
              if Path(STATUS_PATH).exists() else {"note": "never run"})
    journal = Journal(JOURNAL_PATH)
    print(json.dumps({"status": status, "totals": journal.totals(),
                      "control": asdict(Control.read(CONTROL_PATH)),
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
    print(json.dumps({k: v for k, v in asdict(control).items() if k != "error"}, indent=2))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    command, rest = argv[0], argv[1:]
    if command == "build-pool":
        cmd_build_pool()
    elif command == "build-snapshot":
        cmd_build_snapshot()
    elif command == "measure-cross-repo":
        cmd_measure_cross_repo()
    elif command == "run":
        cmd_run(int(rest[0]) if rest else None)
    elif command == "checkpoint":
        cmd_checkpoint()
    elif command == "sources":
        print(json.dumps(corpus_status(), indent=2))
    elif command == "atlas":
        from engine.atlas import write as write_atlas

        out = rest[0] if rest else "runs/atlas.html"
        print(json.dumps(write_atlas(out), indent=2))
    elif command == "census":
        cmd_census()
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
