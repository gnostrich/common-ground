"""Making a deploy self-sufficient: seed its state once, then let it find its own arrows.

A deployed window used to be a photograph. The corpus snapshot and the proposer's journal
were uploaded with the code, so the page showed whatever had been found at upload time and
nothing after — every new arrow needed somebody to redeploy by hand. That is a chore that
will not get done, and a page that silently stops moving is worse than one that says it has
stopped.

Two pieces fix it, and both are about durability rather than cleverness:

**Seeding.** A platform volume mounted at `runs/` SHADOWS whatever the image shipped there,
so uploading state into `runs/` and then mounting a volume over it loses the state on the
first boot. The upload therefore goes to `seed_runs/`, and `seed_state()` copies anything the
volume does not already have. Copy-if-absent, never overwrite: the volume is the live record
once it exists, and re-seeding over it would silently roll the journal back to upload time.

**The daemon in-process.** With `PROPOSER_IN_PROCESS=1` the web service starts the continuous
proposer on a background thread, writing to the same volume the window reads. The deploy then
finds arrows on its own and the page moves without anybody touching it.

It runs the gate suite ONCE at startup rather than every N batches. In a deployed image the
tree cannot change between deploys, so repeating the check re-measures a constant — and this
is the opposite of the case on a development machine, where a human editing files under the
process is precisely why the suite is re-run and why a torn read must not be mistaken for a
regression.

Everything the thread does is EXTRACTION tier. It proposes; it promotes nothing; and it is
still bounded by the same control file, so `pause`, `stop`, the rate and the cost cap all
work against a deployed daemon exactly as against a local one.
"""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path

#: Where the image ships its state. A volume mounted over `runs/` would hide it otherwise.
SEED_DIR_NAME = "seed_runs"

#: Files worth carrying into a fresh volume. The snapshot and pool are expensive to rebuild
#: and are pure functions of (corpus, seed, code); the journal is the irreplaceable one.
SEEDED = ("corpus.snapshot", "pool.jsonl", "proposer.journal.jsonl", "census.json")


def seed_state(root: Path | None = None) -> dict[str, str]:
    """Copy shipped state into `runs/` for anything the volume does not already hold.

    Copy-if-absent is the whole contract. Once a deploy has run, its journal is the live
    record of what was asked and answered; overwriting it from the image would roll the
    ledger back to upload time and re-ask thousands of pairs that were already paid for.
    """
    base = Path(root) if root else Path(__file__).resolve().parents[1]
    src, dst = base / SEED_DIR_NAME, base / "runs"
    out: dict[str, str] = {}
    if not src.is_dir():
        return {"seed": "absent — nothing shipped with the image"}
    dst.mkdir(parents=True, exist_ok=True)
    for name in SEEDED:
        shipped, live = src / name, dst / name
        if not shipped.exists():
            out[name] = "not shipped"
        elif live.exists():
            out[name] = f"kept (volume has {live.stat().st_size:,} bytes)"
        else:
            shutil.copy2(shipped, live)
            out[name] = f"seeded ({live.stat().st_size:,} bytes)"
    return out


def _run_proposer() -> None:
    """The daemon, on a thread, against the same files the window reads."""
    from engine.continuous import (
        CONTROL_PATH,
        JOURNAL_PATH,
        POOL_PATH,
        STATUS_PATH,
        ContinuousProposer,
        Control,
    )
    from engine.journal import Journal

    if not Path(POOL_PATH).exists():
        print(f"[proposer] no candidate pool at {POOL_PATH} — not starting. Ship one in "
              f"{SEED_DIR_NAME}/ or run build-pool.", flush=True)
        return

    # The SAME transport the command line uses. A second implementation here would be a
    # second thing to drift, and this one already refuses any key that is not OpenRouter.
    import proposerd

    try:
        transport, model = proposerd._openrouter_transport()
    except SystemExit as exc:
        print(f"[proposer] not starting: {exc}", flush=True)
        return

    # The control file is the operator's hand on this process whether it runs here or on a
    # laptop, so a deploy writes its starting rate INTO that file rather than holding it in
    # a variable the window cannot see or change.
    control = Control.read(CONTROL_PATH)
    if os.environ.get("PROPOSER_CALLS_PER_HOUR", "").strip():
        control.calls_per_hour = int(os.environ["PROPOSER_CALLS_PER_HOUR"])
    if os.environ.get("PROPOSER_MAX_COST", "").strip():
        control.max_cost = float(os.environ["PROPOSER_MAX_COST"])
    control.stop = False
    control.write(CONTROL_PATH)

    journal = Journal(JOURNAL_PATH)
    print(f"[proposer] in-process: model={model} rate={control.calls_per_hour}/h "
          f"cap={control.max_cost} — EXTRACTION only, promotes nothing", flush=True)
    proposer = ContinuousProposer(
        journal=journal, transport=transport, pool_path=POOL_PATH,
        control_path=CONTROL_PATH, status_path=STATUS_PATH, suite_once=True)
    try:
        proposer.run()
        print(f"[proposer] loop ended: {proposer.status.reason}", flush=True)
    except Exception as exc:                      # a dead thread must leave a record
        import traceback

        print(f"[proposer] died: {type(exc).__name__}: {exc}\n"
              f"{traceback.format_exc()[-1500:]}", flush=True)
    finally:
        journal.close()


def start_proposer_if_asked() -> threading.Thread | None:
    """Start the daemon on a daemon-thread when `PROPOSER_IN_PROCESS` is set.

    Off by default. A window is a read surface, and a process that spends money should not
    begin doing so because somebody deployed a web service.
    """
    if os.environ.get("PROPOSER_IN_PROCESS", "").strip() not in ("1", "true", "yes"):
        return None
    thread = threading.Thread(target=_run_proposer, name="proposer", daemon=True)
    thread.start()
    return thread
