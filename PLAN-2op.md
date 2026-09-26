# Plan: two-instruction pointer machines with constant-factor universality

Goal: a pair (A, B) of fixed instruction bundles, macros over {A,B} implementing FLIP, NEXT, SKIPZ (and separately PREV) exactly, possibly under a tape encoding maintained as an invariant. Below: (1) the exact correctness criterion, which is stronger than it looks; (2) three lemmas that prune most pairs; (3) a near-solution to start from; (4) the enumeration spec for the cheap models; (5) verification, transistor count, ISA statement.

## 1. Correctness criterion, made precise

A macro is a word w over {A,B}. Its effect is a function
(window contents, skip_in) → (window delta, pointer delta, skip_out),
where the window is the group of cells the encoding says the pointer can touch (the rest cell plus the neighbours the word can reach). "Exact" means: for skip_in = 0 the effect equals the primitive's; for skip_in = 1 the effect is identity with skip_out = 0 (the primitive was suppressed).

**Lemma 1 (a·R form).** With skip_in = 1 the first instruction a is suppressed and the rest R runs from skip 0. So every macro longer than one instruction has the form a·R with R ≡ identity on all (window, skip=0) states. From skip 0, in every branch where a sets no skip, the macro's effect equals a's own effect (because R ≡ id). Consequences:

* A single instruction that in some branch is exactly "flip, no move, no skip" is required for FLIP, unless FLIP's first instruction sets the skip in every branch (possible only when the tested cell is a constant of the encoding).
* Likewise "move +1, no flip, no skip" for NEXT.
* The tail R' (R minus its first instruction) is the only place where branches can do different work, and it runs only after a skip. Skip is therefore the only rejoining mechanism; pointer-position branching alone cannot rejoin unless a later skip makes the branches execute different words.
* Search order that follows from this: enumerate identity words R first (cheap, and they are reused by all three macros), then test a·R for a ∈ {A,B}.

**Lemma 2 (a −1 move is necessary).** FLIP and SKIPZ have pointer delta 0 in every branch. Without any −1 move, an identity word can contain no executed move at all (a full circle costs N), so FLIP and SKIPZ macros consist of executed instructions whose moves are off in every branch; the flip and the skip test must then both come from the non-moving instruction, whose powers have period 3 in effect (flip / set-or-clear / identity, with skip states that never match FLIP or SKIPZ in both branches). Encodings do not help, because reaching a second cell of the group and coming back needs −1 or N. So every winning pair has a −1 move component (conditional or not) in one instruction and a +1 in the other. The brute force should still run the no-−1 subspace, but the expected outcome is exhaustion, and Lemma 2 is the reason.

**Lemma 3 (crossing).** Without −1 moves, a cell crossed by NEXT must at crossing time satisfy the mover's condition, and net zero flips means that value is the cell's original value. So a pair whose only +1 mover is "move iff cell = v" cannot implement exact NEXT under any encoding whose data cells take both values: crossing a ¬v data cell corrupts it and nothing can come back. This kills the pure conditional-move designs (A = flip, B = move iff 1) for exact macros; they remain candidates only for the polynomial-overhead fallback in Section 6.

Combined with Lemma 1: modulo the mirror symmetry (swap +1/−1) and value complement (swap 0/1 in all conditions and encodings), the candidate space is

    A = flip + (move −1 iff cell = v) + (optional skip iff cell = v')      [pure flip in the ¬v branch]
    B = move +1 (unconditional or iff cell = u) + (optional skip iff cell = u')  [pure +1 in the no-skip branch]

plus the encoding-dependent exception where a macro's first instruction tests a constant scratch cell and skips in every branch. Sub-operation order inside each bundle (flip before/after move; skip test before/after move, i.e. on the departure or the destination cell) is part of the semantics and must be enumerated.

## 2. Near-solution to start from

Take A = (flip current cell, then move +1), B = (move −1), no skips, no encoding. Then, exactly and without branching:

    FLIP = A B        (flip c, step to c+1, step back)
    NEXT = A B A      (c is flipped twice, pointer ends at c+1)
    PREV = B

Proof for NEXT: A flips the cell it leaves; a walk from c to c+1 in which every cell is departed upward an even number of times is A B A. The same works with A = (move +1, then flip destination): FLIP = B A, NEXT = A B A with the arrival cell flipped twice.

What is missing is SKIPZ, i.e. a skip component on one of the two instructions. Adding it creates a test on whichever cell the instruction is at, which is a neighbour in half the uses; the (x, 1) or (1, x) scratch encodings exist to make that neighbour a constant. This is the smallest search: two base pairs × skip on A or B × test before/after the move × test value 0/1 × two encodings × two rest positions, macros up to length 8. If it succeeds, the answer is a 2-op machine with PREV for free (B) and no encoding beyond one scratch cell per bit. If it fails, widen to conditional −1 (A = flip + move −1 iff cell = v) per Section 1.

Hand-checked dead ends, so nobody repeats them: with A = (flip, +1), B = (skip iff cell = 0 before moving, −1) under (x,1): A B is FLIP from skip 0 but not from skip 1 (R = B is not identity); ABAB is an identity word but neither A·ABAB nor B·ABAB is FLIP. With B = (−1, then skip iff destination = 0) under (1, x): ABAB from x = 0 is exactly the SKIPZ zero-branch (no tape change, delta 0, skip out 1) but the x = 1 branch flips x and ends at −1. These near misses are why the search should be systematic rather than by hand.

## 3. Semantics to enumerate

State: tape (cyclic), pointer, skip flag. Per instruction, an ordered list of sub-ops from: flip (current cell), move (0, +1, −1; unconditional, or iff cell = v where "cell" is the cell under the pointer at that moment, so "iff new" is only distinct when a flip precedes it in the bundle), skiptest (set skip iff cell = v at that moment). Enumerate all orders of the chosen sub-ops (flip/move/skiptest permutations: at most 6 per bundle). Semantics of the skip flag: if set when an instruction is fetched, the instruction does nothing and the flag clears. Disallow a phase bit: instruction meaning must be position-independent. Deduplicate instruction semantics by their effect table on (cell, neighbour, skip) before pairing; expect a few dozen distinct bundles, a few hundred unordered pairs after mirror and complement symmetry.

## 4. Enumeration spec

For each pair (A,B) and each encoding E ∈ {none; dual-rail (x, x̄); (x, 1) and (1, x); period-3 (x, 1, 0) and its rotations} and each rest position within the group:

1. Window: the group plus one group on each side (so 3 to 9 cells). Initial states: all encoded contents × skip_in ∈ {0,1}.
2. Compute effect tables for all words up to length L (start L = 8, then 10, then 12), pruning a word as soon as two branches differ in pointer position by more than the window allows or a branch leaves the window.
3. Identity words: effect = (no delta, pointer 0, skip 0) from all skip-0 states. Record them; they are reused.
4. Test each word as FLIP, NEXT, SKIPZ, PREV against the exact criterion of Section 1 (both skip_in values). Encoding invariant: the macro must map encoded windows to encoded windows, including scratch cells.
5. Output per pair: shortest macro per primitive or "none ≤ L", plus the identity-word list. A pair wins when FLIP, NEXT, SKIPZ all exist (report PREV separately).

Cost: effect tables are small (≤ 2^9 · 2 states); words ≤ 12 over 2 letters are 8190 per pair; a few hundred pairs × a handful of encodings is minutes.

## 5. Verification and deliverables for a hit

* Compiler: Brainfuck (or the 4-op subset) → {A,B} program by macro expansion; the program ring is the concatenation. Loops use the same guarded-instruction scheme as the reference 4-op machine (the problem states it as known); the compiler only substitutes macros.
* Simulator: the machine of Section 3 with memory-mapped I/O cells. Test programs: a 3-bit counter, an echo loop, a fixed-length copy. Compare traces against a direct 4-op simulation instruction by instruction at macro boundaries.
* Transistor estimate for the winning pair (write it out for the actual bundle; expected 10–15): 1-bit opcode needs one inverter for decode; skip flag = one D flip-flop (6 T) or two cross-coupled inverters plus gating (4 T); flip = XOR into the cell (one XOR, 4–6 T, or reuse the cell's own toggle input); move = two pass-transistor gates for ±1 on the pointer shift register (2–4 T); clock/enable gating (2 T). PREV free with the near-solution pair.
* ISA statement: one bit per instruction, meaning fixed. FLIP, NEXT, SKIPZ each expand to 2–8 letters; a loop body becomes a run of letters with no visible structure; the skip tail R' means a single-bit error changes control flow. Not hand-writable; programs come from the compiler.

## 6. Fallback if nothing is found at L = 12

Report the exhaustion table (pair × encoding × primitive, shortest macro or none) and the identity-word inventory. Then evaluate the conditional-move family (A = flip, B = move +1 iff cell = 1, and the two-condition variant A = move iff 1, B = flip + move iff 0) against polynomial overhead: implement a 3-state, 2-symbol Turing machine by hand-written {A,B} code with a tape encoding that keeps the pointer able to cross (Lemma 3 says data cells must be paired with a crossable cell), and measure steps per simulated TM step as a function of tape length. Lemma 3 predicts the overhead is at least linear in N per simulated step, i.e. this family gives BCT-like polynomial universality, not constant factor.
