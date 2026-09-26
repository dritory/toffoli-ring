# Handover C: NAND drum with a program loop

Follows PLAN.md (NAND results) and REPORT.md §1. Goal: the fewest transistors outside memory. Memory and program memory are free.

## 0. Machine

Data drum: N bistable cells, read taps at i and i+1, write tap at i+k, one NAND. Program loop: P cells, read one per tick, advancing in step with the drum. At global tick τ (pass t = ⌊τ/N⌋, cell i = τ mod N):

    if p[τ mod P] = 1:  s[i+k] ← NAND(s[i], s[i+1])       else: s[i+k] unchanged

Hardware: one NAND transistor; the program bit gates the write strobe (diode AND with the clock, or one transistor if drive requires it). 1–2 transistors plus the clock.

**The program loop must be a separate loop of length P, not a second track on the data drum.** A track on the drum has period N, so the enable pattern would be the same every pass. That is the dead case below.

## 1. Theorems to rely on (prove in the write-up; they are short)

**Helix recurrence.** With e_τ the value of the target cell after tick τ:

    e_τ = p(τ mod P) ? NAND(e_{τ−k}, e_{τ−k+1}) : e_{τ−N}.

**Dead case: P divides N.** Then each cell is always written or never written. Never-written cells are constants. Written cells are overwritten before they are read (a write to cell c happens at tick c−k, before its reads at ticks c−1 and c), so across passes the only carried state is the k-cell window at the seam: Lemma A of PLAN.md, period ≤ 2^k.

**Static frame for N = mP − 1.** Put M = N + 1 = mP and write τ = rM + x (row r, column x ∈ [0, M)). Then the enable is p(x mod P), the same in every row, and

    copy site  (p = 0):  u_r(x) = u_{r−1}(x + 1)                  value moves left one site per row
    gate site  (p = 1):  u_r(x) = NAND(u_r(x−k), u_r(x−k+1))      evaluated left to right within a row

with a single twist at the row boundary x = 0 / M−1. In this frame the machine is a static ring of m identical blocks of P sites. Copy sites are delay lines moving data left; gate sites are combinational logic moving data right within a row. The row twist is harmless when the block at the boundary is in a stationary state (values that do not change from row to row), e.g. blank tape.

Verify all three numerically before building on them (task 1).

## 2. Why this should be universal

Per block and per row, the block's new values are computed from its own copy sites (holding values that were one site to the right last row, i.e. part of its own old state plus one bit of the right neighbour's) and from the left neighbour's new values if the block's first gates read that far left. Making the first k sites of each block copy sites removes the left dependence, so over G rows the block rule is a synchronous one-sided CA with the right neighbour as input, and the configuration drifts left one block per P rows. One-sided CAs with enough states are universal: simulate a Turing machine encoded as a CA, with the head carrying its state and the tape drifting. Design the block (the program p) so one TM step takes a constant number of rows.

Useful facts for block design:
* NOT needs its input on two adjacent sites: NAND(y, y). A value held for two rows on a copy chain appears on two adjacent sites, so hold every logical value for at least two rows (time-redundant encoding) or carry it dual.
* A value leaves a gate at site x and is captured next row by the copy site at x−1, if x−1 is a copy site. That is the only way a gate output survives a row.
* Constants: a copy chain fed by NAND(y, NOT y) regenerates 1s; keep a constant rail per block if the design needs it.

## 2b. Correction after the gadget search

The sketch in §2 assumed left-moving data flows freely along copy chains. It does not: a copy site at x reads x+1, and a gate site reads only to its left, so data arriving from the right stops at the first gate site. It continues only if gates to its right pick it up and re-emit it, which sends it rightward. Measured with s = 1 (N = mP − 1): right-movers at about 3.7 sites per row, left-movers only in rare programs at about 0.5 sites per row, no stationary memory, and interactions whose output depends on both inputs (k = 3 only). Universality of the program drum is therefore not established. Follow-up: vary the slide s (N = mP − s, copy sites read x + s) and search for multi-site memory structures.

## 3. Tasks for the cheap models

1. Simulator of the machine exactly as in §0, plus the helix and static-frame forms; check all three agree on random (N, P, k, p, s₀) with N = mP − 1, and that P | N dies (helix-period test from `sim/nand/helix.py`: e_τ = e_{τ−M} for small M after a short transient).
2. Gadget search in the static frame: for k = 2, 3 and block programs p of length P ≤ 16 (all 2^P), classify each block's behaviour on the stationary blank background and with a single injected bit: dies, holds (memory cell), moves left, moves right, copies. Report the cheapest program for each gadget type. This is exhaustive and cheap.
3. From the gadgets, build a block program that implements one step of a fixed small TM (start with a 2-state 2-symbol machine that counts in binary), with one TM step per G rows. Test on a binary counter for 1000 steps, then an echo machine that copies a memory-mapped input cell to an output cell.
4. Report: P, k, m range tested, G (rows per TM step), ticks per TM step as a function of tape length (expected O(N) per step since a row is N ticks), and the transistor count (NAND + strobe gating).

## 4. Deliverables

A program loop pattern p, a drum length rule N = mP − 1, a TM-to-p compiler for small machines, a simulator run showing the counter and the echo, and a one-paragraph plaque statement: "one NAND gate and a program loop; memory and program excluded; universal with polynomial slowdown; program is the loop pattern, input is the initial drum".
