# Handover B: two-instruction pointer machines

Supersedes PLAN-2op.md. Setting: cyclic bit tape with one pointer, cyclic program ring of 1-bit instructions, one per tick, memory-mapped I/O, instruction meaning position-independent (no phase bit). Primary target: pairs with one skip flag. Secondary: stateless pairs.

Question: does a pair (A, B) admit exact, rejoining macros for FLIP, NEXT, SKIPZ (PREV reported separately) under one fixed tape encoding from {none, dual rail, scratch cell, period-3 groups}? Exhaustive over the semantics menu, words to length 12.

## 0. Two corrections to the statement

**The bijectivity filter removes nothing.** Every conditional component is non-injective on (tape, pointer, flag). "Move +1 iff cell = 1" sends both (t, p) with t[p] = 0 and (t, p−1) with t[p−1] = 1 to (t, p). "Skip iff cell = v" collides a suppressed instruction with an executed one. The injective bundles are exactly flip plus unconditional moves, and a pair of those has a data-independent effect, dead for the trivial reason. {flip, move-iff-1} is not a bijective pair. The correct constraint is the converse: an exact macro for a guarded FLIP (SKIPZ·FLIP from cell 1 clears it) needs a non-injective instruction, and every pair with a condition already has one. Bijectivity also does not rule out universality: reversible machines are universal at Bennett-style overhead. It rules out exact macros for irreversible primitives. REPORT.md §4 item 1 overstated this and is corrected.

**The partial result pair is dead for constant factor.** A = NEXT, B = (flip; skip iff old = 1) has no −1 move. On (cell, pending skip) the letter B acts as the 3-cycle (0,0) → (1,0) → (0,1) → (0,0), with (1,1) → (1,0). SKIPZ from skip 0 needs (0,0) → (0,1), so n ≡ 2 (mod 3) B's, and (1,0) → (1,0), so n ≡ 0 (mod 3). Any A executed in a branch moves +1 with no way back except N ticks. Encodings cannot help because only one cell is touched. Do not build on this pair. Start from the near-solution in §2.

## 1. Lemmas (skip-flag pairs)

**a·R form.** A pending skip suppresses only the first letter of a macro. So every macro longer than one letter is a·R with R an identity word from skip 0 (all encoded windows: no tape change, pointer 0, skip out 0). In every branch where a sets no skip, the macro's effect is a's effect alone. Consequences: some letter must be exactly "flip, no move, no skip" in some branch (FLIP), and some letter exactly "+1, no flip, no skip" in some branch (NEXT). The exception is a first letter that tests a constant cell of the encoding and skips in every branch. The skip is the only rejoin mechanism. Enumerate identity words first; all three macros reuse them.

**A −1 move is necessary.** FLIP and SKIPZ have pointer delta 0 in every branch. Without a −1 component, no executed letter in them may move, so they are words in the non-moving letter on one cell, and the 3-cycle argument of §0 generalises: a one-cell word's effect on (cell, skip) is a power of one map on 4 states and cannot match both SKIPZ branches. Run the no-−1 subspace anyway to confirm exhaustion; do not expect hits.

**Crossing.** A cell crossed by NEXT satisfies the mover's condition at crossing time, and with net zero flips that is its original value. A pair whose only +1 is "move iff cell = v" cannot do exact NEXT over a data cell holding ¬v unless a −1 returns to undo a flip. So conditional +1 needs an encoding with a crossable constant cell in every group.

## 1b. Correction after the first run: compile guarded pairs jointly

Under the strict criterion above (SKIPZ as a standalone macro, every macro skip-safe), the a·R lemma forces a macro's first letter to equal the primitive in its no-skip branches. No letter of the near-solution in §2 is a pure flip or a pure +1, so §2 cannot succeed under the strict criterion. The step 1 search confirmed this: none of 160 configurations produced even one skip-safe primitive.

The strict criterion is stronger than constant-factor compilation needs. Compile "SKIPZ X" jointly as one guarded macro CX. The flag is then internal to macros, every macro starts and ends with the flag clear, and the target set is FLIP, NEXT, PREV, CFLIP (clear if 1), CNEXT, CPREV, the same as §6 but with the skip available inside macros. This guarded criterion is the primary one. The strict criterion is kept as a stronger result: a pair that passes it also compiles the reference program without joint compilation.

## 2. Near-solution (valid under the guarded criterion only)

A = (flip, then +1), B = (−1), no skip, no encoding:

    FLIP = A B        NEXT = A B A        PREV = B

exact and branch-free (A flips the cell it leaves; ABA leaves c flipped twice). Only SKIPZ is missing. Add one skip test to A or B, before or after the move (i.e. on the departure or arrival cell), testing 0 or 1. The test then lands on a neighbour in half the uses, which the scratch encodings (x,1), (1,x), (x,0), (0,x) make a constant. This is 2 base pairs (also A = (+1, then flip arrival)) × 2 letters × 2 placements × 2 values × 4 scratch encodings × 2 rest positions, words to length 8. Run it before the full menu.

Hand-checked dead ends, do not repeat: with B = (skip iff cell = 0, then −1) under (x,1), AB is FLIP from skip 0 but not from skip 1; ABAB is an identity word but neither A·ABAB nor B·ABAB is FLIP. With B = (−1, then skip iff arrival = 0) under (1,x), ABAB from x = 0 is exactly the SKIPZ zero-branch, but the x = 1 branch flips x and ends at −1.

## 3. Full menu (skip-flag)

Bundle = ordered sub-ops from: flip (current cell); move ∈ {+1, −1} with condition ∈ {always, iff cell = 0, iff cell = 1} on the cell under the pointer at that moment; skip-test (set flag iff cell = v at that moment). Up to 6 orders per bundle. Semantics: an instruction fetched with the flag set does nothing and clears it. Deduplicate bundles by effect table on (cell, left, right, flag). Keep pairs with a −1 component somewhere; mod out mirror (±1 swap) and complement (0/1 swap in every condition and encoding).

## 4. Enumeration spec

Per pair, encoding E ∈ {none; (x, x̄), (x̄, x); (x,1), (1,x), (x,0), (0,x); period-3 with one data cell and two constants, all arrangements}, rest position:

1. Window = group plus one group each side. States = all valid encodings × flag ∈ {0,1}.
2. Effect tables for all words to L = 8, then 10, then 12. Prune a word when any branch leaves the window.
3. Identity words (skip 0 → no change, delta 0, skip out 0) listed first.
4. Test each word against FLIP, NEXT, SKIPZ, PREV: skip_in = 0 gives the primitive, skip_in = 1 gives identity with skip out 0, all windows map to valid encodings.
5. Output: pair × encoding × primitive → shortest macro or "none ≤ L". A pair wins with FLIP, NEXT, SKIPZ under one encoding and rest position.

## 5. Deliverables for a hit

* Compiler: Brainfuck → 4-op by the reference scheme, then macro substitution. Precondition: write down the reference loop scheme and list the SKIPZ·X combinations it emits (and whether it ever emits SKIPZ SKIPZ). The a·R lemma makes every X macro skip-safe, but that list is the test set.
* Simulator with memory-mapped I/O; run a 3-bit counter and an echo loop; compare against a 4-op simulation at macro boundaries.
* Transistors, write out for the actual bundle: decode 1 inverter (2 T), flag flip-flop (4–6 T), flip = XOR/toggle enable into the cell (4–6 T), ±1 move pass gates with condition from the cell line (2–4 T), clock gating (2 T). About 14–20 for the near-solution plus skip; below 10 is not plausible with a flag.
* ISA statement: one bit per instruction; each logical op is 2–12 letters; the skip tail makes a single-bit error change control flow invisibly. Not hand-writable. Programs come from the compiler.

## 6. Secondary: stateless pairs

Same enumeration with the skip sub-op removed. No flag means SKIPZ has no meaning: the targets become FLIP, NEXT, PREV and CX = "X iff cell = 1" for every X the reference compiler emits after SKIPZ. CFLIP (= clear-if-1 on its own cell) is the hard one. Lemmas: one letter carries +1, the other −1, at least one conditional, flip bundled with one or both (about 60 pairs after symmetry). Branches live only in pointer position and meet on position; the typical rejoin is a sweep whose cost per group is value-independent, e.g. A = (flip, +1 iff new = 1) costs 1 on a 0-cell and 2 on a 1-cell, so a dual-rail group always costs 3, but leaves (1,1) behind. Hand result: A = (flip, +1 iff new = 1), B = (−1 iff cell = 1) under (x,1) gives FLIP = AB exactly; NEXT not found by hand.

## 7. If both exhaust at L = 12

Report the tables and the identity-word inventory. Then evaluate the pure conditional-move family (A = flip, B = +1 iff cell = 1) for polynomial overhead by hand-coding a 3-state 2-symbol Turing machine with a crossable encoding. The crossing lemma predicts cost at least linear in N per simulated step: BCT-like polynomial universality, not constant factor.
