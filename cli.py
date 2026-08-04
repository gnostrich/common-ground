#!/usr/bin/env python3
"""common-ground CLI.

    python cli.py status     # decisions, lock state, phase readiness
    python cli.py pin        # record a landed lexicon artifact's digest into D8
    python cli.py lock       # write seed/SEED.lock (refuses while any decision is blank)
    python cli.py verify     # gate-4 tripwire: recompute seed hashes, fail on drift
    python cli.py register   # append a REGISTRY.jsonl entry (do this BEFORE a phase run)
    python cli.py p0         # P0 gate: lock complete, hashes reproducible
    python cli.py p1         # P1 gate: null battery on the current seed hash
    python cli.py demo       # end-to-end smoke run on synthetic input, writes nothing

Phases beyond P1 need D3, D4's spend cap, D5, and D6. `status` says which.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.lexicon_imports import import_all  # noqa: E402
from adapters.repo_docs import load_preminted  # noqa: E402
from engine import GateViolation  # noqa: E402
from engine.constants import BETA_ARMS, REGISTRY_DIR, decisions  # noqa: E402
from engine.extract import build_k_extractors  # noqa: E402
from engine.logio import RunLog, append_registry  # noqa: E402
from engine.nulls import run_battery  # noqa: E402
from engine.types import ControlState, NullStatus  # noqa: E402
from engine import seed_lock  # noqa: E402

REGISTRY_PATH = REGISTRY_DIR / "REGISTRY.jsonl"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def _mark(status: str) -> str:
    return {"pass": f"{GREEN}PASS{RESET}", "fail": f"{RED}FAIL{RESET}", "blocked": f"{YELLOW}BLOCKED{RESET}"}.get(
        status, status
    )


def _control(state: ControlState) -> str:
    """The positive control's verdict, printed beside the cell's own.

    A cell reporting PASS with a dead control has not passed anything: nobody has shown it
    can fail. The two verdicts belong side by side for exactly that reason.
    """
    return {
        ControlState.LIVE: f"{DIM}ctl:live{RESET}",
        ControlState.DEAD: f"{RED}ctl:DEAD{RESET}",
        ControlState.NOT_RUN: f"{YELLOW}ctl:--{RESET}",
    }[state]


def cmd_status(_: argparse.Namespace) -> int:
    d = decisions()
    lock = seed_lock.current()

    print("decisions")
    for key in sorted(k for k in d if k.startswith("D")):
        status = d[key].get("status", "?")
        colour = GREEN if status == "resolved" else (YELLOW if status == "partial" else RED)
        print(f"  {key}  {colour}{status}{RESET}")

    pending = seed_lock.unresolved_decisions(d)
    blanks = seed_lock.blank_markers_in_decisions_md()

    print("\nseed")
    print(f"  hash        {lock.seed_hash}")
    print(f"  lock        {'PROVISIONAL (seed/SEED.lock absent)' if lock.provisional else 'written'}")
    print(f"  seed files  {len(seed_lock.seed_files())}")
    if blanks:
        print(f"  {YELLOW}{len(blanks)} blank marker(s) remain in seed/DECISIONS.md{RESET}")

    d8 = d.get("D8", {})
    print("\nlexicon pins (D8)")
    for source, spec in sorted(seed_lock.PINNABLE.items()):
        digest = d8.get(spec["digest_key"])
        label = d8.get(spec["label_key"])
        if digest:
            print(f"  {source:<10} {GREEN}pinned{RESET}   {digest[:16]}  ({label})")
        else:
            policy = d8.get(f"{source}_policy", "?")
            note = f"policy {policy!r}" + (f", {spec['label_name']} {label}" if label else "")
            print(f"  {source:<10} {YELLOW}unpinned{RESET} {note} — run `cli.py pin {source} --path ...`")

    print("\nphases")
    p0_ok = not lock.provisional
    print(f"  P0 scaffold + seed assembly   {'ready' if p0_ok else f'{YELLOW}blocked{RESET}: SEED.lock not written'}")
    print(f"  P1 null battery               {'ready' if p0_ok else f'{DIM}gated on P0{RESET}'}")
    for phase, needs in (
        ("P2 adapters", ("D3",)),
        ("P3 ingestion", ("D3", "D4", "D5", "D8")),
        ("P4 audit", ("D3", "D4", "D5", "D6", "D8")),
    ):
        missing = [n for n in needs if d.get(n, {}).get("status") != "resolved"]
        print(f"  {phase:<30}{'ready' if not missing else f'{YELLOW}blocked{RESET} on ' + ', '.join(missing)}")

    if pending:
        print(f"\n{YELLOW}Cannot write SEED.lock:{RESET} {', '.join(pending)}")
        print("KICKOFF section 7.1 — refuse to proceed past P0 with any blank.")
    return 0


def cmd_pin(args: argparse.Namespace) -> int:
    """Record what a D8 fetch policy actually resolved to.

    D8 fixes the *rule* — latest stable Mathlib, current nLab, WordNet 3.1 — and this
    records the artifact. The digest is the pin; the commit/date/version beside it is
    provenance.
    """
    try:
        rec = seed_lock.record_pin(args.source, args.path, args.label)
    except GateViolation as exc:
        print(f"{RED}{exc}{RESET}", file=sys.stderr)
        return 1

    print(f"{GREEN}pinned{RESET} {rec['source']}")
    print(f"  path    {rec['path']}")
    print(f"  digest  {rec['digest']}")
    if rec["replaced"] and rec["replaced"] != rec["digest"]:
        print(f"  {YELLOW}replaced{RESET} {rec['replaced'][:16]} — the artifact changed under the same policy")
    print(f"\n  D8      {rec['d8_status']}")
    if rec["still_blank"]:
        print(f"  {YELLOW}still unpinned:{RESET} {', '.join(rec['still_blank'])}")
    else:
        print(f"  {DIM}all three artifacts pinned; `cli.py lock` is unblocked on D8{RESET}")
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    try:
        state = seed_lock.build(force=args.force)
    except GateViolation as exc:
        print(f"{RED}{exc}{RESET}", file=sys.stderr)
        return 1
    print(f"{GREEN}SEED.lock written{RESET}")
    print(f"  seed_hash  {state.seed_hash}")
    print(f"  files      {len(state.manifest['files'])}")
    return 0


def cmd_verify(_: argparse.Namespace) -> int:
    ok, problems = seed_lock.verify()
    if ok:
        state = seed_lock.load()
        assert state is not None
        print(f"{GREEN}seed hashes reproduce{RESET}  {state.seed_hash}")
        return 0
    print(f"{RED}GATE 4: seed drift{RESET}", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    print(
        "\nAnything that moves addresses is plastic: log a seed-morphism event and cold "
        "re-anneal. No silent bumps.",
        file=sys.stderr,
    )
    return 1


def cmd_register(args: argparse.Namespace) -> int:
    lock = seed_lock.current()
    entry = {
        "entry": "phase-run",
        "phase": args.phase,
        "seed_hash": lock.seed_hash,
        "provisional_seed": lock.provisional,
        "note": args.note or "",
    }
    append_registry(entry, REGISTRY_PATH)
    print(f"{GREEN}registered{RESET} {args.phase} @ {lock.seed_hash[:16]}")
    print("Commit registry/REGISTRY.jsonl before running the phase (KICKOFF section 7.2).")
    return 0


def cmd_p0(_: argparse.Namespace) -> int:
    print("P0 — scaffold + seed assembly")
    lock = seed_lock.current()
    if lock.provisional:
        pending = seed_lock.unresolved_decisions()
        print(f"  {YELLOW}GATE NOT MET{RESET}: SEED.lock absent; unresolved: {', '.join(pending)}")
        print("  Scaffold is complete; seed assembly awaits D3, D4 spend cap, D5, D6.")
        return 1
    ok, problems = seed_lock.verify()
    print(f"  lock complete          {_mark('pass' if not lock.provisional else 'fail')}")
    print(f"  hashes reproducible    {_mark('pass' if ok else 'fail')}")
    for p in problems:
        print(f"    - {p}")
    return 0 if ok else 1


def cmd_p1(args: argparse.Namespace) -> int:
    lock = seed_lock.current()
    print(f"P1 — null battery @ seed {lock.seed_hash[:16]}"
          + (f" {YELLOW}(provisional){RESET}" if lock.provisional else ""))

    d = decisions()
    extractors = build_k_extractors(d, offline=True)
    preminted = load_preminted()
    registry, imports = import_all(d.get("D8", {}), preminted_docs=preminted)
    for result in imports:
        mark = _mark("pass") if result.status == "imported" else _mark("blocked")
        print(f"  lexicon:{result.source:<12} {mark}  {result.detail}")
    print()

    report = run_battery(
        seed_hash=lock.seed_hash,
        extractors=extractors,
        beta=BETA_ARMS[0],
        preminted=preminted,
        held_out=None,
        corpus=(),
        samples=args.samples,
        registry=registry,
    )

    log = RunLog.open(lock.seed_hash, "P1")
    for cell in report.cells:
        print(f"  {cell.cell:<28} {_mark(cell.status.value)}  {_control(cell.control)}  {cell.detail}")
        log.write(cell=cell.cell, cell_status=cell.status.value, cert="monotone",
                  provenance="nulls", detail=cell.detail, stats=cell.stats,
                  control=cell.control.value, control_detail=cell.control_detail)
    log.write(phase="P1", cert="monotone", provenance="nulls",
              battery_status=report.status.value, dead_controls=report.dead_controls)

    if report.dead_controls:
        print(f"\n  {RED}dead controls:{RESET} {', '.join(report.dead_controls)}")
        print("  A cell that cannot fail is not evidence. The battery reads FAIL.")
        for cell in report.cells:
            if cell.control is ControlState.DEAD:
                print(f"    {cell.cell}: {cell.control_detail}")

    print(f"\n  battery  {_mark(report.status.value)}")
    print(f"  log      {log.path.relative_to(Path.cwd()) if log.path.is_relative_to(Path.cwd()) else log.path}")
    if report.status is NullStatus.BLOCKED:
        print(f"\n  {YELLOW}BLOCKED is not green.{RESET} PREREG R1 applies: the run is VOID. "
              "That is 'never tested', not 'tested and failed'.")
    if args.json:
        print(json.dumps(report.as_record(), indent=2))
    return 0 if report.status is NullStatus.PASS else 1


def cmd_demo(_: argparse.Namespace) -> int:
    """Smoke run on synthetic input. Touches no corpus and writes no run log."""
    from engine.constants import shadow
    from engine.pipeline import build_ledger, run_meter
    from engine.types import Document

    lock = seed_lock.current()
    extractors = build_k_extractors(decisions(), offline=True)
    docs = [
        Document("demo:en", "english",
                 "Positivity is preserved under composition.\n"
                 "The cone is positive. However, the cone is not positive in the degenerate case.\n"
                 "If the kernel accepts, the statement is certified.",
                 "repo_docs"),
        Document("demo:lean", "lean",
                 "theorem comp_pos (f g : Cone) : IsPositive (f ∘ g) := by simp\n"
                 "theorem add_pos (f g : Cone) : IsPositive (f + g)",
                 "lean_corpus"),
    ]
    ledger = build_ledger(docs, extractors)
    print("ledger", json.dumps(ledger.summary()))
    for beta in BETA_ARMS:
        result, _, cold = run_meter(ledger, beta, lock.seed_hash, shadow())
        certs = {s.certificate for s in cold.values()}
        print(f"  beta={beta}: loops={len(result.measurements)} "
              f"floor={result.mean_floor():.8f} q95={result.surrogate.get('q95', 0.0):.8f} "
              f"certs={certs or '{}'}")
    print(f"{DIM}synthetic only; no corpus was read and no run log was written{RESET}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """The usable surface (item A): run the pipeline on fixtures and render it."""
    from engine.surface import build_report, html_page, render_markdown

    report = build_report()
    md = render_markdown(report)
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
        print(f"{GREEN}wrote{RESET} {args.md}")
    if args.html:
        Path(args.html).write_text(html_page(report), encoding="utf-8")
        print(f"{GREEN}wrote{RESET} {args.html}")
    if not args.md and not args.html:
        print(md)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Interrogate the fixture run: slots | contested | verdicts | floors | correspondences
    | chart <name> | find <term>."""
    from engine.surface import build_report, query

    try:
        for line in query(build_report(), args.selector, args.arg):
            print(line)
    except ValueError as exc:
        print(f"{RED}{exc}{RESET}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="common-ground", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="decisions, lock state, phase readiness").set_defaults(fn=cmd_status)

    p_pin = sub.add_parser("pin", help="record a landed lexicon artifact's digest into D8")
    p_pin.add_argument("source", choices=sorted(seed_lock.PINNABLE))
    p_pin.add_argument("--path", required=True, help="the dump on disk (file or directory)")
    p_pin.add_argument("--commit", "--date", "--version", dest="label", default=None,
                       help="provenance: Mathlib commit, nLab scrape date, or WordNet version")
    p_pin.set_defaults(fn=cmd_pin)

    p_lock = sub.add_parser("lock", help="write seed/SEED.lock")
    p_lock.add_argument("--force", action="store_true",
                        help="write despite unresolved decisions (records lock_status anyway)")
    p_lock.set_defaults(fn=cmd_lock)

    sub.add_parser("verify", help="gate-4 tripwire").set_defaults(fn=cmd_verify)

    p_reg = sub.add_parser("register", help="append a REGISTRY.jsonl entry before a phase run")
    p_reg.add_argument("phase")
    p_reg.add_argument("--note", default="")
    p_reg.set_defaults(fn=cmd_register)

    sub.add_parser("p0", help="P0 gate").set_defaults(fn=cmd_p0)

    p_p1 = sub.add_parser("p1", help="P1 null battery")
    p_p1.add_argument("--samples", type=int, default=None)
    p_p1.add_argument("--json", action="store_true")
    p_p1.set_defaults(fn=cmd_p1)

    sub.add_parser("demo", help="synthetic smoke run").set_defaults(fn=cmd_demo)

    p_report = sub.add_parser("report", help="usable surface: render the fixture run")
    p_report.add_argument("--md", default=None, help="write the markdown report to this path")
    p_report.add_argument("--html", default=None, help="write the openable HTML page to this path")
    p_report.set_defaults(fn=cmd_report)

    p_query = sub.add_parser("query", help="interrogate the fixture run")
    p_query.add_argument("selector",
                         help="slots | contested | verdicts | floors | correspondences | chart | find")
    p_query.add_argument("arg", nargs="?", default=None, help="name (chart) or term (find)")
    p_query.set_defaults(fn=cmd_query)

    args = parser.parse_args(argv)
    if getattr(args, "samples", None) is None and hasattr(args, "samples"):
        from engine.constants import NULL_FUZZ_SAMPLES

        args.samples = NULL_FUZZ_SAMPLES
    try:
        return int(args.fn(args))
    except GateViolation as exc:
        print(f"{RED}{exc}{RESET}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
