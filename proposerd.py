#!/usr/bin/env python3
"""proposerd — the continuous, global correspondence proposer.

    python3 proposerd.py build-pool          # assemble the GLOBAL pool once (slow, one-shot)
    python3 proposerd.py build-snapshot      # the window's read view over the whole corpus
    python3 proposerd.py run                 # the daemon: runs until stopped or a gate reddens
    python3 proposerd.py walk [n]            # the SAMPLER: n region queries, no pool
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
    # THE MATERIAL DIGEST, recorded at build. Without it nothing can later tell whether the
    # snapshot still describes the material it was derived from, and snapshot-wins becomes
    # silent rather than visible.
    from engine.corpus_sources import resolve
    from engine.staleness import record as record_digest

    roots = [str(src.path) for src in resolve() if src.enabled and src.present and src.path]
    stale = record_digest(roots)
    print(json.dumps({"saved": SNAPSHOT_PATH, "seconds": round(time.time() - started, 1),
                      "material": stale.as_record(), **snap.header()}, indent=2))


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


def _read_view(base, arrows):
    """Slots plus arrows, with NO global closure. The walk closes each region locally.

    `with_arrows` is the window's read view: it recomputes fibers, blocks and loops over the
    entire arrow graph so the header can report a floor. The walk needs none of that — it
    builds one region at a time and computes that region's declared and implied sets from the
    arrows inside it. Paying the global closure at startup cost four minutes at 6,343 arrows
    and rises with every arrow the walk itself adds.
    """
    from engine.corpus_state import CorpusSnapshot

    view = CorpusSnapshot(slots=base.slots, arrows=list(arrows), fibers=[], blocks={},
                          contested=set(base.contested), floor_status=base.floor_status,
                          loops=0, sources=dict(base.sources))
    return view


def cmd_walk(n: int) -> None:
    """The sampler. No pool: each position is drawn from what the last query produced.

    Arrows enter through the ONE inlet at extraction tier, exactly as the pairwise loop's did.
    The walk log records every step's type and reason, so the operator can see whether the
    chain is aimed by prediction error or merely orbiting the structure it started near.
    """
    from engine.corpus_state import CorpusSnapshot, with_arrows
    from engine.inlet import FastTape
    from engine.propose_correspondence import as_correspondence_delta, ProposalOutcome
    from engine.holes import Hole
    from engine.region import arrows_from
    from engine.types import WarrantTier, promotable
    from engine.walk import Walk, _seed_frontier, log_step, step
    from ui.current import _journal_arrows

    def stage(msg: str) -> None:
        """Every phase transition, announced. A process that cannot say what phase it is in
        is the process-level version of a docstring claiming a mechanism it does not run —
        and "silent" spent half an hour meaning "unknown whether loading or wedged"."""
        print(f"[walk] {msg}", flush=True)

    stage("opening transport")
    transport, model = _openrouter_transport()
    stage(f"loading snapshot from {SNAPSHOT_PATH}")
    base = CorpusSnapshot.load(SNAPSHOT_PATH)
    if base.empty:
        raise SystemExit("no corpus snapshot — run `proposerd.py build-snapshot`")
    stage(f"snapshot: {len(base.slots):,} slots — reading journal arrows")
    prior = _journal_arrows()
    stage(f"journal: {len(prior):,} arrows — assembling read view (arrows only, NO closure)")
    # NOT `with_arrows`. That recomputes fibers, blocks and the LOOP set over the whole arrow
    # graph, which took over four minutes at 6,343 arrows and grows with every walk — an
    # eager global closure paid at startup for a walk that only ever looks at one region at a
    # time. The walk needs the arrows and the slots; it computes each region's declared and
    # implied sets locally, from those, when it gets there.
    snapshot = _read_view(base, prior)
    stage(f"read view ready: {len(snapshot.arrows):,} arrows over {len(snapshot.slots):,} slots")
    #: Arrows that predate the composition table. The walk's neighbourhood preference doubles
    #: as a re-audit of them, and confirmations on old stock are counted apart from new finds.
    old_stock = frozenset(tuple(sorted((a.src_slot, a.dst_slot))) for a in prior)

    journal = Journal(JOURNAL_PATH)
    tape = FastTape()
    walk = Walk()
    _seed_frontier(walk, snapshot)
    stage(f"seeded frontier: {len(walk.frontier):,} positions, old-stock {len(old_stock):,}")
    stage(f"walking {n} step(s) with model={model}")
    try:
        for _ in range(n):
            s, proposals, region = step(walk, snapshot, transport, old_stock=old_stock)
            served_model = getattr(transport, "served_model", "") or model
            for arrow in arrows_from(proposals):
                hole = Hole(src_chart=arrow.src_chart, src_slot=arrow.src_slot, src_nu="",
                            dst_chart=arrow.dst_chart, dst_slot=arrow.dst_slot, dst_nu="",
                            type="assert", restatement=0)
                delta = as_correspondence_delta(
                    ProposalOutcome(hole, arrow.kind, arrow.evidence[0] if arrow.evidence
                                    else ""), "lm", "region")
                if delta.warrant.tier != WarrantTier.EXTRACTION or promotable(
                        delta.warrant.tier):
                    raise SystemExit("the sampler may only enter EXTRACTION-tier claims")
                tape.propose(delta, "lm")                 # the ONE inlet
                journal.record_ask(
                    src_chart=arrow.src_chart, src_slot=arrow.src_slot,
                    dst_chart=arrow.dst_chart, dst_slot=arrow.dst_slot, type="assert",
                    answer=arrow.kind, evidence=arrow.evidence[0] if arrow.evidence else "",
                    relation="region", proposer="lm", prompt_hash="region",
                    tier="EXTRACTION", model=served_model)
            log_step(s)
            print(f"  [{s.n}] {s.kind:11} members={s.members:>3} named={s.named:>3} "
                  f"void={s.void:>3} novel={s.novel:>3} conf={s.confirmed_declared:>2} "
                  f"comp={s.confirmed_implied:>2} resid={s.residual:>2} "
                  f"acc={s.acceptance:.0%} ${s.cost:.4f}  {s.reason[:44]}", flush=True)
    finally:
        journal.close()
    print(json.dumps(walk.report(), indent=2))


def cmd_battery() -> None:
    """THE STANDING BATTERY, live: pinned inputs, real corpus, real medium.

    The suite gates the three properties that are pure mechanism. This is the fourth — whether
    the grade is actually there on this model and this corpus — plus the other three measured
    against the real thing rather than a fixture.
    """
    from engine.battery import run_live

    print("battery: loading the read view (with journal arrows) — this is slow",
          flush=True)
    from datetime import date, timezone, datetime
    from engine.battery import due, log_sample, sample_from
    from ui.current import corpus_snapshot

    report = run_live()
    print(json.dumps(report.as_record(), indent=2))
    print()
    for k, v in report.properties.items():
        print(f"  {v:<5} {k:<16} {report.reasons[k]}")
    print(f"\nVERDICT {report.verdict}")

    # ONE POINT ON THE CURVE, appended only when one is DUE. A battery run is cheap to
    # repeat and the curve is a weekly series; sampling it every time it is run would make
    # a dense line out of an operator's debugging and hide the trend it exists to show.
    today = datetime.now(timezone.utc).date().isoformat()
    if due(today):
        s = sample_from(report, corpus_snapshot(), today)
        log_sample(s)
        print(f"\nCURVE POINT logged for {today}: "
              f"attachments={s.attachments_total} (bears_on {s.bears_on_total}, "
              f"corresponds {s.corresponds_total}), "
              f"mean region arrow-density={s.mean_arrow_density:.4f}, "
              f"corpus {s.corpus_slots:,} slots / {s.corpus_arrows:,} arrows")
    else:
        print("\n(no curve point: the last one is less than a week old)")


def cmd_curve() -> None:
    """THE CLAIM, plotted: do daemon-hours turn into perturbation richness?

    Two columns and they must be read together. If attachments rise while arrow-density is
    flat, the gain came from the model rather than from the corpus, and the daemon's hours are
    not what bought it. A flat curve is a real answer.
    """
    from engine.battery import curve

    series = curve()
    if not series:
        print("no curve yet — run `python3 proposerd.py battery` to record t0")
        return
    print(f"{'date':<12} {'attach':>7} {'bears':>6} {'corr':>5} {'density':>8} "
          f"{'slots':>9} {'arrows':>8}  verdict")
    for row in series:
        print(f"{row.get('at',''):<12} {row.get('attachments_total',0):>7} "
              f"{row.get('bears_on_total',0):>6} {row.get('corresponds_total',0):>5} "
              f"{row.get('mean_arrow_density',0):>8.4f} {row.get('corpus_slots',0):>9,} "
              f"{row.get('corpus_arrows',0):>8,}  {row.get('verdict','')}")
    if len(series) < 2:
        print("\n(one point is not a trend. The claim needs the next weekly sample.)")
    else:
        a, b = series[0], series[-1]
        da = b.get("attachments_total", 0) - a.get("attachments_total", 0)
        dd = b.get("mean_arrow_density", 0) - a.get("mean_arrow_density", 0)
        print(f"\nt0 -> now: attachments {da:+d}, mean arrow-density {dd:+.4f}")
        if da > 0 and dd <= 0:
            print("READ THIS CAREFULLY: attachments rose while the field did not get denser. "
                  "That gain did not come from the daemon.")


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
    # `holes_by_subtree_all` returns {chart_pair: {inner_key: [Hole]}} — two levels, and the
    # OUTER key already is the chart pair. An earlier version iterated one level too shallow,
    # so `hole` was a dict key (a string) and the census died on `str.src_chart` after two
    # minutes of corpus rebuild. Counting from the outer key needs no attribute at all.
    subtree: dict[str, int] = {}
    for (a, b), groups in holes_by_subtree_all(slots, deltas, max_depth=1).items():
        pair = " x ".join(sorted((a, b)))
        subtree[pair] = subtree.get(pair, 0) + sum(len(v) for v in groups.values())
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
        usage = dict(client.last_usage)
        # THE SERVED MODEL, carried out of the call. What was requested and what answered
        # are different facts, and only the second one is evidence about an arrow.
        transport.served_model = usage.get("model") or client.model
        return raw, usage

    transport.served_model = client.model
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
    elif command == "battery":
        cmd_battery()
    elif command == "curve":
        cmd_curve()
    elif command == "census":
        cmd_census()
    elif command == "walk":
        cmd_walk(int(rest[0]) if rest else 6)
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
