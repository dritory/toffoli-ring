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
Per orchestrator instruction: SKIPZ X compiled jointly as one macro CX, flag internal to the macro (flag_in=0 only; the word must end with flag_out=0 in every branch). Targets: FLIP, NEXT, PREV (unconditional, as before) plus CFLIP (flip iff bit==1, i.e. clear-if-1), CNEXT (+g iff bit==1 else 0), CPREV (-g iff bit==1 else 0). Window: R = ceil(floor(L/2)/g)+1 groups each side (exact for pruning at that L). A row is a **winner** if it has FLIP, NEXT and CFLIP; CNEXT/PREV/CPREV are reported separately per winner.

### Counts
- Canonical pairs searched: **834**
- Total (pair, encoding, rest) rows: **40829**
- Rows extended to length 12 (>= 3 of the 6 targets at length 10): **629**
- Winners (FLIP, NEXT, CFLIP all found): **80**
- Standalone target counts: FLIP 3857, NEXT 2982, PREV 2570, CFLIP 4773, CNEXT 937, CPREV 1872
- Standalone SKIPZ under the STRICT criterion (for reference, from skip_full.csv): see the Counts section above.

### Winners, ranked by total macro length (FLIP+NEXT+CFLIP)
| rank | A | B | encoding | rest | FLIP | NEXT | CFLIP | total | also CNEXT? | also PREV? | also CPREV? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `(move+1)` | `(move-1,skip(v=0),flip)` | (x,xbar) | 1 | ABBBA(5) | AA(2) | ABABA(5) | 12 | no | no | no |
| 2 | `(move+1)` | `(flip,skip(v=0),move-1)` | (xbar,x) | 0 | ABBBA(5) | AA(2) | ABABA(5) | 12 | no | no | no |
| 3 | `(move+1)` | `(flip,skip(v=0),move-1)` | (xbar,x) | 1 | BBBAA(5) | AA(2) | BABAA(5) | 12 | no | BBBAABBB(8) | no |
| 4 | `(skip(v=0),move+1)` | `(move-1,flip)` | (xbar,x) | 0 | AAABB(5) | AAA(3) | ABABB(5) | 13 | no | BBAAABB(7) | no |
| 5 | `(move+1)` | `(move-1(iff=0),skip(v=0),flip)` | (x,0) | 0 | ABBBABA(7) | AA(2) | BBABA(5) | 14 | no | no | no |
| 6 | `(move+1)` | `(move-1(iff=0),skip(v=0),flip)` | (0,x) | 1 | ABBBABA(7) | AA(2) | BBABA(5) | 14 | no | no | no |
| 7 | `(move+1)` | `(move-1(iff=0),skip(v=0),flip)` | p3('x', 0, 0) | 0 | ABBBABA(7) | AAA(3) | BBABA(5) | 15 | no | no | no |
| 8 | `(move+1)` | `(move-1(iff=0),skip(v=0),flip)` | p3(0, 'x', 0) | 1 | ABBBABA(7) | AAA(3) | BBABA(5) | 15 | no | no | no |
| 9 | `(move+1)` | `(move-1(iff=0),skip(v=0),flip)` | p3(0, 0, 'x') | 2 | ABBBABA(7) | AAA(3) | BBABA(5) | 15 | no | no | no |
| 10 | `(skip(v=0),move+1)` | `(move-1,skip(v=0),flip)` | (x,xbar) | 0 | AAABBB(6) | AAA(3) | AABBAB(6) | 15 | no | BBBAAABBB(9) | no |
| 11 | `(skip(v=0),move+1)` | `(move-1,skip(v=0),flip)` | (xbar,x) | 0 | AAABBB(6) | AAA(3) | ABABBA(6) | 15 | no | BBBAAABBB(9) | no |
| 12 | `(move+1,skip(v=0))` | `(flip,skip(v=0),move-1)` | (x,xbar) | 1 | BBBAAA(6) | AAA(3) | BBAABA(6) | 15 | no | BBBAAABBB(9) | no |
| 13 | `(move+1,skip(v=0))` | `(flip,skip(v=0),move-1)` | (xbar,x) | 1 | BBBAAA(6) | AAA(3) | BABAAA(6) | 15 | no | BBBAAABBB(9) | no |
| 14 | `(move+1)` | `(move-1,skip(v=0),flip)` | (x,xbar) | 0 | AABBB(5) | AA(2) | AABABABAAB(10) | 17 | no | BBBAABBB(8) | no |
| 15 | `(move+1)` | `(move-1,skip(v=0),flip)` | (xbar,x) | 0 | AABBB(5) | AA(2) | AABABAABBA(10) | 17 | no | BBBAABBB(8) | no |
| 16 | `(move+1)` | `(move-1,skip(v=0),flip)` | (xbar,x) | 1 | ABBBA(5) | AA(2) | ABABAABBAA(10) | 17 | no | no | no |
| 17 | `(move+1)` | `(flip,skip(v=0),move-1)` | (x,xbar) | 0 | ABBBA(5) | AA(2) | ABABAABBAA(10) | 17 | no | no | no |
| 18 | `(move+1)` | `(flip,skip(v=0),move-1)` | (x,xbar) | 1 | BBBAA(5) | AA(2) | BABAABBAAA(10) | 17 | no | BBBAABBB(8) | no |
| 19 | `(move+1,flip)` | `(skip(v=0),move-1)` | (x,xbar) | 1 | BBBAA(5) | AABBBAA(7) | BABAA(5) | 17 | no | BBB(3) | no |
| 20 | `(skip(v=0),move+1)` | `(move-1,flip)` | (x,xbar) | 0 | AAABB(5) | AAA(3) | ABABAABBAB(10) | 18 | no | BBAAABB(7) | no |
| 21 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | (x,1) | 0 | BAABB(5) | BAABBBAAA(9) | ABBB(4) | 18 | no | no | BAABBBBAABBB(12) |
| 22 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | (1,x) | 1 | BAABB(5) | BAABBBAAA(9) | ABBB(4) | 18 | no | no | BAABBBBAABBB(12) |
| 23 | `(move+1,skip(v=0))` | `(flip,move-1)` | (x,xbar) | 1 | BBAAA(5) | AAA(3) | BABBABAABA(10) | 18 | no | BBAAABB(7) | no |
| 24 | `(move+1,skip(v=0))` | `(flip,move-1)` | (xbar,x) | 1 | BBAAA(5) | AAA(3) | BABBABBAAA(10) | 18 | no | BBAAABB(7) | no |
| 25 | `(flip,move+1)` | `(skip(v=0),flip,move-1(iff=0))` | (x,0) | 0 | ABAB(4) | ABABABAA(8) | BABBBA(6) | 18 | no | no | no |
| 26 | `(flip,move+1)` | `(skip(v=0),flip,move-1(iff=0))` | (0,x) | 1 | ABAB(4) | ABABABAA(8) | BABBBA(6) | 18 | no | no | no |
| 27 | `(flip,skip(v=0),move+1)` | `(move-1)` | (x,xbar) | 0 | AAABB(5) | AAABBAAA(8) | ABABB(5) | 18 | no | BB(2) | no |
| 28 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | p3('x', 1, 1) | 0 | BAABB(5) | BAABBBAAAA(10) | ABBB(4) | 19 | no | no | no |
| 29 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | p3(1, 'x', 1) | 1 | BAABB(5) | BAABBBAAAA(10) | ABBB(4) | 19 | no | no | no |
| 30 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | p3(1, 1, 'x') | 2 | BAABB(5) | BAABBBAAAA(10) | ABBB(4) | 19 | no | no | no |
| 31 | `(move+1)` | `(move-1(iff=0),skip(v=0),flip)` | p3('x', 0, 0) | 1 | BBBABAA(7) | AAA(3) | BAABABBABA(10) | 20 | no | no | no |
| 32 | `(move+1)` | `(move-1(iff=0),skip(v=0),flip)` | p3(0, 'x', 0) | 2 | BBBABAA(7) | AAA(3) | BAABABBABA(10) | 20 | no | no | no |
| 33 | `(move+1,flip)` | `(skip(v=1),move-1(iff=0),flip)` | (x,0) | 0 | ABAB(4) | ABAAABAB(8) | BABBBABA(8) | 20 | no | no | no |
| 34 | `(move+1,flip)` | `(skip(v=1),move-1(iff=0),flip)` | (0,x) | 1 | ABAB(4) | ABAAABAB(8) | BABBBABA(8) | 20 | no | no | no |
| 35 | `(skip(v=0),move+1)` | `(move-1,flip,skip(v=0))` | (x,xbar) | 0 | AAABBB(6) | AAA(3) | AAABABAAABBA(12) | 21 | no | BBBAAABBB(9) | no |
| 36 | `(skip(v=0),move+1)` | `(move-1,flip,skip(v=0))` | (xbar,x) | 0 | AAABBB(6) | AAA(3) | AAABABABAAAB(12) | 21 | no | BBBAAABBB(9) | no |
| 37 | `(move+1,skip(v=0))` | `(skip(v=0),flip,move-1)` | (x,xbar) | 1 | BBBAAA(6) | AAA(3) | BAABABBABAAA(12) | 21 | no | BBBAAABBB(9) | no |
| 38 | `(move+1,skip(v=0))` | `(skip(v=0),flip,move-1)` | (xbar,x) | 1 | BBBAAA(6) | AAA(3) | BAABABBAABAA(12) | 21 | no | BBBAAABBB(9) | no |
| 39 | `(move+1,skip(v=0))` | `(skip(v=1),move-1,flip)` | (x,xbar) | 1 | ABBBAA(6) | AAA(3) | BABAABBAABBA(12) | 21 | no | BAABBBABB(9) | no |
| 40 | `(move+1,skip(v=0))` | `(skip(v=1),move-1,flip)` | (xbar,x) | 1 | ABBBAA(6) | AAA(3) | BBAABABAABAB(12) | 21 | no | BAABBBABB(9) | no |
| 41 | `(move+1,skip(v=0),flip)` | `(skip(v=0),move-1)` | (x,xbar) | 1 | BBBAAA(6) | AAABBBAAA(9) | BABAAA(6) | 21 | no | BBB(3) | no |
| 42 | `(move+1,skip(v=0),flip)` | `(skip(v=0),move-1)` | (xbar,x) | 1 | BBBAAA(6) | AAABBBAAA(9) | BBAABA(6) | 21 | no | BBB(3) | no |
| 43 | `(flip,skip(v=0),move+1)` | `(move-1,skip(v=0))` | (x,xbar) | 0 | AAABBB(6) | AAABBBAAA(9) | ABABBA(6) | 21 | no | BBB(3) | no |
| 44 | `(flip,skip(v=0),move+1)` | `(move-1,skip(v=0))` | (xbar,x) | 0 | AAABBB(6) | AAABBBAAA(9) | AABBAB(6) | 21 | no | BBB(3) | no |
| 45 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | (x,1) | 1 | BBBAA(5) | ABAABBBAA(9) | BBABBBAA(8) | 22 | no | no | no |
| 46 | `(move+1,skip(v=0))` | `(move-1(iff=1),flip,skip(v=0))` | (x,1) | 0 | ABBBABA(7) | AABBABA(7) | BBABAABA(8) | 22 | no | no | no |
| 47 | `(move+1,skip(v=0))` | `(move-1(iff=1),flip,skip(v=0))` | (1,x) | 1 | ABBBABA(7) | AABBABA(7) | BBABAABA(8) | 22 | no | no | no |
| 48 | `(flip,move+1)` | `(move-1,skip(v=0))` | (x,xbar) | 0 | AABBB(5) | AABBBAA(7) | AABABAABBA(10) | 22 | no | BBB(3) | no |
| 49 | `(flip,move+1)` | `(move-1,skip(v=0))` | (xbar,x) | 0 | AABBB(5) | AABBBAA(7) | AABABABAAB(10) | 22 | no | BBB(3) | no |
| 50 | `(move+1,flip)` | `(skip(v=0),move-1)` | (xbar,x) | 1 | BBBAA(5) | AABBBAA(7) | BABAABBAAA(10) | 22 | no | BBB(3) | no |
| 51 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | p3('x', 1, 1) | 1 | BBBAA(5) | AABAABBBAA(10) | BBABBBAA(8) | 23 | no | no | no |
| 52 | `(skip(v=0),move+1)` | `(flip,move-1(iff=1))` | p3(1, 'x', 1) | 2 | BBBAA(5) | AABAABBBAA(10) | BBABBBAA(8) | 23 | no | no | no |
| 53 | `(move+1,skip(v=0))` | `(move-1(iff=1),flip,skip(v=0))` | p3('x', 1, 1) | 0 | ABBBABA(7) | AAABBABA(8) | BBABAABA(8) | 23 | no | no | no |
| 54 | `(move+1,skip(v=0))` | `(move-1(iff=1),flip,skip(v=0))` | p3(1, 'x', 1) | 1 | ABBBABA(7) | AAABBABA(8) | BBABAABA(8) | 23 | no | no | no |
| 55 | `(move+1,skip(v=0))` | `(move-1(iff=1),flip,skip(v=0))` | p3(1, 1, 'x') | 2 | ABBBABA(7) | AAABBABA(8) | BBABAABA(8) | 23 | no | no | no |
| 56 | `(move+1,skip(v=0),flip)` | `(move-1)` | (x,xbar) | 1 | BBAAA(5) | AAABBAAA(8) | BABBABBAAA(10) | 23 | no | BB(2) | no |
| 57 | `(move+1,skip(v=0),flip)` | `(move-1)` | (xbar,x) | 1 | BBAAA(5) | AAABBAAA(8) | BABBABAABA(10) | 23 | no | BB(2) | no |
| 58 | `(flip,skip(v=0),move+1)` | `(move-1)` | (xbar,x) | 0 | AAABB(5) | AAABBAAA(8) | ABABAABBAB(10) | 23 | no | BB(2) | no |
| 59 | `(skip(v=0),move+1)` | `(skip(v=0),move-1(iff=1),flip)` | (x,1) | 0 | BAABAAB(7) | BAABAAA(7) | ABBBABBAAB(10) | 24 | no | no | no |
| 60 | `(skip(v=0),move+1)` | `(skip(v=0),move-1(iff=1),flip)` | (1,x) | 1 | BAABAAB(7) | BAABAAA(7) | ABBBABBAAB(10) | 24 | no | no | no |
| 61 | `(skip(v=0),move+1)` | `(flip,skip(v=0),move-1(iff=1))` | p3('x', 1, 1) | 0 | BA(2) | BAABBBBBAAAA(12) | ABBBABBBBB(10) | 24 | no | no | BABBABBAB(9) |
| 62 | `(skip(v=0),move+1)` | `(flip,skip(v=0),move-1(iff=1))` | p3(1, 'x', 1) | 1 | BA(2) | BAABBBBBAAAA(12) | ABBBABBBBB(10) | 24 | no | no | BABBABBAB(9) |
| 63 | `(skip(v=0),move+1)` | `(flip,skip(v=0),move-1(iff=1))` | p3(1, 1, 'x') | 2 | BA(2) | BAABBBBBAAAA(12) | ABBBABBBBB(10) | 24 | no | no | BABBABBAB(9) |
| 64 | `(flip,skip(v=0),move+1)` | `(skip(v=0),flip,move-1(iff=1))` | p3('x', 1, 1) | 0 | ABABBBBBA(9) | ABBBAABABA(10) | ABBBB(5) | 24 | no | no | no |
| 65 | `(flip,skip(v=0),move+1)` | `(skip(v=0),flip,move-1(iff=1))` | p3(1, 'x', 1) | 1 | ABABBBBBA(9) | ABBBAABABA(10) | ABBBB(5) | 24 | no | no | no |
| 66 | `(flip,skip(v=0),move+1)` | `(skip(v=0),flip,move-1(iff=1))` | p3(1, 1, 'x') | 2 | ABABBBBBA(9) | ABBBAABABA(10) | ABBBB(5) | 24 | no | no | no |
| 67 | `(skip(v=0),move+1)` | `(skip(v=0),move-1(iff=1),flip)` | p3('x', 1, 1) | 0 | AABABBB(7) | ABABBAAA(8) | AABBABBAAB(10) | 25 | no | no | no |
| 68 | `(skip(v=0),move+1)` | `(skip(v=0),move-1(iff=1),flip)` | p3(1, 'x', 1) | 1 | AABABBB(7) | ABABBAAA(8) | AABBABBAAB(10) | 25 | no | no | no |
| 69 | `(skip(v=0),move+1)` | `(skip(v=0),move-1(iff=1),flip)` | p3(1, 1, 'x') | 2 | AABABBB(7) | ABABBAAA(8) | AABBABBAAB(10) | 25 | no | no | no |
| 70 | `(skip(v=0),move+1)` | `(move-1(iff=0),flip)` | p3('x', 0, 0) | 0 | AABBABB(7) | AABBABAAAA(10) | BAABBBBAA(9) | 26 | AABAB(5) | no | no |
| 71 | `(skip(v=0),move+1)` | `(move-1(iff=0),flip)` | p3(0, 'x', 0) | 1 | AABBABB(7) | AABBABAAAA(10) | BAABBBBAA(9) | 26 | AABAB(5) | no | no |
| 72 | `(skip(v=0),move+1)` | `(move-1(iff=0),flip)` | p3(0, 0, 'x') | 2 | AABBABB(7) | AABBABAAAA(10) | BAABBBBAA(9) | 26 | AABAB(5) | no | no |
| 73 | `(skip(v=0),move+1)` | `(flip,move-1(iff=0),skip(v=0))` | p3('x', 1, 0) | 1 | BBBABABB(8) | AAAAABBABB(10) | BBAABABB(8) | 26 | no | no | no |
| 74 | `(skip(v=0),move+1)` | `(flip,move-1(iff=0),skip(v=0))` | p3(0, 'x', 1) | 2 | BBBABABB(8) | AAAAABBABB(10) | BBAABABB(8) | 26 | no | no | no |
| 75 | `(move+1,skip(v=0),flip)` | `(skip(v=1),move-1)` | (x,xbar) | 1 | BBBAAA(6) | AAABBBAAA(9) | BAABABBAABAA(12) | 27 | no | BBB(3) | no |
| 76 | `(move+1,skip(v=0),flip)` | `(skip(v=1),move-1)` | (xbar,x) | 1 | BBBAAA(6) | AAABBBAAA(9) | BAABABBABAAA(12) | 27 | no | BBB(3) | no |
| 77 | `(skip(v=0),move+1,flip)` | `(move-1,skip(v=1))` | (x,xbar) | 0 | ABBBAA(6) | ABBAAABAA(9) | ABABBAABBAAB(12) | 27 | no | BBB(3) | no |
| 78 | `(skip(v=0),move+1,flip)` | `(move-1,skip(v=1))` | (xbar,x) | 0 | ABBBAA(6) | ABBAAABAA(9) | AABBABABBABA(12) | 27 | no | BBB(3) | no |
| 79 | `(flip,skip(v=0),move+1)` | `(move-1,skip(v=1))` | (x,xbar) | 0 | AAABBB(6) | AAABBBAAA(9) | AAABABABAAAB(12) | 27 | no | BBB(3) | no |
| 80 | `(flip,skip(v=0),move+1)` | `(move-1,skip(v=1))` | (xbar,x) | 0 | AAABBB(6) | AAABBBAAA(9) | AAABABAAABBA(12) | 27 | no | BBB(3) | no |

### Independent brute-force re-verification (top-ranked winner)
Pair: A=`(move+1)`, B=`(move-1,skip(v=0),flip)`, encoding=(x,xbar), rest=1. Cyclic tape of 12 groups, 1000 random tapes, flag_in=0 only (per the guarded criterion), verified with `verify_guarded()` in verify_bruteforce.py (shares no code with guarded_search.py).

- FLIP = `ABBBA`: 1000/1000 checks passed
- NEXT = `AA`: 1000/1000 checks passed
- CFLIP = `ABABA`: 1000/1000 checks passed
