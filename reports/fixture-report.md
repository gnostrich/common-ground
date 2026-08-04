# common-ground — fixture report

**HELD on D5 (STATEMENTS.md / pre-minted files) — floors below are on SYNTHETIC fixtures, not a verdict on the real corpus**

## Routing (ingestion front-end)

| destination | n |
|---|---|
| conversation | 1 |
| english | 1 |
| lean (fixture, D6-gated in prod) | 1 |
| tabular | 1 |

## Object at a glance

| quantity | n |
|---|---|
| documents | 4 |
| deltas | 38 |
| slots | 14 |
| fibers | 8 |
| edges | 17 |
| blocks | 7 |
| contested_blocks | 1 |
| loops | 5 |
| clamps | 0 |
| charts in play | 4 |

## Slots by chart

| chart | n |
|---|---|
| conversation | 6 |
| english | 4 |
| lean | 2 |
| tabular | 2 |

## Cross-chart correspondences (fibers spanning >=2 charts)

- **conversation+english+lean+tabular** @ a61f075a8f25e7f5: leantheorem add_pos (f g : Cone) : IsPositive  | cvthe cone is positive under composition | leantheorem comp_pos (f g : Cone) : IsPositive | enthe cone is positive | tabadd_pos | open
- **conversation+english+lean** @ a61f075a8f25e7f5: enpositivity is preserved under composition | cvthe cone is positive under composition | leantheorem comp_pos (f g : Cone) : IsPositive
- **conversation+english+lean** @ a61f075a8f25e7f5: leantheorem add_pos (f g : Cone) : IsPositive  | enpositivity is preserved under composition | cvthe cone is positive under composition | leantheorem comp_pos (f g : Cone) : IsPositive | enthe cone is positive
- **conversation+english+lean** @ a61f075a8f25e7f5: leantheorem add_pos (f g : Cone) : IsPositive  | cvthe cone is positive under composition | leantheorem comp_pos (f g : Cone) : IsPositive | cvyes, agreed, the cone stays positive under c | enthe cone is positive
- **conversation+lean** @ a61f075a8f25e7f5: leantheorem comp_pos (f g : Cone) : IsPositive | cvyes, agreed, the cone stays positive under c
- **lean+tabular** @ a61f075a8f25e7f5: leantheorem comp_pos (f g : Cone) : IsPositive | tabcomp_pos | proved
- **conversation+english+lean** @ a61f075a8f25e7f5: leantheorem add_pos (f g : Cone) : IsPositive  | cvthe cone is positive under composition | leantheorem comp_pos (f g : Cone) : IsPositive | enthe cone is positive
- **lean+tabular** @ a61f075a8f25e7f5: leantheorem add_pos (f g : Cone) : IsPositive  | tabadd_pos | open

## Holonomy floors (per beta arm) — SYNTHETIC

| beta | loops | mean floor | q95 | 2nd-FDT | certificates |
|---|---|---|---|---|---|
| 1.0 | 5 | 0.00000090 | 0.00000152 | 0.00000090 | monotone |
| 4.0 | 5 | 0.00000010 | 0.00000017 | 0.00000010 | monotone |

translator drift (measured vs declared shadow): n/a

## Conversation ledger — proposal -> verdict (p_fast content; K inert)

| verdict | proposer | decided by | proposal |
|---|---|---|---|
| accepted | Alice | Bob | The cone is positive under composition. |
| open | Bob | - | Yes, agreed, the cone stays positive under composition. |
| rejected | Alice | Carol | The spectral radius equals the largest eigenvalue. |
| open | Carol | - | No, that is wrong; the spectral radius is the maximum modulus eigenvalue. |
| sharpened | Bob | Alice | The transfer defect is first order in the perturbation. |
| open | Alice | - | More precisely, the transfer defect is first order only to leading order. |

## Status

- **phase**: P0-P2 (fixtures only)
- **P3**: HELD on D5 (STATEMENTS.md / pre-minted files) — floors below are on SYNTHETIC fixtures, not a verdict on the real corpus
- **charts**: conversation, english, lean, tabular
- **gates**: gate6 / gate7 / faithfulness / probes / three-moves all green
- **mint (K)**: INERT — the conversation ledger is produced, nothing is promoted
