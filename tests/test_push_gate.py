"""THE PUSH GATE, EXERCISED. Not read — RUN.

A commit went out with one failing test because the rule "do not push red" was held by
remembering rather than by a control. Every other invariant here is held mechanically, so
this one is too.

AND THE CONTROLS FOR IT EXECUTE THE HOOK. `seed/OBJECT-AMENDED.md` carries the law that a
control inspecting source text instead of running the path is testing the map: a gate whose
controls grepped its script for the word "unittest" would be exactly the failure the gate
exists to stop, one level up. So these build a throwaway repository, install the hook into it,
and push.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "hooks" / "pre-push"


def _run(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=300, **kw)


class TheHookExistsAndIsInstallable(unittest.TestCase):

    def test_the_hook_is_versioned_and_executable(self):
        self.assertTrue(HOOK.exists(), "the gate must survive a container reclaim")
        self.assertTrue(os.access(HOOK, os.X_OK), "a non-executable hook is silently skipped")

    def test_the_installer_is_versioned_too(self):
        # core.hooksPath is LOCAL config and does not travel with a clone. The hooks travel;
        # one command restores the pointer.
        inst = REPO / "hooks" / "install"
        self.assertTrue(inst.exists() and os.access(inst, os.X_OK))

    def test_this_repository_has_the_hook_path_configured(self):
        # ABSOLUTE OR RELATIVE. `git config core.hooksPath` reports whatever was set, and a
        # worktree resolves it to an absolute path — so pinning the literal string "hooks"
        # made this control fail on a correctly-configured repository. What matters is that
        # the path RESOLVES to the versioned hooks directory.
        from pathlib import Path
        out = _run(["git", "config", "--get", "core.hooksPath"], REPO)
        got = out.stdout.strip()
        self.assertTrue(got, "run ./hooks/install — the gate is not active")
        self.assertEqual((REPO / "hooks").resolve(),
                         (REPO / got).resolve() if not Path(got).is_absolute()
                         else Path(got).resolve(),
                         f"core.hooksPath={got!r} does not point at the versioned hooks")


class TheGateActuallyREFUSES(unittest.TestCase):
    """Built, installed and pushed for real. A green suite passes; a red one is refused."""

    def _repo_with(self, test_body: str):
        d = Path(tempfile.mkdtemp())
        work, remote = d / "work", d / "remote.git"
        _run(["git", "init", "--bare", str(remote)], d)
        work.mkdir()
        _run(["git", "init"], work)
        _run(["git", "config", "user.email", "t@t"], work)
        _run(["git", "config", "user.name", "t"], work)
        (work / "tests").mkdir()
        (work / "tests" / "__init__.py").write_text("")
        (work / "tests" / "test_x.py").write_text(test_body)
        (work / "hooks").mkdir()
        shutil.copy2(HOOK, work / "hooks" / "pre-push")
        os.chmod(work / "hooks" / "pre-push", 0o755)
        _run(["git", "config", "core.hooksPath", "hooks"], work)
        _run(["git", "add", "-A"], work)
        _run(["git", "commit", "-m", "x"], work)
        _run(["git", "remote", "add", "origin", str(remote)], work)
        return work, remote

    def test_a_GREEN_suite_pushes(self):
        work, remote = self._repo_with(
            "import unittest\n"
            "class C(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(2, 1 + 1)\n")
        out = _run(["git", "push", "-u", "origin", "HEAD"], work)
        self.assertEqual(0, out.returncode, out.stderr[-800:])
        self.assertIn("green in", out.stderr)

    def test_a_RED_suite_is_REFUSED(self):
        work, remote = self._repo_with(
            "import unittest\n"
            "class C(unittest.TestCase):\n"
            "    def test_bad(self):\n"
            "        self.assertEqual(3, 1 + 1)\n")
        out = _run(["git", "push", "-u", "origin", "HEAD"], work)
        self.assertNotEqual(0, out.returncode, "a red suite reached the remote")
        self.assertIn("REFUSED", out.stderr)

    def test_the_refusal_names_the_failing_tests(self):
        # A gate that says only "no" sends the operator back to a 130-second run to find out
        # what it saw.
        work, _ = self._repo_with(
            "import unittest\n"
            "class C(unittest.TestCase):\n"
            "    def test_the_named_one(self):\n"
            "        self.assertEqual(3, 1 + 1)\n")
        out = _run(["git", "push", "-u", "origin", "HEAD"], work)
        self.assertIn("test_the_named_one", out.stderr)

    def test_nothing_reached_the_remote_when_refused(self):
        work, remote = self._repo_with(
            "import unittest\n"
            "class C(unittest.TestCase):\n"
            "    def test_bad(self):\n"
            "        self.assertEqual(3, 1 + 1)\n")
        _run(["git", "push", "-u", "origin", "HEAD"], work)
        refs = _run(["git", "for-each-ref", "--format=%(refname)"], remote)
        self.assertEqual("", refs.stdout.strip(), "the remote took the red push anyway")

    def test_no_verify_still_bypasses_and_that_is_STATED(self):
        # git's own escape hatch cannot be disabled from inside a hook. The gate stops the
        # ACCIDENT, which is what it is for; it does not pretend to stop a decision, and the
        # hook says so rather than implying a guarantee it cannot make.
        work, remote = self._repo_with(
            "import unittest\n"
            "class C(unittest.TestCase):\n"
            "    def test_bad(self):\n"
            "        self.assertEqual(3, 1 + 1)\n")
        out = _run(["git", "push", "--no-verify", "-u", "origin", "HEAD"], work)
        self.assertEqual(0, out.returncode, out.stderr[-400:])
        self.assertIn("--no-verify", HOOK.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class TheAmendmentGateHasTeeth(unittest.TestCase):
    """B4 was a paragraph. /seed is the law, and law may not change silently.

    Each control builds a THROWAWAY repository, installs the real hook, and pushes for real.
    Nothing here reads the hook's source: a gate is verified by being REFUSED, and a substring
    check over a shell script is the map-not-territory failure this project has shipped once.

    THE INNER SUITE IS PINNED. The hook runs `python3 -m unittest discover -s tests` from the
    repository being pushed, so these throwaway repos carry one trivial test of their own. That
    also isolates them from the outer run: without `cwd` set to the throwaway, the inner
    discover walked THIS repository's tests and the controls passed alone but failed under the
    full suite — an order dependence that would have made every green here conditional on how
    the suite was invoked.
    """

    FULL = ("law change\n\nFEATURE-DIFF\n  WHAT x\n  SUPERSEDES y\n"
            "  CONTROLS z\n  FIXTURES w\n")

    def _repo(self, tmp: Path):
        bare, work = tmp / "remote.git", tmp / "work"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        hooks = work / "hooks"
        hooks.mkdir()
        (hooks / "pre-push").write_text((REPO / "hooks" / "pre-push").read_text())
        (hooks / "pre-push").chmod(0o755)
        (work / "tests").mkdir()
        (work / "tests" / "test_ok.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self): pass\n")
        for k, v in (("user.email", "t@t"), ("user.name", "t"), ("core.hooksPath", "hooks")):
            subprocess.run(["git", "-C", str(work), "config", k, v], check=True)
        subprocess.run(["git", "-C", str(work), "remote", "add", "origin", str(bare)], check=True)
        return work

    def _commit(self, work: Path, path: str, body: str, message: str):
        f = work / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
        subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(work), "commit", "-q", "-m", message], check=True)

    def _push(self, work: Path):
        # cwd IS THE THROWAWAY. See the class docstring: without it the hook's own suite run
        # discovers this repository's tests and the result depends on the caller's directory.
        return subprocess.run(["git", "push", "-u", "origin", "HEAD:main"],
                              cwd=str(work), capture_output=True, text=True, timeout=900)

    def test_a_seed_change_WITHOUT_a_feature_diff_is_REFUSED(self):
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            self._commit(work, "seed/SPEC.md", "the law\n", "tweak the spec")
            r = self._push(work)
            self.assertNotEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertIn("without a complete FEATURE-DIFF", r.stderr)

    def test_a_seed_change_WITH_a_complete_feature_diff_PASSES(self):
        """Not vacuous: the same change with the block must go through, or it is a wall."""
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            self._commit(work, "seed/SPEC.md", "the law\n", self.FULL)
            r = self._push(work)
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_an_INCOMPLETE_block_is_refused_and_NAMES_what_is_missing(self):
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            self._commit(work, "seed/SPEC.md", "the law\n",
                         "law change\n\nFEATURE-DIFF\n  WHAT x\n")
            r = self._push(work)
            self.assertNotEqual(0, r.returncode)
            self.assertIn("SUPERSEDES", r.stderr)
            self.assertIn("FIXTURES", r.stderr)

    def test_a_NON_seed_change_needs_no_feature_diff(self):
        """The gate guards the law, not every commit. Requiring it everywhere makes the block
        a ritual, and a ritual is not read."""
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            self._commit(work, "engine/x.py", "x = 1\n", "ordinary change")
            self.assertEqual(0, self._push(work).returncode)

    def test_DELETING_from_the_archive_is_REFUSED(self):
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            self._commit(work, "archive/design/old.md", "the old design\n", "archive it")
            self.assertEqual(0, self._push(work).returncode)
            (work / "archive" / "design" / "old.md").unlink()
            subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(work), "commit", "-q", "-m", "drop it"], check=True)
            r = self._push(work)
            self.assertNotEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertIn("deletes from archive/", r.stderr)

    def test_ADDING_to_the_archive_is_fine(self):
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            self._commit(work, "archive/design/a.md", "one\n", "archive one")
            self.assertEqual(0, self._push(work).returncode)
            self._commit(work, "archive/design/b.md", "two\n", "archive two")
            self.assertEqual(0, self._push(work).returncode)

    def test_EVERY_commit_in_the_range_is_checked_not_only_the_tip(self):
        """A bad commit hidden behind an innocent one is the obvious way past a tip-only gate."""
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            self._commit(work, "engine/x.py", "x = 1\n", "base")
            self.assertEqual(0, self._push(work).returncode)
            self._commit(work, "seed/SPEC.md", "law\n", "sneak the law in")
            self._commit(work, "engine/y.py", "y = 1\n", "innocent tip")
            r = self._push(work)
            self.assertNotEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertIn("without a complete FEATURE-DIFF", r.stderr)

    def test_the_red_suite_gate_still_stands(self):
        """The new gate must not have displaced the old one."""
        with tempfile.TemporaryDirectory() as d:
            work = self._repo(Path(d))
            (work / "tests" / "test_bad.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n"
                "    def test_bad(self): self.fail('planted')\n")
            self._commit(work, "engine/x.py", "x = 1\n", "ordinary change")
            r = self._push(work)
            self.assertNotEqual(0, r.returncode)
            self.assertIn("the suite is red", r.stderr)
