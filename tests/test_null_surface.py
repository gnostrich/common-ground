"""THE NULL SURFACE: the interface is conversation, and nothing else is on it.

Two binary coordinates and one arrow were derived, built, shipped and controlled — assert /
brainstorm, retain, and the claim pullback. The derivation was sound and the premise was
wrong. The coordinates did not need a SURFACE, because they collapse into the physics:
objecthood collapses because every utterance is an authored record on the tape, and
persistence collapses because aging and K already decide what survives. A control that
pre-declares what the physics can discover is a second mechanism for one job.

SO THIS FILE IS MOSTLY ABOUT ABSENCE, and absence is the hardest thing to control. A deleted
feature comes back one convenience at a time — a toggle "just for testing", a mode flag "only
on the API" — and each step is small enough to look harmless. The controls below fail on the
SHAPE rather than on any particular name, so a rebuild under a new name still trips them.

THE TOMBSTONE. OI-41's planted control stays, and this is deliberate: the authorship-transfer
door is REMOVED, and the alarm on it REMAINS. Any code path conferring operator authorship on
medium-authored bytes is still RED, even though nothing today could reach it. An alarm on a
door that no longer exists costs one test and buys the guarantee that rebuilding the door is
loud rather than quiet.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "ui" / "index.html"

#: Names the deleted machinery went by. Checked as WORDS, so a partial rename does not sneak
#: past — but the shape controls below are the real guard, because a rebuild would rename.
GONE = ("retain", "brainstorm", "claimSentence", "override reading", "ACT:")

#: Modules that implemented the surface. Their absence is the deletion; their presence would
#: mean the machinery is dormant rather than gone, which the operator explicitly refused.
DELETED_MODULES = ("engine/mode.py", "engine/claim.py", "engine/posture.py")


def tracked() -> set[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return {p for p in out.splitlines() if p}


class TheMachineryIsDELETEDNotDormant(unittest.TestCase):
    """The operator ruled DELETE, not disable. Dormant machinery is a door left unlocked."""

    def test_the_modules_are_gone_from_the_tree(self):
        t = tracked()
        for m in DELETED_MODULES:
            with self.subTest(module=m):
                self.assertNotIn(m, t, f"{m} still tracked — dormant, not deleted")
                self.assertFalse((REPO / m).exists(), f"{m} still on disk")

    def test_nothing_imports_them(self):
        """An import of a deleted module is an ImportError, so this is belt and braces —
        but it catches a re-add under the same name before anything else does."""
        for rel in tracked():
            if not rel.endswith(".py"):
                continue
            text = (REPO / rel).read_text(errors="ignore")
            for mod in ("posture", "mode", "claim"):
                with self.subTest(file=rel, mod=mod):
                    self.assertNotRegex(text, rf"from \.{mod} import|from engine\.{mod} import")

    def test_they_are_ARCHIVED_not_merely_removed(self):
        """Nothing is ever lost to a supersession. The argument survives the code."""
        arch = REPO / "archive" / "design"
        self.assertTrue(arch.exists(), "the archive must exist before anything is superseded")
        body = "\n".join(p.read_text(errors="ignore") for p in arch.glob("*.md"))
        for m in DELETED_MODULES:
            self.assertIn(m, body, f"{m} was deleted without being archived")


class NoModeMachineryIsOnTheSURFACE(unittest.TestCase):
    """The fixture the operator asked for: a planted toggle, checkbox or ACT line = RED."""

    def setUp(self):
        self.page = PAGE.read_text()

    def test_no_deleted_control_is_named_on_the_page(self):
        for word in GONE:
            with self.subTest(word=word):
                self.assertNotIn(word, self.page, f"{word!r} is back on the surface")

    def test_the_page_carries_NO_checkbox_at_all(self):
        """SHAPE, not name. A rebuilt toggle would be renamed; it would still be a checkbox."""
        self.assertNotRegex(self.page, r'type\s*=\s*["\']checkbox["\']',
                            "a checkbox on this surface is a control pre-declaring what the "
                            "physics can discover")

    def test_the_only_SELECT_is_the_chart(self):
        """A chart is a coordinate of the corpus, not a mode of the operator's speech."""
        ids = re.findall(r'<select[^>]*id="([^"]+)"', self.page)
        self.assertEqual(ids, ["chart"], f"unexpected selector(s) on the surface: {ids}")

    def test_one_entry_box(self):
        self.assertEqual(len(re.findall(r"<textarea", self.page)), 1)

    def test_a_PLANTED_checkbox_would_be_caught(self):
        """The control's own control. Without this the regexes could match nothing."""
        planted = self.page.replace("<textarea", '<input id="x" type="checkbox"> mode\n<textarea', 1)
        self.assertRegex(planted, r'type\s*=\s*["\']checkbox["\']')

    def test_a_PLANTED_act_line_would_be_caught(self):
        self.assertIn("ACT:", "ACT: assert keep")


class TheRESPONSECarriesNoActAndNoMode(unittest.TestCase):
    """Absence at the wire, not only in the markup. A field the page ignores is still a field
    somebody will read, and a mode on the record is a mode in the design."""

    def test_the_perturbation_record_has_no_reading(self):
        from engine.perturb import Perturbation

        p = Perturbation()
        self.assertNotIn("reading", p.as_record())
        self.assertNotIn("reading", p.trace())

    def test_the_region_prompt_carries_no_ACT_grammar(self):
        """The medium was answering the ACT line on live traffic. Removing the reader without
        removing the instruction would leave the model spending tokens on a dead question."""
        from engine.region import REGION_SYSTEM, render_region

        self.assertNotIn("ACT:", REGION_SYSTEM)
        self.assertNotIn("keep-nothing", REGION_SYSTEM)

    def test_the_server_exposes_no_claim_endpoint(self):
        import ui.server as server

        body = Path(server.__file__).read_text()
        self.assertNotIn('path == "/claim"', body,
                         "the authorship-transfer endpoint must be removed, not disabled")


class TheAUTHORSHIPDoorIsRemovedAndTheAlarmREMAINS(unittest.TestCase):
    """OI-41's tombstone. The door is gone; a rebuild must be loud.

    This is the one control here that guards something no code can currently reach. That is
    the point: an alarm on a removed door costs one test and makes re-adding it noisy instead
    of quiet. Warrant rises by K-measurement or by authorship — a third arrow up the tier
    poset does not exist in the diagram, and no convenience may quietly introduce one.
    """

    def test_no_code_path_confers_operator_authorship_on_medium_bytes(self):
        """The shape: something that takes the medium's surface and stamps AUTHORSHIP on it."""
        hits = []
        for rel in tracked():
            if not rel.endswith(".py") or rel.startswith("tests/") or rel.startswith("archive/"):
                continue
            text = (REPO / rel).read_text(errors="ignore")
            for m in re.finditer(r"claimed_from|source_mode|authorship_transfer|CLAIM_TIER", text):
                hits.append(f"{rel}: {m.group(0)}")
        self.assertEqual(hits, [], f"an authorship-transfer path exists again: {hits[:5]}")

    def test_there_is_no_accept_or_approve_control_anywhere(self):
        page = PAGE.read_text().lower()
        for word in ("accept", "approve", "endorse"):
            with self.subTest(word=word):
                self.assertNotIn(f">{word}<", page)

    def test_the_alarm_can_FIRE(self):
        """Not vacuous: the pattern it hunts for must match when the shape is present."""
        self.assertRegex("c = make_claim(claimed_from='answer')", r"claimed_from")


if __name__ == "__main__":
    unittest.main()
