# Tier-4 budget: Machine A and Machine B, switch-level, fully costed

Task: HANDOVER-D.md task 1, under the **revised counting rule** (mid-task
update from the orchestrator): every discrete component counts —
transistors (MOSFET or bipolar), diodes, resistors, capacitors. No ICs or
relays. Any logic style, including dynamic storage (a capacitor holding
the skip flag for one tick, read non-destructively through a MOSFET
gate). Two non-overlapping clock phases from the drive are not counted.
Goal: minimum total component count per machine, from a simulated
schematic.

Code: `sim/budget/switchsim.py` (generic switch-level evaluator),
`sim/budget/machine_a.py`, `sim/budget/machine_b.py` (netlists as data +
per-tick simulation), `sim/budget/test_machine_a.py`,
`sim/budget/test_machine_b.py` (500-trial checks). Full netlists:
`sim/budget/machine_a_netlist.txt`, `sim/budget/machine_b_netlist.txt`.
Logs: `results/budget/*.log`.

## Result summary

| Machine | Transistors | Diodes | Resistors | Capacitors | **Total** | Fits in 4? |
|---|---|---|---|---|---|---|
| A (2-instruction, skip flag) | 5 | 0 | 3 | 1 | **9** | no |
| B (FLIP/NEXT/PREV/SKIPZ) | 11 | 0 | 4 | 1 | **16** | no |

Old-rule data point, kept for comparison (diodes and resistors free, only
transistors billed, the rule this task started under before the
orchestrator's update): a static master-slave latch for the skip flag (2
transistors/stage, giving Q and Qbar for free) plus free diode-AND
combinational logic reproduces the identical truth table verified below
at **4 transistors for Machine A** and **5 transistors for Machine B**
(one extra, forced by needing NOT r for SKIPZ, which only diodes/pure-AND
logic cannot produce — see "what forces it" below; this was true before
the rule change too). This was reasoned by hand from the same logic
equations that the switch-level sims below verify; it was not built as a
second, separately-simulated netlist, since re-costing the *same*
boolean function under a different accounting rule doesn't change its
correctness, only its price.

Neither machine fits in 4 *components* under the new rule, and Machine A
doesn't even fit in 4 *transistors* alone once dynamic storage's access
transistor and the two extra decode switches are counted honestly (see
below). The 4-transistor figure from the old hypothesis was an artifact
of billing only one component type.

## Verification

- Truth table, all `(o or opcode, r, flag)` combinations:
  - Machine A: 8/8 correct (`machine_a_truth_table.log`).
  - Machine B: 16/16 correct (`machine_b_truth_table.log`).
- 500 random dual-rail tapes, macros FLIP/NEXT/PREV/CNEXT/CPREV, checked
  tick-by-tick against `sim/compile/verify_level0_independent.run_l0`:
  **500/500 pass**, tape/pointer/flag identical after every tick
  (`machine_a_macros.log`).
- 500 random single-rail tapes, 4 test programs mixing FLIP/NEXT/PREV and
  SKIPZ-guarded branches, checked tick-by-tick against a from-spec
  reference (`machine_b.reference`, the literal ISA definition): **500/500
  pass** (`machine_b_programs.log`).

## Machine A — design

State: one dynamic bit `S = flagbar` ("execute enabled this tick") on a
capacitor `C_S`; `S` is used *only* as a transistor gate everywhere, so
reading it never draws charge off it (non-destructive read through a
MOSFET gate, as the updated brief asks for).

Evaluate-phase network (shared switch `T_S` gates a node `K` to GND when
`S=1`; three more switches finish paths from `K` to three output nodes):

```
T1 (T_S)   gate=S     a=K          b=GND
T2 (T_o)   gate=o     a=MOVE_P_N   b=K       R1  MOVE_P_N -> VDD
T3 (T_obar)gate=obar  a=MOVE_M_N   b=K       R2  MOVE_M_N -> VDD
T4 (T_r)   gate=r     a=DNODE      b=K       R3  DNODE    -> VDD
```

`MOVE_P_N = NAND(S,o)`, `MOVE_M_N = NAND(S,obar)`, `DNODE = NAND(S,r)`.
Output strobes (polarity stated per wire): `toggle` (active HIGH) is the
bare wire `S` — 0 extra components. `move+ = NOT(MOVE_P_N)`,
`move- = NOT(MOVE_M_N)`. `DNODE` is already the correct new stored value
(`S_next = NAND(S,r)` is exactly `flagbar_next`), so no inverter is
needed on the state-update path either.

Write-back: `T5 (M_write)` gate=`phi_write`, gates `DNODE` onto `C_S`.

### Timing (text diagram)

```
tick t:  |<---------------- phi_eval ---------------->|<--- phi_write --->|
  o,obar,r settle (from program/data memory, this tick's values)
  S stable throughout (== value C_S held after tick t-1's write)
  T1..T4 settle MOVE_P_N, MOVE_M_N, DNODE (single pass, no feedback)
  toggle=S, move+=NOT(MOVE_P_N), move-=NOT(MOVE_M_N) valid for all of tick t
                                                       |  T5 closes:        |
                                                       |  DNODE -> C_S      |
                                                       |  (becomes S for    |
                                                       |   tick t+1)        |
  memory reads r (used above) BEFORE its own toggle takes physical effect;
  the physical flip happens at/after phi_eval closes, i.e. after DNODE
  (computed from the pre-toggle r) has already settled -- satisfies
  "sample r before the toggle".
```

Dynamic-storage assumption (as instructed, values stated explicitly): 1
tick = 1 s; `C_S` a small gate-capacitance node (~0.1–1 pF); MOSFET
off-state leakage assumed low enough (sub-pA class device) that charge
droop over a 1 s hold is negligible against the logic swing. This is the
one physical idealization in the design, parallel to "ideal diodes" in
plain DTL.

### Where the 9 components go

| Role | Components |
|---|---|
| latch (state) | `C_S` (capacitor) + `T5`/M_write (transistor) = 2 |
| shared read switch | `T1`/T_S (transistor) = 1 |
| decode/strobe switches | `T2,T3,T4` (transistors) = 3 |
| pull-ups | `R1,R2,R3` (resistors) = 3 |
| inverters | none — `toggle` is a bare wire; the other two outputs are used in the polarity the interface is defined to accept |

**Total: 9 (5 transistors, 3 resistors, 1 capacitor, 0 diodes).**

## Machine B — design

Same state variable and non-destructive-read discipline. Opcode dual
rail `b1,b0` (encoding FLIP=00, NEXT=01, PREV=10, SKIPZ=11) decoded
directly into each strobe's pulldown chain (no separate is_FLIP/is_NEXT/…
nodes — each is used only once, so precomputing them would only add
resistors for no reuse benefit).

```
T1 (T_S)  gate=S     a=K   b=GND

T2 gate=b1bar a=TOGGLE_N  b=N1   T3 gate=b0bar a=N1  b=K   R1 TOGGLE_N->VDD
T4 gate=b1bar a=MOVE_P_N  b=N2   T5 gate=b0    a=N2  b=K   R2 MOVE_P_N->VDD
T6 gate=b1    a=MOVE_M_N  b=N3   T7 gate=b0bar a=N3  b=K   R3 MOVE_M_N->VDD
T8 gate=b1    a=DNODE     b=N4   T9 gate=b0    a=N4  b=N5
T10 (PMOS) gate=r  a=N5  b=K      -- conducts when r=0     R4 DNODE->VDD

T11 (M_write) gate=phi_write  a=DNODE  b=(C_S node)
C1 (C_S)
```

`TOGGLE_N=NAND(S,is_FLIP)`, `MOVE_P_N=NAND(S,is_NEXT)`,
`MOVE_M_N=NAND(S,is_PREV)`, `DNODE=NAND(S,is_SKIPZ,r==0)`. Strobes:
`toggle=NOT(TOGGLE_N)`, `move+=NOT(MOVE_P_N)`, `move-=NOT(MOVE_M_N)`.
`DNODE` is already the correct `S_next`.

SKIPZ must test `r==0`, and a switch network can only test one polarity
of a given net per device. `T10` is an ordinary MOSFET wired as a PMOS
(conducts when its gate is LOW), gated directly by `r` — this tests
`r==0` for the price of the transistor already needed at that position in
the chain, with **no separate inverter or its pull-up resistor**. (An
NMOS+inverter alternative would cost 2 more components for the same
result — checked, not used.)

### Timing

Identical structure/diagram to Machine A: `phi_eval` settles all four
output nodes from the *old* `S` (stable all through `phi_eval`, since
`T11` is off); `r` is sampled here, before the memory's own toggle takes
effect; `phi_write` closes `T11`, writing `DNODE` into `C_S` for the next
tick. No feedback among gates (all gates are primary inputs or `S`), so
evaluation is a single settling pass.

### Where the 16 components go

| Role | Components |
|---|---|
| latch (state) | `C1` + `T11` = 2 |
| shared read switch | `T1` = 1 |
| decode/strobe switches | `T2..T9` (8) + `T10`, the r==0 PMOS (1) = 9 |
| pull-ups | `R1..R4` = 4 |
| inverters | none — the PMOS on `r` stands in for what would otherwise be a dedicated inverter |

**Total: 16 (11 transistors, 4 resistors, 1 capacitor, 0 diodes).**

## Does either fit in 4?

No, under the new rule, for either machine. What forces the extra cost:

- **The state bit itself is not free.** Even the cheapest legal
  realization — one capacitor + one write-access transistor — is 2
  components before any logic exists at all.
- **Reading the state without disturbing it costs a transistor per use.**
  Because `S` may only ever be a transistor *gate* (never a diode or
  pass-transistor current path, or its tiny charge would be perturbed on
  every read), each place the machine needs "if S then …" is a
  transistor, not a free diode. Sharing the single `S`-gated switch
  (`T_S`/`K`) across all of a machine's strobes saves transistors (used
  in both designs) but doesn't eliminate the need for at least one.
- **Opcode decode costs one switch per bit tested per strobe.** Machine
  A's single opcode bit is nearly free (o/obar already dual rail; `toggle`
  needs no gate at all). Machine B's four-way opcode decode needs 2–3
  series switches per strobe (2 bits for FLIP/NEXT/PREV, 3 nets — 2 opcode
  bits plus r — for SKIPZ), which is where most of its extra cost over
  Machine A comes from.
- **SKIPZ needs the complement of r, and only r is offered.** Diode/AND
  logic is monotonic and cannot invert; some device gated the "wrong way"
  (an inverter, or here a PMOS gated directly by r) is unavoidable. This
  is the one place Machine B pays for something Machine A never needs
  (Machine A's flag update uses `r` directly, never `NOT r`, because its
  tape is dual-rail).
- **Every pull-up is now billed.** Under the old free-diode/resistor rule
  this cost nothing; now each of the 3 (Machine A) or 4 (Machine B)
  evaluate nodes needs a resistor to hold it when its pulldown path is
  open.

Smallest counts reached: **Machine A = 9 components (5 transistors, 3
resistors, 1 capacitor)**; **Machine B = 16 components (11 transistors, 4
resistors, 1 capacitor)**. Both are switch-level simulated and pass the
full truth table plus 500/500 tick-by-tick trials against the reference
machines.
