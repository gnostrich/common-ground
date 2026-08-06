"""OI-36: THE REFLEXIVITY FIREWALL. common-ground's own material stays out of its corpus.

WHY THIS IS NOT HYGIENE. The engine measures whether two claims in different charts say the
same thing. Its own source and its own constitution are claims in english and python about
correspondence, faithfulness, charts and arrows — so if they enter the corpus, every
measurement about correspondence acquires a term contributed by the thing doing the measuring.
The engine would start finding that its own docstring corresponds to its own code, report the
arrow as evidence about the world, and feed it back into the settlement whose energy that
arrow now shifts. Not a false result: an ungrounded one, and one whose loop has no outside.

It is also the one contamination an operator cannot see by reading the answer. A perturbation
that lands in this repo's own material returns claims that are ABOUT the vocabulary of the
question, because the question and the material were written in the same idiolect by the same
person. That reads as the corpus being unusually responsive.

TWO ARMS, BOTH DECLARED FACTS. Neither compares text for resemblance — the banned move, and
doubly banned in a firewall whose whole job is to keep the referee out of the game.

  PROVENANCE  — a slot whose doc id names this repository, by bucket or by a path this
                repository tracks. Exact string facts about where material came from.
  EXACT nu    — a slot whose nu is BYTE-IDENTICAL to the nu of a line of this repo's own seed
                documents. That is gate 1's identity rule, not a similarity: a collision here
                means the same normalized claim, and the seed is where this repo's most
                distinctive prose lives. Catches an ingest re-labelled under another repo.

THE BLIND SPOT, DECLARED. A copy of this repo's material ingested under a different repo
label, from different paths, and paraphrased enough to miss exact-nu collision is invisible
here — and must stay invisible, because the only detector that would catch it is the
resemblance mechanism this engine exists to refuse. The firewall is as strong as declaration
allows and no stronger, which is a property of the design rather than a shortfall in it.
"""

from __future__ import annotations

from pathlib import Path

from .nonempty import census

REPO = Path(__file__).resolve().parent.parent

#: How this repository could be NAMED in a doc id's bucket. Lowercased comparison; these are
#: the spellings a corpus builder could plausibly produce for this repo, not a guess at
#: arbitrary names. A bucket that is none of these is another project's, by declaration.
OWN_BUCKETS = ("common-ground", "common_ground", "commonground")

#: Directories whose contents are this repository's own material rather than corpus material.
#: `runs/` is excluded deliberately: it holds the corpus, which is not this repo's material.
OWN_DIRS = ("engine/", "ui/", "tools/", "tests/", "seed/", "hooks/")

#: Seed documents whose lines are hashed for the exact-nu arm. The constitution and the spec
#: are this repository's most distinctive declared prose, and they are small enough to hash
#: on every run — the arm costs nothing it has to be budgeted for.
SEED_DOCS = ("CONSTITUTION.md", "SPEC.md", "DIALOGIC.md")

#: A line must be at least this long to be hashed. Short lines ("---", "GO", a bare heading)
#: collide with ordinary prose anywhere and would manufacture matches — a false positive in a
#: firewall is worse than useless, because it trains the reader to ignore it.
MIN_LINE = 40


def own_paths() -> set[str]:
    """Every source path this repository tracks, relative and slash-separated."""
    out: set[str] = set()
    for d in OWN_DIRS:
        base = REPO / d.rstrip("/")
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                out.add(str(p.relative_to(REPO)))
    return out


def own_nus(chart: str = "english") -> set[str]:
    """The nu of every substantial line of this repo's seed documents. Exact addressing."""
    from .normalize import nu

    out: set[str] = set()
    for name in SEED_DOCS:
        p = REPO / "seed" / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if len(line) >= MIN_LINE:
                out.add(nu(chart, line))
    return out


def matches(snapshot, paths: set[str] | None = None,
            nus: set[str] | None = None) -> list[dict]:
    """Slots that are this repository's own material, by declaration. Never by resemblance."""
    paths = own_paths() if paths is None else paths
    nus = own_nus() if nus is None else nus
    found: list[dict] = []
    for sid, rec in (getattr(snapshot, "slots", None) or {}).items():
        docs = tuple(str(d) for d in (getattr(rec, "docs", None) or ()))
        for d in docs:
            bucket, _, rest = d.partition("||")
            if bucket.strip().lower() in OWN_BUCKETS:
                found.append({"slot": sid, "arm": "provenance", "why": f"bucket {bucket!r}",
                              "doc": d})
                break
            tail = rest.split("#")[0].strip().lstrip("./")
            if tail and tail in paths:
                found.append({"slot": sid, "arm": "provenance",
                              "why": f"path {tail!r} is tracked by this repository", "doc": d})
                break
        else:
            if (getattr(rec, "nu", "") or "") in nus:
                found.append({"slot": sid, "arm": "exact-nu",
                              "why": "nu is byte-identical to a line of this repo's seed",
                              "doc": docs[0] if docs else ""})
    return found


def audit(snapshot) -> dict:
    """The standing census. Refused over an empty snapshot — OI-24: nothing examined is not
    a finding of zero. `blind_spot` travels ON the record, because a firewall reported without
    its limit is read as a guarantee."""
    slots = getattr(snapshot, "slots", None) or {}
    found = matches(snapshot)
    return census("reflexivity_firewall", slots, {
        "matches": len(found),
        "by_arm": {"provenance": sum(1 for f in found if f["arm"] == "provenance"),
                   "exact-nu": sum(1 for f in found if f["arm"] == "exact-nu")},
        "examples": found[:20],
        "blind_spot": ("this repo's material re-labelled under another bucket, ingested from "
                       "untracked paths, and paraphrased past exact-nu collision is NOT "
                       "detected. The only mechanism that would catch it is textual "
                       "resemblance, which this engine refuses everywhere else and refuses "
                       "here most of all."),
    }, unit="slot")
