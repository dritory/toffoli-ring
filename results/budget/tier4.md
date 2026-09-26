# Tier-4 budget: Machine A and Machine B, switch-level, fully costed

Task: HANDOVER-D.md task 1, under the revised counting rule (every
discrete component counts — transistors, diodes, resistors, capacitors;
no ICs/relays; dynamic storage allowed, read non-destructively through a
MOSFET gate). Two non-overlapping clock phases from the drive are not
counted. Goal: minimum total component count per machine, from a
switch-level simulated schematic.

**This revision replaces the 9- and 16-component figures reported
earlier — those designs were wrong, not just uncounted differently.**
See "What was wrong" below.

Code: `sim/budget/switchsim.py` (generic switch-level evaluator, now with
a not-driven/floating-net check and a non-convergence check),
`sim/budget/storage.py` (the shared master-slave dynamic storage cell),
`sim/budget/machine_a.py`, `sim/budget/machine_b.py` (netlists as data +
explicit two-phase simulation), `sim/budget/test_machine_a.py`,
`sim/budget/test_machine_b.py` (500-trial tick-by-tick checks),
`sim/budget/demo_bad_timing.py` (shows the harness catches a
wrong-order read of r). Netlists: `sim/budget/machine_a_netlist.txt`,
`sim/budget/machine_b_netlist.txt`. Logs: `results/budget/*.log`.

## What was wrong, and the fix

The first pass used one capacitor `S` for the flag, written directly
from the eval network's own output (`DNODE = NAND(S, r)`) through a
single phase-gated access transistor, while `T1..T4` (the network
computing `DNODE` from `S`, `o`, `r`) were treated as if they only ran
during the read phase. They don't: nothing in that design turns them
off, so during the write phase `S` is being overwritten *while the same
live network is still reading the old-and-changing `S` as a transistor
gate* — a direct combinational loop, `S <- NAND(S, r)`. For `r=1` this
is a one-stage ring oscillator (`S <- NOT(S)`), not a latch, and even
where it happened to settle it could end up sampling `r` from *after*
the memory's own toggle for that tick, i.e. the wrong value.

This is confirmed, not just argued: feeding that exact single-capacitor
netlist through the corrected `switchsim.evaluate()` (which now insists
on reaching a fixed point) raises `did not converge in 8 iterations —
likely a combinational feedback loop`. See
`results/budget/single_capacitor_bug_repro.log`.

**Fix — true master-slave storage (`sim/budget/storage.py`):** two
capacitors, `M` (master) and `S` (slave), never directly shorted
together.

```
DNODE --T_wm(gate=phi1)--> M --T_buf(gate=M, NMOS to GND)--> BUF_NODE --T_ws(gate=phi2)--> S
                                  + R_buf(BUF_NODE->VDD)
```

- Phase 1: the eval network computes `DNODE` from the *old, stable* `S`
  (nothing writes `S` this phase — `T_ws`'s gate, `phi2`, is 0). `T_wm`
  is closed (`phi1`=1), so `M` is set to `DNODE`.
- Phase 2: `T_wm` opens, so `M` is now isolated from the still-live
  network — whatever `DNODE` does while `S` is changing this phase can
  no longer reach `M`. `T_buf` reads `M` non-destructively (a gate, not
  a current path) and drives `BUF_NODE = NOT(M)`, a robustly-driven
  signal. `T_ws` closes (`phi2`=1) and copies `BUF_NODE` into `S`. `M`
  and `S` are never electrically shorted to each other (`phi1`,`phi2`
  never overlap and `T_buf` always sits between them), so there is no
  capacitor-to-capacitor charge-sharing to model.
- Choosing the slave to store `flag` (not `flagbar`) makes `T_S` a PMOS
  gated by `S` at no extra cost, and a NAND-stack's built-in inversion
  then lands `DNODE` on exactly `flagbar_next`; `T_buf`'s one inversion
  turns that back into `flag_next` for `S`. **One** buffering inverter
  is enough, not two, because the two inversions (NAND-stack, then
  buffer) are exactly the two needed to get from `flagbar_next` to
  `flag_next`.

Memory-interface timing, stated precisely and simulated that way: `r`
is read once, during phase 1, from the cell under the pointer *before*
this tick's toggle/move are applied; `toggle`/`move+`/`move-` are valid
signals throughout phase 1 and are captured by the memory (its own
circuitry, excluded from the count) at the phase-1→phase-2 boundary;
the memory performs the actual toggle and pointer move during/after
phase 2. So a tick's `r` always reflects the pre-toggle cell, matching
`run_l0`/the spec exactly, and — checked directly —
`sim/budget/demo_bad_timing.py` reads `r` from the *post*-toggle cell
instead and diverges from the reference on essentially every tick
(`results/budget/timing_sensitivity_demo.log`): the harness is not
vacuous, it actually catches this class of bug.

## Result summary (corrected)

| Machine | Transistors | Diodes | Resistors | Capacitors | **Total** | Fits in 4? |
|---|---|---|---|---|---|---|
| A (2-instruction, skip flag) | 7 | 0 | 4 | 2 | **13** | no |
| B (FLIP/NEXT/PREV/SKIPZ) | 13 | 0 | 5 | 2 | **20** | no |

(Superseded old-rule data point, unaffected by this bug since it used a
*static* cross-coupled master-slave latch rather than a bare capacitor —
kept only as a reference point, not re-simulated: diodes/resistors
free, only transistors billed, gives 4 transistors for Machine A and 5
for Machine B. That style of latch does not have this race, because
each stage's own cross-coupled pair, not a bare wire back to the
network, holds the state — but it is not directly comparable, since it
uses free diodes and resistors that the current rule bills.)

## Verification (re-run under the corrected, phase-explicit simulator)

- Truth table, all `(o or opcode, r, flag)` combinations:
  - Machine A: 8/8 correct (`machine_a_truth_table.log`).
  - Machine B: 16/16 correct (`machine_b_truth_table.log`).
- 500 random dual-rail tapes, macros FLIP/NEXT/PREV/CNEXT/CPREV, checked
  tick-by-tick against `sim/compile/verify_level0_independent.run_l0`:
  **500/500 pass** (`machine_a_macros.log`).
- 500 random single-rail tapes, 4 programs mixing FLIP/NEXT/PREV/SKIPZ,
  checked tick-by-tick against a from-spec reference: **500/500 pass**
  (`machine_b_programs.log`).
- Floating-net / no-implicit-storage check: `switchsim.evaluate()` now
  requires every net that is a transistor gate, a resistor-loaded node,
  or a primary input to resolve to 0/1 every phase, unless the caller
  explicitly says it may hold via a capacitor (see `switchsim.py`'s
  `holdable` and the required-net check); it raised no such error on
  either machine's corrected design. Pure pass-through junctions between
  series switches (`K`, `N_tog1`, …) are exempt from this requirement —
  they are never a gate or a resistor-loaded node, carry no logical
  meaning across a phase, and are freshly resolved by connectivity every
  time, so "floating" there is electrically harmless (an open switch
  anywhere else in the same series path already breaks conduction
  regardless of that node's charge).
- Non-convergence check: reproduced the original buggy single-capacitor
  netlist directly against the corrected evaluator and confirmed it is
  rejected (`results/budget/single_capacitor_bug_repro.log`).

## Machine A — corrected design

State: `S` (slave) stores `flag`; `M` (master) holds `flagbar_next`
between phases (see storage.py above). Eval network, always live in
both phases:

```
T1 (T_S,PMOS) gate=S   a=K         b=GND     R1 MOVE_P_N->VDD
T2 (T_o)      gate=o   a=MOVE_P_N  b=K       R2 MOVE_M_N->VDD
T3 (T_obar)   gate=obar a=MOVE_M_N b=K       R3 DNODE->VDD
T4 (T_r)      gate=r   a=DNODE    b=K
```

`toggle` (active low, bare wire `S`) needs no extra components.
`move+ = NOT(MOVE_P_N)`, `move- = NOT(MOVE_M_N)`. `DNODE` feeds the
storage cell (`T5=T_wm, T6=T_buf, T7=T_ws, R4=R_buf, C1=C_M, C2=C_S`),
never directly into `S`.

### Timing (text diagram)

```
tick t:  |<---------------- phi1 ---------------->|<---------------- phi2 ---------------->|
  o,obar,r settle (held by memory for the whole tick)
  S stable throughout phi1 (T7/phi2 is 0, nothing writes it)
  T1..T4 settle MOVE_P_N, MOVE_M_N, DNODE from this stable S and r
  T5 closed (phi1=1): M := DNODE  (= flagbar_next, correct)
  toggle=NOT(S), move+, move- valid for all of phi1; memory latches
  them at the phi1->phi2 boundary and acts during/after phi2 -- so this
  tick's r (used above) is always the PRE-toggle value.
                                            |  T5 opens: M holds.        |
                                            |  T6 (live) reads M,        |
                                            |  BUF_NODE=NOT(M)=flag_next |
                                            |  T7 closed: S:=BUF_NODE    |
                                            |  (becomes flag for t+1)    |
                                            |  T1..T4 keep recomputing   |
                                            |  against the now-changing  |
                                            |  S, but DNODE cannot reach |
                                            |  M (T5 open) -- no loop.   |
```

Dynamic-storage assumption (stated explicitly): 1 tick = 1 s; `C_M`,
`C_S` small gate-capacitance nodes (~0.1–1 pF); MOSFET off-state leakage
assumed low enough (sub-pA class device) that droop over a 1 s hold is
negligible. `M` and `S` are each driven by exactly one access
transistor and never merged with each other or anything else, so no
capacitance-ratio modelling is needed.

### Where the 13 components go

| Role | Components |
|---|---|
| latch (2 capacitors + isolation/buffer) | `C1,C2,T5,T6,T7` = 5 |
| shared read switch | `T1`/T_S = 1 |
| decode/strobe switches | `T2,T3,T4` = 3 |
| pull-ups | `R1..R4` = 4 |
| inverters | `T6` (the M/S buffer; nothing else needs one) |

**Total: 13 (7 transistors, 4 resistors, 2 capacitors, 0 diodes).**

## Machine B — corrected design

Same storage cell. Opcode decode (`b1,b0`: FLIP=00 NEXT=01 PREV=10
SKIPZ=11) folded directly into each strobe's series chain (each decode
is used once, so precomputing shared nodes doesn't pay for itself):

```
T1(T_S,PMOS) gate=S  a=K  b=GND
T2 gate=b1bar a=TOGGLE_N b=N1   T3 gate=b0bar a=N1  b=K   R1 TOGGLE_N->VDD
T4 gate=b1bar a=MOVE_P_N b=N2   T5 gate=b0    a=N2  b=K   R2 MOVE_P_N->VDD
T6 gate=b1    a=MOVE_M_N b=N3   T7 gate=b0bar a=N3  b=K   R3 MOVE_M_N->VDD
T8 gate=b1    a=DNODE    b=N4   T9 gate=b0    a=N4  b=N5
T10(PMOS) gate=r a=N5 b=K  -- conducts iff r=0             R4 DNODE->VDD
+ storage cell: T11=T_wm, T12=T_buf, T13=T_ws, R5=R_buf, C1=C_M, C2=C_S
```

SKIPZ's `r==0` test again costs nothing beyond the transistor already
needed at that chain position (`T10`, wired as a PMOS gated directly by
`r`, instead of a separate inverter). Timing diagram: identical
structure to Machine A's above, `r` sampled during phi1 before the
memory's own toggle.

### Where the 20 components go

| Role | Components |
|---|---|
| latch (2 capacitors + isolation/buffer) | `C1,C2,T11,T12,T13` = 5 |
| shared read switch | `T1`/T_S = 1 |
| decode/strobe switches | `T2..T9` (8) + `T10` (r==0 PMOS) = 9 |
| pull-ups | `R1..R5` = 5 |
| inverters | `T12` (the M/S buffer only) |

**Total: 20 (13 transistors, 5 resistors, 2 capacitors, 0 diodes).**

## Does either fit in 4?

No. What forces the extra cost, updated for the master-slave fix:

- **A race-free state bit needs two capacitors, not one.** A single
  dynamic node cannot be both "read stably by a live network" and
  "written by that same live network's output" without a feedback loop
  (proven above, and reproduced as a non-convergence error). The
  cheapest race-free realization is master + slave: 2 capacitors + 2
  access transistors + 1 buffering inverter (+ its pull-up) = 6
  components, before any of the machine's own logic exists.
- **The buffer is unavoidable, but only needs to be one transistor
  deep**, because a NAND-stack's built-in inversion (used for the eval
  network's own output) and the storage cell's own inversion cancel out
  correctly if the slave stores `flag` and the master stores
  `flagbar_next` — a polarity choice that costs nothing extra (`T_S`
  becomes a PMOS instead of an NMOS, same component count) but saves an
  entire second buffering stage.
- **Reading the state without disturbing it still costs a transistor
  per use**, same as before: `S` is only ever a gate, sharing one switch
  (`T_S`/`K`) across a machine's strobes.
- **Opcode decode** costs one series switch per opcode bit tested per
  strobe — Machine A's single opcode bit is nearly free; Machine B's
  four-way decode needs 2–3 series switches per strobe, which is most
  of its extra cost over Machine A.
- **SKIPZ needs `NOT r`, and only `r` is offered** — met at zero extra
  cost with a PMOS gated directly by `r`, rather than a dedicated
  inverter.
- **Every pull-up is billed.**

Smallest counts reached, both switch-level simulated with a true
race-free master-slave storage cell, both passing the full truth table
and 500/500 tick-by-tick trials against the reference machines:
**Machine A = 13 components (7 transistors, 4 resistors, 2
capacitors)**; **Machine B = 20 components (13 transistors, 5
resistors, 2 capacitors)**.
