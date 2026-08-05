"""The page states numbers, so the page is a claim, and every claim here needs a control.

An earlier version of this page was assembled by hand from figures I had in front of me at
the time. It was accurate exactly once, had no way of saying so afterwards, and carried a
coverage caveat that had been false since the Python chart landed. The renderer replaces that
with something that reads every figure off disk — and these controls plant against the three
ways a page like this lies:

  * it shows a stale number as though it were current,
  * a source it could not read vanishes instead of being reported,
  * it truncates the corpus and does not say that it did.

The last one is the subtle one. A search box over a silently-cut index returns "no match"
for text that is in the corpus, and "no match" is indistinguishable from "not there".
"""

from __future__ import annotations

import json
import re
import unittest

from engine.atlas import NU_BUDGET, Atlas, gather, payload, render, render_with_corpus
from engine.corpus_state import CorpusSnapshot, SlotRecord


def _snapshot(rows) -> CorpusSnapshot:
    snap = CorpusSnapshot()
    for sid, chart, ctype, nu in rows:
        snap.slots[sid] = SlotRecord(slot=sid, chart=chart, type=ctype, nu=nu,
                                     value="T", confidence=1.0, tier="EXTRACTION", docs=())
    return snap


class EveryFigureComesFromDisk(unittest.TestCase):
    def test_no_placeholder_survives_a_render(self):
        """A leftover `{{TOKEN}}` is a figure the renderer forgot to fill, and it would ship
        as literal braces on the page rather than as an error."""
        atlas = Atlas(slots=3, by_chart={"english": 2, "lean": 1}, floor="GAP", asked=10,
                      arrows=4, none=6, calls=2, cost=0.01)
        got = render_with_corpus(atlas, _snapshot([("a" * 64, "english", "assert", "x")]))
        self.assertEqual(re.findall(r"\{\{\w+\}\}", got), [])

    def test_the_readout_carries_the_numbers_it_was_given(self):
        atlas = Atlas(slots=69446, asked=2067, arrows=1126, none=941, calls=173,
                      cost=0.460426, floor="GAP")
        got = render(atlas)
        self.assertIn("69,446", got)
        self.assertIn("2,067", got)
        self.assertIn("1,126", got)
        self.assertIn("0.460", got)
        self.assertIn("46%", got, "none-rate is computed from asked, not carried separately")

    def test_planted_a_changed_journal_changes_the_page(self):
        """PLANTED: the failure mode of a hand-written page — same template, new numbers,
        page unchanged."""
        first = render(Atlas(slots=10, asked=4, arrows=2))
        second = render(Atlas(slots=10, asked=8, arrows=7))
        self.assertNotEqual(first, second)
        self.assertIn("7", second)


class TheFloorNoteFollowsTheLoopCount(unittest.TestCase):
    """The one figure on this page that describes the ENGINE rather than the corpus.

    The template carried "the floor is a gap because no cycle has closed yet" as a flat
    sentence. It was true for weeks, and then a cycle closed — the single most load-bearing
    event this engine can report — and the page would have gone on denying it. Same defect
    as the coverage caveat, so it gets the same control.
    """

    def test_no_loops_says_gap(self):
        got = render(Atlas(slots=10, loops=0))
        self.assertIn("no cycle has closed yet", got)
        self.assertNotIn("A cycle has closed", got)

    def test_planted_one_loop_flips_the_sentence(self):
        """PLANTED: the transition the flat sentence could not survive."""
        got = render(Atlas(slots=10, loops=1, fibers=494))
        self.assertIn("A cycle has closed", got)
        self.assertIn("494", got)
        self.assertNotIn("no cycle has closed yet", got)

    def test_the_note_never_claims_a_promotion(self):
        got = render(Atlas(slots=10, loops=7, fibers=100))
        self.assertIn("nothing is promoted", got)

    def test_plural_agrees_with_the_count(self):
        self.assertIn("1 loop across", render(Atlas(loops=1, fibers=2)))
        self.assertIn("3 loops across", render(Atlas(loops=3, fibers=2)))


class AMissingSourceIsReportedNotDropped(unittest.TestCase):
    def test_gather_on_an_empty_tree_names_every_source_it_could_not_read(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "runs").mkdir()
            atlas = gather(Path(d))
        joined = " ".join(atlas.missing)
        for expected in ("snapshot", "journal", "pool", "census"):
            self.assertIn(expected, joined,
                          f"a missing {expected} must be REPORTED — a section that vanishes "
                          f"looks the same as a section whose number is zero")

    def test_the_missing_list_reaches_the_page(self):
        atlas = Atlas(missing=["no candidate pool — run `proposerd.py build-pool`"])
        self.assertIn("no candidate pool", render(atlas))

    def test_an_empty_atlas_says_no_corpus_rather_than_showing_zero_bars(self):
        got = render(Atlas())
        self.assertIn("No corpus is loaded", got)
        self.assertIn("build-snapshot", got)

    def test_no_arrows_is_stated_as_a_state_not_left_blank(self):
        got = render(Atlas(slots=5, by_chart={"english": 5}))
        self.assertIn("No arrow has been found yet", got)
        self.assertIn("none", got)


class TruncationIsMarkedNeverSilent(unittest.TestCase):
    """A search over a silently-cut index answers "no match" for text that IS in the corpus,
    and that answer is indistinguishable from the true one."""

    def test_a_long_surface_is_cut_and_marked(self):
        long_nu = "positivity " * 200
        data = payload(Atlas(), _snapshot([("s" * 64, "english", "assert", long_nu)]))
        text = data["slots"][0][3]
        self.assertTrue(text.endswith("…"), "a cut surface must SAY it was cut")
        self.assertLessEqual(len(text), NU_BUDGET + 1)
        self.assertEqual(data["truncated"], 1)

    def test_a_short_surface_is_untouched_and_uncounted(self):
        data = payload(Atlas(), _snapshot([("s" * 64, "english", "assert", "the cone")]))
        self.assertEqual(data["slots"][0][3], "the cone")
        self.assertEqual(data["truncated"], 0)

    def test_the_truncated_count_reaches_the_page(self):
        atlas = Atlas(slots=1)
        long_nu = "x" * (NU_BUDGET + 50)
        got = render_with_corpus(atlas, _snapshot([("s" * 64, "english", "assert", long_nu)]))
        self.assertIn(str(NU_BUDGET), got)
        self.assertRegex(got, r"1</?[a-z]*>? of them|1 of them",
                         "the page must state HOW MANY surfaces were cut")

    def test_arrows_are_never_truncated(self):
        """Reading half a bridge is not reading it, so the budget does not apply to arrows."""
        long_side = "funding rate " * 100
        atlas = Atlas(arrow_records=[{
            "src_chart": "english", "dst_chart": "python", "answer": "same_claim",
            "evidence": f"SOURCE (english): {long_side}TARGET (python): {long_side}"}])
        data = payload(atlas, _snapshot([]))
        src, dst = data["arrows"][0][3], data["arrows"][0][4]
        self.assertNotIn("…", src)
        self.assertGreater(len(src), NU_BUDGET)
        self.assertGreater(len(dst), NU_BUDGET)


class ThePageIsSafeToPublish(unittest.TestCase):
    def test_chart_tags_are_stripped_from_every_surface(self):
        r"""The \x01 chart tag is part of the ADDRESS, not part of what the author wrote.
        It also breaks the markup, which is how it was found."""
        data = payload(Atlas(), _snapshot([("s" * 64, "lean", "assert",
                                            "\x01lean\x01theorem t : True")]))
        self.assertNotIn("\x01", data["slots"][0][3])
        self.assertIn("theorem t : True", data["slots"][0][3])

    def test_planted_markup_in_a_surface_cannot_escape_into_the_page(self):
        """PLANTED: a corpus containing HTML. The corpus is somebody's real material and is
        not required to be inert.

        Note what "safe" means here, because the first version of this control asserted the
        wrong thing. The hostile string DOES appear in the page — inside the JSON payload,
        as data, which is the whole point of embedding a corpus. What must hold is narrower
        and stronger: it cannot escape its container. So the page is split at the payload
        boundary and each half is checked for what actually applies to it.
        """
        hostile = '</script><img src=x onerror="alert(1)">'
        atlas = Atlas(slots=1, examples=[{"src_chart": "english", "dst_chart": "lean",
                                          "answer": "same_claim", "evidence": hostile}])
        got = render_with_corpus(atlas, _snapshot([("s" * 64, "english", "assert", hostile)]))
        blob = re.search(r'<script id="corpus" type="application/json">(.*?)</script>',
                         got, re.S).group(1)
        markup = got.replace(blob, "")

        # In the JSON payload: inert. `</` is escaped, so the tag cannot be closed early.
        self.assertIn(r"<\/script>", blob)
        self.assertNotIn("</script>", blob)

        # In the server-rendered markup: escaped, so it renders as text and not as a tag.
        self.assertNotIn("<img src=x", markup)
        self.assertIn("&lt;/script&gt;&lt;img", markup)

    def test_planted_the_escape_is_load_bearing(self):
        """Without the `</` escape the payload WOULD break out. Shown, not assumed."""
        naive = json.dumps({"nu": '</script><img src=x>'})
        self.assertIn("</script>", naive, "an unescaped dump closes the tag — this is the "
                                          "defect the escape in render_with_corpus prevents")

    def test_the_embedded_json_parses_back(self):
        atlas = Atlas(slots=1, arrow_records=[{
            "src_chart": "english", "dst_chart": "go", "answer": "refines",
            "evidence": "SOURCE (english): a </script> b TARGET (go): c"}])
        got = render_with_corpus(atlas, _snapshot([("s" * 64, "english", "assert", "hi")]))
        blob = re.search(r'<script id="corpus" type="application/json">(.*?)</script>',
                         got, re.S).group(1)
        parsed = json.loads(blob.replace("<\\/", "</"))
        self.assertEqual(len(parsed["slots"]), 1)
        self.assertEqual(len(parsed["arrows"]), 1)


class ExamplesAreSpreadAcrossPairs(unittest.TestCase):
    def test_the_examples_are_not_all_from_one_chart_pair(self):
        """Taking the last N outright showed eight rows from whichever pair the daemon was
        working through, which reads as though the engine bridges only one thing."""
        records = ([{"kind": "ask", "answer": "same_claim", "src_chart": "english",
                     "dst_chart": "python", "evidence": f"SOURCE a{i} TARGET b{i}"}
                    for i in range(40)]
                   + [{"kind": "ask", "answer": "same_claim", "src_chart": "english",
                       "dst_chart": "lean", "evidence": "SOURCE x TARGET y"}])
        from engine.atlas import _pick_examples

        picked = _pick_examples(records)
        pairs = {(r["src_chart"], r["dst_chart"]) for r in picked}
        self.assertIn(("english", "lean"), pairs,
                      "the rare pair must survive; taking the tail would have dropped it")


if __name__ == "__main__":
    unittest.main()
