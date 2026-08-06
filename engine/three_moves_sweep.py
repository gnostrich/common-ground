"""`python -m engine.three_moves_sweep` — print the three-moves belonging table.

Every registered extension of the object, with the single move it reduces to. A non-zero
exit means some extension fits none of {swap-base, add-measure, add-morphism} — i.e.
jack-of-all-trades creep slipped into the registry. That is object-singularity failing,
and it fails the build the same way an unclassified gate-6 band does.
"""

from __future__ import annotations

from .three_moves import EXTENSIONS, check_belonging


def main() -> int:
    result = check_belonging()
    for e in EXTENSIONS:
        mark = e.move if e.move in {"swap-base", "add-measure", "add-morphism"} else "CREEP"
        print(f"{e.name:<44} {mark:<13} {e.status}")
    print(f"\n{result.checked} extension(s); by move: "
          + ", ".join(f"{m}={n}" for m, n in result.by_move.items()))
    for e in result.unclassified:
        print(f"UNCLASSIFIED (creep): {e.name} — move={e.move!r} fits no legal move")
    for e in result.bad_status:
        print(f"BAD STATUS: {e.name} — status={e.status!r}")
    if not result.ok:
        print("An extension must reduce to exactly one of swap-base / add-measure / "
              "add-morphism, or it does not belong (seed/OBJECT.md).")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
