"""OI-24: AN OPERATION THAT RAN ON NOTHING DID NOT SUCCEED — IT DID NOT RUN.

The violation this exists for: kind demotion was applied at snapshot-build time, where the
snapshot carries zero arrows because arrows live in the proposer's journal. It adjudicated
nothing, found nothing to demote, and reported a census of all zeroes — which reads exactly
like "the corpus is clean". Two opposite states, one output. The bug ran for a full cycle and
was found by reading the code, not by reading the report, because the report could not say it.

THE SHAPE OF THE DEFECT is general and has nothing to do with demotion. Any operation that
summarizes what it found over a population will, on an empty population, emit a summary
indistinguishable from a clean one — zero findings, zero violations, zero conflicts. Success
on the empty set. It is a defect class, not an incident, so the fix is a shared vocabulary
rather than a guard bolted onto one function.

TWO REGISTERS, and the difference is whether the caller is wrong or the corpus is.

  `require()`  — the population is empty and that is a CALLER BUG. Adjudicating at a place
                 where there is nothing to adjudicate is not a state of the world; it is
                 the wrong call site. Raise, loudly, with the operation named.

  `census()`   — the population is empty and that is a legitimate STATE. An empty corpus, a
                 chart nobody has ingested, a run with no arrows yet. The result is not a
                 finding of zero; it is a REFUSAL, and it says so in the record so that no
                 consumer and no reader can take it for a clean bill of health.

`clean()` is the third piece and the load-bearing one: it is the only way to ask a census
whether it found nothing, and it REFUSES to answer for a refused census. That is what makes
the empty case unrepresentable as success rather than merely discouraged — a consumer cannot
accidentally read `findings == 0` as clean, because the question goes through here.
"""

from __future__ import annotations

from typing import Any, Iterable, Sized


class EmptyAdjudication(Exception):
    """An operation was asked to adjudicate an empty population at a site where that is a bug."""


class RefusedCensus(Exception):
    """`clean()` was asked whether a census over nothing found nothing. It cannot answer."""


def size(population: Any) -> int:
    """Length without consuming. A generator has no size, and pretending otherwise would put
    this module's own blind spot exactly where the defect it guards lives."""
    if population is None:
        return 0
    if isinstance(population, Sized):
        return len(population)
    raise TypeError(f"a population must be sized to be censused; got {type(population).__name__}")


def require(operation: str, population: Any, unit: str = "input") -> int:
    """Assert a non-empty population, or raise naming the operation and the unit."""
    n = size(population)
    if n == 0:
        raise EmptyAdjudication(
            f"{operation}: asked to adjudicate 0 {unit}(s). An all-zero result here would be "
            f"indistinguishable from a clean one, so it is refused rather than reported. "
            f"If an empty population is a real state at this site, use census(), not require().")
    return n


def census(operation: str, population: Any, findings: dict | None = None,
           unit: str = "input") -> dict:
    """A census that carries its own population and cannot report clean over nothing."""
    n = size(population)
    out: dict = dict(findings or {})
    out["operation"] = operation
    out["population"] = n
    out["refused"] = (n == 0)
    if n == 0:
        out["note"] = (f"{operation} adjudicated 0 {unit}(s). This is NOT a finding of zero "
                       f"violations — nothing was examined. Every count below is the count of "
                       f"an empty scan and asserts nothing about the corpus.")
    return out


def clean(record: dict, *counted: str) -> bool:
    """Did this census find nothing? Raises for a refused one rather than saying yes.

    The only sanctioned way to read a census as a clean bill of health. `counted` names the
    keys that are findings; with none given, every integer value counts.
    """
    if record.get("refused"):
        raise RefusedCensus(
            f"{record.get('operation', 'this census')} examined nothing "
            f"({record.get('population', 0)} in population), so it cannot be clean or dirty. "
            f"{record.get('note', '')}".strip())
    keys: Iterable[str] = counted or [k for k, v in record.items()
                                      if isinstance(v, int) and not isinstance(v, bool)
                                      and k != "population"]
    return all(not record.get(k) for k in keys)
