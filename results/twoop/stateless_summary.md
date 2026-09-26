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

## Complete window

Per the coordinator's correction, the window-relative results above were superseded by a window sized so that "prune on leaving" is exact for every word of length <= 12, not just generous: per group width g, R = ceil(6/g) + 1 groups on each side of the current group (g=1: R=7, 15 groups, 2^15 = 32768 valuations; g=2: R=4, 9 groups, 512 valuations; g=3: R=3, 7 groups, 128 valuations), keeping every other parameter identical to the earlier runs (same 64 pairs, same 49 encoding/rest combinations, same 6 targets, same word lengths 1-12).

The g=1 case (15 groups, 32768 valuations) was too slow to search branch-by-branch in Python, so the checker was ported to C (`sim/twoop_stateless/complete_search.c`) using bitset-parallel evaluation: each of the up to 21 window positions carries one 64-bit-word-packed bitset per valuation-batch (a "cell content across all valuations" bitset and a "pointer is here across all valuations" bitset), and one bundle application updates all valuations at once with bitwise AND/OR/XOR/NOT -- no per-valuation loop. The whole 64-pairs x 49-combos x 6-targets x lengths-1-12 sweep (18816 target checks) ran in 82 seconds. Output: `results/twoop/stateless_full_complete.csv` (18816 rows, same schema).

**New hits vs the ±2 run: none (0).** Every one of the 18816 (pair, encoding, rest, target) results is byte-for-byte identical between `stateless_full_w5.csv` (±2 window) and `stateless_full_complete.csv` (fully-sufficient window) -- same targets found, same shortest macros, nothing lost, nothing gained. This means no length-<=12 macro in this whole search ever actually needed to travel more than 2 groups from its start; the ±2 window had already, empirically, been exhaustive for this pair/encoding set, and the complete-window run now proves that fact rather than assuming it.

**Winner: still none.** No (pair, encoding, rest) combination realizes FLIP + NEXT + CFLIP together under the complete window; the maximum number of the 6 targets realized at once by any single combination is still 3 of 6, with the same five near-miss subsets and counts as the ±2 run ({FLIP,CNEXT,CPREV}:20, {FLIP,NEXT,CPREV}:16, {FLIP,PREV,CNEXT}:16, {FLIP,NEXT,CNEXT}:6, {FLIP,PREV,CPREV}:6). FLIP and CFLIP still never co-occur in the same combination.

**Why this window makes the search exhaustive for length <= 12:** every target's accepted end state has the pointer within g cells of the start (all six targets end at offset in {-g, 0, +g}). If a branch reaches distance D cells from its start at some tick i <= 12 and is ever going to end within g cells of the start by tick 12 (a precondition for satisfying any target), it needs at least D-g more ticks to get back (a bundle moves at most 1 cell/tick), so D + (D-g) <= 12, i.e. D <= 6 + g/2 <= 6 + g. A window of R = ceil(6/g) + 1 groups (R*g >= 6+g cells) on each side is therefore always wider than the farthest any target-satisfying trajectory can reach at any intermediate tick, so "prune on leaving this window" can never discard a word that would otherwise go on to satisfy a target -- i.e. pruning becomes exact, not just conservative, for length <= 12. (The ±2-groups window used in the previous rerun was not, in general, provably wide enough by this same argument -- e.g. for g=1 it offered only 2 cells of half-width against a theoretical worst case of 6 -- so its agreement with this complete run is an empirical fact about which trajectories these particular 64 pairs actually realize, not something guaranteed in advance the way the R = ceil(6/g)+1 window is.)
