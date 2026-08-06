"""THE BEHAVIOURAL GATE, RUN. A gloss's warrant is its measured effect, never its plausibility.

Each fixture is perturbed twice — once with the glossary in the compiled sheet and once
without — and the two existing invariant metrics are compared:

  DISCRIMINATION  attachment fraction of the region, deduped by target slot. LOWER is more
                  selective. Invariant to how verbosely the medium replies.
  CITATION        share of sentences carrying a resolvable citation. LOWER-bounded by the
                  sentence count, not by word count. HIGHER is better.

Neither metric is new, and that is deliberate: the standing rule is that no metric ships
without its invariance asserted, and both of these have theirs asserted where they live.

SET-LEVEL FIRST, AND SAID SO. This run measures the glossary AS A SET. Attributing a delta to
one gloss needs a leave-one-out run per gloss — twenty glosses is twenty more A/B passes — so
the per-gloss column reports UNATTRIBUTED rather than dividing the set effect up and calling
each share a measurement. A number that looks per-gloss but is a set effect divided by twenty
is exactly the kind of reading this project has had to withdraw before.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.battery import BATTERY_PATH          # noqa: E402
from engine.grounded import check_answer         # noqa: E402
from engine.medium import (FAILED, VALIDATED, load_glosses, save_glosses)  # noqa: E402
from engine.structure_trace import STRUCTURAL_QUESTION_DEFAULT  # noqa: E402


def fixtures() -> list[tuple[str, str]]:
    spec = json.loads(Path(BATTERY_PATH).read_text(encoding="utf-8"))
    out = [(i.get("id", "?"), i.get("text", "")) for i in spec.get("inputs", [])]
    out.append(("structural", STRUCTURAL_QUESTION_DEFAULT))
    return out


def one_run(question: str, use_glossary: bool) -> dict:
    """One perturbation, one answer, both metrics. The glossary is the only thing that varies."""
    import engine.medium as medium
    from ui.current import _region_transport, ask_the_corpus
    from ui.lm import LMClient, api_key
    from engine.inbound import INBOUND_SYSTEM

    real = medium.load_glosses
    if not use_glossary:
        medium.load_glosses = lambda *a, **k: []
    try:
        rec = ask_the_corpus(question, "english", key=None)
    finally:
        medium.load_glosses = real

    att = rec.get("attachment") or (rec.get("compiled") or {}).get("attachment") or {}
    disc = float((att.get("discrimination") or {}).get("fraction") or 0.0)

    client = LMClient(api_key(None))
    reply = client.complete(INBOUND_SYSTEM, rec["compiled"], 0.2, 1200).strip()
    v = check_answer(reply, rec)
    cite = (v.cited + v.asserted_absent) / v.checked if v.checked else 0.0
    return {"discrimination": disc, "citation": round(cite, 4),
            "checked": v.checked, "ok": v.ok}


def main() -> None:
    glosses = load_glosses()
    if not glosses:
        raise SystemExit("no glosses on disk — run the extraction first")

    rows = []
    for name, text in fixtures():
        without = one_run(text, False)
        with_ = one_run(text, True)
        rows.append({"fixture": name, "without": without, "with": with_})
        print(f"{name:14s} disc {without['discrimination']:.3f} -> {with_['discrimination']:.3f}"
              f"   cite {without['citation']:.3f} -> {with_['citation']:.3f}")

    n = len(rows) or 1
    agg_without = {k: sum(r["without"][k] for r in rows) / n for k in ("discrimination", "citation")}
    agg_with = {k: sum(r["with"][k] for r in rows) / n for k in ("discrimination", "citation")}
    print(f"\nSET MEAN  disc {agg_without['discrimination']:.4f} -> {agg_with['discrimination']:.4f}"
          f"   cite {agg_without['citation']:.4f} -> {agg_with['citation']:.4f}")

    from engine.medium import validate
    for g in glosses:
        validate(g, agg_without, agg_with)
        g.note = ("SET-LEVEL: this delta is the whole glossary's effect, not this gloss's. "
                  "Per-gloss attribution needs a leave-one-out run and has not been done. "
                  + g.note)
    save_glosses(glosses)
    survived = sum(1 for g in glosses if g.status == VALIDATED)
    print(f"\n{survived}/{len(glosses)} glosses survive the set-level gate "
          f"({sum(1 for g in glosses if g.status == FAILED)} failed)")
    Path("runs/gloss_validation.json").write_text(
        json.dumps({"rows": rows, "without": agg_without, "with": agg_with}, indent=1))


if __name__ == "__main__":
    main()
