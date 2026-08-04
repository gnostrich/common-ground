"""The naturality guarantee: ONE write-path to the fast tape.

This is the most important test in the LM-in-the-loop build. Every source — me, the LM,
another instance — enters the fast tape only through `FastTape.propose`. The audit is
structural (by AST): the tape's entry list is appended to in exactly one place. A second
write-path (the planted defect) must make it RED.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine import EngineError
from engine.extract import DeterministicExtractor
from engine.inlet import FastTape, stub_translator
from engine.types import Document, Warrant, WarrantTier

INLET_SRC = Path(__file__).resolve().parents[1] / "engine" / "inlet.py"


def _tape_write_sites(source: str) -> list[str]:
    """Every `self._entries.append(...)` in the source, with its enclosing function name.

    The one-write-path property is: this list has length 1 and that one site is `propose`.
    """
    tree = ast.parse(source)
    sites: list[str] = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.func = "<module>"

        def visit_FunctionDef(self, node):
            prev, self.func = self.func, node.name
            self.generic_visit(node)
            self.func = prev

        def visit_Call(self, node):
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr == "append"
                    and isinstance(f.value, ast.Attribute) and f.value.attr == "_entries"):
                sites.append(self.func)
            self.generic_visit(node)

    V().visit(tree)
    return sites


class OneWritePath(unittest.TestCase):
    def test_the_fast_tape_is_written_in_exactly_one_place(self):
        sites = _tape_write_sites(INLET_SRC.read_text(encoding="utf-8"))
        self.assertEqual(len(sites), 1, f"there must be exactly one write-path; found {sites}")
        self.assertEqual(sites[0], "propose", "the one write-path must be propose()")

    def test_planted_second_write_path_makes_it_red(self):
        # The control: inject a second append outside propose. The audit MUST catch it.
        planted = INLET_SRC.read_text(encoding="utf-8") + (
            "\n\nclass _Sneaky:\n"
            "    def back_door(self, tape, p):\n"
            "        tape._entries.append(p)  # a second pipe — must fail the audit\n"
        )
        sites = _tape_write_sites(planted)
        self.assertGreater(len(sites), 1, "a second write-path must be detected")
        self.assertNotEqual(set(sites), {"propose"}, "the audit must go red on a second pipe")


class EverySourceIsEqualThroughTheInlet(unittest.TestCase):
    def _deltas(self, source_id, text):
        return DeterministicExtractor(source_id, "typed").extract(
            Document(source_id, "english", text, "typed"))

    def test_me_lm_and_instance_are_indistinguishable_in_tier(self):
        tape = FastTape()
        for d in self._deltas("me", "The cone is positive."):
            tape.propose(d, "me")
        for d in self._deltas("lm", "The cone is positive under composition."):
            tape.propose(d, "lm")                       # LM path uses the same propose()
        for d in self._deltas("instB", "The system is observable."):
            tape.propose(stub_translator(d, "B"), "instance:B")   # third source, same inlet

        self.assertEqual(set(tape.by_source()), {"me", "lm", "instance:B"})
        for p in tape.entries:
            self.assertEqual(p.tier, WarrantTier.EXTRACTION,
                             "every proposal is proposal-tier regardless of source")
            self.assertFalse(p.delta.warrant.clamp_eligible)

    def test_source_tag_never_confers_warrant(self):
        tape = FastTape()
        d = self._deltas("me", "The cone is positive.")[0]
        p_me = tape.propose(d, "me")
        p_lm = tape.propose(d, "lm")
        self.assertEqual(p_me.tier, p_lm.tier, "same delta, different tag => same tier")


class TheInletRefusesAClamp(unittest.TestCase):
    def test_a_clamp_eligible_warrant_cannot_enter(self):
        tape = FastTape()
        d = DeterministicExtractor("me", "typed").extract(
            Document("me", "english", "The cone is positive.", "typed"))[0]
        import dataclasses
        clampish = dataclasses.replace(
            d, warrant=Warrant(tier=WarrantTier.KERNEL, detail="kernel receipt"))
        self.assertTrue(clampish.warrant.clamp_eligible)
        with self.assertRaises(EngineError):
            tape.propose(clampish, "me")     # warrant rises at the gate, never at the inlet

    def test_a_blank_source_tag_is_refused(self):
        tape = FastTape()
        d = DeterministicExtractor("me", "typed").extract(
            Document("me", "english", "The cone is positive.", "typed"))[0]
        with self.assertRaises(EngineError):
            tape.propose(d, "  ")


if __name__ == "__main__":
    unittest.main()
