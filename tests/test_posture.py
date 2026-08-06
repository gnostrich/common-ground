"""THE UTTERANCE'S ACT, READ — and the inversion that makes reading safe.

Posture, retain and claim were toggles set before speaking. Read off the speaking they become
one more gated proposal: EXTRACTION tier, through the one inlet, wrong sometimes, correctable.

THE SAFETY ARGUMENT IS THE INVERSION. Everywhere else an unknown mode defaults to ASSERT,
because defaulting the other way would strip warrant from something the operator meant to
stand behind. When the machine READS rather than being told, the risk reverses: a misread that
invents a claim confers authorship nobody asserted. When unsure whether you claimed, assume
you didn't.
"""

import unittest

from engine.mode import ASSERT, BRAINSTORM
from engine.posture import (ACT_GRAMMAR, ACTS, CLAIM_ACT, CONSERVATIVE, DISCARD, EXPLORE_ACT,
                            KEEP, Reading, correct, parse, resolve_claim)


class ItReadsADeclaredTokenNeverProse(unittest.TestCase):

    def test_the_act_vocabulary_is_closed(self):
        self.assertEqual(("assert", "explore", "claim-of"), ACTS)

    def test_each_declared_act_is_read(self):
        self.assertEqual("explore", parse("ACT: explore keep-nothing").act)
        self.assertEqual("assert", parse("ACT: assert keep").act)
        self.assertEqual(7, parse("ACT: claim-of 7 keep").claim_index)

    def test_PROSE_that_sounds_like_a_claim_reads_nothing(self):
        # A reading inferred from the shape of a sentence would be a fluency judgement
        # steering warrant. The token is the only channel.
        for prose in ("that's mine, definitely keep it",
                      "yes exactly — I assert that",
                      "claim that one please"):
            r = parse(prose)
            self.assertEqual(EXPLORE_ACT, r.act, prose)
            self.assertEqual(BRAINSTORM, r.mode)

    def test_the_module_holds_no_similarity_machinery(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "posture.py").read_text()
        for banned in ("difflib", "SequenceMatcher", ".lower().split", "Counter("):
            self.assertNotIn(banned, src)


class TheConservativeDirectionINVERTS(unittest.TestCase):
    """When unsure whether you claimed, assume you didn't."""

    def test_the_conservative_reading_is_explore_keep_nothing(self):
        self.assertEqual((EXPLORE_ACT, DISCARD), CONSERVATIVE)

    def test_a_PLANTED_AMBIGUOUS_utterance_reads_conservatively_and_SAYS_SO(self):
        # The planted control: ambiguity must produce a displayed reading, not a silent guess.
        for raw in ("", "no act line at all", "ACT: assert\nACT: claim-of 3", "ACT: claim-of"):
            r = parse(raw)
            self.assertEqual(EXPLORE_ACT, r.act)
            self.assertEqual(DISCARD, r.persistence)
            self.assertTrue(r.reason, "a default nobody is told about is a reading")
            self.assertIn("reading this as", r.render())

    def test_ambiguity_never_resolves_toward_claiming(self):
        for raw in ("ACT: claim-of", "ACT: assert\nACT: explore", "garbage"):
            self.assertNotEqual(CLAIM_ACT, parse(raw).act)
            self.assertFalse(parse(raw).retains)

    def test_the_inversion_is_opposite_to_the_TOLD_default(self):
        # engine.mode: an unknown TOLD mode is ASSERT. An unread act is EXPLORE. The two
        # defaults point opposite ways on purpose, and both are the safe direction for their
        # own failure mode.
        from engine.mode import normalize
        self.assertEqual(ASSERT, normalize("garbage"))
        self.assertEqual(BRAINSTORM, parse("garbage").mode)


class MisreadsAreVISIBLE(unittest.TestCase):

    def test_every_reading_renders_a_line_for_the_top_of_the_response(self):
        for raw in ("ACT: explore keep-nothing", "ACT: assert keep", "ACT: claim-of 4 keep", ""):
            self.assertTrue(parse(raw).render().startswith("reading this as:"))

    def test_the_line_states_both_coordinates(self):
        self.assertIn("keeping nothing", parse("ACT: explore keep-nothing").render())
        self.assertIn("keeping it", parse("ACT: assert keep").render())

    def test_a_reading_always_carries_its_reason(self):
        for raw in ("ACT: assert keep", "", "ACT: claim-of"):
            self.assertTrue(parse(raw).reason)


class ClaimOfResolvesToDISPLAYEDBytesOrVOIDS(unittest.TestCase):

    def test_a_resolvable_claim_returns_the_displayed_bytes_verbatim(self):
        text = "the cone is positive under composition"
        surface, void = resolve_claim(parse("ACT: claim-of 2 keep"), {2: text})
        self.assertEqual(text, surface)
        self.assertEqual("", void)

    def test_an_unresolvable_index_VOIDS_rather_than_reconstructing(self):
        # A pullback onto a reconstruction would land on something the operator never read.
        surface, void = resolve_claim(parse("ACT: claim-of 9 keep"), {1: "a", 2: "b"})
        self.assertEqual("", surface)
        self.assertIn("VOID", void)

    def test_an_empty_displayed_sentence_VOIDS(self):
        self.assertEqual("", resolve_claim(parse("ACT: claim-of 1 keep"), {1: "  "})[0])

    def test_a_non_claim_reading_resolves_to_nothing(self):
        self.assertEqual(("", "not a claim"),
                         resolve_claim(parse("ACT: explore keep-nothing"), {1: "x"}))


class ACorrectionRestampsWithAnERATRAIL(unittest.TestCase):

    def test_the_prior_reading_is_KEPT_not_overwritten(self):
        prior = parse("ACT: explore keep-nothing", era="e1")
        fixed = correct(prior, parse("ACT: assert keep", era="e2"))
        self.assertEqual("assert", fixed.act)
        self.assertEqual(1, len(fixed.superseded))
        self.assertEqual("explore", fixed.superseded[0]["act"])

    def test_the_trail_accumulates_across_corrections(self):
        a = parse("ACT: explore keep-nothing", era="e1")
        b = correct(a, parse("ACT: assert keep", era="e2"))
        c = correct(b, parse("ACT: claim-of 3 keep", era="e3"))
        self.assertEqual(2, len(c.superseded))
        self.assertEqual(["explore", "assert"], [s["act"] for s in c.superseded])

    def test_the_correction_says_it_was_corrected(self):
        fixed = correct(parse("ACT: explore keep-nothing"), parse("ACT: assert keep"))
        self.assertIn("corrected by the operator", fixed.reason)

    def test_the_era_travels(self):
        self.assertEqual("e9", correct(parse("ACT: explore keep-nothing"),
                                       parse("ACT: assert keep", era="e9")).era)


class TheLocksAreUnchanged(unittest.TestCase):

    def test_a_read_claim_still_enters_through_the_pullback(self):
        # The reading decides how an utterance is TREATED. It confers nothing by itself: the
        # claim still needs displayed bytes and a source record.
        from engine.claim import claim
        r = parse("ACT: claim-of 1 keep")
        surface, _ = resolve_claim(r, {1: "the cone is positive"})
        c = claim(surface, "english", claimed_from="rec-3", source_mode=r.mode)
        self.assertEqual("AUTHORSHIP", c.as_record()["tier"])
        self.assertEqual("rec-3", c.claimed_from)

    def test_a_reading_cannot_manufacture_a_claim_without_bytes(self):
        from engine.claim import claim
        surface, void = resolve_claim(parse("ACT: claim-of 99 keep"), {1: "x"})
        self.assertTrue(void)
        with self.assertRaises(ValueError):
            claim(surface, "english", claimed_from="rec-3")


class TheGrammarLineIsCodomainSyntax(unittest.TestCase):
    """The razor: one sentence, stating the output syntax, no policy."""

    def test_it_states_the_form_and_nothing_else(self):
        self.assertIn("ACT:", ACT_GRAMMAR)
        for banned in ("should", "prefer", "remember", "important", "carefully"):
            self.assertNotIn(banned, ACT_GRAMMAR.lower())

    def test_it_is_one_sentence(self):
        self.assertEqual(1, ACT_GRAMMAR.count("."))



class TheREADReachesTheWINDOW(unittest.TestCase):
    """The parser was green for a release while the reading was dead on the wire.

    `parse()` read `ACT: explore` correctly every time. The perturbation stored it correctly
    every time. And the window reported "the medium emitted no ACT line" on EVERY request ever
    served — because the reading lived on `Perturbation.trace()` and `ui/server._reading_of`
    reads `Perturbation.as_record()`. Two halves that never met, with a green suite on both.

    The conservative direction (OI-43) is what hid it: unread ACT falls to explore/keep-nothing,
    which is right when nothing was said and silently WRONG when `ACT: assert` was. The operator
    would have been downgraded on every assertion and told the medium had said nothing.

    So these controls run at the layer the defect lived at — the record the consumer reads, and
    the HTTP response it becomes — never at the parser, which was never the problem.
    """

    def test_the_reading_is_on_the_record_the_window_reads(self):
        from engine.perturb import Perturbation

        p = Perturbation()
        p.reading = parse("ACT: assert\nb0 -bears_on-> e1")
        rec = p.as_record()
        self.assertIn("reading", rec, "as_record is what ui/server._reading_of consults")
        self.assertEqual(rec["reading"]["act"], "assert")

    def test_the_record_and_the_trace_AGREE(self):
        """Two emitters of one fact is the shape that let them diverge unnoticed."""
        from engine.perturb import Perturbation

        for line in ("ACT: assert", "ACT: explore", "ACT: claim-of 3", ""):
            with self.subTest(line=line):
                p = Perturbation()
                p.reading = parse(line)
                self.assertEqual(p.as_record()["reading"], p.trace()["reading"])

    def test_the_SERVED_response_carries_the_medium_s_act(self):
        """END TO END, over HTTP, with a transport that says `ACT: assert`. This is the exact
        assertion that would have failed for the whole release."""
        import json
        import threading
        import urllib.request
        from http.server import HTTPServer

        import ui.current as current
        from ui.server import Handler

        def _fake(system, user):
            return "ACT: assert\nb0 -bears_on-> e1", {"model": "control/x", "cost": 0.0}

        real = current._region_transport
        current._region_transport = lambda key=None: _fake
        server = HTTPServer(("127.0.0.1", 0), Handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            body = json.dumps({"question": "is the cone positive",
                               "chart": "english"}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.server_address[1]}/ask", data=body,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.load(r)
        finally:
            server.shutdown()
            current._region_transport = real
        reading = out.get("reading") or {}
        self.assertNotIn("emitted no ACT line", reading.get("reason", ""),
                         f"the medium said ACT: assert and the window did not hear it: {reading}")
        self.assertEqual(reading.get("act"), "assert", reading)



if __name__ == "__main__":
    unittest.main()


class TheGrammarIsCaseEXACT(unittest.TestCase):
    """Resolve-or-void applied to case, rather than an exemption argued for folding.

    An earlier version matched case-insensitively and folded the token to canonicalise it. The
    referee sweep refused it — folding is folding whatever it is folding — and the fix was to
    remove the fold, not to argue for it. A token in the wrong case does not match and reads
    conservatively, which is the same discipline every other resolution here follows.
    """

    def test_the_declared_lowercase_token_matches(self):
        self.assertEqual("assert", parse("ACT: assert keep").act)

    def test_a_miscased_token_reads_CONSERVATIVELY_rather_than_being_folded(self):
        for raw in ("ACT: ASSERT keep", "ACT: Claim-Of 3 keep", "ACT: Explore KEEP"):
            r = parse(raw)
            self.assertEqual(EXPLORE_ACT, r.act, raw)
            self.assertFalse(r.retains, raw)

    def test_the_module_folds_no_case_at_all(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "posture.py").read_text()
        body = src[src.index("def parse("):]
        self.assertNotIn(".lower()", body)
        self.assertNotIn(".casefold()", body)
