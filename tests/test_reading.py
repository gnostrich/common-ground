"""The reading surface is a VIEW, and the two ways a view can lie are both controlled.

A surface can show something the measurement did not contain, or drop a warning it did. Both
go RED here. Everything else in this file is about the surface being DERIVED from what the
object says a response is, rather than being a summary somebody wrote.
"""

from __future__ import annotations

import unittest

from engine import reading
from engine.reading import Mover, Reading, check_faithful, check_wording, knee, phrasings, read


class _Step:
    def __init__(self, src_chart, dst_chart):
        self.src_chart, self.dst_chart = src_chart, dst_chart


class _Moved:
    def __init__(self, slot, chart, nu, shift, hops, contested=False, tier="EXTRACTION",
                 path=(), weakest_tier=""):
        self.slot, self.chart, self.nu, self.shift = slot, chart, nu, shift
        self.hops, self.contested, self.tier, self.path = hops, contested, tier, path
        self.weakest_tier = weakest_tier


class _Att:
    def __init__(self, attachment, declared=6, objects=59):
        self.attachment = attachment
        self._d, self._o = declared, objects

    def trace(self):
        return {"corpus_objects": self._o, "declared_in": self._d}


class _Attach:
    def __init__(self, kind, nu, chart):
        self.kind, self.dst_nu, self.dst_chart = kind, nu, chart


class _Rel:
    def __init__(self, moved, floor_status="GAP — undefined because unmeasured"):
        self.moved, self.floor_status = moved, floor_status


class _Compiled:
    def __init__(self, attachment=None, relaxation=None, compiled="FULL TRACE HERE"):
        self.attachment, self.relaxation, self.compiled = attachment, relaxation, compiled


def _typical():
    att = _Att([_Attach("same_claim", "\x01py\x01the decoder is absent", "python"),
                _Attach("bears_on", "\x01en\x01cloud path imports no renderer", "english")])
    moved = [
        _Moved("a" * 64, "english", "\x01en\x01no renderer on the cloud path", 0.90, 2,
               path=(_Step("english", "python"), _Step("python", "lean")),
               weakest_tier="EXTRACTION"),
        _Moved("b" * 64, "python", "\x01py\x01decoder import removed", 0.85, 0),
        # Contested AND high-shift, so it survives the knee — otherwise the dropped-mark
        # control below would pass vacuously, having nothing to drop.
        _Moved("c" * 64, "lean", "\x01lean\x01theorem cone_pos", 0.84, 1,
               contested=True, path=(_Step("lean", "english"),)),
    ]
    return _Compiled(attachment=att, relaxation=_Rel(moved))


class LayerOneComesFirstBecauseEverythingElseRestsOnIt(unittest.TestCase):
    def test_corresponds_and_bears_on_render_distinctly(self):
        r = read(_typical())
        self.assertEqual(len(r.entered_corresponds), 1)
        self.assertEqual(len(r.entered_bears_on), 1)
        body = r.render()
        p = phrasings()
        self.assertIn(p["layer1"]["corresponds"], body)
        self.assertIn(p["layer1"]["bears_on"], body)

    def test_it_is_rendered_above_what_answered(self):
        body = read(_typical()).render()
        p = phrasings()
        self.assertLess(body.index(p["layer1"]["heading"]), body.index(p["layer2"]["heading"]))

    def test_planted_zero_attachments_gives_the_declined_trace_never_silence(self):
        c = _Compiled(attachment=_Att([], declared=6, objects=59), relaxation=None)
        r = read(c)
        self.assertIn("consulted", r.declined.lower())
        self.assertIn("59", r.declined)
        self.assertIn("decline, not a filter", r.declined)

    def test_the_chart_tag_is_stripped_for_reading_only(self):
        r = read(_typical())
        self.assertFalse(any(nu.startswith("\x01") for nu, _ in r.entered_corresponds))
        self.assertTrue(r.movers[0].slot.startswith("a"),
                        "the SLOT is untouched; only the display string is trimmed")


class LayerTwoRanksPropagationAboveProximity(unittest.TestCase):
    def test_a_hop_reached_mover_outranks_direct_touch_at_equal_shift(self):
        moved = [_Moved("d" * 64, "python", "direct", 0.5, 0),
                 _Moved("e" * 64, "english", "reached", 0.5, 2,
                        path=(_Step("english", "python"),))]
        r = read(_Compiled(relaxation=_Rel(moved)))
        self.assertEqual(r.movers[0].slot, "e" * 64,
                         "propagation is the field's contribution; direct touch is proximity")

    def test_each_mover_says_exactly_one_of_direct_or_reached(self):
        p = phrasings()
        body = read(_typical()).render()
        self.assertIn(p["layer2"]["direct"], body)
        self.assertIn(p["layer2"]["reached"], body)

    def test_the_path_renders_as_chart_to_chart_hops(self):
        r = read(_typical())
        self.assertEqual(r.movers[0].path, "english → python → lean")

    def test_a_contested_mover_carries_a_visible_mark(self):
        r = read(_typical())
        contested = [m for m in r.movers if m.contested]
        if contested:
            self.assertIn(phrasings()["layer2"]["contested"], r.render())

    def test_planted_no_movers_says_so_rather_than_rendering_an_empty_list(self):
        r = read(_Compiled(relaxation=_Rel([])))
        self.assertIn(phrasings()["layer2"]["none"], r.render())


class TheCutIsAKneeNotACount(unittest.TestCase):
    def test_it_cuts_at_a_dominant_drop(self):
        self.assertEqual(knee([0.9, 0.85, 0.8, 0.02, 0.01]), 3)

    def test_planted_a_dominant_but_tiny_gap_is_not_a_cliff(self):
        """[0.90, 0.85, 0.84]: the first drop dominates the second five to one, and as a
        fraction of the range it looks just like a real cliff. It is not one — 0.84 moved."""
        self.assertEqual(knee([0.90, 0.85, 0.84]), 3)

    def test_planted_a_flat_distribution_is_one_population_and_all_of_it_shows(self):
        """Not a failure to cut — the honest reading of a list with no gap in it."""
        self.assertEqual(knee([0.5, 0.5, 0.5, 0.5]), 4)

    def test_two_real_movers_and_forty_do_not_both_show_five(self):
        few = knee([0.9, 0.88, 0.01])
        many = knee([1.0 - i * 0.001 for i in range(40)] + [0.0001])
        self.assertEqual(few, 2)
        self.assertEqual(many, 40)

    def test_there_is_no_k_constant(self):
        for name in ("TOP_K", "MAX_MOVERS", "SHOW_N", "K"):
            self.assertFalse(hasattr(reading, name), f"{name} is a free constant")


class LayerThreeRendersOnlyWhatIsTrue(unittest.TestCase):
    def test_contested_ground_is_named_when_it_exists(self):
        r = read(_typical())
        self.assertTrue(any("contested ground" in l for l in r.field_lines))

    def test_planted_no_contested_movers_means_no_contested_line(self):
        moved = [_Moved("d" * 64, "python", "quiet", 0.5, 1, path=(_Step("python", "en"),))]
        r = read(_Compiled(relaxation=_Rel(moved)))
        self.assertFalse(any("contested ground" in l for l in r.field_lines),
                         "a line that is always present stops being read")

    def test_the_weakest_link_is_the_minimum_warrant_the_answer_rests_on(self):
        moved = [_Moved("d" * 64, "python", "strong", 0.9, 1, weakest_tier="CI_RECEIPT",
                        path=(_Step("python", "en"),)),
                 _Moved("e" * 64, "lean", "weak", 0.8, 2, weakest_tier="EXTRACTION",
                        path=(_Step("lean", "en"),))]
        r = read(_Compiled(relaxation=_Rel(moved)))
        line = next(l for l in r.field_lines if "Weakest link" in l)
        self.assertIn("EXTRACTION", line)

    def test_the_floor_is_always_stated_when_the_trace_has_one(self):
        r = read(_typical())
        self.assertTrue(any(l.startswith("Floor:") for l in r.field_lines))

    def test_strength_is_derived_so_the_reader_need_not_read_tiers(self):
        p = phrasings()
        faint = read(_Compiled(relaxation=_Rel(
            [_Moved("d" * 64, "python", "only touched", 0.2, 0)])))
        self.assertEqual(faint.strength, p["layer3"]["faint"])
        firm = read(_Compiled(relaxation=_Rel(
            [_Moved("e" * 64, "lean", "reached", 0.9, 2, weakest_tier="CI_RECEIPT",
                    path=(_Step("lean", "en"),))])))
        self.assertEqual(firm.strength, p["layer3"]["firm"])


class TheSurfaceIsFaithfulToTheTrace(unittest.TestCase):
    def test_a_clean_reading_has_no_violations(self):
        c = _typical()
        self.assertEqual(check_faithful(read(c), c), [])

    def test_planted_a_claim_not_in_the_trace_is_red(self):
        c = _typical()
        r = read(c)
        r.movers.append(Mover(nu="invented", chart="english", shift=0.4, hops=1,
                              slot="z" * 64))
        out = check_faithful(r, c)
        self.assertTrue(out)
        self.assertIn("not in the trace", out[0])

    def test_planted_a_dropped_contested_mark_is_red(self):
        c = _typical()
        r = read(c)
        for m in r.movers:
            m.contested = False
        out = check_faithful(r, c)
        self.assertTrue(any("dropped a CONTESTED mark" in x for x in out))

    def test_planted_an_invented_attachment_is_red(self):
        c = _typical()
        r = read(c)
        r.entered_bears_on.append(("made up", "lean"))
        self.assertTrue(any("attachment" in x for x in check_faithful(r, c)))


class NothingIsDeletedTheTraceIsCollapsedNotDropped(unittest.TestCase):
    def test_the_full_trace_is_present_behind_the_toggle(self):
        c = _typical()
        body = read(c).render()
        self.assertIn(phrasings()["trace_toggle"], body)
        self.assertIn(c.compiled, body)


class Gate10AppliesToTheWording(unittest.TestCase):
    def test_the_pinned_phrasings_claim_no_mechanism(self):
        self.assertEqual(check_wording(), [])

    def test_planted_a_mental_state_phrasing_is_caught(self):
        p = phrasings()
        p["layer2"]["heading"] = "What the field believes:"
        out = check_wording(p)
        self.assertTrue(out)
        self.assertIn("claims a mechanism", out[0])

    def test_planted_retrieval_vocabulary_is_caught(self):
        p = phrasings()
        p["layer2"]["heading"] = "Best match:"
        self.assertTrue(check_wording(p))

    def test_the_phrasings_are_pinned_on_disk_with_a_revision(self):
        p = phrasings()
        self.assertIn("revision", p)
        self.assertIn("pinned", p)
        for section in ("layer1", "layer2", "layer3"):
            self.assertTrue(p[section], f"{section} must carry its wording")


if __name__ == "__main__":
    unittest.main()
