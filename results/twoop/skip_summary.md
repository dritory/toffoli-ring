# Skip-flag full menu search: summary
Scope: HANDOVER-B.md sections 2-4 (skip-flag pairs). Sections 6-7 (stateless pairs) are out of scope for this report.
## Counts
- Canonical pairs searched (mod mirror + complement symmetry, each with a +1 mover and a -1 mover): **1017**
- Encoding x rest combinations per pair: **49**
- Total (pair, encoding, rest) rows: **49833**
- Rows extended to length 12 (had >= 2 of FLIP/NEXT/SKIPZ at length 10): **275**
- Winners (FLIP, NEXT and SKIPZ all found for the same pair/encoding/rest): **0**
- Standalone primitive counts (rows where that primitive alone was found, regardless of the others): FLIP 552, NEXT 706, PREV 706, SKIPZ 180 (out of 49833 rows)

## No winner
Exhaustive search over **1017** canonical pairs x **49** encoding/rest combinations (**49833** rows total), words to length 10 (extended to 12 for the **275** rows that already had >= 2 of FLIP/NEXT/SKIPZ at length 10), found **no pair** achieving FLIP, NEXT and SKIPZ together under any single encoding and rest position.

## No -1 subspace confirmation
```
no -1 subspace confirmatory run, L=8
pairs tested: 2550
(pair x encoding x rest) rows checked: 124950
rows where FLIP was found: 1870
rows where NEXT was found: 1684
rows where SKIPZ was found: 2100
winners (FLIP+NEXT+SKIPZ together): 0

Confirms the handover's 'A -1 move is necessary' lemma: exhaustive at L=8 across all bundles with no -1 move, no encoding/rest achieves FLIP+NEXT+SKIPZ together.
```

## Window +/-2 rerun
Requested by the orchestrator: rerun step 1 (all of it) and every step-2 row that had >= 2 of FLIP/NEXT/SKIPZ at length 10, with the window widened to the current group +/- 2 groups (prune only when a branch leaves that wider window). Raw report:

```
Step 1 rerun (half_width=2, L=10): 160 configurations
Step 1 new hits (found wide, not found narrow): 0
Step 1 new full winners under wide window: 0

Step 2 promising rows rechecked (had search_L=12, i.e. >=2/3 at L=10): 275
Step 2 new hits (found wide, not found narrow): 0
Step 2 new full winners under wide window: 0
```

## Guarded-macro criterion
Per orchestrator instruction: SKIPZ X compiled jointly as one macro CX, flag internal to the macro (flag_in=0 only; the word must end with flag_out=0 in every branch). Targets: FLIP, NEXT, PREV (unconditional, as before) plus CFLIP (flip iff bit==1, i.e. clear-if-1), CNEXT (+g iff bit==1 else 0), CPREV (-g iff bit==1 else 0). Window: R = ceil(floor(L/2)/g)+1 groups each side (exact for pruning at that L).

**Criterion correction (from the orchestrator):** a guarded FLIP acts on the same cell it tests, so CFLIP is just CLEAR and carries no data interaction -- the reference machine's actual data dependence comes only from SKIPZ.NEXT and SKIPZ.PREV, i.e. from CNEXT and CPREV. Accordingly:
- **Primary winner table**: rows with FLIP, NEXT, PREV, CNEXT **and** CPREV all present, ranked by the total length of those five macros.
- **Secondary table**: rows with FLIP, NEXT and at least one of CNEXT/CPREV (with or without PREV), that do not already qualify for the primary table.
- The old FLIP+NEXT+CFLIP criterion is reported as a footnote count only.

### Counts
- Canonical pairs searched: **1017**
- Total (pair, encoding, rest) rows: **49833**
- Rows extended to length 12 (>= 3 of the 6 targets at length 10): **661**
- Standalone target counts: FLIP 4560, NEXT 2982, PREV 2981, CFLIP 6381, CNEXT 937, CPREV 2121
- **Primary winners (FLIP, NEXT, PREV, CNEXT, CPREV all found): 2**
- **Secondary winners (FLIP, NEXT, and at least one of CNEXT/CPREV, not already primary): 24**
- Footnote -- old criterion (FLIP, NEXT, CFLIP all found; CFLIP carries no data interaction, superseded by the correction above): 80

Best total-length in the complete CSV for the primary (five-macro) criterion: **39**. Orchestrator's independently-verified reference row totals **39** (ABB=3 + ABBAAA=6 + BAABBBABBABB=12 + ABBAAB=6 + ABBABABAABBB=12). The reference row itself is the best in the complete CSV (nothing beats it).

### (1) Primary winners, ranked by total length of FLIP+NEXT+PREV+CNEXT+CPREV
| rank | A | B | encoding | rest | FLIP | NEXT | PREV | CNEXT | CPREV | total5 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `(flip,skip(v=0),move+1)` | `(flip,skip(v=0),move-1)` | (x,xbar) | 0 | ABB(3) | ABBAAA(6) | BAABBBABBABB(12) | ABBAAB(6) | ABBABABAABBB(12) | 39 |
| 2 | `(flip,skip(v=0),move+1)` | `(flip,skip(v=0),move-1)` | (xbar,x) | 1 | BAA(3) | ABBAAABAABAA(12) | BAABBB(6) | BAABABABBAAA(12) | BAABBA(6) | 39 |

### Independent brute-force re-verification (top 3 of table 1)

Rank 1: A=`(flip,skip(v=0),move+1)`, B=`(flip,skip(v=0),move-1)`, encoding=(x,xbar), rest=0. Cyclic tape of 12 groups, 1000 random tapes, flag_in=0 only, verified with `verify_guarded()` in verify_bruteforce.py (shares no code with guarded_search.py).

- FLIP = `ABB`: 1000/1000 checks passed
- NEXT = `ABBAAA`: 1000/1000 checks passed
- PREV = `BAABBBABBABB`: 1000/1000 checks passed
- CNEXT = `ABBAAB`: 1000/1000 checks passed
- CPREV = `ABBABABAABBB`: 1000/1000 checks passed

Rank 2: A=`(flip,skip(v=0),move+1)`, B=`(flip,skip(v=0),move-1)`, encoding=(xbar,x), rest=1. Cyclic tape of 12 groups, 1000 random tapes, flag_in=0 only, verified with `verify_guarded()` in verify_bruteforce.py (shares no code with guarded_search.py).

- FLIP = `BAA`: 1000/1000 checks passed
- NEXT = `ABBAAABAABAA`: 1000/1000 checks passed
- PREV = `BAABBB`: 1000/1000 checks passed
- CNEXT = `BAABABABBAAA`: 1000/1000 checks passed
- CPREV = `BAABBA`: 1000/1000 checks passed

### (2) Secondary rows (FLIP, NEXT, and >=1 of CNEXT/CPREV; not already primary): 24 total, top 20 shown
| A | B | encoding | rest | FLIP | NEXT | PREV | CNEXT | CPREV |
|---|---|---|---|---|---|---|---|---|
| `(move+1)` | `(move-1(iff=0),flip)` | (x,0) | 0 | AB(2) | AA(2) | no | BABBABAA(8) | no |
| `(move+1)` | `(move-1(iff=0),flip)` | (0,x) | 1 | AB(2) | AA(2) | no | BABBABAA(8) | no |
| `(move+1,skip(v=0))` | `(move-1(iff=1),flip)` | (x,1) | 0 | AB(2) | AAABAB(6) | no | no | BABBAB(6) |
| `(move+1,skip(v=0))` | `(move-1(iff=1),flip)` | (1,x) | 1 | AB(2) | AAABAB(6) | no | no | BABBAB(6) |
| `(move+1)` | `(skip(v=0),move-1(iff=0),flip)` | (x,0) | 0 | ABA(3) | AA(2) | no | BABBBABAAA(10) | no |
| `(move+1)` | `(skip(v=0),move-1(iff=0),flip)` | (0,x) | 1 | ABA(3) | AA(2) | no | BABBBABAAA(10) | no |
| `(flip,skip(v=0),move+1)` | `(flip,move-1,skip(v=1))` | (x,xbar) | 0 | ABB(3) | ABBAAA(6) | no | ABBAAB(6) | no |
| `(flip,skip(v=0),move+1)` | `(flip,move-1,skip(v=1))` | (xbar,x) | 0 | ABB(3) | ABBAAA(6) | no | ABBABA(6) | no |
| `(flip,skip(v=0),move+1)` | `(flip,skip(v=0),move-1)` | (xbar,x) | 0 | ABB(3) | ABBAAA(6) | BAABBBABBABB(12) | ABBABA(6) | no |
| `(move+1,skip(v=0))` | `(move-1(iff=1),flip)` | (x,1) | 1 | BA(2) | AABABA(6) | no | no | BABBABBABA(10) |
| `(move+1,skip(v=0))` | `(move-1(iff=1),flip)` | p3('x', 1, 1) | 0 | AB(2) | AAAABAB(7) | no | no | BABBABBAB(9) |
| `(move+1,skip(v=0))` | `(move-1(iff=1),flip)` | p3(1, 'x', 1) | 1 | AB(2) | AAAABAB(7) | no | no | BABBABBAB(9) |
| `(move+1,skip(v=0))` | `(move-1(iff=1),flip)` | p3(1, 1, 'x') | 2 | AB(2) | AAAABAB(7) | no | no | BABBABBAB(9) |
| `(flip,skip(v=0),move+1)` | `(flip,skip(v=0),move-1)` | (x,xbar) | 1 | BAA(3) | ABBAAABAABAA(12) | BAABBB(6) | no | BAABAB(6) |
| `(skip(v=0),move+1)` | `(move-1(iff=0),flip)` | p3('x', 0, 0) | 0 | AABBABB(7) | AABBABAAAA(10) | no | AABAB(5) | no |
| `(skip(v=0),move+1)` | `(move-1(iff=0),flip)` | p3(0, 'x', 0) | 1 | AABBABB(7) | AABBABAAAA(10) | no | AABAB(5) | no |
| `(skip(v=0),move+1)` | `(move-1(iff=0),flip)` | p3(0, 0, 'x') | 2 | AABBABB(7) | AABBABAAAA(10) | no | AABAB(5) | no |
| `(skip(v=0),move+1)` | `(flip,skip(v=0),move-1(iff=1))` | p3('x', 1, 1) | 0 | BA(2) | BAABBBBBAAAA(12) | no | no | BABBABBAB(9) |
| `(skip(v=0),move+1)` | `(flip,skip(v=0),move-1(iff=1))` | p3(1, 'x', 1) | 1 | BA(2) | BAABBBBBAAAA(12) | no | no | BABBABBAB(9) |
| `(skip(v=0),move+1)` | `(flip,skip(v=0),move-1(iff=1))` | p3(1, 1, 'x') | 2 | BA(2) | BAABBBBBAAAA(12) | no | no | BABBABBAB(9) |
