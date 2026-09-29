# Block-skip CPU: fewest components

ISA: FLIP, NEXT, PREV, IFZ (if cell = 0 enter skip mode), MARK (no-op, ends
skip mode). In skip mode every instruction is suppressed until a MARK, which
clears skip mode and is itself a no-op. The program ring advances +1 every tick
(so there is no program-pointer output). One state bit S. Opcodes arrive
one-hot in both polarities from program memory (free). Data interface as before:
input `r`; outputs toggle / move_plus / move_minus (active-low nets, like
`MOVE_P_N` in trick3, in the resistor technologies).

Code: `sim/budget/blockskip/` (`ref.py` behavioural reference, `machine_nmos.py`,
`machine_nmos_skip1.py`, `machine_dtl.py` + `dtl_dc.py` DC solver, `machine_cmos*.py`,
tests `test_*.py`, `*minimality*.py`, `nmos_led_dc.py`, `dtl_check.py`,
`programs.py`, `run_programs*.py`).

## Result

| Design | Transistors | Resistors | LEDs | Notes |
|---|---|---|---|---|
| **A. NMOS resistor-load + static latch, block-skip** | **10** | 6 | 6 (indicators) | phi2-gated, hazard-safe |
| A'. same, ungated (ideal tick only) | 9 | 6 | 6 (indicators) | glitches at real tick boundaries |
| A-skip1. NMOS, skip-one variant | 16 | 7 | 7 (indicators) | needs master-slave (trick3 structure) |
| **B. LED diode-transistor logic, 12 V, block-skip** | **3** | 9 | 15 (logic) | phi2-gated |
| B'. same, ungated | 3 | 8 | 12 (logic) | ideal tick only |
| C. CMOS (secondary), block-skip, pass-gate strobes | 23 | - | - | full complementary |
| C'. CMOS, restoring NOR strobes | 26 | - | - | |
| C-skip1. CMOS skip-one | 31 (34 with NOR strobes) | - | - | master-slave 16 T + NOR3 + strobes |

Block-skip is cheaper than skip-one in every technology (10 T vs 16 T in NMOS,
23 vs 31 in CMOS). Reason: block-skip's set and reset conditions do not depend on S
(set = K and r=0, reset = MK; K and MK are one-hot so they never coincide), so the
state is one SR latch with no master stage. Skip-one must clear S one tick later
but not re-set it when the skipped instruction is itself an IFZ, so its next state
depends on S and needs a real one-tick delay (master-slave).

## A. NMOS design (10 T, 6 R)

```
hold pair   Ts1 (gate Qb: Q->GND)   Ts2 (gate Q: Qb->GND)      R_Q, R_Qb      Q = S
RB          T_r (gate r: RB->GND)                              R_RB           RB = NOT r
set  S:=1   Qb -K- . -RB- X        (K and r==0)
reset S:=0  Q  -MK- X
tail        X -phi2- GND            (one tail shared by set and reset)
strobes     TGN -F- Q,  MPN -N- Q,  MMN -P- Q      R_TGN, R_MPN, R_MMN
```

* Strobe = one pass transistor from the strobe net to Q, plus its pull-up: net =
  NOT(op) OR S, i.e. low exactly when op is active and S=0. 1 T + 1 R per strobe
  (a NAND would be 2 T; sharing a Nm tail as in trick3 gives 4 T for the three,
  this gives 3 T). S changes only in phi2 of K/MK ticks, when F/N/P are 0, so the
  strobes are glitch-free in both phases (asserted in the test).
* The shared write tail is safe (contrast with static.md's Trick 2 finding): K and
  MK are primary one-hot lines, so the set and reset branches can never both
  conduct; RB is derived but only sits in the K branch.
* Folding the master into the logic: not needed. The gating by phi2 makes S's
  next state independent of S, which removes the whole master stage (trick3 spent
  9 T and 3 R on master + slave for the same job). Ungated is 1 T cheaper but a
  real ring changes lines at different times: with skip mode on and F falling
  while MK rises, the ungated latch resets early and pulses the toggle strobe (shown
  in `glitch_minimality_nmos.py`: unclocked `Q=0 toggle_strobe=1`, clocked
  `Q=1 toggle_strobe=0`). Also a wandering `r` while K is present would set S.
* Rejected: removing RB (a pull-down-only network cannot express "K and r=0"; the
  two-step set-then-undo needs the old S); separate tails (+1 T); NAND strobes.

### Voltage assumption for the LEDs (NMOS)
5 V supply, logic-level NMOS (Vth 0.8..2 V, BSS138 class, Ron a few ohm), red LED in
series with each pull-up, LED drop about 2 V at mA currents, R = 1 kohm. Pulled
low the stack conducts about 3 mA (LED lit, low level below 0.05 V even through
three series devices). High level: an unloaded net carries only leakage, where an
LED drops about 1.1-1.4 V, so high is about 3.3-3.9 V, above Vth by >= 1.5 V.
`nmos_led_dc.py` solves the whole netlist (all 40 state/opcode/r cases x 2
phases) at (Vf, Vth) = (1.8,0.8), (2.0,1.5), (2.2,2.0), (1.8,2.0), (2.2,0.8): 0
truth-table failures; worst high 3.34 V, worst low 0.02 V; every gate node is
at least 1.57 V from Vth on the "on" side and 0.79 V on the "off" side. Static DC
only.

### A-skip1 (16 T, 7 R)
Trick3 structure: eval node DNODE = NOR(Kbar, r, S) behind a phi1 tail (4 T),
master Tm2/Tm1 + phi2 tail (3 T), differential slave with two write tails (6 T),
plus 3 pass-transistor strobes. Strobes valid in phi1 only (S falls in phi2 of a
skipped tick).

## B. LED diode-transistor logic (3 T, 9 R, 15 LED), VDD = 12 V

NOR-type SR latch, AND-OR-INVERT gates:

```
S  = NOT(Sb + phi2.MK)          Sb = NOT(S + phi2.K.RB)      RB = NOT r  (open-drain T on r)
```
* AND node: pull-up Ra = 4.7 k, one LED per input (anode on the node, cathode on
  the input), then ONE level-shift LED to the gate node (bleeder Rg = 10 k to GND),
  NMOS (drain pull-up 1 k). The OR of terms is done at the gate node by giving each
  term its own LED (S and Sb feed the other gate through one LED each).
* Strobes: LED-OR of op_bar and S with a 22 k bleeder, no transistor (active low:
  clean 0 V low, about 10 V high).
* Rule found on the way: an OR node has no pull-down drive, so it must never feed
  an AND node (first attempt, a NAND-latch fed by OR nodes, failed the DC check: the
  OR node sat at 5 V). All inter-gate signals are transistor outputs or ring lines.
  Transistor count is 3 (two latch inverters + the r inversion); 2 is impossible
  here because every signal that feeds a diode input must come from a transistor.
* RB has no pull-up (found by the removal search): it only feeds an AND-node LED.
* Voltage problem and fix: with one input low the AND node sits at V_low + Vf =
  2.0-2.4 V, which can turn a MOSFET on. The level-shift LED cuts it to
  <= 0.2 V at the gate (exponential LED model, worst corner), and the bleeder makes
  the gate a true 0 when no LED conducts. Use a standard-threshold NMOS (Vth
  2..4 V, IRF510 class) so that low is clearly off and the gate high (5-10 V) is
  clearly on.
* DC levels (`dtl_check.py`, Vf 1.8-2.2 V per LED independently, Vth 2-4 V):

| Node / case | Level |
|---|---|
| S, Sb high (pull-up, loaded by 3 strobe LEDs / cross LED) | 10.7-11.3 V |
| S, Sb low (NMOS on) | 0.02 V |
| gate node, transistor off (AND node low through level-shift LED) | 0.0-0.2 V (margin to Vth_min = 2 V: >= 1.55 V) |
| gate node, transistor on | 6.8-9.6 V (gate minus Vth >= 4.9 V in every random sample) |
| forcing path alone (latch loop opened, old state held) | gate 6.79 V worst, above Vth_max by 2.8 V |
| AND node, one input low | 1.9-2.4 V |
| AND node, all inputs high | clamped by level-shift LED + gate node (about gate + 2 V) |
| strobe net low / high | 0.00 V / 10.2-10.4 V |
| RB low / high | 0.0 V / about 10 V |
| LED currents | AND-input LED 2.15 mA when its input is low (lit); level-shift LED <= 0.18 mA; cross LED <= 0.92 mA; strobe LED <= 0.46 mA |

  Coverage of `dtl_dc.py`/`dtl_check.py`: static DC operating points (Newton with
  homotopy; LED Shockley n=2, MOSFET smooth switch Ron 2 ohm, 1 nS off), each gate
  type over all input combinations and all 2^k LED corners of that gate, plus 60
  random (Vf, Vth) machine samples x 40 cases. Not covered: dynamics/speed,
  temperature, real MOSFET subthreshold curves, ring-line source impedance
  (assumed ideal 0/12 V), power of the constantly lit LEDs.
* B' (ungated) is 3 T, 8 R, 12 LED, hazard-prone. A DTL skip-one variant was not
  built (would need master-slave, roughly twice the latch).

## Verification (all with the same reference `ref.py`)

| Check | A (10 T) | A' | A-skip1 | B (DTL) | B' | C (23 T) |
|---|---|---|---|---|---|---|
| Truth table (state x 5 opcodes x r = 20) | 20/20 | 20/20 | 20/20 x master seeds | 20/20 | 20/20 | 20/20 |
| 500 random programs+tapes, tick-by-tick | 500/500 | 500/500 | 500/500 | 500/500 (analog DC per phase) | 500/500 | 500/500 |
| Local minimality, all subsets of 1..3 removed | none removable (16 comp.) | none (15) | none (23) | none (27), incl. hazard tests | - | 6 single survivors = TG halves (ideal switch cannot see them); the 26 T NOR version: none |

* DTL also 100 random tapes at each corner (Vf,Vth) = (1.8,2), (2.2,4), (1.8,4), (2.2,2): all pass.
* Minimality covers removal only, not a search over other topologies. For the
  DTL, removal of a phi2 LED is caught by two hazard tests (overlap of F falling and
  MK rising, K with wandering r), not by the truth table.

## Programs (normal-form loops: ring = outer loop, state in data cells)

Run on the behavioural reference and on the switch-level machine in lock step,
all tick outputs equal (interpretation of "both levels"); also on CMOS, and on the
DTL analog model (reduced workload). Every instruction costs one tick, skipped or
not, so a ring pass always costs exactly the program length.

| Program | Length | Ticks per operation | Notes |
|---|---|---|---|
| 8-bit counter | 40 | 40 per increment (data independent) | cells [h=0, n0..n7], n = NOT bit; chain `FLIP IFZ NEXT` x7 to one MARK, carry trail of 1s lets a chain of `IFZ PREV` walk home; 300 increments incl. wrap checked |
| echo | 10 | 10 per pass | `IFZ FLIP MARK NEXT IFZ PREV FLIP NEXT MARK NEXT` on [out, in]; out is 0 briefly inside a pass |
| 8-bit copy | 10 | 10 per bit, 80 for 8 bits | same code, one bit per pass, layout [d0 s0 d1 s1 ..]; the ring is the loop |
| BB(2,2) Turing machine | 262 | 262 per TM step, 1572 for the 6 steps to halt | state as one-hot tokens travelling with the head (6 groups of 9 cells); tape [1,1,1,1,0,0] and state equal the `tm.py` trace after every step |

BB(2,2) uses one AND gadget (two IFZ on different cells, then a resync through a
sentinel cell, since a skipped chain leaves the pointer at data-dependent
positions) - nested blocks cannot have code between the inner and outer MARK,
and all tests inside one chain must be at the same pointer offset unless
resynced. Cell order was searched exhaustively (9! layouts, shortest 262).

Comparison with the earlier jump machine (152 T, seek jumps): counter 7-87 ticks
(avg ~17, length 8), echo 14-15, copy 116 for 8 bits. Block-skip needs more
ticks and longer programs (fixed pass cost, no early exit), for about a fifteenth
of the transistors.

## Local minimality / limits
* No component of A, B (and the skip-one design) can be removed, alone or in any
  combination of up to 3. Not proved globally minimal.
* The 9 T ungated NMOS design and the 12-LED ungated DTL are cheaper only under
  the ideal-tick assumption.
