# THE CERTIFIED-POSITIVITY FIXTURE — frozen acceptance, three columns

**FROZEN.** The question, the table's rows, and the pre-registration do not change. Columns are
added as the pipeline changes; **no column is ever removed or rewritten**, including the ones
recording a failure. That rule is the whole value of the artifact: a fixture whose bad readings
get tidied away measures nothing.

**THE QUESTION**, verbatim and unchanging:

> what does the certified positivity work establish

**WHY THIS ONE.** The corpus holds substantial certified-positivity material in BOTH english and
lean — English claims describing Lean theorems, and the Lean theorems themselves. So the region
reliably seats objects from two charts that are *about the same work*, and whether the machine
relates them across the chart boundary is exactly the property under test. A fixture where the
answer is easy tells you nothing about a mechanism built for cross-chart correspondence.

**BOTH OUTCOMES WERE PRE-REGISTERED** before any column was measured. Lean attachment rising is
the protocol working; lean attachment staying at zero is the protocol not reaching the gap, and
is a result rather than a failure of the fixture. Neither reading is a surprise, which is what
pre-registration buys.

---

## THE TABLE

| | **A — pre-B2** | **B — HALF-COLLAPSED** | **C — collapsed** |
|---|---|---|---|
| build | pre-dialogue | `7e216540c563` | pending |
| pipeline | propose (coords) + render (prose) | propose (coords) + dialogue | one dialogue |
| calls | 2 | **2** | 1 conversation |
| region composition | 1 bias / 40 english / 19 lean | 1 bias / 40 english / 19 lean | pending |
| attachments | — | **2 english, 0 lean** (2 of 59 shown) | pending |
| lean attached | **0 of 19** | **0 of 19** | pending |
| propagation | — | **2 moved**, 0 over declared arrows | pending |
| dialogue turns | n/a | 1 | pending |
| arrows from prose | n/a | **0 records, 0 resolved, 0 claims** | pending |
| faithful | ✓ | ✓ — 3/3 receipted, 0 violations, 9 citable | pending |
| latency | — | 6.6s | pending |

**Column A is the operator's recorded baseline** (lean 0 of 19 attached; the medium was shown
`theorem coverage_prime_free` beside the English claim describing it, and connected nothing).
The intermediate figures in column A are marked `—` rather than filled: a like-for-like run of
*this* question under the pre-B2 build was not captured before that build was replaced, and
copying numbers across from a differently-worded run would be a fabrication. What column A
asserts is the one number that was recorded.

---

## COLUMN B IS PRESERVED DELIBERATELY

Column B is a **failed state**, kept because it is the cleanest evidence this project has
produced that **the two-mouth pipeline cannot be half-collapsed.**

What happened: the render call was deleted and a dialogue put in its place — but the *propose*
call was left standing. The split therefore survived under new names, `propose` + `dialogue`
instead of `propose` + `render`, and the commit message claimed the split was gone. The suite
was green at 1564. Nothing caught it. It was found by reading a live transcript.

**The diagnostic number is `arrows from prose: 0`.** The medium had been taught the
`[i] -kind-> [j]` form and did not use it once — not because it refused, but because it had
nothing to relate: the propose call had already done the attachment and handed the dialogue a
field of **two objects**. A conversation cannot draw arrows across a corpus it was never shown.

Read together, columns A and B say something a single column could not: the dialogue does not
*add* attachment capability on top of the coordinate call. It **replaces** it, or it starves.
Propagation fell from the recorded baseline to 2 moved and 0 hops over declared arrows, which is
the pipeline doing *less* than before while every test stayed green.

---

## WHAT COLUMN C MUST SHOW

Not "better numbers" — that would be a target, and a fixture with a target is a fixture somebody
tunes toward. It must show, whatever the values:

1. **one conversation** — a single sequence of turns, no coordinates-only call beside it;
2. **the medium seated in front of the whole region**, in region numbering (`[e1]`, `[l45]`), so
   the chart tag is visible to it when relating across languages;
3. **arrows extracted from prose, counted as records and as distinct claims**, both reported;
4. **the same checker**, on the same grammar, ungated by any of the above.

Whether lean attachment moves off zero is the measurement. It is not the pass condition.

---

## HOW TO RE-RUN

Against the SERVED url, never local code — a fixture that measures the working tree measures
something nobody is using. `tools/acceptance.py` speaks to the deploy; the raw traffic for any
row is on the page in the dialogue panel, digest-verified per block.
