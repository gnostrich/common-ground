# THE CERTIFIED-POSITIVITY FIXTURE — frozen acceptance, seven columns and a baseline

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
| build | pre-dialogue | `7e216540c563` | `6bc9309592bd` |
| pipeline | propose (coords) + render (prose) | propose (coords) + dialogue | one dialogue |
| calls | 2 | **2** | **5** — 1 + 3 interrogations + the residual re-ask |
| region composition | 1 bias / 40 english / 19 lean | 1 bias / 40 english / 19 lean | 1 bias / 40 english / 19 lean |
| attachments | — | **2 english, 0 lean** (2 of 59 shown) | **22 english, 0 lean** (22 of 59 shown) |
| lean attached | **0 of 19** | **0 of 19** | **0 of 19** |
| propagation | — | **2 moved**, 0 over declared arrows | **24 moved**, 2 over declared arrows |
| dialogue turns | n/a | 1 | 5 (budget, then [b0] re-asked) |
| arrows from prose | n/a | **0 records, 0 resolved, 0 claims** | **52 records, 34 resolved, 34 claims** |
| faithful | ✓ | ✓ — 3/3 receipted, 0 violations, 9 citable | ✗ — 4/4 receipted, 3 violations, **61 citable** |
| latency | — | 6.6s | 24.4s |

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

## WHAT COLUMN C SHOWED

All four conditions hold. One conversation; the medium seated in front of all sixty region
objects in region numbering; arrows extracted from prose and counted as records and as claims;
the same checker on the same grammar.

**The number under test did not move: lean 0 of 19.** Everything else did. Attachment went from
2 to 22, arrows from prose from 0 records to 52, and propagation crossed a declared arrow for
the first time on this fixture — 2 of 24 movers reached over one. The pipeline is doing more,
across the same region, and still relating nothing to a Lean object.

**COLUMN C COST FOUR DEFECTS TO MEASURE**, every one of them found by running the fixture rather
than by reading code, and every one of them the same class: *a rule the medium cannot comply
with is a rule that only ever convicts.*

1. **The referee read a different sheet.** Turn 1 was shown sixty labelled objects; the checker
   resolved against three. It ruled three real corpus claims fabricated. Fixed by printing and
   registering every seated object in one act — `citable` in column C is **61**, which is what
   the medium can actually see.
2. **The residual could not fire.** `answers()` read the raw reply, so a turn of pure arrow
   lines counted as answering because an arrow line contains a citation; and `attached_labels()`
   looked for a label on records that do not carry one, so its degradation clause ran on every
   request. The page displayed an EMPTY answer while the mechanism built for that exact case
   stayed silent.
3. **The weld rule was checked and never stated.** Four WELDED verdicts against one answer,
   every convicted sentence true, from a medium whose prompt never said that co-citation asserts
   a relation. `[∅rel]` was enforceable and unwritable. Stating it — one clause of codomain
   syntax — took violations from 4 to 0 and sentences checked from 9 to 22 in the same act.
4. **The residual and the answer disagreed about "answered".** `_close` scanned every turn;
   `Dialogue.answer` displays only turns asked the operator's question. An interrogation turn
   answered its own question, the residual saw it and declined to fire, and the served page
   showed four turns, fifty resolved arrows and no answer.

The general control now standing: for every verdict `check_answer` can return, the prompt must
contain the TOKEN that makes compliance possible, and a new verdict kind with no entry in that
table fails the test.

---

## COLUMN D — THE TWO-TIER MEASUREMENT

**THE DEVIATION, STATED.** Both tiers ran LOCALLY, against `ui.server.Handler` on a loopback
port, on one commit and one corpus snapshot. The re-run rule says served-only and it is the
right rule; it cannot answer this question. The deploy carries one model pin, so measuring a
second tier on it means repointing the thing the operator is about to test. Running both here
also makes the comparison stronger than served-vs-local would have been: the model is the only
variable rather than one of three. The harness is `tools/fixture_positivity.py`; it drives the
shipped handler rather than re-implementing the path, takes the tier from `OPENROUTER_MODEL` —
the build's own pin, no second selection mechanism — and reports cost from what the provider
reported, never from a rate multiplied by a token count.

**THE SECOND TIER, NAMED AND STAMPED:** `google/gemini-2.5-pro`. Same family as the pinned
`google/gemini-2.5-flash`, so size is what changes and not the vendor's prompt conventions.

**ONE DRAW PER TIER WAS THE ORDER; IT IS NOT ENOUGH, AND THAT IS ITSELF THE FINDING.** The first
pro draw returned lean 0. The third returned lean 2. A single draw either way would have settled
a question the data does not settle, so the run was extended to eight draws at flash and six at
pro, and the range is reported rather than a representative number.

| | **flash** (n=8) | **pro** (n=6) |
|---|---|---|
| build | `afcbf1362169` | `afcbf1362169` |
| **lean attached** | **0 of 19, all 8 draws** | **0,0,0,0,2,3** — non-zero in **2 of 6** |
| attachments (of 59 shown) | 0–23 | 0–6 |
| arrows from prose | 0–89 records, 0–56 resolved | 0–22 records, 0–22 resolved |
| propagation | 0–23 moved, 0–2 over arrows | 0–8 moved, 0–3 over arrows |
| dialogue turns | 1–5 | 1–4 |
| faithful | **clean in 7 of 8**; 2–22 checked, receipted = checked | **clean in 0 of 6**; 1–9 violations |
| latency | 8–39s | 15–220s |
| cost per run | $0.0010–$0.0067 | $0.0000–$0.1499 |
| total spend | $0.0387 | $0.5878 |

### THE FINDING, IN ONE SENTENCE

**The chart boundary is crossable at the larger tier but not reliably — lean attachment moved
off zero for the first time in this fixture's history, in 2 of 6 draws, at roughly 20x the cost
and 8x the latency, while the larger tier was worse on every other row measured** — so the
residual gap is not simply model capability, and the medium-labels and lexicon lanes remain the
fix rather than a model swap.

### WHAT THAT DOES TO THE PRE-REGISTRATION

Both readings were pre-registered and **both partly fired**, which is the outcome the
pre-registration did not anticipate and is why it is written down before the numbers rather
than after. Read strictly:

- *Lean attachment moves at the larger tier ⇒ the gap is capability, and interactive-tier model
  choice becomes a priced decision.* It moved. The price is now measured: **~20x per answer for
  a one-in-three chance at 2–3 lean objects out of 19**, bought at the cost of a faithfulness
  verdict that never came back clean.
- *Lean attachment stays 0 at both ⇒ the gap is vocabulary/bridging.* It did not stay 0 — but it
  did not become reliable either, and the tier that crossed the boundary attached FEWER objects
  overall and failed the checker in every draw. A capability that appears a third of the time
  and degrades the rest of the answer is not the capability the reading was about.

**No model spend is recommended.** The interactive pin stays `google/gemini-2.5-flash`.

### WHAT ELSE THE DRAWS SAID

- **The metric is bimodal at flash**, not noisy around a mean: attachment is either ~22 or ~0–2,
  with nothing between. Six of eight draws landed high. Whatever selects between the two modes
  is unmeasured and is a better lead than model size.
- **Pro spends its tokens thinking.** Prompt tokens are comparable; completion tokens ran 5–8x
  flash's, and two draws returned no usable arrows at all after 15s and 75s respectively.
- **Cost was reported as $0.0000 on two calls** (one per tier). That is what OpenRouter returned,
  not an inference: unreported and free are different facts and are not collapsed here.

---

## COLUMN E — THE REPAIRED SAMPLER, AND WHAT A RISING COUNT MEANS

**Awakened by order**, not by a bridge lane: two ruled sampler-layer defects landed and the
fixture is the acceptance for both. Recorded as a column rather than a note because the
mechanism under test changed.

| | **D-flash** (reference) | **E — after the two fixes** |
|---|---|---|
| build | `afcbf1362169` | `65d190eba233` |
| turns | 1–5 | **4** |
| turn 2 | contest on `[e16]` | contest on **`[e1]`** — attached |
| turn 3 | contest on `[e16]` *(same question)* | contest on **`[e31]`** — attached |
| turn 4 | contest on `[e16]` *(same question)* | contest on **`[e43]`** — attached |
| turn 5 | re-ask: `[b0]` had no answering turn | — not needed; turn 1 answered |
| residual outcomes | — | all three **resolved** |
| attachment | 22, all bears_on | **34, all bears_on** |
| answer | 462 chars | 8,871 chars |
| faithful | 3 violations | **60 violations** |
| composition | 3 uncontested | **31 welded / 28 uncontested / 1 unresolved** over 58 sentences |

Three consecutive runs returned identical figures.

**WHAT THE TWO FIXES WERE.** Residual scoping: the interrogator read corpus-wide ambient
contests — `[e16]` every turn, regardless of what the perturbation touched — and now reads only
contests among objects this perturbation ATTACHED, BORE ON or MOVED. The narrow boundary was
implemented; there is no 1-hop neighbourhood expansion. And the bias admits only `bears_on`: the
parser voided `bears_on` between two corpus claims while waving `same_claim` TO THE BIAS
through, so a typed question was being given assertion-grade coupling to the corpus on the
strength of having been typed.

---

### THE LESSON THIS COLUMN EXISTS TO HOLD

**A RISING VIOLATION COUNT UNDER A REPAIRED REFEREE AND DOUBLED REACH IS PROGRESS WEARING RED.**
Three violations became sixty, and every part of that increase is the machine working:
attachment doubled because the bias fix stopped mis-kinded arrows from consuming the medium's
attention, more attached objects means more contests among reached objects are visible, and the
referee now resolves against the whole shown sheet instead of three labels.

**ONLY THE COMPOSITION SAYS WHICH.** 28 of the 60 are `uncontested` — a rule the medium cannot
comply with, because turn 1's sheet does not mark contested objects, so `[!]` is enforceable and
unwritable. That is row 523's class, and it is a debt this build owes rather than an answer this
build got wrong. A bare count of 60 cannot distinguish it from an answer that fabricated sixty
times.

**THE STANDING RULE, FROM HERE:** a violation count is never recorded anywhere in this project
without its composition beside it.

---

## COLUMN F — THE ROSTER CLAUSE, MEASURED AND WITHDRAWN

One FORM clause naming the roster shape. Three identical draws on the served build, then a
bisect on one commit with the clause as the only variable.

| | **E** | **F — served** | **bisect A** (local, with) | **bisect B** (local, without) |
|---|---|---|---|---|
| build | `65d190e` | `cf27ddb` | `cf27ddb` | `cf27ddb` |
| violations | 60 | **4** | 3 | **0** |
| composition | 31 welded / 28 uncontested / 1 unresolved | 0 welded / 3 uncontested / 1 unresolved | 2 welded / 1 unresolved | — |
| attachment | 34 of 59 | **59 of 59** | **0 of 59** | 8 of 59 |
| **discrimination** | 0.576 | **1.00 — RED** | **0.00** | **0.136 — ok** |
| lean attached | 0 of 19 | 19 of 19 *(void)* | 0 | 0 |
| answer | 8,871 chars | 4,585 | 5,403 | 232–783 |

**THE WELD MEASUREMENT SUCCEEDED: 31 → 0.** No roster survived explicit instruction. That is a
real answer to the question column F was run to ask.

**AND THE CLAUSE DESTABILIZED ATTACHMENT, WHICH IS WHY IT IS GONE.** The engine's own guard
flagged the served run: *"the medium drew an arrow to essentially every object it was shown, so
the attachment carries no information."* Locally the same clause drove attachment to the
opposite pole, 0 of 59 at fraction 0.00. Opposite directions, one instability — "split a roster
into one sentence per object" reads as MENTION EVERYTHING, and a medium told to mention
everything either relates to everything or gives up.

**LEAN 19 OF 19 IS VOID.** It was 19 of 19 because everything was 59 of 59. The number the
two-tier measurement chased has not moved; it was swamped. **A boundary crossed at fraction 1.0
was not crossed** — and that is now a standing rule: no attachment metric is reportable without
its discrimination fraction beside it.

**A SECOND RAZOR-LEGAL WORDING ALSO FAILED.** "Relate at most two labels per sentence… a claim
needs a sentence only if the answer rests on it" — constraining shape without inviting coverage
— gave attachment 2 of 59 and a **59,349-character answer over 370 sentences**. A third failure
mode from a second wording.

**TWO WORDINGS, TWO DEGENERACIES, SO THE CLAUSE IS WITHDRAWN** and the 13 enumeration-shaped
convictions return as the known, recorded, honest cost. A working system with understood
convictions beats a degenerate system with a lower count.

**TEMPLATE BYTES ARE STEERING BYTES.** Any future wording change to a prompt gets a code-grade
acceptance: three draws on this fixture, discrimination reported, before it lands.

---

## THE BASELINE — `baseline-1`, RE-STAMPED to build `73d7706cb397`

> **RE-STAMP NOTE, appended rather than applied.** This block was written at build
> `b484b945d8af` and its figures below are that build's, kept because nothing here is ever
> rewritten. `seed/BASELINE.json` was then re-stamped to **`73d7706cb397`** after row 532's
> fix, and the authoritative figures moved: **violations 60 → 59**, composition **31 welded /
> 28 uncontested / 1 unresolved → 31 / 27 / 1**. Everything else held.
>
> **THE COUNT MOVING BY ONE UNDERSTATES IT ENTIRELY.** The fix was symmetric — three objects
> the checker held hot without the wire marking them stopped convicting (the trap), and three
> the wire marked without the checker enforcing started convicting (the useless mark). Six
> convictions were replaced by five. What changed is that **every remaining conviction is
> compliable**: 19 marked on the wire, 19 held hot by the checker, and the two sets identical.
>
> **`seed/BASELINE.json` IS AUTHORITATIVE**, and it is the record the auditor defends. This
> divergence sat here undetected between the re-stamp and column G — two records of one fact
> disagreeing, which is row 532's own shape one layer up — so it now carries a control:
> `tests/test_baseline_record.py` refuses a fixture file that does not name the current
> baseline build and its violation count.

**The convergence target, met.** Not an aspiration: a checklist frozen before the pass was run,
and every item measured on the SERVED build.

| check | target | measured |
|---|---|---|
| **a. no degeneracy** | discrimination in a sane band, attachment informative | **0.576**, 34 of 59 attached |
| **b. battery** | ≤ 2 standing-known findings over 10 probes | **0 findings over 10 probes** |
| **c. stability** | 3 consecutive draws, consistent shape | 3 draws, **byte-identical figures** |
| **d. turn shape** | distinct residuals, discharge, answer-debt only when owed | 4 turns, `[e1]`/`[e31]`/`[e43]`, all **resolved**, no re-ask needed |
| **e. walk wire** | byte-identical to pre-fix | the `build_region` invariance property, **green** |

**THE HONEST COMPOSITION, which is the baseline's real content:**

```
58 sentences checked, 60 violations
  31 welded      18 genuine (a)-class + 13 enumeration (b)-class — the RECORDED COST
                 of withdrawing the roster clause, per the convergence mandate
  28 uncontested compliable and uncomplied: the (!) mark reaches turn 1's sheet and the
                 rule is stated, and the medium does not write [!]. A conviction, not a trap.
   1 unresolved
```

**A COUNT OF 60 IS NOT A FAILING GRADE HERE, AND THAT IS THE POINT OF RECORDING THE
COMPOSITION.** Every one of the 60 is understood, classified, and traceable to a decision
somebody made on purpose. Column F is what a lower count bought last time: 4 violations at
discrimination 1.00, which is a machine that has stopped discriminating rather than a machine
that has stopped erring.

**FROM HERE, THE AUDITOR'S JOB IS DEFENDING THIS.** Any regression from these figures is a RED
that outranks other work: discrimination outside the band, a finding on any probe, a
draw-to-draw shape collapse, a turn without a preceding question, or a change in the walk's
wire.

---

## COLUMN G — THE LEXICON LANE, TIER B MEASURED AND WITHDRAWN

**THIS COLUMN LANDS BECAUSE IT WAS PROMISED, NOT BECAUSE IT WENT WELL.** The rider on the go
order was that the acceptance table lands as a fixture artifact *regardless of outcome — all
three pre-registered branches produce a recorded column, including withdrawal*. This is the
withdrawal branch, recorded.

### What was measured

One local A/B on a single commit with the lane as the ONLY variable, two draws per arm,
byte-identical within each arm. **Tier B alone**, because tier A had nothing in it:
`seed/DECISIONS.json` records **0 of 184 imported senses carrying a formal face**, so
`lexicon_registry()` returns an empty registry and every gloss on the wire was a mechanical
`rmap.render` output wearing `[REPO_DOC — unauthored]`.

| | **lane OFF** | **lane ON — tier B** |
|---|---|---|
| build | one commit, both arms | same commit |
| corpus | local, **0 arrows** | local, **0 arrows** |
| draws | 2, byte-identical | 2, byte-identical |
| attachment | **8 of 59** | **2 of 59** |
| **discrimination** | **0.1356 — in band** | **0.0339 — BELOW the 0.05 floor** |
| lean attached | **0 of 19** | **0 of 19** |
| gloss coverage | n/a — lane off | **19 of 19, fraction 1.00** |
| **authored coverage** | n/a | **0 of 19, fraction 0.00** |
| dialogue turns | 2 | 1 |
| sentences checked | 6 | 45 |
| violations | **0** — `{}` | **17** — `{welded: 11, unresolved: 6}` |
| answer | 650 / 666 chars | 5,425 chars |

**THE ARROW COUNT IS ON THE TABLE BECAUSE IT HAS TO BE** (row 531): both arms ran on the local
corpus at 0 arrows, where the served build stands on ~19K. Two measurements at different arrow
counts are two measurements of two corpora — so these figures are comparable *to each other*,
which is all an A/B needs, and are **not** comparable to the served baseline's 0.576.

### The reading, against the branches pre-registered before the run

1. *Lean attachment rises AND the discrimination spread narrows* → the lane works.
   **Did not fire.** Lean attachment was 0 in both arms and discrimination fell out of band.
2. *Rises where coverage is high, flat where it is zero* → the mechanism works, the data is the
   constraint. **UNTESTED, and it is the live one.** Authored coverage was 0.00 in every arm;
   there is no arm in which it was high. Branch 2 cannot be read off a measurement that never
   varied the quantity it names.
3. *Flat despite coverage* → the handle is not what was missing; **the lane is withdrawn and
   the finding recorded.** **FIRED, for tier B.** Coverage 19 of 19 at fraction 1.00, and lean
   attachment did not move.

**SO: TIER B IS WITHDRAWN AND TIER A IS UNMEASURED.** Those are two different statements and
the coverage split is what keeps them apart — which is exactly why coverage was made mandatory
on every figure this lane produces before any figure existed.

### Why "no change" would have been the wrong call

Tier B did not merely fail to help. **Attachment fell 8 → 2 and the engine's own guard fired**
at 0.0339, below the 0.05 floor. Nineteen mechanical readings bridged nothing and pushed
attachment toward the empty pole, and violations went 0 → 17 as the answer grew eightfold.

**THIS IS THE SECOND TIME AN ADDITION TO TURN 1'S SHEET HAS COST ATTACHMENT** — the roster
clause of column F was the first, and it destabilized in both directions. The lane is a
different mechanism with the same signature, and the standing rule reads the same way it did in
column F: **a boundary metric is not reportable without its discrimination fraction, and an
addition that moves the fraction out of band is withdrawn regardless of its intent.**

### What landed, and what did not

`rendered` defaults to **False** on `gloss_for` and `glosses_for`. **Nothing is deleted.** Tier
A — an operator-AUTHORED face, resolved by exact whole-string membership — runs with no code
change the day those faces exist, and tier B stays reachable behind an explicit argument so the
next person measures it rather than re-deriving it. `c12` plants all of that four ways,
including an AST check that the gate is a parameter defaulting to False rather than a deleted
branch, and a check that the module still carries the two figures that withdrew it.

**THE RIDER'S PLANTED CONTROL IS GREEN.** `c11` asserts that a gloss cannot silence the lexical
residual: a glossed cluster with no apex **still** raises `apexless`, and an AST check confirms
the fourth door has no import path to this lane at all. A gloss reads one declaration; it is
not a name for a proposition several claims share, so it must not satisfy `named()`.

### THE SHORTFALL, STATED

**The acceptance as specced was a battery-wide spread over the ten probe types, before and
after. What decided it was a single-probe A/B on this fixture.** The spread was not bought,
because an arm that lands below the discrimination floor on the first probe is not a candidate
whose spread is worth paying for — but the shortfall is real and it is recorded here rather
than implied by a table that looks complete. **The spread is owed to tier A**, on the day
authored faces exist, and that is the run branch 2 was written for.

---

## COLUMNS A–D: CLOSED

- **A — pre-B2 baseline.** Two mouths, coordinates then prose. Lean 0 of 19; the medium was
  shown the Lean theorem beside the English claim describing it and connected nothing.
- **B — the half-collapse.** The render call deleted, the propose call left standing, the split
  surviving under new names. Lean 0 of 19, and `arrows from prose: 0` — a conversation cannot
  draw arrows across a corpus it was never shown. Kept as the cleanest evidence this project has
  that the two-mouth pipeline cannot be half-collapsed.
- **C — the collapse, served.** One conversation over the whole region in region numbering.
  Attachment 2 → 22, arrows from prose 0 → 52 records / 34 resolved, propagation crossing a
  declared arrow for the first time, citable 9 → 61. Lean 0 of 19. Cost four referee defects to
  measure, all of the named class, all now controlled.
- **D — the two tiers.** flash 0 of 19 in all 8 draws; pro 0,0,0,0,2,3 in 6. The boundary is
  crossable by capability and not reliably — ~20x cost, ~8x latency, worse faithfulness in every
  draw. No model spend; flash stays the pinned interactive medium.

**THE FIXTURE IS NOW DORMANT-STANDING.** It is not retired and nothing in it may be edited: the
question, the rows, the pre-registration and all four columns stand as written. It has answered
what it was built to answer — whether the machine relates across the chart boundary, and whether
model size is the reason it does not — and re-running it against the same mechanism would only
resample a number already measured fourteen times.

**COLUMN E WAS AN AWAKENING BY ORDER**, which the rule below did not anticipate and which is
now recorded as the second legitimate kind: the operator ruled two sampler-layer defects and
made this fixture their acceptance. That is a change to the mechanism under test, which is
exactly what the rule is about — it simply arrived from a ruling rather than from a lane.

**ITS NEXT LEGITIMATE AWAKENING IS A BRIDGE LANE LANDING**, or another ruled change to the
mechanism. Medium-labels, or the lexicon lane,
or anything else that gives the English and Lean charts a shared handle. That is a change to the
mechanism under test, which is exactly what a new column is for. A re-run for any other reason —
a model change, a prompt tweak, a slow week — is resampling noise and calling it evidence.

---

## HOW TO RE-RUN

Against the SERVED url, never local code — a fixture that measures the working tree measures
something nobody is using. `tools/acceptance.py` speaks to the deploy; the raw traffic for any
row is on the page in the dialogue panel, digest-verified per block.

`tools/fixture_positivity.py` is the harness for a question this rule cannot answer: comparing
two model tiers, where the deploy's single pin makes served-only impossible. It drives the
SHIPPED handler on a loopback port rather than re-implementing the request path, and any column
it produces must say so, as column D does. It is not a substitute for a served run and no column
measured with it may be recorded without the deviation stated beside the numbers.

RAW ARTIFACTS STAY OFF THE REPOSITORY. Each run writes the answer verbatim and every convicted
sentence, which is corpus text — the operator's private material — and this repository is
public. `runs/fixture-*/` is gitignored for that reason. The numbers live here; the claims stay
on the machine that measured them.
