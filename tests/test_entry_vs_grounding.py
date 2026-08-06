"""Chart ENTRY and CLAMP ELIGIBILITY are independent (GATES sentence 3).

The gate says: "Only top-tier warrants ground (clamp-eligible): Lean kernel-accept under
pinned toolchain; CI-green test receipts." It governs GROUNDING, not entry. The router used
to conflate them and shelved every non-elaborating .lean — 407 files in the GitHub corpus —
while adapters/lean_corpus.py had it right and the Aristotle corpus ran 12,041 Lean slots at
extraction tier with zero clamps. These controls pin the distinction so it cannot regress.
"""

from __future__ import annotations

import unittest

from engine import EngineError
from engine.router import LEAN, SHELF, route
from engine.types import Clamp, Warrant, WarrantTier

_LEAN = "theorem foo (a : Nat) : a + 0 = a := by simp"


class EntryDoesNotRequireGrounding(unittest.TestCase):
    def test_a_lean_file_enters_the_chart_without_elaboration(self):
        r = route("Foo.lean", _LEAN)
        self.assertEqual(r.destination, LEAN, "a .lean file enters the Lean chart")
        self.assertIsNotNone(r.document, "entry means a document reaches the extractors")
        self.assertIn("NOT clamp-eligible", r.reason)

    def test_it_is_not_shelved(self):
        self.assertNotEqual(route("Foo.lean", _LEAN).destination, SHELF,
                            "shelving unelaborated Lean conflates entry with grounding")

    def test_entry_is_independent_of_the_elaboration_predicate(self):
        """The SAME file enters the chart whether or not the kernel accepted it."""
        yes = route("Foo.lean", _LEAN, lean_elaborates=lambda t: (True, ""))
        no = route("Foo.lean", _LEAN, lean_elaborates=lambda t: (False, "no toolchain"))
        self.assertEqual(yes.destination, no.destination, LEAN)
        self.assertIsNotNone(yes.document)
        self.assertIsNotNone(no.document)
        # ...but the REASON records the clamp-eligibility difference.
        self.assertIn("clamp-eligible", yes.reason)
        self.assertIn("NOT clamp-eligible", no.reason)


class GroundingStillRequiresTopTier(unittest.TestCase):
    def test_an_extraction_warrant_cannot_clamp(self):
        with self.assertRaises(EngineError):
            Clamp("s1", "T", Warrant(tier=WarrantTier.EXTRACTION, detail="read it"))

    def test_the_adapter_refuses_clamps_without_a_pinned_toolchain(self):
        from adapters.lean_corpus import clamps_from_receipts

        with self.assertRaises(EngineError) as cm:
            clamps_from_receipts([], [], lean_toolchain=None)
        self.assertIn("D6", str(cm.exception))

    def test_entering_the_chart_grounds_nothing(self):
        # The whole point: the slot is readable and settles, but nothing it says is backed.
        r = route("Foo.lean", _LEAN)
        self.assertIsNotNone(r.document)
        with self.assertRaises(EngineError):
            Clamp("s1", "T", Warrant(tier=WarrantTier.EXTRACTION, detail="from a lean file"))


class PlantedEntryRequiresKernelIsRed(unittest.TestCase):
    """The mandated planted-defect control: a router that gates ENTRY on kernel-acceptance
    must be caught. This simulates the old (mistaken) rule and asserts the check fires."""

    @staticmethod
    def _entry_gated_on_kernel(name, text, elaborates):
        """The defect: entry conditional on elaboration."""
        ok, reason = elaborates(text)
        return route(name, text) if ok else None      # shelved when not kernel-checked

    def test_the_old_rule_would_lose_the_document(self):
        planted = self._entry_gated_on_kernel(
            "Foo.lean", _LEAN, lambda t: (False, "no toolchain"))
        self.assertIsNone(planted, "precondition: the planted rule drops the file")
        live = route("Foo.lean", _LEAN)
        self.assertIsNotNone(live.document,
                             "the live router must NOT gate entry on kernel-acceptance")
        self.assertNotEqual(planted, live, "entry-requires-kernel is a defect, and differs")


if __name__ == "__main__":
    unittest.main()
