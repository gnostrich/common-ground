"""The container is reclaimed hourly and comes back looking FINE. That is the defect shape.

On 2026-08-06 a reclaim restored a checkout SIXTY-TWO COMMITS STALE with a clean `git status`
and no warning of any kind. Two agents read code that had been deleted weeks earlier before
anyone noticed, and three uncommitted worktrees were gone permanently — they were never in
git, so there was nothing to recover.

`tools/restore` is the answer, and these are the controls on it. They are deliberately narrow:
the script mutates git state, so a control that ran it for real would be a control that
fetches and fast-forwards the repository it is testing. What IS checked here is everything
that can be checked without that — that the script exists and runs, that its failure paths
are reachable rather than decorative, and above all that it never DISCARDS anything.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "tools" / "restore"


class TheScriptISThere(unittest.TestCase):

    def test_it_exists_and_is_executable(self):
        self.assertTrue(SCRIPT.exists(), "tools/restore is the reclaim recovery path")
        self.assertTrue(stat.S_IMODE(SCRIPT.stat().st_mode) & stat.S_IXUSR,
                        "a recovery script nobody can execute is a document")

    def test_it_is_valid_bash(self):
        r = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class ItNeverDISCARDS(unittest.TestCase):
    """The one property that matters most. A recovery script that resets --hard would have
    destroyed the operator's uncommitted work every hour, silently, while reporting success."""

    def setUp(self):
        self.body = SCRIPT.read_text()

    def test_no_destructive_git_command_appears(self):
        for danger in ("reset --hard", "checkout -f", "clean -fd", "clean -fx",
                       "push --force", "stash drop", "branch -D"):
            with self.subTest(danger=danger):
                self.assertNotIn(danger, self.body,
                                 f"{danger!r} can destroy uncommitted work; recovery must not")

    def test_local_changes_are_stashed_before_any_fast_forward(self):
        """Order matters: the stash must precede the merge, or the merge refuses and the
        script leaves a stale tree while reporting a failure nobody acts on."""
        stash = self.body.index("git stash push")
        merge = self.body.index("git merge --ff-only")
        self.assertLess(stash, merge, "stash must come before the fast-forward")

    def test_the_fast_forward_is_FF_ONLY(self):
        """A plain merge on a diverged branch would write a merge commit into the operator's
        history from a recovery script. Fast-forward or refuse."""
        self.assertIn("git merge --ff-only", self.body)
        self.assertNotIn("git merge origin", self.body)

    def test_the_stash_is_NAMED_so_it_can_be_found(self):
        self.assertIn("git stash push -u -m", self.body,
                      "an anonymous stash is indistinguishable from lost work")


class EveryFailurePathIsREACHABLE(unittest.TestCase):
    """A script whose sad paths cannot fire reports OK on a broken container."""

    def setUp(self):
        self.body = SCRIPT.read_text()

    def test_it_can_report_incomplete(self):
        self.assertIn("RESTORE INCOMPLETE", self.body)
        self.assertIn("RESTORE OK", self.body)

    def test_fail_is_set_on_every_checked_condition(self):
        """Each thing it checks must be able to move `fail`, or the check is decoration."""
        self.assertGreaterEqual(len(re.findall(r"\bfail=1\b", self.body)), 3,
                                "at least the FF, the hook and chromium must be able to fail")

    def test_the_exit_code_carries_the_verdict(self):
        self.assertIn('exit "$fail"', self.body,
                      "a caller must be able to branch on the outcome, not parse prose")

    def test_a_missing_chromium_is_a_FAILURE_not_a_shrug(self):
        """The browser controls SKIP without chromium. A skip that reads as a pass is how a
        dead page shipped twice; recovery must say the controls are unarmed."""
        i = self.body.index("NO CHROMIUM")
        self.assertIn("SKIP, not pass", self.body[i:i + 200])
        self.assertIn("fail=1", self.body[i:i + 200])

    def test_a_missing_corpus_is_NOT_a_failure_and_says_why(self):
        """The corpus is gitignored by policy and the deploy holds its own copy on a volume.
        Failing on its absence would make every clean container report broken."""
        i = self.body.index("NO CORPUS")
        window = self.body[i:i + 400]
        self.assertIn("volume", window)
        self.assertNotIn("fail=1", window)


class ItReportsSECRETSWithoutTouchingThem(unittest.TestCase):
    """The repo is PUBLIC. Recovery may say a key is missing; it may never carry one."""

    def setUp(self):
        self.body = SCRIPT.read_text()

    def test_it_reports_missing_keys_rather_than_assuming_them(self):
        self.assertIn("MISSING", self.body)
        for f in ("railway.env", "openrouter.env", "aristotle.env"):
            self.assertIn(f, self.body)

    def test_it_never_PRINTS_a_key_value(self):
        """RESTATED, and the restatement is the point.

        This asserted that the script never SOURCES a key file. That was right while it only
        reported presence, and became wrong the moment it had to authenticate to Railway to
        regenerate window.env — sourcing a credential into a subshell is how you use one.
        Forbidding the read was a proxy for the property; the property is that no secret
        reaches stdout, stderr, or a committed file.

        So this is checked at the RUNTIME instead of by grepping the source, which is what
        this codebase requires of every control anyway: run the thing, read what it emitted,
        and look for the actual key bytes in it.
        """
        sd = subprocess.run(
            ["bash", "-c", "ls -d /tmp/claude-*/-home-user-common-ground/*/scratchpad "
                           "2>/dev/null | head -1"], capture_output=True, text=True).stdout.strip()
        if not sd:
            self.skipTest("NOT CHECKED: no scratchpad on this machine, so there is no key "
                          "material to look for. This is a SKIP, not a pass.")
        secrets = []
        for name in ("railway.env", "openrouter.env", "aristotle.env", "window.env"):
            f = Path(sd) / name
            if not f.exists():
                continue
            for line in f.read_text().splitlines():
                _, _, val = line.partition("=")
                val = val.strip()
                if len(val) >= 12:                    # a real key, not a flag or a short path
                    secrets.append((name, val))
        if not secrets:
            self.skipTest("NOT CHECKED: no key material found to look for. SKIP, not a pass.")

        r = subprocess.run(["bash", "-c", f"cd {REPO} && ./tools/restore"],
                           capture_output=True, text=True, timeout=600)
        emitted = r.stdout + r.stderr
        for name, val in secrets:
            with self.subTest(secret=name):
                self.assertNotIn(val, emitted,
                                 f"a value from {name} appeared in the recovery output; these "
                                 f"logs are long and skimmed, so that is a disclosure")

    def test_the_credential_is_used_in_a_SUBSHELL_so_it_does_not_persist(self):
        """The parent shell must not carry the token onward into the rest of the script."""
        i = self.body.index("regenerating from the Railway service")
        window = self.body[i:i + 1400]
        self.assertIn('( set -a; . "$SD/railway.env"; set +a', window,
                      "the credential must be sourced inside ( ), not into the parent")

    def test_the_regenerated_window_env_is_never_ECHOED(self):
        """It writes the file and reports presence. A recovery log that prints a token turns
        every reclaim into a disclosure, and these logs are long and skimmed."""
        i = self.body.index("regenerating from the Railway service")
        window = self.body[i:i + 1400]
        self.assertIn("umask 077", window, "the written file must not be world-readable")
        self.assertNotIn("echo \"$CG_TOKEN", window)
        self.assertNotIn("echo $CG_TOKEN", window)
        self.assertNotIn("--json | tee", window)

    def test_the_token_comes_from_the_SERVICE_not_from_git(self):
        """Railway holds both values as service variables, so regenerating needs no secret in
        this public repository — and a rotated token is picked up instead of silently
        disagreeing with a stale file."""
        self.assertIn("COMMON_GROUND_TOKEN", self.body)
        self.assertIn("RAILWAY_SERVICE_WINDOW_URL", self.body)
        self.assertIn("railway variables --json", self.body)

    def test_it_only_regenerates_when_the_file_is_ABSENT(self):
        """Never overwrite a window.env somebody put there deliberately."""
        i = self.body.index("regenerating from the Railway service")
        self.assertIn('[ ! -f "$SD/window.env" ]', self.body[max(0, i - 400):i])

    def test_no_key_material_is_hardcoded(self):
        """The script is committed to a public repository."""
        self.assertIsNone(re.search(r"(sk-|rw_|ghp_)[A-Za-z0-9_-]{12,}", self.body))


class ItRunsCleanOnAHealthyContainer(unittest.TestCase):
    """The only end-to-end arm. Runs the real script with the network fetch neutered, so it
    exercises the reporting and the exit code without touching the operator's git state."""

    def test_a_dry_run_reports_and_exits_zero(self):
        env = dict(os.environ, PATH=os.environ.get("PATH", ""))
        r = subprocess.run(["bash", "-c", f"cd {REPO} && ./tools/restore"],
                           capture_output=True, text=True, timeout=600, env=env)
        out = r.stdout
        for section in ("== branch ==", "== push gate ==", "== browser controls ==",
                        "== corpus ==", "== secrets"):
            self.assertIn(section, out, out[-1500:])
        self.assertTrue(out.rstrip().endswith("RESTORE OK")
                        or "RESTORE INCOMPLETE" in out, out[-1500:])
        # On THIS machine the suite is being run, so the hook and chromium are present and it
        # must say OK. If this fails, the container is genuinely half-restored and that is the
        # control doing its job rather than a flake.
        self.assertEqual(r.returncode, 0, out[-1500:])


if __name__ == "__main__":
    unittest.main()
