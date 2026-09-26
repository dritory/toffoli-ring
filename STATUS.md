# Status

| System | Verdict | Basis |
|---|---|---|
| Toffoli drum, fixed rule (k = 2..5) | open; k = 2 conjectured not universal | REPORT.md: no vacuum gliders, no silent signals, random-permutation cycle statistics for k = 2 |
| NAND drum, fixed rule, any tap geometry | **not universal** | PLAN.md: the ring is never read (k-bit register), write-between and write-behind collapse; verified |
| NAND drum + target diode (R3) | **not universal** (empirically) | collapses to a helical rotation within 7 passes in 5197/5200 runs |
| NAND drum + program loop | not established, parked | HANDOVER-C.md: movers exist, but no program has both directions; no resettable bit |
| Drum + 1-bit latch | inconclusive, parked | HANDOVER-A.md, results/latch |
| Two-instruction CPU, no skip flag | no working pair to length 12 | exhaustive, complete window |
| Two-instruction CPU, skip flag, strict macros | no working pair | exhaustive over 1017 pairs x 49 encodings |
| **Two-instruction CPU, skip flag, guarded macros** | **universal, runs Turing machines** | see below |

## The working machine

One opcode bit. Both instructions: flip the cell under the pointer; if it is now 0, skip the next instruction; move one cell. A moves right, B moves left. A skipped instruction does nothing and clears the skip.

Tape: each logical bit x is two cells (x, not x).

Macros (exact, verified on random tapes): FLIP = ABB, NEXT = ABBAAA, PREV = BAABBBABBABB, step right iff 1 = ABBAAB, step left iff 1 = ABBABABAABBB. Gates built from them in the reference machine: CNOT at any distance, Toffoli, CLEAR (`sim/compile/`).

Compiler: `sim/compile/sweep.py` turns a Turing machine into one fixed cyclic program (the pointer sweeps one group per pass; the head's group applies the transition). Verified at the reference level against a direct TM after every step (counter 300 steps, echo 50 steps, BB(2,2) to halt), and at the hardware level by an independent simulator (`sim/compile/verify_level0_independent.py`): tape and pointer identical to the reference run after every group visit; BB(2,2) halts with 4 ones in 6 steps; the counter counts.

Overhead: **constant per TM step.** The head-following compiler (`sim/compile/follow.py`) makes one pass of the program exactly one TM step: the pointer moves to the head's new group by a guarded-move chain, and the pass word does not depend on tape length. Measured at the hardware level:

| Machine | States | Group width | Ticks per TM step at 12 / 24 / 48 groups |
|---|---|---|---|
| counter | 4 | 150 | 120,750 / 120,750 / 120,750 |
| echo | 3 | 119 | 95,880 / 95,880 / 95,880 |
| BB(2,2) | 3 | 119 | 74,808 / 74,808 / 74,808 |

Verified twice: by the compiler's own verifier at both levels (`sim/compile/verify_follow.py`), and by an independent hardware simulator that decodes the tape, head and state after every step and compares them with the direct Turing machine (`sim/compile/verify_follow_independent.py`: counter 300 steps and BB(2,2) to halt, at 12, 24 and 48 groups). Program length grows as O(|Q|²) with the number of TM states. Space: one group of 12 + 31·|Q| + 14 logical bits (twice that in cells) per tape cell. Not supported yet: a rule that stays in place and changes state; rings under 3 groups.

Hardware: **11 components** (6 transistors, 3 resistors, 2 capacitors; `sim/budget/minimal/`), down from 13 (7 transistors, 4 resistors, 2 capacitors, 0 diodes), from a switch-level simulated schematic with explicit two-phase timing and a master-slave dynamic flag (`sim/budget/machine_a_netlist.txt`, `results/budget/tier4.md`). Verified tick by tick against the reference machine on 500 random tapes. The four-instruction reference machine (FLIP, NEXT, PREV, SKIPZ) takes 20 components (13 transistors, 5 resistors, 2 capacitors). These are the best designs found, not proven minima. Assumes MOSFET leakage low enough for a 1-second hold on the flag capacitors.
