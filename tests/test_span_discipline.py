"""Gate 8: any property attributed to a slot is computed over that slot's address span.

Two defects of this shape were found in one pass — the b-value computed over the raw
segment (#2) and the confidence jitter seeded on the whole document (#3) — so the check is
shaped to the FORM (a slot-attributed property whose seed or input is wider than the
address), and the planted-defect controls restore each shape and require RED.
"""

from __future__ import annotations

import pathlib
import shutil
import tempfile
import unittest

from engine.extract import DeterministicExtractor
from engine.normalize import nu
from engine.static_checks import SLOT_ATTRIBUTED_FIELDS, check_span_discipline
from engine.types import Document

_STMT = "theorem foo (a : R) : a ^ 2 = 0 <-> a = 0"
_CLEAN = f"{_STMT} := by simp\n\n/-- A neighbouring note. -/"
# Same claim; the trailing docstring carries negation+hedge prose about ANOTHER declaration.
_DIRTY = f"{_STMT} := by\n  intro h; linarith\n\n/-- This does not touch bar; it might not be injective. -/"


def _only(doc_text: str, doc_id: str):
    ex = DeterministicExtractor("k0", "extract_v1")
    return ex.extract(Document(doc_id, "lean", doc_text, "s"))[0]


class TheLiveEngineIsInSpan(unittest.TestCase):
    def test_the_check_is_green(self):
        r = check_span_discipline()
        self.assertEqual(r.violations, [], f"gate 8 violations: {r.violations}")
        self.assertGreater(r.checked_functions, 0, "no Span-building function was examined")

    def test_out_of_span_prose_moves_nothing_attributed_to_the_slot(self):
        a, b = _only(_CLEAN, "a"), _only(_DIRTY, "b")
        self.assertEqual(nu("lean", _CLEAN), nu("lean", _DIRTY), "same address span")
        for field in sorted(SLOT_ATTRIBUTED_FIELDS) + ["slot", "nu"]:
            self.assertEqual(getattr(a, field), getattr(b, field),
                             f"{field} moved with out-of-span text")

    def test_position_in_the_file_moves_nothing(self):
        target = "theorem target (a : R) : a + 0 = a := by simp"
        first = "theorem first (b : R) : b = b := rfl"
        inserted = "theorem inserted (c : R) : c = c := rfl"
        ex = DeterministicExtractor("k0", "extract_v1")
        by_nu = lambda text, did: {d.nu: d for d in ex.extract(Document(did, "lean", text, "s"))}
        one = by_nu(f"{first}\n\n{target}", "one")
        two = by_nu(f"{first}\n\n{inserted}\n\n{target}", "two")
        key = next(k for k in one if "target" in k)
        self.assertEqual(one[key].confidence, two[key].confidence,
                         "inserting a declaration shifted a later slot's confidence")
        self.assertEqual(one[key].value, two[key].value)


class PlantedDefectsMakeItRed(unittest.TestCase):
    """The mandated controls: each defect shape restored must make the check RED."""

    def _planted(self, old: str, new: str):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.copytree("engine", tmp / "engine")
            p = tmp / "engine" / "extract.py"
            src = p.read_text(encoding="utf-8")
            self.assertIn(old, src, "the line to plant against has moved")
            p.write_text(src.replace(old, new), encoding="utf-8")
            return check_span_discipline(root=tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_wider_than_address_seed_is_red(self):
        # Defect #3's shape: the confidence draw seeded on the whole document.
        r = self._planted(
            'rng = DRNG("extract", self.extractor_id, self.prompt_id, slot_address)',
            'rng = DRNG("extract", self.extractor_id, self.prompt_id, doc.content_hash)')
        self.assertTrue(r.violations, "a document-wide seed must make gate 8 RED")
        self.assertTrue(any("confidence" in v.context for v in r.violations))

    def test_a_wider_than_address_input_is_red(self):
        # Defect #2's shape: the b-value computed over text beyond the address span.
        r = self._planted(
            "value, base = self._value_for(address_span.casefold())",
            "value, base = self._value_for(doc.text.casefold())")
        self.assertTrue(r.violations, "a document-wide value input must make gate 8 RED")
        self.assertTrue(any("value" in v.context for v in r.violations))


if __name__ == "__main__":
    unittest.main()
