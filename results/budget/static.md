# Capacitor-free Machine A: static (feedback-only) storage

Task: find the fewest-component **capacitor-free** implementation of the
two-instruction CPU (GOAL.md, tier4.md, `results/budget/minimal.md`'s
11-component design), counting every transistor, resistor and diode, no
capacitors and no reliance on node capacitance holding a value across a
phase. Up to 3 non-overlapping clock phases from the drive are free
(only 2 were needed).

Code: `sim/budget/switchsim.py` (extended with `evaluate_static`, the
cross-coupled/static-feedback evaluator), `sim/budget/static/sr_latch.py`
(extension test bed, Trick 1), `sim/budget/static/machine_static_trick3.py`
(winning design, 20 components) + `test_machine_static_trick3.py`,
`sim/budget/static/machine_static_baseline.py` (Trick 5 baseline, 25
components) + `test_machine_static_baseline.py`.

**Result: 20 components (14 transistors, 6 resistors, 0 capacitors, 0
diodes) is the best capacitor-free design found, verified with the same
rigor as `minimal.md` (full 8/8 truth table + 500/500 random-tape
check), against a straightforward baseline of 25.** This is 9 more than
the capacitor-based machine_a11 (11) -- static storage is provably more
expensive here, but 20 is well below what a naive per-stage rebuild
(25, Trick 5) costs, thanks to folding the master latch into the eval
network's own output node (Trick 3).

## The switchsim extension: `evaluate_static`

`evaluate()`'s plain Gauss-Seidel fixed point can't model a genuine
cross-coupled loop: with nothing to seed it, symmetric latches (e.g. an
SR latch with both inputs released at once) oscillate between two
symmetric all-transistors-closed / all-open corners forever, which is a
modelling artifact, not the real bistable circuit.

`evaluate_static(transistors, resistors, fixed, feedback_nets, seed)`
adds a `seed` (the loop's own state nets, carried from the previous
phase) used only to seed pass-1's gate lookups -- the feedback nets are
still resolved from the live circuit, never held fixed. Method:

1. Run the ordinary fixed-point search starting from `seed`. This is a
   deterministic function of the given previous state (no
   iteration-order ambiguity in this union-find model), so if it
   converges, that answer stands -- this correctly handles the normal
   master/slave case where a net that's already been recomputed ahead of
   the rest of the loop (e.g. a master latch mid-transition) legitimately
   disagrees with a net that hasn't been written yet, without that being
   a race.
2. If it does **not** converge (or hits contention) from the literal
   given seed, probe every one of the `2**len(feedback_nets)` starting
   corners of the feedback nets to find what stable points these fixed
   inputs actually admit.
   - None found anywhere -> **oscillation** error (a true astable
     circuit for these inputs).
   - One or more found, but the given seed itself doesn't settle onto
     any of them -> **race/metastable** error: exactly the classic
     released-simultaneous-set/reset case, where the previous state does
     not decide which of several genuinely stable outcomes to land on.
3. The usual floating-net check (`_check_floating`) still applies to the
   result: any gate/resistor net that isn't fixed, resistor-pulled, or a
   (now-resolved) feedback net raises, same "no implicit storage" rule
   as `evaluate()`.

Ratioed rule (a closed transistor path to a rail beats a resistor; two
transistor paths to different rails is a contention error) is inherited
unchanged from `evaluate()`'s union-find + rail-resolution core, which
`evaluate_static` reuses (`_fixed_point`).

### Tested on a plain SR latch first (`sim/budget/static/sr_latch.py`)

Resistor-load cross-coupled pair (Trick 1: 2 transistors + 2 resistors,
no sizing dependence -- ratioed rule always lets a closed transistor
path override the resistor) plus 2 pull-down write transistors (S, R):

- **Hold** (S=R=0): both prior states (Q=1 and Q=0) reproduce themselves. PASS
- **Set/reset**, from either starting state: PASS
- **S=R=1** (both asserted): forces Q=Qbar=0, the expected
  invalid/non-complementary state. PASS
- **Race**: releasing S=R=1 -> S=R=0 simultaneously, seeded from that
  invalid Q=Qbar=0 state. Two stable points exist for S=R=0 ((1,0) and
  (0,1)); the seed is neither, and literal iteration from it oscillates.
  Correctly raised as race/metastable. PASS
- **Oscillation**: a 1-stage inverter ring (Y := NOT Y, no resistor,
  genuinely no stable point for any seed). Correctly raised. PASS
- **Floating net**: a transistor gated by an undriven net is still
  rejected. PASS

## Trick 2 finding: a shared clock tail is unsafe here

The brief's Trick 2 ("slave written from the master's two nodes through
set/reset pull-downs sharing one clock transistor") was tried literally:
one tail node common to both the SET pull-down (gated by the master's
node) and the RESET pull-down (gated by its complement). **Rejected by
the simulator as a genuine race**, not a modelling quirk: the
complement is generated by an inverter, which lags its input by one
Gauss-Seidel pass. For one pass, both gates can read as simultaneously
true (the master node mid-transition, its inverted output not yet
caught up) -- and a literal shared tail node bridges the two nodes being
written (e.g. S and Sbar) directly together through it, **regardless of
whether the clock transistor is open or closed**, corrupting the hold
pair. This isn't specific to our netlist: it happens whenever a shared
tail's two data gates are combinational outputs (anything with gate
delay), rather than true primary inputs (like `o`/`ō`, which the
memory-interface spec already supplies pre-complemented from program
memory with no gate delay -- sharing is fine there).

**Conclusion: sharing one clock transistor between a data-gated SET and
RESET pull-down only saves a component when both gates are guaranteed
never to transiently coincide; when either is a derived/inverted signal,
each write pull-down needs its own tail transistor.** Both designs below
use this corrected (2-tail) form.

## Trick 3 (winner): master folded into the eval network's own DNODE

Instead of a separate master latch copied from `DNODE` via a write
transistor, `DNODE` **is** the master node directly -- no copy, no
separate write path needed for it. One new transistor, `T_en` (an
enable tail inserted in the eval network's own `T_S -> GND` path, gated
`phi1`), lets the eval network's pulldown chain be cleanly disconnected
from `DNODE` during phase 2 so the master's own cross-coupled feedback
(not the still-live-if-ungated eval network) can hold it. `MBAR` (a
plain always-on inverter of `DNODE`) supplies the master's second,
already-differential polarity for free -- exactly the "both flag
polarities for the eval network at no cost" the brief describes, here
repurposed to feed the slave's differential write.

```
Eval (unchanged from machine_a11.py except T_S's tail):
  T_S    gate=S      a=K     b=EN         T_en gate=phi1 a=EN b=GND
  T_o    gate=o      a=MOVE_P_N b=K       T_obar gate=obar a=MOVE_M_N b=K
  T_r    gate=r      a=DNODE b=K
  R: MOVE_P_N->VDD, MOVE_M_N->VDD, DNODE->VDD

Master (folds into DNODE -- no separate master node):
  Tm2 (always live): gate=DNODE a=MBAR b=GND      R_MBAR: MBAR->VDD
  Tm1 (hold, phi2 tail): gate=MBAR a=DNODE b=MTAIL   T_ph2 gate=phi2 a=MTAIL b=GND

Slave (S=g, read by T_S; written from DNODE/MBAR, 2 separate tails --
see the Trick 2 finding):
  Ts1,Ts2 (always live, cross-coupled): gate=Sbar/S a=S/Sbar b=GND
  R_S: S->VDD   R_Sbar: Sbar->VDD
  T_wset   gate=DNODE a=Sbar b=WTAIL_A   T_ph2a gate=phi2 a=WTAIL_A b=GND
  T_wreset gate=MBAR  a=S    b=WTAIL_B   T_ph2b gate=phi2 a=WTAIL_B b=GND
```

| Role | Components |
|---|---|
| eval network + enable tail | `T_S,T_o,T_obar,T_r,T_en` = 5 transistors, `R1,R2,R3` = 3 resistors |
| master (folded into DNODE) | `Tm1,Tm2,T_ph2` = 3 transistors, `R_MBAR` = 1 resistor |
| slave | `Ts1,Ts2,T_wset,T_ph2a,T_wreset,T_ph2b` = 6 transistors, `R_S,R_Sbar` = 2 resistors |

**Total: 20 (14 transistors, 6 resistors, 0 capacitors, 0 diodes).**
`sim/budget/static/machine_static_trick3.py`.

### Verification

- Truth table, all 8 `(o, r, flag)` combos: 8/8 correct, no
  `evaluate_static` error in either phase.
- 500 random dual-rail tapes, macros FLIP/NEXT/PREV/CNEXT/CPREV, checked
  tick-by-tick against `run_l0` (same seed, macros, timing discipline as
  `minimal/test_machine_a11.py`): **500/500 pass**
  (`sim/budget/static/test_machine_static_trick3.py`).
- Local minimality: removing any one of the 20 components (all 14
  transistors individually, all 6 resistors individually) breaks
  correctness (wrong truth-table rows) or is rejected outright (floating
  net / missing net) -- checked directly, all 20 removals fail.

## Trick 5 (baseline): straightforward static master-slave

No folding: `DNODE`'s own complement `DBAR` is generated by a dedicated
inverter, and both master and slave are separate cross-coupled pairs
(Trick 1), each written through 2 independently-tailed pull-downs (per
the Trick 2 finding).

| Role | Components |
|---|---|
| eval network (unchanged, no `T_en` needed -- nothing ever writes back into `DNODE`) | 4 transistors, 3 resistors |
| `DBAR` generation | `T_inv` = 1 transistor, `R_DBAR` = 1 resistor |
| master | `Tm1,Tm2,T_wsetM,T_ph1a,T_wresetM,T_ph1b` = 6 transistors, `R_M,R_Mbar` = 2 resistors |
| slave | `Ts1,Ts2,T_wsetS,T_ph2a,T_wresetS,T_ph2b` = 6 transistors, `R_S,R_Sbar` = 2 resistors |

**Total: 25 (17 transistors, 8 resistors, 0 capacitors, 0 diodes).**
`sim/budget/static/machine_static_baseline.py`. Verified the same way:
truth table 8/8, random-tape 500/500
(`sim/budget/static/test_machine_static_baseline.py`).

Trick 3 saves exactly the baseline's `DBAR`-generation cost (2) plus the
difference between a from-scratch master (6 components: hold pair +
2-tailed write) and folding DNODE in directly (master costs only
`T_en,Tm1,Tm2,T_ph2,R_MBAR` = 5, since the eval network's own `DNODE` and
its resistor are reused for free) -- 25 - 20 = 5 components saved, matching
(2 DBAR + 1 from a leaner master-write path with one shared node reused).

## Trick 4: can the data cell itself serve as the master? No -- provably

After the toggle, the currently-addressed data cell holds `NOT(r_old)`,
and `flag_next = r_old` exactly when executing (`flag=0`) -- tempting to
read that bit back "for free" instead of building a master latch at all.
It provably cannot work, independent of any circuit realization:

**Toggle and move always happen together.** The spec's only branch that
toggles (`else: toggle, move by o, flag := r`) *also* moves the pointer
by `o` in the same tick, unconditionally (there is no "toggle without
moving" case in the two-instruction machine). So on every tick where the
cell is toggled, the pointer has already left that exact cell by the
time the next tick begins -- there is no tick where the flag would need
reading from a cell the pointer is still sitting on.

The memory interface (excluded from the component count, but its read
port is fixed by the spec) only ever exposes `r`, the bit **under the
current pointer**. Once the pointer moves, the just-toggled cell's
content is no longer on that wire at all -- reading it back "for free"
next tick would require either (a) a second pointer/address register
remembering the old address, or (b) a dedicated bit remembering the old
cell's content independent of the pointer. Both are exactly the master
(or master+slave) latch this trick set out to eliminate, just relocated
-- no netlist trick recovers the lost information once the pointer has
moved on, because nothing in the given interface lets two different
addresses be read in the same tick. Defining "the pointer moves only at
the end of the tick" (using a 3rd phase, as the brief allows) does not
help either: it only delays *when* the pointer moves, not the fact that
it moves every time the cell is toggled, so the same-cell read window
closes at the same point in the very next tick regardless of how the
phases are sliced within the current one.

This is a data-flow argument about the fixed memory-addressing
interface, not a property of any particular circuit, so it needed no
simulation to check.

## Bottom line

| Design | Transistors | Resistors | Capacitors | Total | Verified |
|---|---|---|---|---|---|
| machine_a11 (capacitor-based, `minimal.md`) | 6 | 3 | 2 | **11** | 8/8, 500/500 |
| **Trick 3 (winner, capacitor-free)** | 14 | 6 | 0 | **20** | 8/8, 500/500 |
| Trick 5 (straightforward static baseline) | 17 | 8 | 0 | **25** | 8/8, 500/500 |

- **Trick 1** (resistor-load cross-coupled SR latch, 2T+2R, no sizing
  dependence): worked, validated standalone first as required, and is
  the building block both static designs' master/slave stages use.
- **Trick 2** (shared clock transistor for set+reset): did **not** work
  as literally stated -- caught by `evaluate_static` as a genuine
  bridging race whenever the two write gates are combinational
  (inverter-derived), not primitive inputs. Each write pull-down needs
  its own tail transistor instead; this is reflected in both Trick 3 and
  the Trick 5 baseline's actual costs above.
- **Trick 3** (master folded into the eval network's own output node,
  eliminating a separate master write path and the `DBAR` generator):
  worked, and is the best design found -- 20 components, 5 fewer than
  the straightforward baseline.
- **Trick 4** (data cell doubles as the master): provably cannot work --
  toggle and move are coupled in the spec, so the pointer always leaves
  the just-toggled cell the same tick, and the fixed memory interface
  never exposes two addresses' content in the same tick to recover it.
- **Trick 5** (straightforward static master-slave, no merging): works,
  25 components, the baseline both other designs beat or match.

Capacitor-free costs 20, 1.8x the capacitor-based 11 -- consistent with
GOAL.md's framing of capacitors as a real, non-free saving whose only
downside is the physical-build risk (holding charge for one tick), not
component count.
