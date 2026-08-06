"""OI-19, MECHANIZED: what the operator typed is what the LM reads. In bytes.

OI-19 says operator input is an EXTERNAL FIELD TERM — never normalized, never addressed as a
stage, never objectified into the category. The constitution named the violation in prose
(`input-nu as pipeline`) and shipped without a control, so the prose was the only thing
holding it. This file is the control.

WHY BYTES AND NOT BEHAVIOUR. Every other faithfulness property in this engine is checked by
running something and reading a verdict. This one cannot be: a normalized bias produces a
perfectly well-formed region, a perfectly plausible set of arrows, and an answer that reads
correctly — it just answers a question the operator did not ask. Case, emphasis, punctuation
and repetition are the operator's, and nu deliberately destroys all four because that is what
nu is FOR: it is the identity rule, and identity must be insensitive to exactly those things.
The defect is not that nu is wrong. It is that nu's output was put on the wire.

THE TWO CHANNELS. A perturbation makes two LM calls and the typed text has a different job in
each. The PROPOSE call carries the bias as object `[0|bias]` in the region diagram; the RENDER
call carries it as the BOUNDARY CONDITION over the compiled field. Both are the operator
speaking. Both are checked here, at the transcript, which is the last place before the socket.

ESCAPING IS NOT NORMALIZATION. The object line is a line, so a newline in the typed text must
be escaped or it would end the object. That escaping is invertible and the control inverts it
before comparing — which is the difference between a format and a filter, and is the reason
the comparison below is on `unescape_nu(payload)` rather than on the raw line.
"""

from __future__ import annotations

import unittest

from engine.corpus_state import CorpusSnapshot, SlotRecord
from engine.correspondence import Correspondence
from engine.normalize import address
from engine.perturb import perturb
from engine.region import BIAS_CHART, label, unescape_nu
from engine.transcript import CURRENT as TRANSCRIPT, start
from engine.types import WarrantTier

#: Every hostile property nu removes, in one string: mixed case, doubled space, a terminal
#: question mark, an exclamation, and a unicode dash. If any of these survives to the wire the
#: bias is the operator's; if none does, the bias is the addresser's.
TYPED = "Does Certified POSITIVITY hold  for the Bernstein basis? I think NOT — why?"


def _corpus(n: int = 12) -> CorpusSnapshot:
    slots, arrows, docs = {}, [], {}
    for i in range(n):
        chart = "english" if i % 2 == 0 else "python"
        sid, nu = address(chart, f"claim number {i} about the cone", "assert")
        slots[sid] = SlotRecord(slot=sid, chart=chart, type="assert", nu=nu,
                                value="true", confidence=1.0, tier="EXTRACTION",
                                docs=(f"repo||dir/file{i // 4}.md",))
        docs[i] = sid
    for i in range(0, n - 1, 2):
        arrows.append(Correspondence(
            src_chart="english", src_slot=docs[i], dst_chart="python", dst_slot=docs[i + 1],
            kind="same_claim", tier=WarrantTier.EXTRACTION, proposer="lm",
            prompt_hash="t", evidence=("seed",)))
    return CorpusSnapshot(slots=slots, arrows=tuple(arrows))


def _transport(reply: str = ""):
    def t(system: str, user: str):
        return reply, {"model": "control"}
    return t


def bias_payload(user: str) -> str:
    """The `[0|bias]` object's text as it went out, unescaped back to the typed bytes.

    Reads the WIRE, not the region object. A control that asked the `Region` what its bias
    member holds would pass on a renderer that dropped it — the map-not-territory failure in
    its purest form, and the exact shape that let `/seed` ship broken under a green suite.
    """
    head = f"[{label(BIAS_CHART, 0)}] "
    for line in user.splitlines():
        if line.startswith(head):
            return unescape_nu(line[len(head):])
    raise AssertionError(f"no {head.strip()} object on the wire at all")


class TheOperatorsBytesReachTheProposeCall(unittest.TestCase):
    """Channel one: the region diagram. This is the channel that was violated."""

    def setUp(self):
        start()
        perturb(TYPED, _corpus(), _transport())
        calls = [c for c in TRANSCRIPT.calls if c.port == "propose"]
        self.assertEqual(len(calls), 1, "the propose call must be recorded, exactly once")
        self.wire = calls[0].user

    def test_the_bias_object_carries_the_typed_bytes(self):
        self.assertEqual(bias_payload(self.wire), TYPED,
                         "OI-19: the operator's input reaches the medium as typed, or the "
                         "medium is answering the addresser's paraphrase of the question")

    def test_case_survives(self):
        self.assertIn("POSITIVITY", self.wire)
        self.assertIn("NOT", self.wire)

    def test_punctuation_and_spacing_survive(self):
        payload = bias_payload(self.wire)
        self.assertTrue(payload.endswith("?"), "a terminal question mark is the speech act")
        self.assertIn("  ", payload, "doubled space is the operator's, not noise to collapse")
        self.assertIn("—", payload, "a unicode dash is content")

    def test_the_nu_is_NOT_what_went_out(self):
        """The negative twin: nu still exists, is still the address, and is still not the wire.

        Including the CHART TAG. `nu` opens with `\x01en\x01` — the bias wearing the english
        chart's costume — which is the other half of the violation OI-19 names. The bias's
        chart is written on its LABEL, where the medium can see it and where an arrow form is
        enumerated from it; smuggled inside the text it is neither."""
        _slot, nu_value = address("english", TYPED, "assert")
        payload = bias_payload(self.wire)
        self.assertNotEqual(payload, nu_value)
        self.assertNotIn("\x01", payload)
        self.assertNotIn("\\x01", self.wire.splitlines()[1],
                         "the bias object carries no chart tag inside its text")

    def test_the_address_is_still_computed_from_nu(self):
        """OI-20: identity and attachment never share a rule. Showing raw does not move the
        address — the slot is still nu's, and `commit` still retains by that one path."""
        p = perturb(TYPED, _corpus(), _transport())
        slot, nu_value = address("english", TYPED, "assert")
        self.assertEqual(p.typed_slot, slot)
        self.assertEqual(p.typed_nu, nu_value)


class TheOperatorsBytesReachTheRenderCall(unittest.TestCase):
    """Channel two: the compiled field. The boundary condition is quoted, not restated."""

    def test_the_boundary_condition_is_the_typed_text(self):
        from engine.inbound import compile_input

        c = compile_input(TYPED, _corpus(), "english", transport=_transport())
        self.assertIn(TYPED, c.compiled,
                      "the render call's input must quote the operator verbatim")
        self.assertEqual(c.typed, TYPED)

    def test_it_is_quoted_even_when_nothing_moved(self):
        """The degenerate branches are where a restatement would hide. An empty corpus takes
        the no-region path, which composes its own string — and must still quote."""
        from engine.inbound import compile_input

        c = compile_input(TYPED, CorpusSnapshot(slots={}, arrows=()), "english",
                          transport=_transport())
        self.assertIn(TYPED, c.compiled)


class PlantedNormalizationIsRED(unittest.TestCase):
    """The control's own control. Each plant is a normalization somebody could plausibly add
    for a plausible reason — lowercasing to 'match the corpus', collapsing whitespace to 'clean
    the input', stripping punctuation to 'help the parser'. All three must be caught."""

    def _wire_with(self, transform) -> str:
        typed = transform(TYPED)
        start()
        perturb(typed, _corpus(), _transport())
        return [c for c in TRANSCRIPT.calls if c.port == "propose"][0].user

    def test_lowercasing_the_bias_is_caught(self):
        wire = self._wire_with(str.lower)
        with self.assertRaises(AssertionError):
            self.assertEqual(bias_payload(wire), TYPED)

    def test_collapsing_whitespace_is_caught(self):
        wire = self._wire_with(lambda s: " ".join(s.split()))
        with self.assertRaises(AssertionError):
            self.assertEqual(bias_payload(wire), TYPED)

    def test_stripping_terminal_punctuation_is_caught(self):
        wire = self._wire_with(lambda s: s.rstrip("?!."))
        with self.assertRaises(AssertionError):
            self.assertEqual(bias_payload(wire), TYPED)

    def test_the_full_nu_pipeline_is_caught(self):
        """The exact defect OI-19 names. If this plant passed, the control would be blind to
        the violation that was actually running."""
        wire = self._wire_with(lambda s: address("english", s, "assert")[1])
        with self.assertRaises(AssertionError):
            self.assertEqual(bias_payload(wire), TYPED)

    def test_an_untransformed_bias_passes(self):
        """Not vacuous: the same assertion on the identity transform must hold."""
        self.assertEqual(bias_payload(self._wire_with(lambda s: s)), TYPED)


class TheCorpusObjectsAreUNCHANGED(unittest.TestCase):
    """Scope. OI-19 is about the operator's term, not about the corpus. A corpus claim has no
    bytes other than its nu — nu IS what the engine holds for it — so the asymmetry is real
    and this control states it rather than letting a future reader infer a general rule."""

    def test_a_corpus_member_still_goes_out_as_its_nu(self):
        snap = _corpus()
        start()
        perturb(TYPED, snap, _transport())
        wire = [c for c in TRANSCRIPT.calls if c.port == "propose"][0].user
        nus = {r.nu for r in snap.slots.values()}
        on_wire = [ln for ln in wire.splitlines()
                   if ln.startswith("[") and BIAS_CHART not in ln.split("]")[0]]
        found = [ln for ln in on_wire if any(unescape_nu(ln.split("] ", 1)[-1]) == n
                                             for n in nus)]
        self.assertTrue(found, "corpus objects must still be rendered from their nu")

    def test_the_walks_regions_are_untouched_by_this(self):
        """`build_region(bias=None)` is the walk. Every member's surface is empty, so `wire`
        falls through to `nu` and the walk renders exactly what it rendered before."""
        from engine.region import build_region, render_region

        snap = _corpus()
        region = build_region(snap, size=6)
        self.assertEqual([m.surface for m in region.members], [""] * len(region.members))
        walk = render_region(region)
        self.assertNotIn(f"[{label(BIAS_CHART, 0)}] ", walk)
        for m in region.members:
            self.assertEqual(m.wire, m.nu)


if __name__ == "__main__":
    unittest.main()
