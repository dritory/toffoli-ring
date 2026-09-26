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

Overhead: program length O(|Q|²) per group, independent of tape length; one sweep costs O(tape length), so the slowdown is polynomial (linear in tape length per step in the worst case). Constant factor per TM step is not yet implemented (milestone 2 in the compiler task).

Hardware estimate: skip flip-flop, one gate to arm the skip from the cell value, enable gating for flip and move, opcode drives the move direction. Estimated 5–8 transistors; not yet checked against a schematic.
