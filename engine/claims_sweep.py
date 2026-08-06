"""`make claims` — gate 10: every claimed property is warranted by a control, or not claimed.

Docstrings are not warrants. A function that claims a complexity bound, an index, an
exactness property or an equivalence must have that property enforced by a named control.
"""

from __future__ import annotations

import sys

from .static_checks import CLAIMED_PROPERTY_SITES, check_claim_discipline


def main() -> int:
    result = check_claim_discipline()
    print(f"gate 10 — claim discipline: {result.checked_functions} function(s) across "
          f"{result.checked_files} file(s)\n")
    for row in CLAIMED_PROPERTY_SITES:
        print(f"  {row['site']}")
        print(f"      claims  {row['claim']}")
        print(f"      control {row['control']}")
    if result.violations:
        print(f"\n{len(result.violations)} UNWARRANTED CLAIM(S):")
        for v in result.violations:
            print(f"  - {v}")
        print("\nEither assert the property in a control and register the site, or remove "
              "the claim. A docstring is a description of intent, not a property of the build.")
        return 1
    print(f"\n{len(CLAIMED_PROPERTY_SITES)} claimed propert(ies), all warranted. OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
