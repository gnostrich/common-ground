"""THE AUDITOR'S OWN TESTS (CONSTITUTION.md B2, applied reflexively to the auditor itself).

Every control tools/auditor.py performs must (a) run cleanly against the real repo it is part
of, and (b) be PROVABLY ABLE TO FAIL — a control that cannot fail is not a control. Where a
twin needs a "bad" fixture, it is built in a scratch tempdir or by dependency-injecting a
monkeypatched collaborator (`tools.build_registry.MAP`, `engine.grammar.BLOCKS`, a throwaway
git repository) — never by writing to engine/, ui/ or seed/, which the auditor itself may not
touch and which this file, being part of the same lane, does not touch either.

Nothing here calls the SERVED url. `wire()` and `battery()` are network-dependent by charter
(CONSTITUTION.md B3 items 3 and 6) and are exercised by actually running `tools/auditor.py`
against the live deploy, not by this suite — a fixture that faked the network would be exactly
the fluent-fake the operator warned against. What IS tested here is the machinery around them:
that `battery()` reuses `tools.acceptance.run` rather than opening a second client, that an
unset CG_URL is reported rather than crashing, and that a client exception is retried once and
then filed as a finding with whatever evidence exists.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import auditor  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class DiscoveryFindsThePlantedTwinsByNameAndOnlyByWholeWord(unittest.TestCase):
    """The word-tokenizer that decides "is this a planted-defect fixture", tested in
    isolation from any file on disk. This class IS the planted-defect twin for the matcher:
    it proves the matcher can say yes and, separately, that it can say no."""

    def test_camelcase_class_names_carrying_planted_or_red_match(self):
        for name in ("PlantedNormalizationIsRED", "ThePlantedArmCarriesTheWeight",
                     "RedGatesHalt", "PlantedDefects", "PlantedTrueCorrespondence"):
            self.assertTrue(auditor._is_planted_name(name), name)

    def test_snake_case_method_names_carrying_the_three_named_idioms_match(self):
        for name in ("test_planted_gap_is_found_miss_rate_zero",
                     "test_a_red_static_gate_stops_the_loop",
                     "test_the_shape_arm_can_actually_FIRE",
                     "test_the_PLANTED_none_equals_none_comparison_no_longer_succeeds"):
            self.assertTrue(auditor._is_planted_name(name), name)

    def test_PLANTED_ordinary_words_that_merely_contain_the_letters_do_not_match(self):
        # A bare substring scan for "red" fires on every name below. A whole-word scan must
        # not. Without this test, `_is_planted_name` could regress to `"red" in name.lower()`
        # and nothing else here would notice.
        for name in ("AlreadyCredited", "ShreddedDocuments",
                     "TheDataChannelIsNarrowAndVERIFIED", "test_a_digest_is_REQUIRED",
                     "CorrespondenceIsDirected", "TheReducedForm"):
            self.assertFalse(auditor._is_planted_name(name), name)

    def test_the_real_suite_yields_a_known_class_name_match(self):
        found = auditor.discover_planted_defects()
        key = "tests.test_correspondence.PlantedTrueCorrespondence"
        self.assertIn(key, found)
        self.assertTrue(found[key]["class_name_matches"])

    def test_the_real_suite_yields_a_known_method_only_match(self):
        found = auditor.discover_planted_defects()
        key = "tests.test_key_exposure.NoKeySHAPEIsCommitted"
        self.assertIn(key, found)
        entry = found[key]
        self.assertFalse(entry["class_name_matches"])
        self.assertIn("test_the_shape_arm_can_actually_FIRE", entry["matched_methods"])

    def test_a_method_only_match_runs_only_that_method_not_the_whole_class(self):
        entry = {"class_name_matches": False,
                 "matched_methods": ["test_the_shape_arm_can_actually_FIRE"]}
        ids = auditor.planted_test_ids({"tests.test_key_exposure.NoKeySHAPEIsCommitted": entry})
        self.assertEqual(ids, ["tests.test_key_exposure.NoKeySHAPEIsCommitted."
                               "test_the_shape_arm_can_actually_FIRE"])

    def test_a_class_name_match_runs_the_whole_class(self):
        entry = {"class_name_matches": True, "matched_methods": []}
        ids = auditor.planted_test_ids({"tests.test_correspondence.PlantedTrueCorrespondence":
                                        entry})
        self.assertEqual(ids, ["tests.test_correspondence.PlantedTrueCorrespondence"])

    def test_an_unparseable_file_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            (work / "test_broken.py").write_text("def not valid python(:\n")
            found = auditor.discover_planted_defects(tests_dir=work)
        self.assertTrue(any("parse_error" in v for v in found.values()))
        # AND an unparseable file must never be handed to the runner as something to execute.
        self.assertEqual(auditor.planted_test_ids(found), [])


class LivenessRunsForRealAndCanFail(unittest.TestCase):
    """B2 / B3 item 2: liveness must EXECUTE the classes it finds — never merely name them —
    and it must be provably able to report a failure, not just report success."""

    def test_liveness_passes_on_the_real_suite_right_now(self):
        result = auditor.liveness()
        self.assertTrue(result["ok"], result.get("failed") or result.get("detail"))
        # 5 modules were hardcoded before this lane's change; the real suite carries planted
        # twins in 40+ files, so a low count here means discovery regressed to that old list.
        self.assertGreater(result["classes_discovered"], 50)
        self.assertGreater(result["test_ids_run"], 50)

    def test_a_vanished_planted_class_is_caught_not_silently_passed(self):
        # THE EXACT FAILURE MODE B2 NAMES: the null battery went quiet and the silence was
        # read as a pass. Pointing the runner at a plausible-but-absent class in a real,
        # loadable module reproduces "the plant stopped reaching the checker" without deleting
        # anything real.
        result = auditor.run_test_ids(
            ["tests.test_correspondence.PlantedTrueCorrespondenceButRenamedAway"])
        self.assertFalse(result["ok"])

    def test_an_empty_worklist_is_a_finding_not_a_silent_pass(self):
        result = auditor.run_test_ids([])
        self.assertFalse(result["ok"])

    def test_a_real_assertion_failure_in_a_synthetic_isolated_fixture_is_caught(self):
        # A standalone module in a scratch directory — never tests/, never engine/ui/seed —
        # run with that directory as cwd, so the real suite and the pre-push gate never see
        # it. This is the twin proving `run_test_ids` catches a genuine failing assertion, not
        # just an import error.
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            (work / "tests").mkdir()
            (work / "tests" / "__init__.py").write_text("")
            (work / "tests" / "test_synthetic_plant.py").write_text(textwrap.dedent("""\
                import unittest

                class PlantedSyntheticFailure(unittest.TestCase):
                    def test_it_fires(self):
                        self.fail("planted: this must be caught")
                """))
            result = auditor.run_test_ids(
                ["tests.test_synthetic_plant.PlantedSyntheticFailure"], cwd=work)
        self.assertFalse(result["ok"])
        self.assertTrue(any("PlantedSyntheticFailure" in f for f in result["failed_ids"]),
                        result["failed_ids"])

    def test_a_synthetic_fixture_that_actually_passes_is_reported_ok(self):
        # The companion to the test above: not vacuous. The same machinery, a fixture that
        # FIRES CLEAN, must come back ok — or "catches failure" would be indistinguishable
        # from "always reports failure".
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            (work / "tests").mkdir()
            (work / "tests" / "__init__.py").write_text("")
            (work / "tests" / "test_synthetic_plant.py").write_text(textwrap.dedent("""\
                import unittest

                class PlantedSyntheticSuccess(unittest.TestCase):
                    def test_it_fires_clean(self):
                        self.assertTrue(True)
                """))
            result = auditor.run_test_ids(
                ["tests.test_synthetic_plant.PlantedSyntheticSuccess"], cwd=work)
        self.assertTrue(result["ok"], result["detail"])
        self.assertEqual(result["failed_ids"], [])

    def test_a_broken_cwd_is_reported_not_raised(self):
        result = auditor.run_test_ids(
            ["tests.test_correspondence.PlantedTrueCorrespondence"],
            cwd=Path("/no/such/directory/could/exist/here"))
        self.assertFalse(result["ok"])


class BatteryReusesAcceptanceRatherThanASecondClient(unittest.TestCase):
    """The operator's explicit instruction: tools/acceptance.py already talks to the served
    URL; battery() must call it, not open a second HTTP/browser path."""

    def test_battery_imports_tools_acceptance_run_not_a_second_client(self):
        import ast
        tree = ast.parse((REPO / "tools" / "auditor.py").read_text(encoding="utf-8"))
        imported = any(
            isinstance(n, ast.ImportFrom) and n.module == "tools.acceptance"
            and any(a.name == "run" for a in n.names)
            for n in ast.walk(tree))
        self.assertTrue(imported, "battery() must import tools.acceptance.run")

    def test_no_second_urllib_or_playwright_client_is_built_for_the_ask_endpoint(self):
        src = (REPO / "tools" / "auditor.py").read_text(encoding="utf-8")
        self.assertNotIn('"/ask"', src)
        self.assertNotIn("'/ask'", src)

    def test_an_unset_CG_URL_is_a_finding_not_a_crash(self):
        with mock.patch.dict("os.environ", {"CG_URL": "", "CG_TOKEN": ""}):
            rows = auditor.battery()
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["ok"])
        self.assertIn("CG_URL", rows[0]["detail"])

    def test_a_client_that_always_raises_is_retried_once_then_filed_as_a_finding(self):
        # PLANTED: tools.acceptance.run always raises. battery() must not propagate the
        # exception (it would take the whole audit down) — it must retry exactly once and
        # then report, carrying whatever evidence exists.
        calls = []

        def _boom(url, token, out):
            calls.append((url, token, out))
            raise TimeoutError("planted: page.screenshot timed out")

        with mock.patch.dict("os.environ", {"CG_URL": "http://x.invalid", "CG_TOKEN": "t"}):
            with mock.patch("tools.acceptance.run", side_effect=_boom):
                rows = auditor.battery()
        self.assertEqual(len(calls), 2, "must retry exactly once, not zero and not many")
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["ok"])
        self.assertIn("partial_screenshots", rows[0])

    def test_a_client_that_succeeds_on_the_second_try_is_used(self):
        calls = []

        def _flaky(url, token, out):
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("planted: transient")
            return {"rows": [{"case": "sharp", "text": "x", "seconds": 1.0,
                              "faithful": "faithful: []", "model": "m",
                              "responded": True, "answer_chars": 10, "rests_on": "",
                              "screenshot": None}]}

        with mock.patch.dict("os.environ", {"CG_URL": "http://x.invalid", "CG_TOKEN": "t"}):
            with mock.patch("tools.acceptance.run", side_effect=_flaky):
                rows = auditor.battery()
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["ok"], rows[0])

    def test_a_RED_faithfulness_verdict_from_the_real_client_shape_is_not_ok(self):
        row = {"case": "vague", "text": "x", "seconds": 1.0, "faithful": "RED", "model": "m",
              "responded": True, "answer_chars": 10, "rests_on": "", "screenshot": None}
        with mock.patch.dict("os.environ", {"CG_URL": "http://x.invalid", "CG_TOKEN": "t"}):
            with mock.patch("tools.acceptance.run", return_value={"rows": [row]}):
                rows = auditor.battery()
        self.assertFalse(rows[0]["ok"])


class RegistryAndConformanceCanBothFail(unittest.TestCase):
    """Planted twins via dependency injection on `tools.build_registry.MAP` — never on
    seed/CONSTITUTION.md itself, which the auditor may not write to."""

    def test_registry_ok_is_consistent_with_build_registry_directly(self):
        from tools.build_registry import build
        reg = build()
        result = auditor.registry()
        self.assertEqual(result["ok"], not reg["unresolved"])
        self.assertEqual(result["unresolved"], reg["unresolved"])

    def test_a_planted_unresolvable_control_fails_registry(self):
        import tools.build_registry as br
        saved = dict(br.MAP)
        try:
            br.MAP["OI-1"] = {"C": ["tests/test_auditor.py:NoSuchClassAnywhereInThisFile"],
                              "E": []}
            result = auditor.registry()
        finally:
            br.MAP.clear()
            br.MAP.update(saved)
        self.assertFalse(result["ok"])
        self.assertTrue(any("NoSuchClassAnywhereInThisFile" in u
                            for u in result["unresolved"]))

    def test_a_planted_unresolvable_E_site_fails_conformance(self):
        import tools.build_registry as br
        saved = dict(br.MAP)
        try:
            br.MAP["OI-1"] = {**saved.get("OI-1", {}), "E": ["engine/no_such_file_ever.py"]}
            result = auditor.conformance()
        finally:
            br.MAP.clear()
            br.MAP.update(saved)
        self.assertFalse(result["ok"])
        self.assertTrue(any("no_such_file_ever" in m for m in result["missing_sites"]))

    def test_a_clean_MAP_passes_conformance(self):
        result = auditor.conformance()
        self.assertTrue(result["ok"], result["missing_sites"])


class PromptRazorEnumeratesRealPromptsAndCatchesADriftedBlock(unittest.TestCase):
    """B3 item 5. `prompt_razor()` real-imports engine.grammar (and three other LM-facing
    prompt constants); twins are planted by monkeypatching `engine.grammar.BLOCKS` for the
    duration of one call, never by editing engine/grammar.py."""

    def test_the_real_render_path_blocks_pass_today(self):
        result = auditor.prompt_razor()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["kinds"], ["WIRE", "TASK", "FORM"])
        self.assertEqual(result["illegal_blocks"], [])

    def test_the_other_lm_facing_prompt_enumeration_is_exhaustive_right_now(self):
        # A grep-equivalent AST scan for every module-level *_SYSTEM/*_PROMPT constant under
        # engine/, so a fifth prompt appearing anywhere is what makes this test the razor's
        # own blind-spot detector rather than a fixed guess.
        import ast
        found = set()
        for f in (REPO / "engine").glob("*.py"):
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                        and isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                    if name.endswith("_SYSTEM") or name.endswith("_PROMPT"):
                        found.add(f"engine.{f.stem}.{name}")
        expected = {"engine.region.REGION_SYSTEM", "engine.propose_correspondence.PROPOSE_SYSTEM",
                   "engine.medium.LABEL_SYSTEM", "engine.inbound.INBOUND_SYSTEM"}
        self.assertEqual(found, expected,
                         "a new LM-facing prompt constant appeared that prompt_razor() does "
                         "not enumerate (or one vanished) — update its other-prompts list")
        result = auditor.prompt_razor()
        self.assertEqual(set(result["other_lm_facing_prompts"]), expected - {
            "engine.inbound.INBOUND_SYSTEM"})  # that one IS the render path, checked above

    def test_a_planted_bracket_free_FORM_block_is_caught(self):
        import engine.grammar as g
        saved = g.BLOCKS
        try:
            g.BLOCKS = (("WIRE", "State goes here."), ("TASK", "Do the thing."),
                       ("FORM", "Write it out however feels natural, no format required."))
            result = auditor.prompt_razor()
        finally:
            g.BLOCKS = saved
        self.assertFalse(result["ok"])
        self.assertTrue(result["render_path"].get("form_sentences_missing_bracket_syntax"))

    def test_a_planted_multi_sentence_TASK_block_is_caught(self):
        import engine.grammar as g
        saved = g.BLOCKS
        try:
            g.BLOCKS = (("WIRE", "State goes here."),
                       ("TASK", "Answer the question. Also feel free to editorialize."),
                       ("FORM", "Cite with [4]."))
            result = auditor.prompt_razor()
        finally:
            g.BLOCKS = saved
        self.assertFalse(result["ok"])
        self.assertEqual(result["render_path"]["task_block_sentence_count"], 2)

    def test_a_planted_illegal_kind_tag_is_caught(self):
        import engine.grammar as g
        saved = g.BLOCKS
        try:
            g.BLOCKS = (("STYLE", "Prefer a warm, engaging voice throughout."),)
            result = auditor.prompt_razor()
        finally:
            g.BLOCKS = saved
        self.assertFalse(result["ok"])
        self.assertTrue(result["illegal_blocks"])

    def test_deep_semantic_classification_is_marked_not_implemented_honestly(self):
        result = auditor.prompt_razor()
        self.assertTrue(result["not_implemented"], "a check that cannot be implemented must "
                        "say so rather than silently pass or fabricate a verdict")


class ChangelogCompletenessReportsAFindingRatherThanCrashing(unittest.TestCase):
    """B3 item 7, NEW. Exercised against real, throwaway git repositories — genuine subprocess
    git plumbing, never a stubbed one — pointed at by monkeypatching `auditor.REPO`, never at
    the real seed/CHANGELOG.md."""

    def _throwaway_repo(self, work: Path):
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=work, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=work, check=True)

    def _commit(self, work: Path, path: str, body: str, message: str):
        f = work / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
        subprocess.run(["git", "add", "-A"], cwd=work, check=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=work, check=True)

    def _head(self, work: Path) -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=work, capture_output=True,
                              text=True, check=True).stdout.strip()

    FULL_DIFF = ("law change\n\nFEATURE-DIFF\n  WHAT x\n  SUPERSEDES y\n"
                "  CONTROLS z\n  FIXTURES w\n")

    def test_a_planted_missing_changelog_file_is_reported_never_crashes(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            self._throwaway_repo(work)
            (work / "seed").mkdir()
            self._commit(work, "engine/x.py", "x = 1\n", "ordinary change")
            with mock.patch.object(auditor, "REPO", work):
                result = auditor.changelog(window=5)
        self.assertFalse(result["changelog_exists"])
        self.assertFalse(result["ok"])
        self.assertTrue(any("does not exist" in f for f in result["findings"]))

    def test_a_planted_design_commit_missing_its_feature_diff_is_found(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            self._throwaway_repo(work)
            (work / "seed").mkdir()
            self._commit(work, "engine/x.py", "x = 1\n", "ordinary change, no block at all")
            with mock.patch.object(auditor, "REPO", work):
                result = auditor.changelog(window=5)
        self.assertFalse(result["ok"])
        self.assertEqual(result["design_change_commits_checked"], 1)
        self.assertFalse(result["rows"][0]["has_feature_diff"])
        self.assertTrue(result["findings"])

    def test_a_planted_design_commit_with_the_block_but_no_changelog_entry_is_found(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            self._throwaway_repo(work)
            (work / "seed").mkdir()
            (work / "seed" / "CHANGELOG.md").write_text("- nothing relevant here\n")
            self._commit(work, "engine/x.py", "x = 1\n", self.FULL_DIFF)
            with mock.patch.object(auditor, "REPO", work):
                result = auditor.changelog(window=5)
        self.assertFalse(result["ok"])
        self.assertTrue(result["rows"][0]["has_feature_diff"])
        self.assertFalse(result["rows"][0]["in_changelog_md"])

    def test_a_complete_planted_design_commit_passes_both_halves(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            self._throwaway_repo(work)
            (work / "seed").mkdir()
            self._commit(work, "engine/x.py", "x = 1\n", self.FULL_DIFF)
            sha = self._head(work)
            (work / "seed" / "CHANGELOG.md").write_text(f"- {sha[:8]} law change\n")
            with mock.patch.object(auditor, "REPO", work):
                result = auditor.changelog(window=5)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["findings"], [])

    def test_a_non_design_commit_needs_no_feature_diff_at_all(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            self._throwaway_repo(work)
            self._commit(work, "seed/.keep", "", "placeholder")  # keep seed/ non-empty for git
            self._commit(work, "README.md", "docs only\n", "just docs, no block needed")
            with mock.patch.object(auditor, "REPO", work):
                result = auditor.changelog(window=5)
        self.assertEqual(result["design_change_commits_checked"], 0)

    def test_design_change_scope_matches_the_stated_prefixes(self):
        self.assertTrue(auditor._touches_design(["engine/grammar.py"]))
        self.assertTrue(auditor._touches_design(["ui/server.py"]))
        self.assertTrue(auditor._touches_design(["hooks/pre-push"]))
        self.assertTrue(auditor._touches_design(["seed/CONSTITUTION.md"]))
        self.assertTrue(auditor._touches_design(["seed/SPEC.md"]))
        self.assertFalse(auditor._touches_design(["tests/test_auditor.py"]))
        self.assertFalse(auditor._touches_design(["README.md"]))
        self.assertFalse(auditor._touches_design(["seed/CHANGELOG.md"]))

    def test_the_real_repo_right_now(self):
        # Whatever the real answer is, it must not crash, and it must be internally
        # consistent (ok iff the file exists and every checked row is ok).
        result = auditor.changelog()
        self.assertEqual(result["ok"],
                         result["changelog_exists"] and all(r["ok"] for r in result["rows"]))


class TheAuditorCannotWriteToEngineUiOrSeed(unittest.TestCase):
    """The non-negotiable rule, asserted rather than claimed: run the mechanism for real and
    fingerprint the protected trees before and after."""

    def test_the_mechanism_detects_a_write_in_a_scratch_root(self):
        # PLANTED: proves assert_read_only can FAIL — using a throwaway root that stands in
        # for engine/ui/seed, never those directories themselves.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "f.txt").write_text("before")

            def _mutate():
                (root / "f.txt").write_text("after — a write happened")
                return "ran"

            result = auditor.assert_read_only(_mutate, roots=[root])
        self.assertFalse(result["ok"])
        self.assertEqual(result["result"], "ran")

    def test_the_mechanism_detects_a_new_file_appearing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "f.txt").write_text("content")

            def _add_a_file():
                (root / "new.txt").write_text("surprise")
                return None

            result = auditor.assert_read_only(_add_a_file, roots=[root])
        self.assertFalse(result["ok"])

    def test_a_genuinely_read_only_action_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "f.txt").write_text("content")
            result = auditor.assert_read_only(lambda: (root / "f.txt").read_text(),
                                              roots=[root])
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "content")

    def test_the_real_offline_checks_touch_nothing_under_engine_ui_or_seed(self):
        # The REAL protected directories, the REAL functions — restricted to the checks that
        # never touch the network, so this stays deterministic. wire()/battery() only ever
        # urlopen and read local files (no write calls appear anywhere in their bodies or the
        # modules they call into), and are exercised against the live deploy separately.
        def _offline_checks():
            return {"sweeps": auditor.sweeps(), "registry": auditor.registry(),
                   "conformance": auditor.conformance(), "razor": auditor.prompt_razor(),
                   "liveness": auditor.liveness(), "copy": auditor.copy_checks(),
                   "changelog": auditor.changelog()}

        result = auditor.assert_read_only(
            _offline_checks, roots=[REPO / "engine", REPO / "ui", REPO / "seed"])
        self.assertTrue(result["ok"], result["detail"])


class AuditAssemblyReachesFindingsFromEverySection(unittest.TestCase):
    """Structural: every section of `audit()` must be able to land in `findings`, and a clean
    report from every section must yield a clean run — proven together so neither can regress
    into "always red" or "always green" without this failing. Each section function is
    monkeypatched independently, so this needs no network and runs in well under a second."""

    SECTION_NAMES = ("sweeps", "registry", "conformance", "prompt_razor", "wire", "battery",
                     "liveness", "copy_checks", "changelog")

    def _run_with(self, outcomes: dict):
        with mock.patch.multiple(auditor, **{n: mock.DEFAULT for n in self.SECTION_NAMES}) \
                as mocks:
            for name, value in outcomes.items():
                mocks[name].return_value = value
            return auditor.audit()

    def test_a_planted_failure_in_every_section_reaches_findings(self):
        result = self._run_with({
            "sweeps": [{"check": "x", "ok": False, "detail": "planted sweep failure"}],
            "registry": {"ok": False, "unresolved": ["OI-99: nowhere"],
                        "committed_registry_is_current": True},
            "conformance": {"ok": False, "detail": "1 site missing",
                            "missing_sites": ["OI-1: nowhere"]},
            "prompt_razor": {"ok": False, "illegal_blocks": ["STYLE: x"],
                            "render_path": {}, "not_implemented": []},
            "wire": {"ok": False, "detail": "unreachable"},
            "battery": [{"case": "sharp", "ok": False, "faithful": "RED"}],
            "liveness": {"ok": False, "failed": ["FAIL: x (tests.y.Z)"], "detail": "x"},
            "copy_checks": [{"check": "ui-surface", "ok": False, "detail": "planted"}],
            "changelog": {"ok": False, "findings": ["planted changelog gap"]},
        })
        self.assertFalse(result["clean"])
        joined = " ".join(result["findings"])
        for needle in ("SWEEP", "REGISTRY", "CONFORMANCE", "RAZOR", "WIRE",
                      "BATTERY", "LIVENESS", "COPY", "CHANGELOG"):
            self.assertIn(needle, joined, f"a failure in {needle}'s section did not surface")

    def test_all_clean_sections_yield_a_clean_report(self):
        result = self._run_with({
            "sweeps": [{"check": "x", "ok": True, "detail": ""}],
            "registry": {"ok": True, "unresolved": [], "committed_registry_is_current": True},
            "conformance": {"ok": True, "missing_sites": []},
            "prompt_razor": {"ok": True, "illegal_blocks": [], "render_path": {},
                            "not_implemented": []},
            "wire": {"ok": True, "commit_match": True, "model_drift": False,
                    "snapshot_stale": False, "served": "abc"},
            "battery": [{"case": "sharp", "ok": True}],
            "liveness": {"ok": True, "failed": []},
            "copy_checks": [{"check": "ui-surface", "ok": True, "detail": ""}],
            "changelog": {"ok": True, "findings": []},
        })
        self.assertTrue(result["clean"], result["findings"])

    def test_not_implemented_items_survive_into_the_top_level_report_even_when_clean(self):
        result = self._run_with({
            "sweeps": [{"check": "x", "ok": True, "detail": ""}],
            "registry": {"ok": True, "unresolved": [], "committed_registry_is_current": True},
            "conformance": {"ok": True, "missing_sites": []},
            "prompt_razor": {"ok": True, "illegal_blocks": [], "render_path": {},
                            "not_implemented": ["planted: this check was not implemented"]},
            "wire": {"ok": True, "commit_match": True, "model_drift": False,
                    "snapshot_stale": False, "served": "abc"},
            "battery": [{"case": "sharp", "ok": True}],
            "liveness": {"ok": True, "failed": []},
            "copy_checks": [{"check": "ui-surface", "ok": True, "detail": ""}],
            "changelog": {"ok": True, "findings": []},
        })
        self.assertTrue(result["clean"])
        self.assertIn("planted: this check was not implemented", result["not_implemented"])


if __name__ == "__main__":
    unittest.main()
