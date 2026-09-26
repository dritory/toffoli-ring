# Step 1: near-solution + one skip-test (HANDOVER-B section 2)

Base pairs: A=(flip,+1),B=(-1) and A=(+1,flip),B=(-1). One skip-test (v=0 or v=1) inserted at every position into A or into B. Tested under scratch encodings (x,1),(1,x),(x,0),(0,x), both rest positions, words up to length 10.

Total configurations tested: **160**

Configurations with FLIP, NEXT and SKIPZ all found: **0**

## Interpretation notes

- "Every possible position" is read literally as every insertion slot in the 2-op letter (3 slots: before both ops, between them, after both) and every slot in the 1-op letter (2 slots), a strict superset of the handover's own count of "2 placements" (departure/arrival), since two of those slots are equivalent up to relabelling v and we did not want to risk missing a case by assuming that equivalence.
- Search length: the handover's section 2 prose mentions length 8; the task instructions for step 1 explicitly say length 10, which is what was run here.
- Exactness and the flag: every configuration here has a skip-test in exactly one bundle, so the flag is reachable and the full flag_in=1 identity requirement is enforced for every word tested (see `search.flag_reachable`). This differs from the flagless base pair (tested only in the sanity suite), where flag_in=1 can never actually occur and is not enforced -- see the final report for this interpretation decision.

No configuration in step 1 found all three of FLIP, NEXT, SKIPZ within length 10. Full results below.

## Full results table

| A | B | encoding | rest | FLIP | NEXT | SKIPZ | PREV |
|---|---|---|---|---|---|---|---|
| `(skip(v=0),flip,move+1)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),flip,move+1)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),flip,move+1)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),flip,move+1)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),flip,move+1)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),flip,move+1)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),flip,move+1)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),flip,move+1)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),flip,move+1)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=0),move+1)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,skip(v=1),move+1)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=0))` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1,skip(v=1))` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=0),move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(skip(v=1),move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=0))` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(flip,move+1)` | `(move-1,skip(v=1))` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=0),move+1,flip)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(skip(v=1),move+1,flip)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=0),flip)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,skip(v=1),flip)` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=0))` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip,skip(v=1))` | `(move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=0),move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(skip(v=1),move-1)` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=0))` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (x,1) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (x,1) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (1,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (1,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (x,0) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (x,0) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (0,x) | 0 | none<=10 | none<=10 | none<=10 | none<=10 |
| `(move+1,flip)` | `(move-1,skip(v=1))` | (0,x) | 1 | none<=10 | none<=10 | none<=10 | none<=10 |
