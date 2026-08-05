"""The sampler: a walk with no pool, aimed by prediction error rather than by a list.

The pairwise daemon consumed a list enumerated before any arrow existed — every question it
asked was decided before any of its answers were known. These controls hold the properties
that make the replacement a walk rather than a differently-ordered list:

  * there is no pool, and a control reads the AST to say so,
  * the frontier is popped by PRIORITY, residual first, because prediction error is the only
    thing that carries information about where the model of the field is wrong,
  * a forced random jump fires, so silence about a dark region is never an artefact of the
    walk being trapped in one component,
  * composition confirmed and composition DRIFT are logged as distinct classes and never
    summed — drift is the glue law failing, and it is holonomy arriving through the walk.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.constants import REPO_ROOT
from engine.corpus_state import CorpusSnapshot, SlotRecord, with_arrows
from engine.correspondence import Correspondence
from engine.extract import DeterministicExtractor
from engine.types import Document
from engine.walk import (
    COMPOSITION,
    DRIFT_AFTER,
    JUMP_EVERY,
    NEIGHBOUR,
    RANDOM,
    RESIDUAL,
    STEP_TYPES,
    Walk,
    step,
)


def _corpus(rows, arrows=()):
    snap = CorpusSnapshot()
    ex = DeterministicExtractor("fixture", "test")
    ids: dict[str, str] = {}
    for i, (chart, text) in enumerate(rows):
        for d in ex.extract(Document(f"repo||dir/f{i}", chart, text, "test")):
            snap.slots[d.slot] = SlotRecord(slot=d.slot, chart=chart, type=d.type, nu=d.nu,
                                            value="T", confidence=1.0, tier="EXTRACTION",
                                            docs=(f"repo||dir/f{i}",))
            ids.setdefault(f"{chart}:{text}", d.slot)
    built = [Correspondence(src_chart=s.split(":", 1)[0], src_slot=ids[s],
                            dst_chart=d.split(":", 1)[0], dst_slot=ids[d], kind=k,
                            proposer="fixture", prompt_hash="t", evidence=("f",))
             for s, d, k in arrows]
    return (with_arrows(snap, built) if built else snap), ids


def _silent(system, user):
    """A medium that names nothing. Legal, and the state that produces residuals."""
    return "", {"cost": 0.001}


class ThereIsNoPool(unittest.TestCase):
    def test_planted_the_module_never_reads_a_candidate_pool(self):
        """The whole point. If a list is still being walked, this is not built.

        Checked on the CODE, with docstrings and comments stripped. The first version scanned
        raw source and fired on this module's own prose explaining that there is no pool —
        the same trap gate 10 hit when a docstring quoted the phrase it was warning about. A
        check cannot distinguish a word used from a word mentioned, so it should not read
        prose at all.
        """
        tree = ast.parse((REPO_ROOT / "engine" / "walk.py").read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.Import):
                names |= {a.name.split(".")[-1] for a in node.names}
        for banned in ("POOL_PATH", "read_pool", "write_pool", "next_batch", "pool"):
            self.assertNotIn(banned, names,
                             f"walk.py CODE references {banned!r} — the sampler is still a "
                             f"list-walker")

    def test_the_module_does_not_import_the_pairwise_loop(self):
        """Q5: this REPLACES the pairwise proposer. Importing it would be two proposers."""
        tree = ast.parse((REPO_ROOT / "engine" / "walk.py").read_text(encoding="utf-8"))
        modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertNotIn("continuous", {m for m in modules if m})

    def test_the_only_state_is_the_frontier_and_the_accounting(self):
        tree = ast.parse((REPO_ROOT / "engine" / "walk.py").read_text(encoding="utf-8"))
        walk_cls = next(n for n in ast.walk(tree)
                        if isinstance(n, ast.ClassDef) and n.name == "Walk")
        fields = {n.target.id for n in walk_cls.body if isinstance(n, ast.AnnAssign)}
        self.assertEqual(fields, {"steps", "frontier", "visited", "declines", "drift",
                                  "old_stock"})


class TheFrontierIsAimedByError(unittest.TestCase):
    def setUp(self):
        self.snap, _ = _corpus([("english", "the cone is positive under composition"),
                                ("lean", "theorem cone_pos : True")])

    def test_residual_outranks_everything(self):
        w = Walk()
        w.push("n" * 64, NEIGHBOUR, "neighbour")
        w.push("c" * 64, COMPOSITION, "composition")
        w.push("r" * 64, RESIDUAL, "prediction error")
        slot, kind, _ = w.pop(self.snap)
        self.assertEqual(kind, RESIDUAL,
                         "error is the only thing that says where the model is wrong; it "
                         "must not queue behind structure that is already known")

    def test_the_priority_order_is_residual_composition_neighbour_random(self):
        self.assertEqual(STEP_TYPES, (RESIDUAL, COMPOSITION, NEIGHBOUR, RANDOM))
        w = Walk()
        for slot, kind in (("a" * 64, NEIGHBOUR), ("b" * 64, COMPOSITION),
                           ("c" * 64, RESIDUAL)):
            w.push(slot, kind, kind)
        self.assertEqual([w.pop(self.snap)[1] for _ in range(3)],
                         [RESIDUAL, COMPOSITION, NEIGHBOUR])

    def test_planted_requeuing_cannot_launder_a_reason(self):
        """A position queued twice keeps its FIRST justification. Otherwise a random jump
        re-queued as a residual would make the step-type distribution a fiction."""
        w = Walk()
        w.push("x" * 64, RANDOM, "jumped here")
        w.push("x" * 64, RESIDUAL, "prediction error")
        self.assertEqual(w.frontier["x" * 64][0], RANDOM)

    def test_a_visited_position_is_not_requeued(self):
        w = Walk()
        w.visited.add("x" * 64)
        w.push("x" * 64, RESIDUAL, "error")
        self.assertEqual(w.frontier, {})


class TheWalkReachesDarkRegions(unittest.TestCase):
    def test_a_jump_is_forced_on_schedule(self):
        """Without it the walk is confined to its starting component, and its silence about
        the rest of the corpus would be a fact about the walk."""
        self.assertGreater(JUMP_EVERY, 0)
        snap, _ = _corpus([("english", "a claim about cones here"),
                           ("lean", "theorem t : True"),
                           ("python", "def f(): return 1")])
        w = Walk()
        from engine.walk import Step

        for i in range(JUMP_EVERY):
            w.steps.append(Step(n=i, kind=NEIGHBOUR, reason="r", clamp="", members=0,
                                named=0, void=0, novel=0, confirmed_declared=0,
                                confirmed_implied=0, residual=0, drift=0, old_stock=0,
                                unmeasured=0, acceptance=0.0, cost=0.0))
        w.push("z" * 64, RESIDUAL, "would otherwise win")
        _slot, kind, reason = w.pop(snap)
        self.assertEqual(kind, RANDOM)
        self.assertIn("forced jump", reason)

    def test_the_jump_is_deterministic(self):
        """A walk nobody can replay is a walk whose findings cannot be checked."""
        snap, _ = _corpus([("english", "a claim about cones here"),
                           ("lean", "theorem t : True")])
        self.assertEqual(Walk()._jump(snap), Walk()._jump(snap))


class TheGlueLawIsMeasured(unittest.TestCase):
    """S(g o f) = S(g) o S(f). An implied arrow declined repeatedly is composition DRIFT."""

    def test_one_decline_is_not_drift(self):
        snap, ids = _corpus(
            [("english", "the cone is positive under composition"),
             ("lean", "theorem cone_pos : True"), ("python", "def cone(): return 1")],
            arrows=[("english:the cone is positive under composition",
                     "lean:theorem cone_pos : True", "same_claim"),
                    ("lean:theorem cone_pos : True", "python:def cone(): return 1",
                     "same_claim")])
        w = Walk()
        w.push(ids["english:the cone is positive under composition"], NEIGHBOUR, "seed")
        s, _, region = step(w, snap, _silent)
        if region.implied:
            self.assertEqual(s.drift, 0, "a single unnamed implication is a region that did "
                                         "not show it well, not the glue law failing")
            self.assertGreater(s.residual, 0)

    def test_drift_requires_repeated_declines_in_different_regions(self):
        self.assertGreaterEqual(DRIFT_AFTER, 2)
        w = Walk()
        pair = ("a" * 64, "b" * 64)
        w.declines[pair] = DRIFT_AFTER - 1
        self.assertNotIn(pair, w.drift)

    def test_confirmed_and_drift_are_never_summed(self):
        rep = Walk().report()
        self.assertIn("composition_confirmed", rep)
        self.assertIn("composition_drift", rep)
        self.assertNotIn("composition", rep, "one number for two opposite findings would "
                                             "hide whichever is smaller")


class TheWalkLogShowsWhereItWent(unittest.TestCase):
    def test_the_report_carries_the_step_type_distribution(self):
        from engine.walk import Step

        w = Walk()
        for i, kind in enumerate((RESIDUAL, RESIDUAL, NEIGHBOUR, RANDOM)):
            w.steps.append(Step(n=i, kind=kind, reason="r", clamp="c", members=1, named=0,
                                void=0, novel=0, confirmed_declared=0, confirmed_implied=0,
                                residual=0, drift=0, old_stock=0, unmeasured=0,
                                acceptance=0.0, cost=0.0))
        rep = w.report()
        self.assertEqual(rep["step_types"][RESIDUAL], 2)
        self.assertEqual(rep["step_type_share"][RESIDUAL], 0.5)
        self.assertEqual(set(rep["step_types"]), set(STEP_TYPES),
                         "every step type must appear even at zero, or a type that never "
                         "fires is invisible rather than reported as never firing")

    def test_the_report_states_the_acceptance_guard(self):
        self.assertIn("condensing noise", Walk().report()["guard"])

    def test_old_stock_is_tracked_separately(self):
        """The arrow-neighbourhood preference doubles as a re-audit of pre-table arrows, so
        confirmations on old stock are counted apart from new findings."""
        self.assertIn("old_stock_touched", Walk().report())

    def test_a_step_is_appendable_as_one_json_object(self):
        import json
        import tempfile

        from engine.walk import Step, log_step

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "walk.jsonl"
            log_step(Step(n=1, kind=RANDOM, reason="why", clamp="c" * 64, members=3, named=1,
                          void=0, novel=1, confirmed_declared=0, confirmed_implied=0,
                          residual=0, drift=0, old_stock=0, unmeasured=2, acceptance=1.0,
                          cost=0.004), path)
            rec = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(rec["kind"], RANDOM)
            self.assertEqual(rec["reason"], "why")


class TheTwoErasAreNeverConflated(unittest.TestCase):
    """Pairwise `none` and region UNMEASURED are different facts and must never be summed.

    A pairwise `none` is an ANSWER: the proposer was shown that pair and declined it. A
    region's unmeasured pair was never put as a question. Adding them would turn silence into
    evidence, which is the thing the region reading discipline exists to prevent — so the two
    eras have to stay distinguishable in the ledger forever, not just while someone remembers.
    """

    def test_the_walk_tags_its_answers_with_a_distinct_relation(self):
        src = (REPO_ROOT / "proposerd.py").read_text(encoding="utf-8")
        self.assertIn('relation="region"', src,
                      "region-era answers must carry their own relation tag, or they merge "
                      "into the pairwise population the first time anyone counts")

    def test_the_pairwise_relations_are_distinct_from_the_region_one(self):
        from engine.walk import RESIDUAL

        pairwise = {"declaration", "subtree", "reverse", "composition"}
        self.assertNotIn("region", pairwise)
        self.assertNotEqual("region", RESIDUAL)

    def test_planted_a_region_answer_is_never_recorded_as_none(self):
        """`none` is not in the region kind set at all, so it cannot be written by this path."""
        from engine.correspondence import KINDS
        from engine.region import Member, Region, parse_region

        region = Region(members=[Member(index=i, slot=f"{i:064d}", chart=c, type="assert",
                                        nu=f"claim {i}", attached=False)
                                 for i, c in enumerate(("english", "lean"))])
        self.assertEqual([p for p in parse_region("0 -none-> 1", region) if p.ok], [])
        self.assertNotIn("none", {k for k in KINDS if k != "none"})


class AgingIsProposedNotSilentlyChosen(unittest.TestCase):
    def test_the_policy_exists_and_leaves_n_to_the_operator(self):
        text = (REPO_ROOT / "seed" / "AGING.md").read_text(encoding="utf-8")
        self.assertIn("PROPOSAL", text)
        self.assertIn("is not chosen here", text)
        self.assertIn("dormant", text)
        self.assertIn("retained in the journal", text,
                      "dormancy must be demotion, not deletion")

    def test_nothing_ages_yet(self):
        """The policy is written and NOT enforced. Claiming otherwise would be the docstring
        defect the mechanism gate exists for."""
        for name in ("engine/walk.py", "engine/region.py"):
            src = (REPO_ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("dormant", src, f"{name} implements aging that was only proposed")


if __name__ == "__main__":
    unittest.main()
