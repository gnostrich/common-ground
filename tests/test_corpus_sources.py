"""The one seam between the mechanism and somebody's material, and its planted defects.

Until this file existed, `proposerd.py` read three `CG_*` environment variables and carried a
hard-coded list of excluded conversation ids, which meant the engine could not be handed to
anyone else without handing over the shape of one person's disk. The pointer now lives in a
gitignored file, and these controls cover the three ways that seam can fail quietly:

  * an unconfigured fork ingests nothing and prints a confident zero,
  * an export is read without its owner ever having decided what to leave out,
  * the pointer file gets committed and publishes the paths it was supposed to keep private.

Each is planted against — the control is run on a manifest that has the defect, to show it
would actually fire, and not merely on the good case where passing proves nothing.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from engine import EngineError
from engine.constants import REPO_ROOT
from engine.corpus_sources import (
    EXAMPLE_PATH,
    LOCAL_PATH,
    active,
    config_path,
    resolve,
    status,
)


class _Manifest:
    """A corpus manifest on disk, pointed at by `$CG_CORPUS` for the duration of a test."""

    def __init__(self, sources):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.path = self.root / "corpus.local.json"
        self.path.write_text(json.dumps({"sources": sources}), encoding="utf-8")
        self._prior = os.environ.get("CG_CORPUS")
        os.environ["CG_CORPUS"] = str(self.path)

    def close(self):
        if self._prior is None:
            os.environ.pop("CG_CORPUS", None)
        else:
            os.environ["CG_CORPUS"] = self._prior
        self._dir.cleanup()


class AnUnconfiguredForkSaysSo(unittest.TestCase):
    """A zero from "nothing is plugged in" and a zero from "the corpus is empty" are
    different facts, and only one of them means the run was meaningful."""

    def test_no_manifest_reports_rather_than_returning_empty(self):
        prior = os.environ.get("CG_CORPUS")
        os.environ["CG_CORPUS"] = str(Path(tempfile.gettempdir()) / "does-not-exist.json")
        try:
            self.assertEqual(resolve(), [])
            got = status()
            self.assertFalse(got["configured"])
            self.assertIn(EXAMPLE_PATH.name, got["note"])
            self.assertIn("gitignored", got["note"])
        finally:
            if prior is None:
                os.environ.pop("CG_CORPUS", None)
            else:
                os.environ["CG_CORPUS"] = prior

    def test_a_manifest_whose_sources_are_all_missing_is_reported_not_run(self):
        """PLANTED: every declared source points somewhere that isn't there."""
        m = _Manifest([{"name": "gone", "kind": "repos", "path": "/nowhere/at/all"}])
        try:
            found = resolve()
            self.assertEqual(len(found), 1, "an absent source must still be REPORTED")
            self.assertFalse(found[0].present)
            self.assertIn("/nowhere/at/all", found[0].reason)
            self.assertEqual(active(), [])
            got = status()
            self.assertTrue(got["configured"])
            self.assertEqual(got["active"], 0)
            self.assertIn("unconfigured", got["note"])
        finally:
            m.close()

    def test_a_present_source_carries_no_reason(self):
        m = _Manifest([{"name": "here", "kind": "repos", "path": tempfile.gettempdir()}])
        try:
            found = resolve()
            self.assertTrue(found[0].present)
            self.assertEqual(found[0].reason, "")
            self.assertEqual(len(active()), 1)
        finally:
            m.close()

    def test_a_disabled_source_is_listed_but_not_active(self):
        m = _Manifest([{"name": "off", "kind": "repos", "path": tempfile.gettempdir(),
                        "enabled": False}])
        try:
            self.assertEqual(len(resolve()), 1)
            self.assertEqual(active(), [], "disabled must mean not ingested")
            self.assertFalse(resolve()[0].enabled)
        finally:
            m.close()


class AnExportMustDeclareItsExclusions(unittest.TestCase):
    """A personal archive holds material its owner never meant to hand to an engine, and the
    failure mode of forgetting is that it has already been read. So the key is required, and
    leaving it empty has to be an act rather than a default."""

    def test_planted_export_without_exclude_is_refused(self):
        """PLANTED: the exact omission the old `CG_EXCLUSIONS` check guarded against."""
        m = _Manifest([{"name": "archive", "kind": "claude_export",
                        "path": "/tmp/conversations.json"}])
        try:
            with self.assertRaises(EngineError) as caught:
                resolve()
            self.assertIn("exclude", str(caught.exception))
        finally:
            m.close()

    def test_an_empty_exclusion_list_is_accepted_because_it_was_written_down(self):
        m = _Manifest([{"name": "archive", "kind": "claude_export",
                        "path": "/tmp/conversations.json", "exclude": []}])
        try:
            found = resolve()
            self.assertEqual(found[0].exclude, ())
        finally:
            m.close()

    def test_exclusions_are_carried_through_to_the_source(self):
        m = _Manifest([{"name": "archive", "kind": "claude_export",
                        "path": "/tmp/conversations.json", "exclude": ["abc123", "def456"]}])
        try:
            src = resolve()[0]
            self.assertEqual(src.exclude, ("abc123", "def456"))
            self.assertEqual(src.as_record()["excluded_ids"], 2)
        finally:
            m.close()

    def test_only_export_kinds_carry_the_requirement(self):
        """A repo tree has no per-conversation exclusions to forget, so requiring the key
        there would be ceremony rather than a guard."""
        m = _Manifest([{"name": "repos", "kind": "repos", "path": tempfile.gettempdir()}])
        try:
            self.assertEqual(resolve()[0].exclude, ())
        finally:
            m.close()


class AMalformedManifestIsAnErrorNotAnEmptyCorpus(unittest.TestCase):
    def test_planted_unknown_kind_names_the_legal_ones(self):
        """PLANTED: a typo'd kind must not be skipped as 'no loader, never mind'."""
        m = _Manifest([{"name": "typo", "kind": "repositories", "path": "/tmp"}])
        try:
            with self.assertRaises(EngineError) as caught:
                resolve()
            self.assertIn("repositories", str(caught.exception))
            self.assertIn("lean_corpus", str(caught.exception))
        finally:
            m.close()

    def test_planted_broken_json_names_the_file(self):
        d = tempfile.TemporaryDirectory()
        bad = Path(d.name) / "corpus.local.json"
        bad.write_text('{"sources": [', encoding="utf-8")
        prior = os.environ.get("CG_CORPUS")
        os.environ["CG_CORPUS"] = str(bad)
        try:
            with self.assertRaises(EngineError) as caught:
                resolve()
            self.assertIn("corpus.local.json", str(caught.exception))
        finally:
            if prior is None:
                os.environ.pop("CG_CORPUS", None)
            else:
                os.environ["CG_CORPUS"] = prior
            d.cleanup()


class ThePointerFileNeverEntersTheRepository(unittest.TestCase):
    """The whole point of the seam is that the mechanism can be forked, shared or made public
    while every corpus stays wherever its owner keeps it. That only holds if the file naming
    those paths is ignored by git — so the ignore rule itself is under test."""

    def test_the_local_pointer_is_gitignored(self):
        got = subprocess.run(["git", "check-ignore", "-v", LOCAL_PATH.name],
                             cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(got.returncode, 0,
                         f"{LOCAL_PATH.name} is NOT gitignored — forking this repository "
                         f"would publish the paths it names")

    def test_planted_the_check_can_fail(self):
        """A name git does NOT ignore, to show the assertion above is load-bearing."""
        got = subprocess.run(["git", "check-ignore", "-v", "engine/router.py"],
                             cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertNotEqual(got.returncode, 0)

    def test_the_committed_template_is_not_the_live_pointer(self):
        self.assertNotEqual(EXAMPLE_PATH, LOCAL_PATH)
        self.assertTrue(EXAMPLE_PATH.exists(), "the template a fork copies must be committed")

    def test_the_template_parses_and_declares_every_kind_the_loader_knows(self):
        from engine.corpus_sources import KINDS

        raw = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(raw["kinds"]), set(KINDS),
                         "the template must document exactly the kinds resolve() accepts")
        for row in raw["sources"]:
            self.assertIn(row["kind"], KINDS)
            if row["kind"] == "claude_export":
                self.assertIn("exclude", row, "the template must model the required key")

    def test_the_override_env_var_is_honoured(self):
        prior = os.environ.get("CG_CORPUS")
        os.environ["CG_CORPUS"] = "/some/other/place.json"
        try:
            self.assertEqual(config_path(), Path("/some/other/place.json"))
        finally:
            if prior is None:
                os.environ.pop("CG_CORPUS", None)
            else:
                os.environ["CG_CORPUS"] = prior
        self.assertEqual(config_path(), LOCAL_PATH)


class NoPathIsNamedInTheEngine(unittest.TestCase):
    """The seam is only real if it is the ONLY place a corpus location appears. This is the
    same shape as the router control that caught me writing chart names into `route()`."""

    def test_the_retired_env_vars_appear_nowhere(self):
        retired = ("CG_LEAN_CORPUS", "CG_CLAUDE_EXPORT", "CG_EXCLUSIONS", "CG_REPO_ROOT")
        offenders = []
        for path in sorted(REPO_ROOT.glob("*.py")) + sorted(REPO_ROOT.glob("engine/*.py")):
            text = path.read_text(encoding="utf-8")
            for name in retired:
                if name in text:
                    offenders.append(f"{path.name}: {name}")
        self.assertEqual(offenders, [], "the manifest replaced these; a survivor is a "
                                        "second, undocumented way to point at a corpus")

    def test_no_engine_module_names_an_absolute_corpus_path(self):
        """PLANTED against `/workspace`, the path that used to be a default argument."""
        offenders = []
        for path in sorted(REPO_ROOT.glob("engine/*.py")):
            text = path.read_text(encoding="utf-8")
            if '"/workspace' in text or "'/workspace" in text:
                offenders.append(path.name)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
