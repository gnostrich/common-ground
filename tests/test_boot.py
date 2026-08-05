"""Seeding a deploy's state, and the one way it can destroy the thing it is protecting.

A platform volume mounted at `runs/` shadows whatever the image shipped there, so state is
uploaded to `seed_runs/` and copied across on boot. The copy must be copy-IF-ABSENT. Once a
deploy has run, its journal is the live record of every pair asked and every answer paid for;
re-seeding over it on the next deploy would roll the ledger back to upload time and re-ask
thousands of pairs. That is the planted defect here, because it is the expensive one and it
would look like nothing at all — the service would come up healthy with an older number.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ui.boot import SEED_DIR_NAME, seed_state, start_proposer_if_asked


_SAVED_FORCE: str | None = None


def setUpModule():
    """These tests must not depend on the operator's environment.

    `CG_SEED_FORCE` names files seeding may overwrite. A DEPLOY sets it, and the daemon runs
    this suite as a gate there — so an ambient value turned the copy-if-absent controls into
    force-overwrite controls and halted a deployed proposer with a message about a defect
    that was not present. Same shape as the ambient OPENROUTER_API_KEY that broke test_ui:
    a control that reads the environment is testing the environment.
    """
    global _SAVED_FORCE
    _SAVED_FORCE = os.environ.pop("CG_SEED_FORCE", None)


def tearDownModule():
    if _SAVED_FORCE is not None:
        os.environ["CG_SEED_FORCE"] = _SAVED_FORCE


class _Deploy:
    """An image directory with shipped state, and a runs/ dir standing in for a volume."""

    def __init__(self, shipped: dict[str, str], live: dict[str, str] | None = None):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        seeds = self.root / SEED_DIR_NAME
        seeds.mkdir()
        for name, body in shipped.items():
            (seeds / name).write_text(body, encoding="utf-8")
        if live is not None:
            runs = self.root / "runs"
            runs.mkdir()
            for name, body in live.items():
                (runs / name).write_text(body, encoding="utf-8")

    def read(self, name: str) -> str:
        return (self.root / "runs" / name).read_text(encoding="utf-8")

    def close(self):
        self._dir.cleanup()


class AFreshVolumeIsSeeded(unittest.TestCase):
    def test_shipped_state_is_copied_when_the_volume_is_empty(self):
        d = _Deploy({"proposer.journal.jsonl": "shipped", "census.json": "{}"})
        try:
            report = seed_state(d.root)
            self.assertIn("seeded", report["proposer.journal.jsonl"])
            self.assertEqual(d.read("proposer.journal.jsonl"), "shipped")
        finally:
            d.close()

    def test_a_file_the_image_does_not_ship_is_reported_not_invented(self):
        d = _Deploy({"census.json": "{}"})
        try:
            report = seed_state(d.root)
            self.assertEqual(report["corpus.snapshot"], "not shipped")
            self.assertFalse((d.root / "runs" / "corpus.snapshot").exists())
        finally:
            d.close()

    def test_no_seed_directory_at_all_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = seed_state(Path(tmp))
            self.assertIn("absent", report["seed"])


class TheLiveJournalIsNeverOverWritten(unittest.TestCase):
    """The expensive failure, and the one that would look like nothing."""

    def test_planted_a_redeploy_must_not_roll_the_ledger_back(self):
        d = _Deploy(shipped={"proposer.journal.jsonl": "upload-time"},
                    live={"proposer.journal.jsonl": "everything asked since"})
        try:
            report = seed_state(d.root)
            self.assertEqual(d.read("proposer.journal.jsonl"), "everything asked since",
                             "seeding overwrote the live ledger — every pair asked since "
                             "the last deploy would be re-asked and re-paid for")
            self.assertIn("kept", report["proposer.journal.jsonl"])
        finally:
            d.close()

    def test_a_partially_populated_volume_gets_only_what_it_lacks(self):
        d = _Deploy(shipped={"proposer.journal.jsonl": "shipped-journal",
                             "pool.jsonl": "shipped-pool"},
                    live={"proposer.journal.jsonl": "live-journal"})
        try:
            seed_state(d.root)
            self.assertEqual(d.read("proposer.journal.jsonl"), "live-journal")
            self.assertEqual(d.read("pool.jsonl"), "shipped-pool")
        finally:
            d.close()


class OverwritingIsAnActNotAFlag(unittest.TestCase):
    """Copy-if-absent is right almost always and wrong exactly once.

    A volume that took a STUB on its first boot refuses the real file forever afterwards, by
    the very rule that protects it — which is what happened: an 801-byte journal blocked a
    2 MB one, and the deployed daemon started from zero. So overwriting must be possible, and
    must be an act: a NAMED file, logged with what it replaced.
    """

    def test_a_named_file_is_replaced_and_the_replacement_is_logged(self):
        from ui.boot import FORCE_ENV

        d = _Deploy(shipped={"proposer.journal.jsonl": "the real thing"},
                    live={"proposer.journal.jsonl": "stub"})
        try:
            with mock.patch.dict(os.environ, {FORCE_ENV: "proposer.journal.jsonl"}):
                report = seed_state(d.root)
            self.assertEqual(d.read("proposer.journal.jsonl"), "the real thing")
            self.assertIn("FORCED", report["proposer.journal.jsonl"])
            self.assertIn("replaced", report["proposer.journal.jsonl"])
        finally:
            d.close()

    def test_planted_an_unnamed_file_is_still_kept(self):
        """The flag is per-file on purpose: "overwrite whatever" would undo the protection."""
        from ui.boot import FORCE_ENV

        d = _Deploy(shipped={"proposer.journal.jsonl": "shipped", "census.json": "shipped"},
                    live={"proposer.journal.jsonl": "live", "census.json": "live"})
        try:
            with mock.patch.dict(os.environ, {FORCE_ENV: "census.json"}):
                seed_state(d.root)
            self.assertEqual(d.read("proposer.journal.jsonl"), "live",
                             "a file not named must never be overwritten")
            self.assertEqual(d.read("census.json"), "shipped")
        finally:
            d.close()

    def test_with_the_variable_unset_nothing_is_overwritten(self):
        d = _Deploy(shipped={"proposer.journal.jsonl": "shipped"},
                    live={"proposer.journal.jsonl": "live"})
        try:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CG_SEED_FORCE", None)
                seed_state(d.root)
            self.assertEqual(d.read("proposer.journal.jsonl"), "live")
        finally:
            d.close()


class TheDaemonDoesNotStartByAccident(unittest.TestCase):
    """A process that spends money must not begin because somebody deployed a web service."""

    def test_it_is_off_unless_asked(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PROPOSER_IN_PROCESS", None)
            self.assertIsNone(start_proposer_if_asked())

    def test_planted_an_unset_variable_is_not_a_truthy_string(self):
        for value in ("", "0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {"PROPOSER_IN_PROCESS": value}):
                self.assertIsNone(start_proposer_if_asked(),
                                  f"{value!r} must not start a spending process")


class TheSuiteGateIsRunOnceOnlyWhereTheTreeCannotChange(unittest.TestCase):
    def test_suite_once_skips_the_rerun_but_static_gates_still_run(self):
        """PLANTED: `suite_once` must not silently disable the STATIC gates too — those are
        cheap, and they are the ones that catch a bad seed or a display on the f-path."""
        from engine.continuous import ContinuousProposer
        from engine.journal import Journal

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pool.jsonl").write_text("", encoding="utf-8")
            journal = Journal(root / "j.jsonl")
            try:
                p = ContinuousProposer(
                    journal=journal, transport=lambda s, u: ("{}", {}),
                    pool_path=root / "pool.jsonl", control_path=root / "c.json",
                    status_path=root / "s.json", run_suite=False, suite_once=True)
                calls = {"n": 0}
                with mock.patch("engine.continuous.static_gate_report",
                                side_effect=lambda: (calls.__setitem__("n", calls["n"] + 1)
                                                     or [])):
                    self.assertTrue(p._check_gates())
                    self.assertTrue(p._check_gates())
                self.assertEqual(calls["n"], 2, "static gates must run every time")
            finally:
                journal.close()

    def test_the_default_is_every_time_because_a_dev_tree_changes(self):
        from engine.continuous import ContinuousProposer
        from engine.journal import Journal

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pool.jsonl").write_text("", encoding="utf-8")
            journal = Journal(root / "j.jsonl")
            try:
                p = ContinuousProposer(
                    journal=journal, transport=lambda s, u: ("{}", {}),
                    pool_path=root / "pool.jsonl", control_path=root / "c.json",
                    status_path=root / "s.json", run_suite=False)
                self.assertFalse(p.suite_once,
                                 "a machine where a human edits files under the process "
                                 "must re-run the suite; that is where the torn read was")
            finally:
                journal.close()


if __name__ == "__main__":
    unittest.main()
