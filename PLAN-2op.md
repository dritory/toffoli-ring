# Plan: two-instruction pointer machines with constant-factor universality

Primary target: **stateless pairs** (no skip flag; the CPU holds nothing between ticks). Fallback: pairs with a skip flag (Section 6). Same enumeration; the stateless menu is smaller, and the encoding is where the difficulty moves: pointer position is the only place a branch can live, so rejoining is the whole game.

## 1. What "exact" means without a flag

A macro is a word w over {A,B}; every letter executes. Two branches (different encoded contents of the window) diverge only when a conditional move fires in one and not the other; from then on the same letters act at different positions, so they flip different cells. A macro is exact for a primitive P when, for every encoded window content:

1. the final pointer offset is the same in all branches, equal to P's;
2. the tape delta, read through the encoding, is P's, and every cell of the window (including scratch cells and neighbouring groups) is again validly encoded;
3. no branch touches a cell outside the window (or touches it an even number of times with no move depending on it).

**SKIPZ is not a primitive here.** With no flag, "SKIPZ X" in the reference 4-op program must compile to one macro that does X iff the cell is 1 and rejoins. So the target set is

    FLIP, NEXT, PREV, and CX = "X iff cell = 1" for each X that the reference compiler emits after SKIPZ

CNEXT and CPREV may be single conditional-move letters under a suitable encoding; CFLIP is the hard one. First task for whoever builds the compiler: write down the reference 4-op loop scheme and list exactly which `SKIPZ·X` combinations it emits (if it ever emits `SKIPZ SKIPZ`, that combination needs its own macro too). Everything downstream depends on that list.

## 2. Pruning lemmas (stateless)

**L1 (both directions).** FLIP and CFLIP have pointer delta 0 in every branch. If the flipping instruction moves in some branch, that branch must come back, which needs the opposite direction. If the flipping instruction never moves (pure FLIP), the other instruction is a conditional +1 (or −1) alone, and exact NEXT is impossible by L2. If the flipping instruction moves unconditionally, FLIP has no branch that returns. Hence: one instruction carries +1, the other −1, at least one of them conditional, and the flip is bundled with one or both. Modulo mirror (swap ±1) and complement (swap 0/1 in every condition and in the encoding), that is the entire candidate space.

**L2 (crossing).** A cell crossed by NEXT satisfies the mover's condition at crossing time; net zero flips means that value is the cell's original value. So a group that NEXT crosses must contain, for each data value, a cell that the mover can cross, and a data cell of the wrong value can be crossed only after a flip that is later undone by a return. With +1 and −1 both available this is a constraint on macro structure, not an impossibility, and it is why the encoding must supply constant cells (scratch) or complementary pairs (dual rail).

**L3 (sweeps encode in position).** For A = (flip, then +1 iff new = 1): a 0-cell costs one A to cross and is left as 1; a 1-cell costs two A's and is left as 1. So A^n sweeps right, sets everything to 1, and the pointer position after n letters is a function of the values crossed. Dual rail (x, x̄) costs 3 per group whichever x is, so A^3 crosses a group and rejoins the branches on position but with (1,1) on the tape. That is the shape of every stateless rejoin: branches separate on cost, meet on position, and the tape must be re-derived from what happened in between. Any winning macro will have this sweep-and-return structure; look for it in the hits.

Hand-checked so far (under (x,1), pointer resting on x): A = (flip, +1 iff new=1), B = (−1 iff cell=1) gives FLIP = AB exactly (x=0: A sets x, steps onto the scratch, B steps back; x=1: A clears x and stays, B stays). NEXT is not found by hand: the x=0 branch reaches the next data cell one letter earlier than the x=1 branch and any conditional letter executed there branches on the next bit. Period-3 groups with two constants are the natural fix; not tried.

## 3. Semantics to enumerate (stateless)

Instruction = ordered bundle of: flip (current cell), move ∈ {+1, −1} with condition ∈ {always, iff cell = 0, iff cell = 1} evaluated on the cell under the pointer at that moment (so "iff new" exists only when the flip precedes the move in the bundle; "flip after move" flips the destination). Per instruction: flip ∈ {none, before, after} × move ∈ {±1} × condition ∈ {always, =0, =1}: 18 bundles, fewer after dedupe by effect table. Pairs with opposite move directions and at least one conditional: about 60 after mirror and complement symmetry. No phase bit; instruction meaning is position-independent.

## 4. Enumeration spec

For each pair, each encoding E ∈ {none; dual rail (x, x̄) and (x̄, x); (x, 1), (1, x), (x, 0), (0, x); period-3 groups with one data cell and two constants, all 3 rest positions} and each rest position:

1. Window = the group with one full group on each side (3–9 cells), contents ranging over all valid encodings, pointer at rest.
2. Effect tables for all words up to L = 8, then 10, then 12 (8190 words per pair at 12). Prune a word as soon as any branch leaves the window, since later letters then read unknown cells.
3. Test each word against every target primitive of Section 1 under the exactness criterion (offset equal across branches, tape delta correct, encoding invariant). Record the shortest hit per (pair, encoding, primitive).
4. A pair wins when FLIP, NEXT and every CX in the reference list exist for one common encoding and rest position (PREV and CPREV reported separately: with a −1 letter in the pair they are often free).

Cost is minutes. Report as a table: pair × encoding × primitive → shortest macro or none ≤ 12.

## 5. Verification, transistors, ISA

* Compiler: reference 4-op scheme (Section 1) then macro substitution; program ring = concatenation. Tests: 3-bit counter, echo loop through memory-mapped I/O cells, fixed-length copy. Compare against a 4-op simulation at macro boundaries.
* Transistor estimate for a stateless winner: opcode decode 1 inverter (2 T), flip = XOR into cell or cell toggle enable (4–6 T), move ±1 = two pass gates on the pointer register with the condition taken from the cell line (2–4 T), clock gating (2 T). About 8–12, no flip-flop. Fallback skip machine adds one flip-flop (4–6 T).
* ISA statement: one bit per instruction; each logical op is a run of 3–12 letters whose branches are invisible in the text; a single-bit error changes where a branch rejoins. Not hand-writable; programs come from the compiler.

## 6. Fallback: pairs with a skip flag

Run only if Section 4 exhausts at L = 12. Same enumeration with a skip sub-op (set skip iff cell = v, evaluated on the cell under the pointer at that moment) added to the bundles, the skip flag added to the state, and SKIPZ restored as a primitive with skip_in/skip_out in the effect tables. Two lemmas specific to this case:

* a·R form: a pending skip suppresses only the first letter, so every multi-letter macro is a·R with R an identity word from skip 0, and in any branch where a sets no skip the macro equals a alone. Enumerate identity words first.
* A −1 move is still necessary, for the same reason as L1 plus the fact that identity words cannot move without it.

Near-solution for this case, no encoding: A = (flip, then +1), B = (−1) gives FLIP = AB, NEXT = ABA, PREV = B exactly; only SKIPZ is missing, and adding a skip test to A or B makes it test a neighbour, which the (x,1) encoding turns into a constant. Recorded dead ends: with B = (skip iff cell=0, then −1) under (x,1), AB is FLIP from skip 0 but not from skip 1; ABAB is an identity word but neither A·ABAB nor B·ABAB is FLIP. With B = (−1, then skip iff destination=0) under (1,x), ABAB from x=0 is exactly the SKIPZ zero-branch but the x=1 branch flips x and ends at −1.

## 7. If both exhaust

Report the tables. Then evaluate the pure conditional-move family (A = flip, B = +1 iff cell = 1; and A = +1 iff 1, B = flip + −1 iff 0) for polynomial overhead by hand-coding a 3-state 2-symbol Turing machine with an encoding that keeps the pointer able to cross; L2 predicts at least linear cost in N per simulated step, i.e. BCT-like polynomial universality rather than constant factor.
