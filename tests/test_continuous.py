"""Controls for the continuous proposer. Every claim it makes is planted against.

The daemon runs unattended, so "it behaves" is not a thing that can be observed by watching
it. Each property below is asserted by BREAKING it: the journal is corrupted, a promotable
delta is pushed at the inlet, a gate is reddened, the composition cap is exceeded, the source
is edited to name promotion machinery. A control that passes only when nothing is wrong is
not a control.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from engine import EngineError
from engine.compose import COMPOSITION, compose, contradictions, unasked
from engine.constants import REPO_ROOT
from engine.continuous import (
    ContinuousProposer,
    Control,
    ProposerStatus,
    read_pool,
    wait_for_slot,
    write_pool,
)
from engine.correspondence import Correspondence
from engine.holes import Hole
from engine.journal import Journal
from engine.propose_correspondence import ProposalOutcome, as_correspondence_delta
from engine.static_checks import check_proposer_discipline
from engine.types import Provenance, Warrant, WarrantTier

EN, LN, TB = "english", "lean", "tabular"


def hole(src_chart, src, dst_chart, dst, type_="assert"):
    return Hole(src_chart=src_chart, src_slot=src, src_nu=f"\x01{src_chart}\x01{src}",
                dst_chart=dst_chart, dst_slot=dst, dst_nu=f"\x01{dst_chart}\x01{dst}",
                type=type_, restatement=0)


def arrow(src_chart, src, dst_chart, dst, kind="same_claim"):
    return Correspondence(src_chart=src_chart, src_slot=src, dst_chart=dst_chart,
                          dst_slot=dst, kind=kind, proposer="lm")


class FakeTransport:
    """Answers every candidate with a scripted kind; records what it was shown."""

    def __init__(self, kind="same_claim", usage=None, fail=False):
        self.kind = kind
        self.usage = usage or {}
        self.fail = fail
        self.seen: list[str] = []

    def __call__(self, system, user):
        self.seen.append(user)
        if self.fail:
            raise RuntimeError("transport down")
        n = user.count("[") and max(int(line[1:line.index("]")]) for line in user.splitlines()
                                    if line.startswith("[")) + 1
        answers = [{"i": i, "kind": self.kind, "evidence": "e"} for i in range(n or 0)]
        return json.dumps({"answers": answers}), dict(self.usage)


class Harness:
    """A daemon wired to temp files, a fake transport, a fake clock and no sleeping."""

    def __init__(self, holes=(), relation="pool", transport=None, now=1_000_000.0,
                 journal_lines=()):
        self.dir = Path(tempfile.mkdtemp())
        self.pool = self.dir / "pool.jsonl"
        if holes:
            write_pool(self.pool, holes, relation)
        self.journal_path = self.dir / "journal.jsonl"
        if journal_lines:
            self.journal_path.write_text(
                "\n".join(json.dumps(r) for r in journal_lines) + "\n", encoding="utf-8")
        self.control = self.dir / "control.json"
        self.status = self.dir / "status.json"
        self.clock = now
        self.slept: list[float] = []
        self.journal = Journal(self.journal_path)
        self.transport = transport or FakeTransport()
        self.proposer = ContinuousProposer(
            self.journal, self.transport, pool_path=self.pool, control_path=self.control,
            status_path=self.status, sleeper=self.slept.append, clock=lambda: self.clock,
            run_suite=False)

    def set_control(self, **kw):
        Control(**kw).write(self.control)

    def close(self):
        self.journal.close()
        shutil.rmtree(self.dir, ignore_errors=True)


class JournalIsTheOnlyMemory(unittest.TestCase):
    def test_answers_survive_a_restart(self):
        d = Path(tempfile.mkdtemp())
        try:
            j = Journal(d / "j.jsonl")
            j.record_ask(src_chart=EN, src_slot="a", dst_chart=LN, dst_slot="b", type="assert",
                         answer="same_claim", evidence="e", relation="pool", proposer="lm",
                         prompt_hash="p", tier="EXTRACTION")
            j.record_ask(src_chart=EN, src_slot="c", dst_chart=LN, dst_slot="d", type="assert",
                         answer="none", evidence="", relation="pool", proposer="lm",
                         prompt_hash="p", tier="EXTRACTION")
            j.close()

            again = Journal(d / "j.jsonl")
            self.assertTrue(again.asked("a", "b"))
            self.assertEqual(again.answer_for("c", "d"), "none")
            self.assertEqual(len(again.arrows), 1, "a `none` is not an arrow")
            self.assertEqual(again.totals()["arrows"], 1)
            again.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_torn_line_is_skipped_not_guessed(self):
        """PLANTED: a half-written final line, as a kill mid-write would leave."""
        d = Path(tempfile.mkdtemp())
        try:
            path = d / "j.jsonl"
            j = Journal(path)
            j.record_ask(src_chart=EN, src_slot="a", dst_chart=LN, dst_slot="b", type="assert",
                         answer="same_claim", evidence="e", relation="pool", proposer="lm",
                         prompt_hash="p", tier="EXTRACTION")
            j.close()
            with path.open("a", encoding="utf-8") as fh:
                fh.write('{"kind": "ask", "src_slot": "x", "dst_slo')

            again = Journal(path)
            self.assertTrue(again.asked("a", "b"))
            self.assertFalse(again.asked("x", "y"), "a torn line must contribute nothing")
            self.assertEqual(again.counts["corrupt_lines"], 1, "and must be COUNTED")
            again.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_asking_is_directed(self):
        """The reverse arrow is a separate claim, so it is a separate question."""
        d = Path(tempfile.mkdtemp())
        try:
            j = Journal(d / "j.jsonl")
            j.record_ask(src_chart=EN, src_slot="a", dst_chart=LN, dst_slot="b", type="assert",
                         answer="same_claim", evidence="", relation="pool", proposer="lm",
                         prompt_hash="p", tier="EXTRACTION")
            self.assertTrue(j.asked("a", "b"))
            self.assertFalse(j.asked("b", "a"), "assuming symmetry is the defect")
            j.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)


class NeverReAsks(unittest.TestCase):
    def test_an_answered_pair_never_returns(self):
        h = Harness(holes=[hole(LN, "l1", EN, "e1"), hole(LN, "l2", EN, "e2")])
        try:
            first = h.proposer.next_batch(10)
            self.assertEqual(len(first), 2)
            h.proposer.run_batch(first)

            h.proposer.rewind_pool()
            second = h.proposer.next_batch(10)
            repeats = [x for x, _ in second if h.journal.asked(x.src_slot, x.dst_slot)]
            self.assertEqual(repeats, [], "an answered pair must never be asked again")
        finally:
            h.close()

    def test_a_restarted_daemon_does_not_re_ask(self):
        """PLANTED: the process dies after one batch and comes back cold."""
        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        try:
            h.proposer.run_batch(h.proposer.next_batch(10))
            h.journal.close()

            journal = Journal(h.journal_path)
            revived = ContinuousProposer(journal, FakeTransport(), pool_path=h.pool,
                                         control_path=h.control, status_path=h.status,
                                         sleeper=lambda s: None, run_suite=False)
            offered = [(x.src_slot, x.dst_slot, rel) for x, rel in revived.next_batch(10)]
            self.assertNotIn(("l1", "e1", "pool"), offered,
                             "a cold restart re-asked a pair the journal already answers")
            self.assertEqual(offered, [("e1", "l1", "reverse")],
                             "the REVERSE is a separate claim and is still open; nothing else")
            self.assertEqual(len(revived.arrows()), 1,
                             "and the arrow must be replayed through the inlet")
            journal.close()
        finally:
            h.close()

    def test_replay_goes_through_the_one_inlet(self):
        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        try:
            h.proposer.run_batch(h.proposer.next_batch(10))
            h.journal.close()
            journal = Journal(h.journal_path)
            revived = ContinuousProposer(journal, FakeTransport(), pool_path=h.pool,
                                         control_path=h.control, status_path=h.status,
                                         sleeper=lambda s: None, run_suite=False)
            self.assertEqual(len(revived.tape.entries), 1)
            self.assertEqual(revived.tape.entries[0].tier, WarrantTier.EXTRACTION)
            journal.close()
        finally:
            h.close()


class CompositionIsPrioritized(unittest.TestCase):
    def test_implied_pairs_come_first(self):
        h = Harness(holes=[hole(LN, "l9", EN, "e9")])
        try:
            for a in (arrow(EN, "A", LN, "B"), arrow(LN, "B", TB, "C")):
                h.proposer._enter(as_correspondence_delta(
                    ProposalOutcome(hole(a.src_chart, a.src_slot, a.dst_chart, a.dst_slot),
                                    a.kind, ""), "lm", "p"))
            batch = h.proposer.next_batch(5)
            self.assertTrue(batch, "composition produced no candidate")
            first, relation = batch[0]
            self.assertEqual(relation, "composition")
            self.assertEqual({first.src_slot, first.dst_slot}, {"A", "C"})
        finally:
            h.close()

    def test_the_composition_table_is_partial_on_purpose(self):
        self.assertNotIn(("refines", "instance_of"), COMPOSITION)
        self.assertNotIn(("instance_of", "instance_of"), COMPOSITION)
        self.assertNotIn(("instance_of", "refines"), COMPOSITION)
        result = compose([arrow(EN, "A", LN, "B", "instance_of"),
                          arrow(LN, "B", TB, "C", "instance_of")])
        self.assertEqual(result.implied, [],
                         "an undefined composite must imply nothing, not the nearest kind")

    def test_intra_chart_implication_is_residue_not_an_arrow(self):
        """Gate 1 owns intra-chart identity, so composition cannot manufacture one."""
        result = compose([arrow(EN, "A", LN, "B"), arrow(LN, "B", EN, "C")])
        self.assertEqual(result.implied, [])
        self.assertEqual(len(result.residues), 1)
        self.assertEqual(result.residues[0].src_chart, result.residues[0].dst_chart)

    def test_reverse_direction_is_offered_after_composition(self):
        h = Harness()
        try:
            h.proposer._enter(as_correspondence_delta(
                ProposalOutcome(hole(EN, "A", LN, "B"), "same_claim", ""), "lm", "p"))
            batch = h.proposer.next_batch(5)
            self.assertEqual([(x.src_slot, x.dst_slot, rel) for x, rel in batch],
                             [("B", "A", "reverse")])
        finally:
            h.close()


class CompositionIsBounded(unittest.TestCase):
    """The hub cap is enforced, and what it drops is COUNTED (gate 10 site)."""

    def test_the_cap_holds_and_the_remainder_is_counted(self):
        arrows = ([arrow(EN, f"in{i}", LN, "HUB") for i in range(6)] +
                  [arrow(LN, "HUB", TB, f"out{j}") for j in range(6)])
        uncapped = compose(arrows, hub_cap=1000)
        self.assertEqual(len(uncapped.implied), 36)
        self.assertEqual(uncapped.dropped, 0)

        capped = compose(arrows, hub_cap=10)
        self.assertEqual(len(capped.implied), 10, "the cap was not enforced")
        self.assertEqual(capped.dropped, 26, "the remainder was truncated silently")
        self.assertEqual(capped.hubs_capped, 1)
        self.assertEqual(len(capped.implied) + capped.dropped, 36,
                         "counted + kept must account for every composite")


class ContradictionIsFlagged(unittest.TestCase):
    def test_an_implied_pair_already_answered_none_is_recorded(self):
        h = Harness()
        try:
            h.journal.record_ask(src_chart=EN, src_slot="A", dst_chart=TB, dst_slot="C",
                                 type="assert", answer="none", evidence="", relation="pool",
                                 proposer="lm", prompt_hash="p", tier="EXTRACTION")
            for a in (arrow(EN, "A", LN, "B"), arrow(LN, "B", TB, "C")):
                h.proposer._enter(as_correspondence_delta(
                    ProposalOutcome(hole(a.src_chart, a.src_slot, a.dst_chart, a.dst_slot),
                                    a.kind, ""), "lm", "p"))
            h.proposer.next_batch(5)

            self.assertEqual(len(h.journal.contradictions), 1)
            record = h.journal.contradictions[0]
            self.assertEqual(record["implied"], "same_claim")
            self.assertEqual(record["recorded"], "none")
            self.assertEqual(record["via"], ["A", "B", "C"])
        finally:
            h.close()

    def test_it_is_flagged_not_resolved(self):
        """Neither side is silently overwritten: the `none` stands, no arrow is minted."""
        h = Harness()
        try:
            h.journal.record_ask(src_chart=EN, src_slot="A", dst_chart=TB, dst_slot="C",
                                 type="assert", answer="none", evidence="", relation="pool",
                                 proposer="lm", prompt_hash="p", tier="EXTRACTION")
            for a in (arrow(EN, "A", LN, "B"), arrow(LN, "B", TB, "C")):
                h.proposer._enter(as_correspondence_delta(
                    ProposalOutcome(hole(a.src_chart, a.src_slot, a.dst_chart, a.dst_slot),
                                    a.kind, ""), "lm", "p"))
            before = len(h.proposer.arrows())
            h.proposer.next_batch(5)
            self.assertEqual(h.journal.answer_for("A", "C"), "none", "the `none` was rewritten")
            self.assertEqual(len(h.proposer.arrows()), before, "an arrow was minted for it")
        finally:
            h.close()

    def test_an_agreeing_answer_is_not_a_contradiction(self):
        h = Harness()
        try:
            h.journal.record_ask(src_chart=EN, src_slot="A", dst_chart=TB, dst_slot="C",
                                 type="assert", answer="same_claim", evidence="",
                                 relation="pool", proposer="lm", prompt_hash="p",
                                 tier="EXTRACTION")
            result = compose([arrow(EN, "A", LN, "B"), arrow(LN, "B", TB, "C")])
            self.assertEqual(contradictions(result.implied, h.journal), [])
            self.assertEqual(unasked(result.implied, h.journal), [],
                             "an answered pair is not unasked")
        finally:
            h.close()


class NothingIsPromotable(unittest.TestCase):
    def test_a_promotable_delta_is_refused_at_the_daemon(self):
        """PLANTED: an AUTHORSHIP-tier claim pushed at the daemon's inlet path."""
        h = Harness()
        try:
            base = as_correspondence_delta(
                ProposalOutcome(hole(EN, "A", LN, "B"), "same_claim", ""), "lm", "p")
            import dataclasses
            promoted = dataclasses.replace(
                base, warrant=Warrant(tier=WarrantTier.AUTHORSHIP, detail="planted"))
            with self.assertRaises(EngineError):
                h.proposer._enter(promoted)
            self.assertEqual(len(h.proposer.tape.entries), 0)
        finally:
            h.close()

    def test_everything_a_run_enters_is_extraction(self):
        h = Harness(holes=[hole(LN, f"l{i}", EN, f"e{i}") for i in range(5)])
        try:
            h.proposer.run_batch(h.proposer.next_batch(10))
            tiers = {p.tier for p in h.proposer.tape.entries}
            self.assertEqual(tiers, {WarrantTier.EXTRACTION})
        finally:
            h.close()


class ProposerDisciplineIsStatic(unittest.TestCase):
    """The daemon cannot promote — asserted on the source, then planted against."""

    def test_the_real_source_is_clean(self):
        result = check_proposer_discipline()
        self.assertTrue(result.ok, [str(v) for v in result.violations])

    def _planted(self, edit):
        root = Path(tempfile.mkdtemp())
        (root / "engine").mkdir()
        for name in ("continuous.py", "journal.py", "compose.py"):
            src = (REPO_ROOT / "engine" / name).read_text(encoding="utf-8")
            (root / "engine" / name).write_text(edit(name, src), encoding="utf-8")
        try:
            return check_proposer_discipline(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_naming_promotion_machinery_makes_it_red(self):
        def edit(name, src):
            if name != "continuous.py":
                return src
            return src.replace("        self.tape.propose(delta, self.proposer)",
                               "        tier = WarrantTier.AUTHORSHIP\n"
                               "        self.tape.propose(delta, self.proposer)")

        result = self._planted(edit)
        self.assertFalse(result.ok, "a planted AUTHORSHIP reference was not caught")
        self.assertTrue(any("AUTHORSHIP" in str(v) for v in result.violations))

    def test_a_second_inlet_call_site_makes_it_red(self):
        """PLANTED: a write path that bypasses the tier assertion."""
        def edit(name, src):
            if name != "continuous.py":
                return src
            return src.replace(
                "    def arrows(self)",
                "    def sneak(self, delta):\n"
                "        self.tape.propose(delta, self.proposer)\n\n"
                "    def arrows(self)")

        result = self._planted(edit)
        self.assertFalse(result.ok, "a second .propose() call site was not caught")
        self.assertTrue(any("inlet call sites" in str(v) for v in result.violations))


class RateLimitSurvivesRestart(unittest.TestCase):
    """The window is read off the durable log, so a restart cannot reset the budget."""

    def test_a_fresh_process_still_sees_the_spent_budget(self):
        d = Path(tempfile.mkdtemp())
        try:
            j = Journal(d / "j.jsonl")
            for _ in range(5):
                j.record_call(candidates=1, ok=True)
            j.close()

            revived = Journal(d / "j.jsonl")
            now = max(revived.calls)
            self.assertEqual(revived.calls_since(now - 3600.0), 5)
            self.assertGreater(wait_for_slot(revived, 5, now), 0.0,
                               "a restart reset the rate budget")
            self.assertEqual(wait_for_slot(revived, 50, now), 0.0)
            revived.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_calls_outside_the_window_do_not_count(self):
        d = Path(tempfile.mkdtemp())
        try:
            j = Journal(d / "j.jsonl")
            j.record_call(candidates=1, ok=True)
            now = j.calls[0] + 7200.0
            self.assertEqual(j.calls_since(now - 3600.0), 0)
            self.assertEqual(wait_for_slot(j, 1, now), 0.0)
            j.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)


class OperatorControl(unittest.TestCase):
    def test_stop_halts_and_is_recorded(self):
        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        try:
            h.set_control(stop=True)
            status = h.proposer.run(max_batches=5)
            self.assertEqual(status.batches, 0)
            self.assertIn("HALTED", status.reason)
            self.assertEqual(h.journal.totals()["halts"], 1)
        finally:
            h.close()

    def test_pause_stops_asking_without_stopping_the_process(self):
        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        try:
            h.set_control(paused=True)
            h.proposer.run(max_batches=2, max_iterations=2)
            self.assertEqual(h.journal.totals()["calls"], 0, "a paused daemon made a call")
            self.assertTrue(h.slept, "a paused daemon must wait, not spin")
            self.assertTrue(json.loads(h.status.read_text())["paused"])
        finally:
            h.close()

    def test_a_malformed_control_file_pauses_rather_than_defaults(self):
        """PLANTED: a typo in the control file must not silently un-pause the daemon."""
        d = Path(tempfile.mkdtemp())
        try:
            path = d / "control.json"
            path.write_text("{not json", encoding="utf-8")
            control = Control.read(path)
            self.assertTrue(control.paused)
            self.assertIn("unreadable", control.error)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_missing_control_file_is_conservative(self):
        control = Control.read(Path(tempfile.mkdtemp()) / "absent.json")
        self.assertFalse(control.paused)
        self.assertLessEqual(control.calls_per_hour, 60)

    def test_cost_cap_halts(self):
        h = Harness(holes=[hole(LN, "l1", EN, "e1")],
                    transport=FakeTransport(usage={"cost": 1.5}))
        try:
            h.set_control(max_cost=1.0)
            h.proposer.run_batch(h.proposer.next_batch(5))
            self.assertGreaterEqual(h.journal.spend, 1.0)
            status = h.proposer.run(max_batches=3)
            self.assertIn("cost cap", status.reason)
        finally:
            h.close()

    def test_rate_limit_defers_instead_of_calling(self):
        h = Harness(holes=[hole(LN, f"l{i}", EN, f"e{i}") for i in range(4)])
        try:
            h.journal.record_call(candidates=1, ok=True)
            h.set_control(calls_per_hour=1)
            h.proposer.run(max_batches=1, max_iterations=2)
            self.assertEqual(h.journal.totals()["calls"], 1, "the rate limit was ignored")
            self.assertIn("rate limited", h.proposer.status.reason)
        finally:
            h.close()


class RedGatesHalt(unittest.TestCase):
    def test_a_red_static_gate_stops_the_loop(self):
        """PLANTED: one gate reports red; the daemon must halt, not log and continue."""
        import engine.continuous as continuous

        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        original = continuous.static_gate_report
        continuous.static_gate_report = lambda: [
            {"check": "planted", "ok": False, "violations": ["planted defect"]}]
        try:
            status = h.proposer.run(max_batches=3)
            self.assertEqual(status.batches, 0)
            self.assertIn("static gate red", status.reason)
            self.assertEqual(h.journal.totals()["calls"], 0)
        finally:
            continuous.static_gate_report = original
            h.close()

    def test_gates_are_green_right_now(self):
        from engine.continuous import static_gate_report

        red = [r for r in static_gate_report() if not r["ok"]]
        self.assertEqual(red, [], "the standing gates are not green")


class TransportFailureIsRecordedNotSwallowed(unittest.TestCase):
    def test_a_failed_call_is_journalled_and_asks_nothing(self):
        h = Harness(holes=[hole(LN, "l1", EN, "e1")], transport=FakeTransport(fail=True))
        try:
            counts = h.proposer.run_batch(h.proposer.next_batch(5))
            self.assertEqual(counts["errors"], 1)
            self.assertEqual(h.journal.totals()["call_errors"], 1)
            self.assertFalse(h.journal.asked("l1", "e1"),
                             "a failed call must leave the pair unasked, to be retried")
        finally:
            h.close()


class CostIsReportedNotEstimated(unittest.TestCase):
    def test_unreported_cost_stays_unreported(self):
        h = Harness(holes=[hole(LN, "l1", EN, "e1")], transport=FakeTransport(usage={}))
        try:
            h.proposer.run_batch(h.proposer.next_batch(5))
            totals = h.journal.totals()
            self.assertEqual(totals["cost"], 0.0)
            self.assertIn("0/1 calls reported a cost", totals["cost_coverage"])
        finally:
            h.close()

    def test_reported_cost_accumulates(self):
        h = Harness(holes=[hole(LN, f"l{i}", EN, f"e{i}") for i in range(2)],
                    transport=FakeTransport(usage={"cost": 0.25, "prompt_tokens": 10}))
        try:
            h.proposer.run_batch(h.proposer.next_batch(1))
            h.proposer.run_batch(h.proposer.next_batch(1))
            self.assertAlmostEqual(h.journal.totals()["cost"], 0.5)
            self.assertIn("2/2", h.journal.totals()["cost_coverage"])
        finally:
            h.close()


class TruncatedRepliesAreSalvagedNotGuessed(unittest.TestCase):
    """A reply cut off mid-array keeps the answers that arrived and drops the partial one."""

    def test_complete_objects_survive_and_the_tail_is_dropped(self):
        from engine.propose_correspondence import parse_answers

        holes = [hole(LN, f"l{i}", EN, f"e{i}") for i in range(4)]
        raw = ('{"answers": [\n'
               '  {"i": 0, "kind": "same_claim", "evidence": "both state positivity"},\n'
               '  {"i": 1, "kind": "none", "evidence": "different claims"},\n'
               '  {"i": 2, "kind": "refines", "evi')          # cut mid-object
        got = parse_answers(raw, holes)
        self.assertEqual([(o.hole.src_slot, o.kind) for o in got],
                         [("l0", "same_claim"), ("l1", "none")])

    def test_nothing_is_completed_for_the_truncated_answer(self):
        """PLANTED: the cut lands right after a `kind` — it must STILL be dropped."""
        from engine.propose_correspondence import parse_answers

        holes = [hole(LN, f"l{i}", EN, f"e{i}") for i in range(3)]
        raw = ('{"answers": [{"i": 0, "kind": "none", "evidence": "x"}, '
               '{"i": 1, "kind": "same_claim"')
        got = parse_answers(raw, holes)
        self.assertEqual(len(got), 1, "an unterminated object was completed")
        self.assertEqual(got[0].kind, "none")

    def test_evidence_quoting_our_own_nu_tag_still_parses(self):
        """OBSERVED: the proposer quotes the corpus back, tag and all.

        A nu-string carries `\\x01lean\\x01` as a literal control character. Strict JSON
        forbids an unescaped control character inside a string, so a faithful quotation of
        our own normalized surface was being thrown away as unparsable — 4 of 5 real calls.
        """
        from engine.propose_correspondence import parse_answers

        holes = [hole(LN, "l0", EN, "e0")]
        raw = ('{"answers": [{"i": 0, "kind": "none", "evidence": '
               '"SOURCE (lean): \x01lean\x01def SigmaSing : Set = {S | S.det = 0}"}]}')
        got = parse_answers(raw, holes)
        self.assertEqual(len(got), 1, "a quoted nu tag made the whole batch unparsable")
        self.assertIn("SigmaSing", got[0].evidence)

    def test_a_bare_array_without_the_wrapper_is_accepted(self):
        """Observed on the real corpus: the proposer answers with the array and no wrapper."""
        from engine.propose_correspondence import parse_answers

        holes = [hole(LN, f"l{i}", EN, f"e{i}") for i in range(2)]
        raw = '```json\n[{"i": 0, "kind": "none", "evidence": "x"}, ' \
              '{"i": 1, "kind": "same_claim", "evidence": "y"}]\n```'
        got = parse_answers(raw, holes)
        self.assertEqual([o.kind for o in got], ["none", "same_claim"])

    def test_a_reply_with_no_objects_at_all_yields_nothing(self):
        from engine.propose_correspondence import parse_answers

        self.assertEqual(parse_answers("I would rather not answer.", [hole(LN, "a", EN, "b")]), [])


class PoolIsStreamed(unittest.TestCase):
    def test_round_trip(self):
        d = Path(tempfile.mkdtemp())
        try:
            path = d / "pool.jsonl"
            write_pool(path, [hole(LN, "l1", EN, "e1"), hole(LN, "l2", TB, "t2")], "declaration")
            got = list(read_pool(path))
            self.assertEqual([r for _, r in got], ["declaration", "declaration"])
            self.assertEqual([h.dst_slot for h, _ in got], ["e1", "t2"])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_corrupt_pool_line_is_skipped(self):
        d = Path(tempfile.mkdtemp())
        try:
            path = d / "pool.jsonl"
            write_pool(path, [hole(LN, "l1", EN, "e1")], "declaration")
            with path.open("a", encoding="utf-8") as fh:
                fh.write("{broken\n")
            self.assertEqual(len(list(read_pool(path))), 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


class AMalformedAnswerCannotKillTheDaemon(unittest.TestCase):
    """OBSERVED: a proposer returned `{"answers": [0, 1, 2]}` and the daemon died mid-run.

    It had been up ninety minutes. The journal's last line was a successful call and the
    status file still said `running`, so nothing in the system recorded what ended it.
    """

    def test_a_bare_integer_where_an_answer_belongs_is_dropped(self):
        from engine.propose_correspondence import parse_answers

        holes = [hole(LN, "l0", EN, "e0")]
        for payload in ('{"answers": [0, 1, 2]}',
                        '[0, "x", null]',
                        '{"answers": [{"i": 0, "kind": "none"}, 7]}'):
            got = parse_answers(payload, holes)
            self.assertTrue(all(o.kind in ("none", "same_claim", "refines", "instance_of")
                                for o in got), payload)

    def test_the_valid_answers_beside_a_malformed_one_still_land(self):
        from engine.propose_correspondence import parse_answers

        holes = [hole(LN, f"l{i}", EN, f"e{i}") for i in range(3)]
        got = parse_answers(
            '{"answers": [{"i": 0, "kind": "same_claim", "evidence": "a"}, 5, '
            '{"i": 2, "kind": "none", "evidence": "b"}]}', holes)
        self.assertEqual([(o.hole.src_slot, o.kind) for o in got],
                         [("l0", "same_claim"), ("l2", "none")])

    def test_an_unexpected_crash_becomes_a_halt_record(self):
        """PLANTED: run_batch raises. The loop must record it, not vanish."""
        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        try:
            def boom(chunk):
                raise RuntimeError("planted")

            h.proposer.run_batch = boom
            status = h.proposer.run(max_batches=3, max_iterations=3)
            self.assertIn("HALTED", status.reason)
            self.assertEqual(h.journal.totals()["halts"], 1)
            halt = [r for r in h.journal.tail(10) if r["kind"] == "halt"][-1]
            self.assertIn("planted", halt["detail"])
        finally:
            h.close()


class TheLedgerIsCommittableAndCarriesNoCorpus(unittest.TestCase):
    """The journal quotes the corpus; the ledger is the half that may enter the repository.

    Leaving the whole journal out of git cost 737 answered pairs to a container reclaim. The
    fix is a split, not a relaxation: `evidence` is the only field carrying corpus text, and
    resume needs the directed pair and the verdict, which are slot hashes.
    """

    QUOTE = "theorem cone_pos : 0 < cone.det := by simpa using h.le"

    def _journal_with_a_quote(self, d):
        j = Journal(d / "j.jsonl")
        j.record_ask(src_chart=LN, src_slot="l1", dst_chart=EN, dst_slot="e1", type="assert",
                     answer="same_claim", evidence=self.QUOTE, relation="declaration",
                     proposer="lm", prompt_hash="p", tier="EXTRACTION")
        j.record_ask(src_chart=LN, src_slot="l2", dst_chart=EN, dst_slot="e2", type="assert",
                     answer="none", evidence="", relation="pool", proposer="lm",
                     prompt_hash="p", tier="EXTRACTION")
        j.record_call(candidates=2, ok=True, cost=0.001, error="")
        return j

    def test_no_quoted_span_survives_into_the_ledger(self):
        d = Path(tempfile.mkdtemp())
        try:
            j = self._journal_with_a_quote(d)
            counts = j.export_redacted(d / "ledger.jsonl")
            body = (d / "ledger.jsonl").read_text(encoding="utf-8")
            self.assertNotIn(self.QUOTE, body, "the corpus quote reached the committable file")
            self.assertNotIn("cone_pos", body, "a fragment of the quote reached it")
            self.assertIn("sha256:", body, "the quote must be replaced by its hash, not dropped")
            self.assertEqual(counts["records"], 3)
            j.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_ledger_is_enough_to_resume(self):
        """The whole point: a reclaim must cost time, not answers."""
        d = Path(tempfile.mkdtemp())
        try:
            j = self._journal_with_a_quote(d)
            j.export_redacted(d / "ledger.jsonl")
            j.close()

            revived = Journal(d / "ledger.jsonl")       # as if the journal itself were lost
            self.assertTrue(revived.asked("l1", "e1"))
            self.assertEqual(revived.answer_for("l2", "e2"), "none")
            self.assertEqual(len(revived.arrows), 1)
            self.assertEqual(revived.arrows[0].answer, "same_claim")
            self.assertEqual(revived.totals()["calls"], 1)
            self.assertAlmostEqual(revived.spend, 0.001)
            revived.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_hash_is_verifiable_by_someone_holding_the_corpus(self):
        """Redacted is not the same as discarded: the quote is still attested."""
        from engine.hashing import sha256_text

        d = Path(tempfile.mkdtemp())
        try:
            j = self._journal_with_a_quote(d)
            j.export_redacted(d / "ledger.jsonl")
            j.close()
            rows = [json.loads(l) for l in (d / "ledger.jsonl").read_text().splitlines() if l]
            arrow = next(r for r in rows if r.get("answer") == "same_claim")
            self.assertEqual(arrow["evidence"], f"sha256:{sha256_text(self.QUOTE)[:16]}")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_free_text_field_added_later_is_redacted_too(self):
        """PLANTED: `note`, `error` and `detail` also carry free text and must be covered."""
        d = Path(tempfile.mkdtemp())
        try:
            j = Journal(d / "j.jsonl")
            j.record_call(candidates=1, ok=False, error=f"no parsable answers; raw: {self.QUOTE}")
            j.record_halt("crashed", f"traceback quoting {self.QUOTE}")
            j.export_redacted(d / "ledger.jsonl")
            body = (d / "ledger.jsonl").read_text(encoding="utf-8")
            self.assertNotIn(self.QUOTE, body,
                             "a quote reached the ledger through a field other than evidence")
            j.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)


class ATornReadIsNotARegression(unittest.TestCase):
    """The daemon reads a working tree a human may be editing.

    It halted once on `OSError: lineno is out of bounds` — a module imported from a longer
    version of a file that had just been shortened. The gate was right to stop; the cause was
    an edit underneath it. Re-running once distinguishes the two without masking either.
    """

    def test_a_transient_red_does_not_halt(self):
        import engine.continuous as continuous

        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        calls = {"n": 0}

        def flaky(root=None, timeout=900):
            calls["n"] += 1
            return (calls["n"] > 1, "torn read" if calls["n"] == 1 else "")

        original, h.proposer.run_suite = continuous.suite_green, True
        continuous.suite_green = flaky
        try:
            self.assertTrue(h.proposer._check_gates(), "a transient red halted the daemon")
            self.assertEqual(calls["n"], 2, "it must re-run exactly once")
            self.assertEqual(h.journal.totals()["halts"], 0)
        finally:
            continuous.suite_green = original
            h.close()

    def test_a_real_red_still_halts(self):
        """PLANTED: red twice. The retry must not become a way past the gate."""
        import engine.continuous as continuous

        h = Harness(holes=[hole(LN, "l1", EN, "e1")])
        original, h.proposer.run_suite = continuous.suite_green, True
        continuous.suite_green = lambda root=None, timeout=900: (False, "genuinely broken")
        try:
            self.assertFalse(h.proposer._check_gates(), "a real red gate did not halt")
            self.assertEqual(h.journal.totals()["halts"], 1)
            halt = [r for r in h.journal.tail(10) if r["kind"] == "halt"][-1]
            self.assertIn("confirmed on re-run", halt["reason"])
        finally:
            continuous.suite_green = original
            h.close()
