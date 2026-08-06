"""THE BEHAVIOURAL GATE AT PROPER n. Repeats, per-class rows, and a paired statistic.

THE FIRST RUN WAS UNDER-POWERED AND SAID SO. Four fixtures, one run each, produced a citation
delta of -0.0036 — about one sentence in 275 — and a discrimination delta of -0.14. The gate
refused the glossary on the citation term, correctly, because the gate is a conjunction. But
refusing on a quantity that small at n=4 is not a measurement; it is a coin landing on the
side the arithmetic happened to fall.

WHAT THIS RUN DOES DIFFERENTLY, and why each part is needed:

  MORE FIXTURES   the whole battery, the acceptance-session questions, both halves of the
                  paraphrase pair, and the canonical structural question. The paraphrase pair
                  earns its place twice over: it is the cliff test, so if a glossary makes two
                  near-identical phrasings diverge, that shows up here rather than later.
  REPEATS         every fixture runs R times per arm. Without repeats there is no estimate of
                  run-to-run variation, and without that a delta cannot be called real or
                  noise — only asserted to be one. The medium is sampled, not deterministic;
                  the same question twice is not the same measurement twice.
  PAIRED          arms alternate within a repeat, so drift in the served model over a
                  half-hour run lands on both arms rather than on one.
  PER CLASS       every fixture carries a CLASS (sharp / question / vague / paraphrase /
                  structural) and is reported per class as well as pooled. The first run had
                  the structural fixture improving by 0.61 and the vague fixture degrading to
                  the limit case in the same average. An average over two effects with
                  opposite signs is a number about neither.

THE STATISTIC, and it is not a rate. `MIN_RATE_N` governs rates; this is a paired mean
difference over independent runs, so what makes it a finding is its own dispersion: the mean
paired delta is reported with the standard error across pairs, and a delta is DISTINGUISHABLE
only when |mean| exceeds twice that error. Anything else is reported as indistinguishable at
this n, with the n stated, and the number of pairs that would be needed is stated too rather
than left for the reader to infer.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.battery import BATTERY_PATH                      # noqa: E402
from engine.grounded import check_answer                     # noqa: E402
from engine.medium import FAILED, VALIDATED, load_glosses, save_glosses, validate  # noqa: E402
from engine.structure_trace import STRUCTURAL_QUESTION_DEFAULT  # noqa: E402

#: Runs per fixture per arm. Three is the smallest number that yields a dispersion estimate at
#: all; it is stated as the floor it is, not as a sufficient n, and the report says what n
#: would be needed for whatever it finds.
REPEATS = 3

#: The operator's own questions, from the acceptance session — the ones that decide usable.
ACCEPTANCE = [
    ("acceptance", "what is the relationship between the second fundamental form and the "
                   "spectral gap"),
    ("acceptance", "does this corpus contain anything about holonomy"),
    ("acceptance", "what won't reconcile"),
]


def fixtures() -> list[tuple[str, str, str]]:
    """(class, id, text). The class is what makes the per-class rows possible."""
    spec = json.loads(Path(BATTERY_PATH).read_text(encoding="utf-8"))
    out: list[tuple[str, str, str]] = []
    for item in spec.get("inputs", []):
        out.append((item.get("id", "?"), item.get("id", "?"), item.get("text", "")))
    pair = spec.get("paraphrase_pair") or {}
    for half in ("a", "b"):
        if pair.get(half):
            out.append(("paraphrase", f"paraphrase-{half}", pair[half]))
    for i, (cls, q) in enumerate(ACCEPTANCE, start=1):
        out.append((cls, f"{cls}-{i}", q))
    out.append(("structural", "structural", STRUCTURAL_QUESTION_DEFAULT))
    return out


def one_run(question: str, use_glossary: bool) -> dict:
    """One perturbation, one answer, both metrics. The glossary is the only thing that varies."""
    import engine.medium as medium
    from engine.inbound import INBOUND_SYSTEM
    from ui.current import ask_the_corpus
    from ui.lm import LMClient, api_key

    real = medium.load_glosses
    if not use_glossary:
        medium.load_glosses = lambda *a, **k: []
    try:
        rec = ask_the_corpus(question, "english", key=None)
    finally:
        medium.load_glosses = real

    att = rec.get("attachment") or {}
    disc = float((att.get("discrimination") or {}).get("fraction") or 0.0)
    reply = LMClient(api_key(None)).complete(INBOUND_SYSTEM, rec["compiled"], 0.2, 1200).strip()
    v = check_answer(reply, rec)
    cite = (v.cited + v.asserted_absent) / v.checked if v.checked else 0.0
    return {"discrimination": disc, "citation": round(cite, 4), "sentences": v.checked}


def paired(deltas: list[float]) -> dict:
    """Mean paired delta with the dispersion that decides whether it is a finding."""
    n = len(deltas)
    mean = statistics.fmean(deltas) if n else 0.0
    sd = statistics.stdev(deltas) if n > 1 else 0.0
    se = (sd / (n ** 0.5)) if n > 1 else 0.0
    distinguishable = bool(se) and abs(mean) > 2 * se
    # How many pairs WOULD be needed for this effect at this dispersion, so an
    # indistinguishable result reports its own cost instead of leaving it to be inferred.
    needed = int(((2 * sd / abs(mean)) ** 2) + 0.999) if mean and sd else 0
    return {"mean": round(mean, 5), "sd": round(sd, 5), "se": round(se, 5), "n": n,
            "distinguishable": distinguishable, "pairs_needed": needed}


def main() -> None:
    glosses = load_glosses()
    if not glosses:
        raise SystemExit("no glosses on disk — run the extraction first")

    fx = fixtures()
    print(f"{len(fx)} fixture(s) x {REPEATS} repeat(s) x 2 arms = "
          f"{len(fx) * REPEATS * 2} runs\n")

    rows: list[dict] = []
    for cls, fid, text in fx:
        for r in range(REPEATS):
            # ARMS ALTERNATE so model drift over a long run lands on both, not on one.
            first, second = (False, True) if r % 2 == 0 else (True, False)
            a = one_run(text, first)
            b = one_run(text, second)
            without, with_ = (a, b) if first is False else (b, a)
            rows.append({"class": cls, "fixture": fid, "repeat": r,
                         "without": without, "with": with_,
                         "d_disc": with_["discrimination"] - without["discrimination"],
                         "d_cite": with_["citation"] - without["citation"]})
            print(f"  {fid:16s} r{r}  disc {without['discrimination']:.3f}->"
                  f"{with_['discrimination']:.3f}  cite {without['citation']:.3f}->"
                  f"{with_['citation']:.3f}")

    pooled = {"discrimination": paired([r["d_disc"] for r in rows]),
              "citation": paired([r["d_cite"] for r in rows])}
    per_class: dict[str, dict] = {}
    for cls in sorted({r["class"] for r in rows}):
        sub = [r for r in rows if r["class"] == cls]
        per_class[cls] = {"discrimination": paired([r["d_disc"] for r in sub]),
                          "citation": paired([r["d_cite"] for r in sub])}

    print("\nPOOLED")
    for k, v in pooled.items():
        mark = "FINDING" if v["distinguishable"] else f"indistinguishable at n={v['n']}"
        extra = "" if v["distinguishable"] else f" (needs ~{v['pairs_needed']} pairs)"
        print(f"  {k:16s} {v['mean']:+.5f} +- {v['se']:.5f} (sd {v['sd']:.5f}, n {v['n']})"
              f"  {mark}{extra}")

    print("\nPER CLASS")
    for cls, v in per_class.items():
        d, c = v["discrimination"], v["citation"]
        print(f"  {cls:12s} disc {d['mean']:+.4f}+-{d['se']:.4f}"
              f"{' FINDING' if d['distinguishable'] else ''}   "
              f"cite {c['mean']:+.4f}+-{c['se']:.4f}"
              f"{' FINDING' if c['distinguishable'] else ''}")

    # THE GATE, fed the pooled means — but ONLY the deltas that are distinguishable count as
    # movement. An indistinguishable delta is not a small improvement and not a small
    # worsening; it is no measurement, and feeding it to a conjunction lets noise decide.
    eff = {}
    for metric, v in pooled.items():
        eff[metric] = v["mean"] if v["distinguishable"] else 0.0
    baseline = {"discrimination": 0.0, "citation": 0.0}
    for g in glosses:
        validate(g, baseline, eff)
        g.note = (f"n={pooled['discrimination']['n']} pairs, set-level. " + g.note)
    save_glosses(glosses)
    survived = sum(1 for g in glosses if g.status == VALIDATED)
    print(f"\n{survived}/{len(glosses)} glosses survive "
          f"({sum(1 for g in glosses if g.status == FAILED)} failed)")

    Path("runs/gloss_validation.json").write_text(json.dumps(
        {"repeats": REPEATS, "rows": rows, "pooled": pooled, "per_class": per_class,
         "effective_deltas_fed_to_gate": eff}, indent=1))
    print("\nwritten: runs/gloss_validation.json")


if __name__ == "__main__":
    main()
