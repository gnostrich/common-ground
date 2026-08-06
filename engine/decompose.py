"""OI-30: A KNOWN CAUSE MUST NOT ABSORB AN UNKNOWN ONE.

A total gets explained by causes, the named causes do not add up to the total, and the
remainder goes somewhere. There are only three places it can go, and two of them are lies:

  * folded into the largest named cause, which overstates a real mechanism,
  * silently dropped, so the parts do not sum and nobody can tell by looking,
  * named as UNATTRIBUTED, which is the truth and is the only option this module offers.

WHY IT MATTERS HERE SPECIFICALLY. This engine's whole claim is that its numbers are what the
physics did. A decomposition whose remainder has been folded into a named cause reports a
mechanism working better than it does, and reports it in the exact register — a clean table of
causes — that reads as rigour. The lean-delta separation is the precedent: a delta that a
known cause explained was kept apart from one nothing explained, and keeping them apart is
what made the unexplained one findable.

THE SHAPE IS OI-24'S, ONE LEVEL UP. There, a census over nothing had to be a different object
from a census that found nothing. Here, a remainder of zero has to be a different object from
a remainder nobody computed — so `unattributed` is ALWAYS present, including when it is zero.
A missing key and a zero are the same to a reader skimming a table, which is why the key is
never omitted.

OVER-ATTRIBUTION IS A DIFFERENT DEFECT and gets a different answer. If the named causes sum to
MORE than the total, something is double-counted; a negative remainder would be arithmetic
covering a bug. That raises.
"""

from __future__ import annotations


class OverAttributed(Exception):
    """Named causes sum to more than the total. Something is counted twice."""


class NotDecomposed(Exception):
    """`attributed()` was asked of a record that carries no decomposition."""


#: The key. One spelling, everywhere, so a reader who learns it once can scan any table this
#: engine prints and know immediately whether a remainder was computed or merely absent.
UNATTRIBUTED = "unattributed"


def decompose(operation: str, total: int | float, parts: dict,
              unit: str = "item") -> dict:
    """Explain `total` by named causes, and NAME what the causes do not explain."""
    named = sum(parts.values())
    if named > total:
        raise OverAttributed(
            f"{operation}: named causes sum to {named} but the total is {total}. A negative "
            f"remainder is arithmetic covering a double count, so it is refused rather than "
            f"reported. Causes: {dict(parts)}")
    rest = total - named
    # OI-24 LIVES INSIDE OI-30. A decomposition of a ZERO total reports every cause at zero
    # and a remainder of zero, which reads as "everything is explained" — success on the empty
    # set, one level up. Nothing was explained because nothing happened, and those are
    # different facts. `refused` marks it with the same word `engine.nonempty` uses, so one
    # reader's habit covers both.
    refused = (total == 0)
    return {
        "operation": operation,
        "total": total,
        "unit": unit,
        "by_cause": dict(parts),
        # ALWAYS PRESENT, including at zero. A missing key and a zero read identically to
        # somebody skimming, and the whole point is that they must not.
        UNATTRIBUTED: rest,
        "refused": refused,
        "note": (f"no {unit}(s) happened, so nothing was explained and nothing was left "
                 f"unexplained. This is NOT a clean decomposition; it is an empty one."
                 if refused else
                 f"{named} of {total} {unit}(s) are explained by a named cause; {rest} "
                 f"{'is' if rest == 1 else 'are'} NOT. An unattributed count is a measurement, "
                 f"not a rounding error — it is the part no mechanism here accounts for."
                 if rest else
                 f"all {total} {unit}(s) are explained by a named cause."),
    }


def attributed(record: dict) -> bool:
    """Is every unit explained? Raises for a record that never decomposed anything.

    The refusal matters as much as the answer: asking "is it fully attributed?" of a plain
    counts dict would get `True` from a dict that simply has no remainder key, which is the
    silent-drop case this module exists to make impossible.
    """
    if not isinstance(record, dict) or UNATTRIBUTED not in record or "by_cause" not in record:
        raise NotDecomposed(
            f"this record carries no decomposition, so it cannot be asked whether everything "
            f"is attributed. Build it with decompose(). Keys present: "
            f"{sorted(record) if isinstance(record, dict) else type(record).__name__}")
    if record.get("refused"):
        raise NotDecomposed(
            f"{record.get('operation', 'this decomposition')} covered 0 {record.get('unit', 'item')}(s), "
            f"so it cannot be fully or partly attributed. {record.get('note', '')}".strip())
    return not record[UNATTRIBUTED]


def sums(record: dict) -> bool:
    """The arithmetic, checkable by a reader of the record alone."""
    return (sum(record["by_cause"].values()) + record[UNATTRIBUTED]) == record["total"]
