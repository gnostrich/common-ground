"""OI-36, MECHANIZED: the firewall was an audit somebody ran once. Now it runs every time.

A one-off audit reporting "0 matches across 80,566 slots" is a fact about a Tuesday. The
corpus grows, new sources are ingested, and the property it established silently stops being
checked — which is the same failure mode as a constitution whose invariants have no controls,
applied to the one invariant that keeps the referee out of the game it is refereeing.

TWO POPULATIONS, DELIBERATELY. The planted snapshots run ALWAYS and prove the detector can
detect; the real corpus runs when it is on disk and proves the corpus is clean. Only the
second is skippable, and it is skipped LOUDLY rather than passing — a firewall control that
quietly passes when it cannot see the corpus is worse than no control, because the green
reports a property nobody checked.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from engine.corpus_state import CorpusSnapshot, SNAPSHOT_PATH, SlotRecord
from engine.nonempty import RefusedCensus, clean
from engine.reflexivity import (MIN_LINE, OWN_BUCKETS, REPO, audit, matches, own_nus,
                                own_paths)


def _slot(sid: str, docs, nu: str = "\x01en\x01some ordinary corpus claim") -> SlotRecord:
    return SlotRecord(slot=sid, chart="english", type="assert", nu=nu, value="true",
                      confidence=1.0, tier="EXTRACTION", docs=tuple(docs))


def _snap(*slots) -> CorpusSnapshot:
    return CorpusSnapshot(slots={s.slot: s for s in slots}, arrows=())


class TheDetectorDETECTS(unittest.TestCase):
    """Runs unconditionally. If the corpus is absent this file still proves something."""

    def test_a_slot_from_this_repos_bucket_is_caught(self):
        for bucket in OWN_BUCKETS:
            with self.subTest(bucket=bucket):
                found = matches(_snap(_slot("a", (f"{bucket}||engine/region.py",))))
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0]["arm"], "provenance")

    def test_the_bucket_arm_is_case_insensitive(self):
        self.assertEqual(len(matches(_snap(_slot("a", ("Common-Ground||x.py",))))), 1)

    def test_a_slot_naming_a_path_THIS_repo_tracks_is_caught(self):
        """The re-labelling case: another bucket, but this repository's own file."""
        found = matches(_snap(_slot("a", ("SomeOtherProject||engine/region.py",))))
        self.assertEqual(len(found), 1)
        self.assertIn("tracked by this repository", found[0]["why"])

    def test_a_docstring_fragment_on_our_own_path_is_caught(self):
        found = matches(_snap(_slot("a", ("x||engine/grounded.py#doc:check_answer",))))
        self.assertEqual(len(found), 1)

    def test_a_seed_line_ingested_under_ANY_bucket_is_caught_by_exact_nu(self):
        """Arm two. No provenance signal at all — the bucket and path are a stranger's — and
        the nu collides byte-for-byte with a line of this repo's constitution."""
        nus = sorted(own_nus())
        self.assertTrue(nus, "the seed documents must be readable for this arm to exist")
        found = matches(_snap(_slot("a", ("StrangersRepo||docs/notes.md",), nu=nus[0])))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["arm"], "exact-nu")

    def test_ordinary_corpus_material_is_NOT_caught(self):
        """The false-positive direction. A firewall that fires on everything trains its
        reader to ignore it, which is the same as not having one."""
        self.assertEqual(matches(_snap(
            _slot("a", ("certified-positivity||src/Positivity.lean",)),
            _slot("b", ("Perp-Options-AMM||amm/pricing.py",)),
            _slot("c", ("Autosynth||lib/graph.go#doc:Walk",)))), [])

    def test_a_path_that_merely_LOOKS_like_ours_is_not_caught(self):
        """`engine/region.py` in somebody else's tree is their file. The arm matches the
        repo-relative path this repository actually tracks, not a suggestive suffix."""
        self.assertEqual(matches(_snap(_slot("a", ("Other||vendor/engine/region.py",)))), [])


class TheAuditIsACensusAndObeysOI24(unittest.TestCase):

    def test_an_empty_snapshot_is_REFUSED_not_reported_clean(self):
        a = audit(CorpusSnapshot(slots={}, arrows=()))
        self.assertTrue(a["refused"], "no corpus is not a finding of no contamination")
        with self.assertRaises(RefusedCensus):
            clean(a, "matches")

    def test_a_real_snapshot_answers(self):
        a = audit(_snap(_slot("a", ("certified-positivity||src/P.lean",))))
        self.assertFalse(a["refused"])
        self.assertEqual(a["population"], 1)
        self.assertTrue(clean(a, "matches"))

    def test_a_contaminated_snapshot_is_NOT_clean(self):
        a = audit(_snap(_slot("a", ("common-ground||engine/region.py",))))
        self.assertFalse(clean(a, "matches"))
        self.assertEqual(a["by_arm"]["provenance"], 1)

    def test_the_blind_spot_travels_ON_the_record(self):
        """A firewall reported without its limit is read as a guarantee."""
        a = audit(_snap(_slot("a", ("x||y.py",))))
        self.assertIn("resemblance", a["blind_spot"])
        self.assertIn("NOT", a["blind_spot"])


class TheMaterialThisRepoKnowsAboutItself(unittest.TestCase):

    def test_own_paths_covers_the_engine_and_is_not_empty(self):
        p = own_paths()
        self.assertIn("engine/region.py", p)
        self.assertIn("seed/CONSTITUTION.md", p)
        self.assertNotIn("runs/corpus.snapshot", p,
                         "the corpus is not this repository's own material")

    def test_own_nus_excludes_short_lines(self):
        """A bare heading or a rule collides with prose everywhere. Hashing them would
        manufacture matches, and a false positive in a firewall is worse than useless."""
        from engine.normalize import nu

        self.assertNotIn(nu("english", "---"), own_nus())
        self.assertNotIn(nu("english", "GO"), own_nus())

    def test_MIN_LINE_is_a_stated_threshold_not_a_silent_one(self):
        self.assertGreaterEqual(MIN_LINE, 20)


class TheREALCorpusIsClean(unittest.TestCase):
    """The standing arm. Skipped LOUDLY when the corpus is not on disk — never passed."""

    def test_the_served_corpus_carries_no_common_ground_material(self):
        p = REPO / SNAPSHOT_PATH
        if not p.exists():
            self.skipTest(f"NOT CHECKED: no corpus at {SNAPSHOT_PATH}. This is a SKIP and not "
                          f"a pass — the reflexivity property is unverified on this machine.")
        a = audit(CorpusSnapshot.load(str(p)))
        self.assertFalse(a["refused"])
        self.assertEqual(a["matches"], 0,
                         f"common-ground's own material is in the corpus: {a['examples']}")
        self.assertTrue(clean(a, "matches"))


if __name__ == "__main__":
    unittest.main()
