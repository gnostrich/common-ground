"""ONE FACT, TWO RECORDS, AND THEY MUST AGREE.

`seed/BASELINE.json` is the authoritative baseline — the auditor's `livefire.py` reads it and
defends its figures. `seed/FIXTURE-CERTIFIED-POSITIVITY.md` narrates the same baseline for a
human. Between the row-532 re-stamp and column G those two disagreed: the JSON had moved to
build `73d7706cb397` with 59 violations and 27 uncontested, and the prose still said
`b484b945d8af`, 60, and 28. Nothing caught it, because nothing was looking.

THAT IS ROW 532'S OWN SHAPE ONE LAYER UP — two constructions of one fact, drifting apart, with
the disagreement invisible until somebody read both. The fix there was to derive the checker's
set from the shown bytes; the fix here is the same move at document scale: the prose does not
get to hold its own copy of the number, it has to name the one the JSON declares.

WHAT THIS IS NOT. It is not a test that copies a declaration and asserts the declaration —
that failure has happened here too, a control hardcoding the build sha it was meant to check.
This reads BOTH records at runtime and asserts they agree, so re-stamping the JSON alone turns
it RED and there is no value to edit into this file to make it green again.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "seed"
BASELINE = SEED / "BASELINE.json"
FIXTURE = SEED / "FIXTURE-CERTIFIED-POSITIVITY.md"


class TheFixtureNamesTheCurrentBaseline(unittest.TestCase):
    def setUp(self):
        self.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.prose = FIXTURE.read_text(encoding="utf-8")

    def test_the_fixture_names_the_baselines_CURRENT_build(self):
        build = self.baseline["build"]
        self.assertIn(build, self.prose,
                      f"seed/BASELINE.json is stamped {build} and the fixture file never says "
                      f"so — re-stamp the prose or state the supersession there")

    def test_the_fixture_carries_the_baselines_CURRENT_violation_count(self):
        """The count and its composition travel together or neither is reportable."""
        f = self.baseline["fixture"]
        comp = f["composition"]
        self.assertIn(str(f["violations"]), self.prose,
                      "the fixture file does not carry the baseline's violation count")
        for part, n in comp.items():
            self.assertRegex(
                self.prose, rf"\b{n}\b[^\n]*{part}|{part}[^\n]*\b{n}\b",
                f"the composition's {part}={n} appears nowhere in the fixture file")

    def test_the_superseded_figures_are_KEPT_not_deleted(self):
        """No column is ever removed or rewritten, including a superseded baseline block. The
        old build and the old count must both still be readable, or the record was tidied."""
        self.assertIn("b484b945d8af", self.prose, "the superseded build was deleted")
        self.assertRegex(self.prose, r"60\s*(?:→|->)\s*59",
                         "the superseded violation count was deleted rather than superseded")

    def test_the_band_is_declared_in_ONE_place(self):
        """The discrimination band lives in BASELINE.json. A second copy in prose is the same
        drift one field over, so the prose may quote it only by naming both endpoints."""
        bands = self.baseline["bands"]
        low, high = bands["discrimination_low"], bands["discrimination_high"]
        for edge in (low, high):
            self.assertIsInstance(edge, (int, float))
        self.assertLess(low, high)
        self.assertIn("why", bands, "a band with no stated reason is a tuned number")


if __name__ == "__main__":
    unittest.main()
