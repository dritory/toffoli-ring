# Stateless two-instruction pairs: exhaustive search (HANDOVER-B.md section 6)

Pairs searched: **64** raw candidate pairs (all satisfying: one bundle carries +1, the other -1, at least one move conditional, at least one bundle has a flip).

Encoding x rest-position combinations: **49** (1 none + 4 dual-rail-complementary + 8 dual-rail-with-constant + 36 period-3).

Total (pair, encoding, rest) combinations tested: **3136**, each against all 6 targets to word length <= 12 (18816 target-checks total).


## Winners

**None.** No (pair, encoding, rest) combination realizes FLIP, NEXT and CFLIP simultaneously for any word of length <= 12.


Breakdown of how many of the 3 core targets {FLIP, NEXT, CFLIP} any single combination manages together:

- {CFLIP, NEXT}: 6 combinations
- {FLIP, NEXT}: 116 combinations
- {NEXT}: 228 combinations
- {FLIP}: 260 combinations
- {CFLIP}: 34 combinations
- {(none)}: 2492 combinations

Notably FLIP and CFLIP were **never** found together in the same combination (0 out of 3136); CFLIP itself was found in 40 combinations, all of them under a dual-rail complementary encoding (x,not x) or (not x,x) -- never under a scratch-cell or period-3 encoding.

## Closest near-misses (most targets realized at once: 3 of 6)


### {CNEXT, CPREV, FLIP} -- 20 combinations

- pair `A=(+1?1) B=(flip;-1?1)`, encoding `(x,1)`, rest=0: FLIP=BA, CNEXT=AA, CPREV=BAABBB
- pair `A=(+1?1) B=(-1?1;flip)`, encoding `(x,1)`, rest=0: FLIP=AB, CNEXT=AA, CPREV=BABBAB
- pair `A=(flip;+1?1) B=(-1?1)`, encoding `(x,1)`, rest=0: FLIP=AB, CNEXT=ABAABA, CPREV=BB
- pair `A=(+1?1;flip) B=(-1?1)`, encoding `(x,1)`, rest=0: FLIP=BA, CNEXT=ABAABA, CPREV=BB

### {CPREV, FLIP, NEXT} -- 14 combinations

- pair `A=(+1) B=(-1?1;flip)`, encoding `(x,1)`, rest=0: FLIP=AB, NEXT=AA, CPREV=BABBAB
- pair `A=(flip;+1) B=(flip;-1?1)`, encoding `(x,1)`, rest=0: FLIP=ABB, NEXT=ABBABA, CPREV=ABBBABBB
- pair `A=(+1;flip) B=(-1?1;flip)`, encoding `(x,1)`, rest=0: FLIP=ABB, NEXT=ABAABB, CPREV=BABBBABB

### {CNEXT, FLIP, PREV} -- 14 combinations

- pair `A=(flip;+1?1) B=(flip;-1)`, encoding `(x,1)`, rest=0: FLIP=BAA, PREV=BAABAB, CNEXT=BAAABAAA
- pair `A=(+1?1;flip) B=(-1)`, encoding `(x,1)`, rest=0: FLIP=BA, PREV=BB, CNEXT=ABAABA
- pair `A=(+1?1;flip) B=(-1;flip)`, encoding `(1,x)`, rest=1: FLIP=BAA, PREV=BABBAA, CNEXT=ABAAABAA

### {CNEXT, FLIP, NEXT} -- 6 combinations

- pair `A=(+1) B=(-1?0;flip)`, encoding `(x,0)`, rest=0: FLIP=AB, NEXT=AA, CNEXT=BABBABAA

### {CPREV, FLIP, PREV} -- 6 combinations

- pair `A=(+1?0;flip) B=(-1)`, encoding `(x,0)`, rest=0: FLIP=BA, PREV=BB, CPREV=ABAABABB

## Exhaustion statement

All 64 candidate pairs, satisfying the section-6 constraints (one +1-mover, one -1-mover, >=1 conditional move, >=1 flip), were tested against all 49 (encoding, rest-position) combinations listed in the encodings menu (none; dual-rail (x,not x) and (not x,x); dual-rail-with-constant (x,1),(1,x),(x,0),(0,x); period-3 with one data cell and two constants, all 4 constant-arrangements x all 3 rotations), and against all 6 targets (FLIP, NEXT, PREV, CFLIP, CNEXT, CPREV), for every word over {A,B} of length 1 through 12, pruning (per the spec) any word whose pointer leaves the 3-group window in any of the 8 logical-bit valuations of the window. No combination realizes FLIP + NEXT + CFLIP together. The exhaustive search is complete to word length 12 as specified; nothing beyond that length was attempted.

Symmetry class count: modding the 64 raw candidate pairs out by the bundle-level mirror (reverse move direction) and complement (swap 0/1 in every condition) transformations yields **18** equivalence classes (14 of size 4, 4 of size 2). All 64 raw pairs were searched directly rather than only 18 representatives, so this class count is reported for reference only and does not narrow the exhaustion claim above.

## Window ±2 rerun

Per the coordinator's correction, the original run's window rule (prune a word as soon as any branch's pointer leaves the *current group ±1* window, i.e. 3 groups / 8 valuations) was widened to *current group ±2* (5 groups, 32 valuations of logical bits, window size 5g cells), keeping every other parameter identical: same 64 pairs, same 49 (encoding, rest) combinations, same 6 targets, same word lengths 1-12. Results written to `results/twoop/stateless_full_w5.csv` (18816 rows, same schema as `stateless_full.csv`).

**Winners under the ±2 window: still none.** No (pair, encoding, rest) combination realizes FLIP + NEXT + CFLIP together; the maximum number of the 6 targets found at once by any single combination is still 3 (same as the ±1 run). FLIP and CFLIP still never co-occur in the same combination.

**New target hits that appear only with the wider window (12 total, all NEXT or PREV, none FLIP/CFLIP/CNEXT/CPREV):**

| pair | encoding | rest | target | macro |
|---|---|---|---|---|
| A=(+1;flip) B=(-1?0;flip) | (0,x) | 1 | NEXT | ABAABB |
| A=(+1;flip) B=(-1?0;flip) | (0,1,x) | 2 | NEXT | AABAAABB |
| A=(+1;flip) B=(-1?0;flip) | (0,0,x) | 2 | NEXT | ABABAABB |
| A=(+1;flip) B=(-1?1;flip) | (1,x) | 1 | NEXT | ABAABB |
| A=(+1;flip) B=(-1?1;flip) | (1,0,x) | 2 | NEXT | AABAAABB |
| A=(+1;flip) B=(-1?1;flip) | (1,1,x) | 2 | NEXT | ABABAABB |
| A=(+1?0;flip) B=(-1;flip) | (x,0) | 0 | PREV | BABBAA |
| A=(+1?0;flip) B=(-1;flip) | (x,1,0) | 0 | PREV | BBABBBAA |
| A=(+1?0;flip) B=(-1;flip) | (x,0,0) | 0 | PREV | BABABBAA |
| A=(+1?1;flip) B=(-1;flip) | (x,1) | 0 | PREV | BABBAA |
| A=(+1?1;flip) B=(-1;flip) | (x,0,1) | 0 | PREV | BBABBBAA |
| A=(+1?1;flip) B=(-1;flip) | (x,1,1) | 0 | PREV | BABABBAA |

These 12 words all have length 6-8, i.e. genuinely wander out to the second group before returning -- exactly the case the ±1 window incorrectly pruned. No word found under the ±1 window is lost under the wider window (12 new hits, 0 lost, 0 changed among the 18816-12 combos that were already resolved either way), consistent with ±2 being a strict superset of what ±1 could see.

Updated 3-of-6 near-miss subset counts under ±2 (compare to the ±1 counts above): {FLIP,CNEXT,CPREV} 20 (unchanged), {FLIP,NEXT,CPREV} 16 (was 14, +2 from the new NEXT hits above), {FLIP,PREV,CNEXT} 16 (was 14, +2 from the new PREV hits above), {FLIP,NEXT,CNEXT} 6 (unchanged), {FLIP,PREV,CPREV} 6 (unchanged). Still no 4-of-6 or better, and no FLIP+NEXT+CFLIP anywhere.
