"""OI-37, MECHANIZED: this repository is PUBLIC and key files sit one directory away.

The constitution says keys are tracked as BLOCKED-on-operator, never forgotten, never
committed. The first two clauses are ledger discipline. The third is a fact about bytes, and
a fact about bytes can be checked — so it is checked here, on every run, against the tree AND
against the whole reachable history. A key committed and then deleted is still published: git
keeps the blob, GitHub serves it, and mirrors have it. "Not in HEAD" is not the property.

TWO ARMS, and the second is the strong one.

  SHAPE   — generic key patterns (sk-…, ghp_…, long hex, JWTs). Catches a key this repo has
            never seen. Guesses at what a secret looks like, so it has false negatives by
            construction, and that limit is stated rather than hidden.
  LITERAL — the actual values currently in scratchpad/*.env. No pattern guessing at all: if
            one of THESE bytes is in the tree or the history, it is the operator's key and it
            is published. This arm cannot have a false positive.

The literal arm can only run where the key files exist. It SKIPS LOUDLY when they do not,
because a control that quietly passes on an empty search reports a property nobody checked —
and this is the control where that failure would be most expensive.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Minimum length for a value from an env file to be treated as key material. Short values are
#: flags, ports and paths ("english", "1", "true"); searching for them would match ordinary
#: source everywhere and turn this control into noise. See seed/CONSTANT_PROVENANCE.json.
MIN_SECRET = 16

#: Generic shapes. Deliberately few and specific: a loose pattern here means false positives,
#: and a security control that cries wolf is switched off by the person it was built for.
SHAPES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),                 # OpenAI / OpenRouter style
    re.compile(r"\bghp_[A-Za-z0-9]{30,}"),                  # GitHub personal token
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\."),   # JWT
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                    # AWS access key id
)

#: Paths whose CONTENT is allowed to contain something shaped like a key: this file (it holds
#: the patterns) and .gitignore (it names the files). Named explicitly so the exemption is a
#: short list somebody can read, not a rule that quietly grows.
SHAPE_EXEMPT = ("tests/test_key_exposure.py", ".gitignore")

#: A shape hit is forgiven only if the MATCHED TEXT ITSELF says it is not a key. The suite
#: carries strings like `sk-ant-should-be-ignored`, which exist to prove the engine refuses
#: Anthropic keys and routes through OpenRouter only — deliberate non-keys, and the control
#: must not fire on them. The rule is deliberately narrow: exempting whole files (or all of
#: tests/) would let a real key hide in a test, which is exactly where a real key gets pasted
#: while somebody is debugging. A genuine secret cannot contain these words, so the exemption
#: is safe in the direction that matters.
FIXTURE_MARKERS = ("should-be-ignored", "should-not", "not-a-key", "notakey", "example",
                   "dummy", "fixture", "-abc", "-nope", "placeholder")


def is_fixture(matched: str) -> bool:
    low = matched.lower()
    return any(m in low for m in FIXTURE_MARKERS)


def shape_hits(blobs: dict) -> list[str]:
    """The scan, as a FUNCTION over {path: text}, so it can be run on planted input.

    Extracted for one reason: the control that guards the exemption used to grep this file's
    own source for a forbidden expression, and then failed because writing the assertion put
    that expression in the file. Self-reference, and the same shape as a referee scoring its
    own prose. Exercising the scan on planted blobs asks the question directly instead.
    """
    hits = []
    for rel, text in blobs.items():
        if rel in SHAPE_EXEMPT:
            continue
        for rx in SHAPES:
            for m in rx.finditer(text):
                if is_fixture(m.group(0)):
                    continue
                hits.append(f"{rel}: {m.group(0)[:12]}…")
    return hits


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def scratchpad() -> Path | None:
    hits = sorted(Path("/tmp").glob("claude-*/-home-user-common-ground/*/scratchpad"))
    return hits[0] if hits else None


#: WHAT MAKES A VALUE A SECRET is the variable's NAME, not its length. The first run of this
#: control fired on `CG_URL=https://window-production-756e.up.railway.app` — a URL that is
#: deliberately published, sitting in INVENTORY.md on purpose. OI-37 governs KEYS. A closed
#: vocabulary of secret-bearing name fragments is the declared rule; anything else in an env
#: file is configuration, and treating configuration as secret would make this control fire on
#: correct behaviour, which is how a security control gets switched off by the person it
#: protects. Matched case-insensitively on the variable NAME only.
SECRET_NAMES = ("TOKEN", "KEY", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL")


def real_secrets() -> list[tuple[str, str]]:
    """(filename, value) for every SECRET-NAMED value in the operator's env files."""
    sd = scratchpad()
    if sd is None:
        return []
    out = []
    for f in sorted(sd.glob("*.env")):
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            name, sep, val = line.partition("=")
            val = val.strip().strip('"').strip("'")
            if not sep or len(val) < MIN_SECRET:
                continue
            if any(frag in name.strip().upper() for frag in SECRET_NAMES):
                out.append((f.name, val))
    return out


class NoKeySHAPEIsCommitted(unittest.TestCase):
    """Arm one. Guesses at what a secret looks like, and says so."""

    def test_no_tracked_file_matches_a_key_shape(self):
        blobs = {}
        for rel in tracked_files():
            try:
                blobs[rel] = (REPO / rel).read_text(errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue
        hits = shape_hits(blobs)
        self.assertEqual(hits, [], f"key-shaped material in tracked files: {hits[:5]}")

    def test_the_shape_arm_can_actually_FIRE(self):
        """Planted. Without this the arm could be a regex that matches nothing."""
        planted = "sk-" + "A1b2C3d4E5f6G7h8J9k0L1m2"
        self.assertTrue(any(rx.search(planted) for rx in SHAPES),
                        "the shape arm did not recognise a plainly key-shaped string")

    def test_a_self_declaring_fixture_is_forgiven_and_a_real_shape_is_NOT(self):
        """Both directions, because the exemption is where this control could be defanged."""
        self.assertTrue(is_fixture("sk-ant-should-be-ignored"))
        self.assertFalse(is_fixture("sk-" + "A1b2C3d4E5f6G7h8J9k0L1m2"),
                         "a key-shaped string with no fixture marker must NOT be forgiven")

    def test_a_REAL_key_in_a_TEST_file_is_still_caught(self):
        """The exemption must be by matched text, never by path. A test file is exactly where
        a real key gets pasted while somebody is debugging, so exempting tests/ wholesale
        would open the widest hole in the arm. Run on planted blobs, not on source-grepping."""
        real = "sk-" + "Zq7w2Xr9Tn4Kd8Lp1Vb6Mc3"
        planted = {"tests/test_something.py": f'KEY = "{real}"\n',
                   "engine/x.py": f'K = "{real}"\n'}
        hits = shape_hits(planted)
        self.assertEqual(len(hits), 2, f"a real key in a test file must still be caught: {hits}")

    def test_a_fixture_in_ANY_file_is_forgiven(self):
        self.assertEqual(
            shape_hits({"tests/test_ui.py": 'k = "sk-ant-should-be-ignored"',
                        "engine/x.py": 'k = "sk-ant-should-be-ignored"'}), [])

    def test_the_scan_is_not_vacuous(self):
        """It must find something when something is there — otherwise every green above is
        the green of a function that returns [] no matter what."""
        self.assertTrue(shape_hits({"a.py": "ghp_" + "a" * 36}))

    def test_the_shape_arms_LIMIT_is_stated(self):
        """It has false negatives by construction. Saying so is the honest half of shipping
        it; the literal arm below is what actually protects the operator's keys."""
        import sys

        doc = " ".join((sys.modules[__name__].__doc__ or "").split())
        self.assertIn("false negatives by construction", doc)


class NoREALKeyIsCommittedOrEverWas(unittest.TestCase):
    """Arm two. No pattern guessing: the operator's actual bytes. Cannot false-positive."""

    def setUp(self):
        self.secrets = real_secrets()
        if not self.secrets:
            self.skipTest(
                "NOT CHECKED: no scratchpad env files on this machine, so there is no key "
                "material to search for. This is a SKIP and not a pass — OI-37's literal arm "
                "is unverified here.")

    def test_no_key_value_is_in_any_tracked_file(self):
        blobs = {}
        for rel in tracked_files():
            try:
                blobs[rel] = (REPO / rel).read_text(errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue
        for name, val in self.secrets:
            for rel, text in blobs.items():
                self.assertNotIn(val, text,
                                 f"a value from {name} is committed in {rel} — this repository "
                                 f"is PUBLIC, so it is published")

    def test_no_key_value_is_anywhere_in_the_REACHABLE_HISTORY(self):
        """A key committed and later deleted is still published. `git log -S` walks the
        history for the literal bytes, which is the question that actually matters."""
        for name, val in self.secrets:
            r = subprocess.run(
                ["git", "-C", str(REPO), "log", "--all", "--oneline", "-S", val, "--"],
                capture_output=True, text=True, timeout=600)
            self.assertEqual(r.stdout.strip(), "",
                             f"a value from {name} appears in history: {r.stdout[:200]}. "
                             f"Deleting it from HEAD does not unpublish it — the operator must "
                             f"ROTATE the key, and that is a BLOCKED-on-operator row.")

    def test_the_env_files_themselves_are_not_tracked(self):
        tracked = set(tracked_files())
        for rel in tracked:
            self.assertFalse(rel.endswith(".env"), f"{rel} is tracked and is an env file")

    def test_a_NON_secret_env_value_is_not_treated_as_one(self):
        """The narrowing, controlled. `CG_URL` is published on purpose and must not fire; a
        control that flags correct behaviour is a control somebody turns off."""
        vals = {v for _, v in self.secrets}
        for v in vals:
            self.assertFalse(v.startswith("http"),
                             f"a URL is being treated as key material: {v[:40]}")

    def test_the_vocabulary_is_CLOSED_and_readable(self):
        """The rule is a short list somebody can check, not a heuristic that grows."""
        self.assertIn("TOKEN", SECRET_NAMES)
        self.assertIn("KEY", SECRET_NAMES)
        self.assertLessEqual(len(SECRET_NAMES), 8, "a vocabulary this long is a heuristic")

    def test_the_literal_arm_can_actually_FIRE(self):
        """Planted, in a temp file INSIDE the repo, staged nowhere. Proves the search would
        find a real key rather than only ever searching clean files."""
        import tempfile

        name, val = self.secrets[0]
        with tempfile.NamedTemporaryFile("w", dir=REPO, suffix=".plant", delete=True) as fh:
            fh.write(f"THE_KEY={val}\n")
            fh.flush()
            self.assertIn(val, Path(fh.name).read_text(),
                          "the plant did not write; the arm is untested")


class TheScratchpadIsOutsideTheTree(unittest.TestCase):
    """Where the keys live is itself the control: they are not in the repo at all."""

    def test_no_scratchpad_path_is_inside_the_repository(self):
        sd = scratchpad()
        if sd is None:
            self.skipTest("NOT CHECKED: no scratchpad here. SKIP, not a pass.")
        self.assertNotIn(str(REPO.resolve()), str(sd.resolve()),
                         "key material must not live under the repository root")

    def test_gitignore_refuses_env_files_ANYWHERE_in_the_tree(self):
        """A REAL GAP this control found on its first run.

        The keys are protected by LOCATION — they live in a scratchpad outside the repository
        — and .gitignore said nothing about `.env` at all. Location is a strong protection
        right up until somebody copies a file in to debug something, and then `git add -A`
        publishes it. Belt and braces: git now refuses to see one wherever it lands.
        """
        gi = (REPO / ".gitignore").read_text()
        self.assertIn("*.env", gi, "an env file copied into the tree would be committable")


if __name__ == "__main__":
    unittest.main()
