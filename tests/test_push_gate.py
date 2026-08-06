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
        out = _run(["git", "config", "--get", "core.hooksPath"], REPO)
        self.assertEqual("hooks", out.stdout.strip(),
                         "run ./hooks/install — the gate is not active")


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
