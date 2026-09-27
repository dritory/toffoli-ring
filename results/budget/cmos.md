# Pure-MOSFET Machine A: fewest-transistor CMOS/ratioed implementation

Task: given `results/budget/static.md`'s 20-component capacitor-free
design (Trick 3: 14 transistors + 6 resistors), find the fewest-
**transistor** implementation with **no resistors, capacitors or
diodes at all** -- every pull-up in the design must itself be a MOSFET
(PMOS full-CMOS, or a weak PMOS/NMOS keeper in an allowed ratioed
fight), verified by an extension of `switchsim.py` that models
transistor *strength* (strong write/pull-down devices vs. weak keepers)
and enforces the ratioed-write safety rule.

Code: `sim/budget/cmos/cmos_sim.py` (the strength-aware evaluator,
`evaluate_cmos_static`), `sim/budget/cmos/sram6t.py` (6T SRAM cell --
the extension's first test bed), `sim/budget/cmos/machine_cmos_ratioed.py`
(the winning design, 20 transistors) + `test_machine_cmos_ratioed.py` +
`minimality_ratioed.py`, `sim/budget/cmos/machine_cmos_full.py` (the
fully complementary comparison design, 28 transistors) +
`test_machine_cmos_full.py` + `minimality_full.py`,
`sim/budget/cmos/hold_check.py` (clock-stopped-in-either-phase check,
both designs).

**Result: 20 transistors (14 strong NMOS + 6 weak PMOS keepers), 0
resistors, 0 capacitors, 0 diodes is the fewest-transistor pure-MOSFET
design found** -- the direct 1:1 conversion of Trick 3's 6 resistors
into 6 weak-PMOS keepers, verified with the same rigor as `static.md`
(8/8 truth table, 500/500 random-tape check, all 20 single-component
removals break it, holds indefinitely with the clock stopped in either
phase). **A fully complementary variant (no ratioed fights anywhere)
costs 28 transistors** -- 8 more, the real price of never allowing a
strong device to overpower a weak one.

## The simulator extension: transistor strength classes

`sim/budget/cmos/cmos_sim.py`'s `evaluate_cmos_static(transistors,
fixed, feedback_nets, seed, holdable, max_iters)` mirrors
`switchsim.evaluate_static`'s contract (same seed-then-corner-search
method for latches, same oscillation/race diagnosis) but drops
resistors entirely: every transistor tuple is now `(gate, a, b, kind,
strength)`, `kind` `'n'`/`'p'` as before, `strength` `'strong'` (a
write/pull-down device, sized to win a ratioed fight) or `'weak'` (a
continuously-on keeper, meant to be overpowered).

**Resolution rule**, each Gauss-Seidel pass: for value 1 and value 0
separately, find the best (lowest-weakness) path from any net *fixed*
to that value, through the graph of currently-closed transistors (a
0-1 shortest path: a `'strong'` edge costs 0, a `'weak'` edge costs 1 --
so the path's strength is its *weakest* link, matching how a real
series resistance is dominated by the highest-resistance device once
the ratio is large). A net that is itself externally fixed (a primary
input, or VDD/GND) is authoritative and never up for a vote -- but see
below for the two rail nets specifically. Any other net:

- reachable to only one value -> resolves to it, strength irrelevant;
- reachable to both, one strong / one weak -> **the strong value wins**
  (the allowed ratioed write -- the caller must still state the
  required on-resistance ratio, since the topology check alone can't
  measure ohms);
- reachable to both at the **same** strength -> **contention error**
  (`strong-vs-strong`: two low-impedance drivers to different rails, a
  real short; `weak-vs-weak`: neither keeper dominates, indeterminate).

**A subtlety this task's own worked example forced** (see "Tested on a
6T SRAM cell" below): in a genuinely differential design (two access
transistors writing into a cross-coupled pair simultaneously), the
*first* Gauss-Seidel pass can see a same-strength tie on one node
purely because the *other* node's inverter gate hasn't caught up yet
for one pass (exactly the kind of one-pass lag `static.md`'s "Trick 2
finding" already identified) -- even though the real, continuous-time
circuit resolves it correctly via regenerative feedback once the first
side's flip releases the gate. Raising immediately on that transient
tie would reject a standard, correctly-ratioed 6T SRAM write as a false
contention. So a tie found mid-iteration is **deferred** (left
unresolved for that pass, exactly like an ordinary not-yet-driven net)
and only raised as a genuine error if it is **still** present once the
whole network reaches its Gauss-Seidel fixed point (`_tie_check`) --
a real, permanent short cannot resolve by iterating further, so this
loses no real detections while accepting legitimate regenerative
writes. A second, related fix: VDD and GND are excluded as hops in
each other's reachability search (`_relax`'s `exclude` parameter) --
without it, a weak keeper resolving its own *local* strong-vs-weak
fight elsewhere in the circuit made the VDD/GND rails themselves look
like they had a faint leakage path to each other, which then
(wrongly) contaminated unrelated nets' own resolution. Rails are ideal,
zero-impedance supplies; nothing in the circuit can lean on them.

### Tested on a 6T SRAM cell first (`sim/budget/cmos/sram6t.py`)

Classic 6-transistor cell: 2 cross-coupled CMOS inverters (`PMOS1/NMOS1`
gated by `QB`, `PMOS2/NMOS2` gated by `Q`) + 2 NMOS access transistors
(`ACC1`/`ACC2`, gated by `WL`, bridging `BL`/`BLB` to `Q`/`QB`).
`PMOS1`/`PMOS2` are `weak` keepers; `NMOS1`/`NMOS2`/`ACC1`/`ACC2` are
`strong`. Bit lines are modelled as ordinary fixed nets (the write
driver and address decode are memory-interface circuitry, outside the
counted budget, exactly like `o`/`r`/`phi1`/`phi2` elsewhere in this
project).

- **Write 0 and write 1**, from both prior stored values (4 cases): PASS
  -- the access transistor's strong path always overpowers the opposing
  weak PMOS keeper, exactly the standard "pull-up ratio" write.
- **Hold**, both states, with `WL` held low and the settled state fed
  back as the next seed 5x in a row: reproduces itself indefinitely. PASS
- **Contention case**: a mutated cell where one keeper is (wrongly)
  rebuilt as a permanently-on **strong** NMOS pull-up instead of a weak
  PMOS -- writing against it raises `strong-vs-strong` contention
  correctly (the fixed nets `VDD` and `BL` end up connected by an
  all-strong path through the node under write, an unconditional,
  non-transient short). The same mutated cell, on a plain *hold*
  (`WL`=0, no write in progress) does **not** raise an exception: the
  transient tie between the bad keeper and `NMOS1` resolves itself over
  a few passes into a *different*, still self-consistent state --
  `Q` silently snaps to 1 and forgets the seed's `Q`=0 regardless of
  history. This is a real and instructive failure mode in its own
  right, not a gap in the check: it demonstrates that a keeper strong
  enough to sometimes win isn't just an occasional short, it can make a
  node **incapable of holding one of its two values at all** -- exactly
  why the rule requires the keeper to be weak, not merely "whatever
  beats a resistor" as the older `evaluate_static` model implicitly
  allowed.
- **Weak-vs-weak contention**: an isolated minimal case (a net pulled
  toward VDD only by a permanently-on weak PMOS and toward GND only by
  a permanently-on weak NMOS, nothing else driving it) correctly raises
  `weak-vs-weak` contention.

## Machine A, ratioed (winner): Trick 3, resistors -> weak PMOS keepers

Trick 3's structure and timing are unchanged (see `static.md` for the
full derivation of the shared-enable eval network, the master folded
into the eval network's own `DNODE`, and the differential slave latch);
only each of its 6 resistors is replaced by one weak PMOS keeper (gate
tied to GND, so permanently on, weakly pulling its net to VDD). This is
a direct, mechanical substitution: `evaluate_static`'s old rule ("a
closed transistor always beats a resistor") is exactly the strong-
beats-weak ratioed rule this extension enforces explicitly, so nothing
about the topology, the phase timing, or the master/slave-fold trick
needed to change.

```
Eval network (unchanged): T_S(gate=S=g), T_en(gate=phi1), T_o(gate=o),
  T_obar(gate=obar), T_r(gate=r) -- all strong NMOS
Master (folds into DNODE): Tm2(gate=DNODE, always live), Tm1(gate=MBAR),
  T_ph2(gate=phi2) -- all strong NMOS
Slave: Ts1, Ts2 (always-live cross-coupled hold pair), T_wset(gate=DNODE),
  T_ph2a(gate=phi2), T_wreset(gate=MBAR), T_ph2b(gate=phi2) -- all strong NMOS
Keepers (replacing the 6 resistors, gate=GND -> always on):
  KP_MOVE_P -> MOVE_P_N, KP_MOVE_M -> MOVE_M_N, KP_DNODE -> DNODE,
  KP_MBAR -> MBAR, KP_S -> S, KP_SBAR -> Sbar -- all weak PMOS
```

| Role | Components |
|---|---|
| eval network + enable tail (strong NMOS) | `T_S,T_en,T_o,T_obar,T_r` = 5 |
| eval network keepers (weak PMOS) | `KP_MOVE_P,KP_MOVE_M,KP_DNODE` = 3 |
| master (strong NMOS) | `Tm1,Tm2,T_ph2` = 3 |
| master keeper (weak PMOS) | `KP_MBAR` = 1 |
| slave (strong NMOS) | `Ts1,Ts2,T_wset,T_ph2a,T_wreset,T_ph2b` = 6 |
| slave keepers (weak PMOS) | `KP_S,KP_SBAR` = 2 |

**Total: 20 transistors (14 strong NMOS + 6 weak PMOS), 0 resistors, 0
capacitors, 0 diodes.** `sim/budget/cmos/machine_cmos_ratioed.py`.

Which fight is which (each is exactly one strong series chain vs. one
weak keeper on the same node -- never two chains on the same node at
once, so no strong-vs-strong risk exists by construction):

| Weak keeper (node) | Overpowered by (strong), when |
|---|---|
| `KP_MOVE_P` (MOVE_P_N) | `T_S,T_en,T_o` chain, when `g`&`phi1`&`o` |
| `KP_MOVE_M` (MOVE_M_N) | `T_S,T_en,T_obar` chain, when `g`&`phi1`&`obar` |
| `KP_DNODE` (DNODE) | `T_S,T_en,T_r` chain (phi1, when `g`&`r`) **or** `Tm1,T_ph2` chain (phi2, when `MBAR`&`phi2`) |
| `KP_MBAR` (MBAR) | `Tm2`, whenever `DNODE`=1 (always live, either phase) |
| `KP_S` (S) | `Ts2`, whenever `Sbar`=1 (always live) **or** `T_wreset,T_ph2b` chain (phi2, when `MBAR`&`phi2`) |
| `KP_SBAR` (Sbar) | `Ts1`, whenever `S`=1 (always live) **or** `T_wset,T_ph2a` chain (phi2, when `DNODE`&`phi2`) |

**Required ratio: every one of these fights needs the strong side's
on-resistance <= 1/5 of the weak keeper's** (R_on,weak / R_on,strong >=
5x), the ratio this task specifies as the safety margin for an allowed
ratioed write. This is the same margin the 6T SRAM test bed's access-
vs-keeper fight needs, and no fight in this design ever asks for more
than one strong device in series against one keeper (unlike some real
SRAM cells, there's no "two keepers in series" or "keeper vs. two
independent strong attackers on one node" case to size around).

### Verification

- Truth table, all 8 `(o,r,flag)` combos: 8/8 correct, no
  `evaluate_cmos_static` error in either phase.
- 500 random dual-rail tapes, macros FLIP/NEXT/PREV/CNEXT/CPREV, checked
  tick-by-tick against `run_l0` (same seed, macros, timing discipline as
  `static.md`'s and `minimal.md`'s tests): **500/500 pass**
  (`sim/budget/cmos/test_machine_cmos_ratioed.py`).
- Local minimality: removing any one of the 20 transistors (individually)
  breaks the truth table or raises a simulator error -- checked
  directly, **all 20/20 removals fail** (`minimality_ratioed.py`).
- Clock stopped in either phase: `phase1`/`phase2` applied 6x in a row
  with the same `o`,`r` and the previous result fed back as the seed
  reproduces itself exactly (checked both phases, both flag polarities,
  all `(o,r)`) -- a genuine static latch, not a capacitor
  (`hold_check.py`).

## Fully complementary variant (no ratioed fights at all), for comparison

Same overall structure (master folded into the eval network's own
node, differential slave), but every ratioed fight is rebuilt with true
complementary CMOS:

- The eval network's shared pass-transistor demux (`T_S`/`T_en` shared
  by all three branches) has no clean complementary dual -- the PMOS
  mirror of a shared-prefix demux is not itself a demux -- so it is
  rebuilt as **3 independent static CMOS NAND2 gates**: `MOVE_P_N =
  NAND(g,o)`, `MOVE_M_N = NAND(g,obar)`, `DNODE_COMB = NAND(g,r)` (the
  same boolean functions `machine_a11`/Trick 3 already use, see
  `minimal.md`), each 2 series NMOS + 2 parallel PMOS = 4 transistors.
  Losing the shared prefix is most of why this variant costs more.
- Master and slave are each a standard transmission-gate latch **with
  two inversions in its feedback loop**: `TG_write` copies the live
  input in; `INV1`'s output doubles as the free complementary output
  (`MBAR`, `Sbar`) and feeds `INV2`, whose output is fed back through
  `TG_hold`. (A single inverter fed straight back through a bare TG,
  with only one inversion in the loop, is not a latch -- it is exactly
  the 1-stage inverter-ring oscillator `static.md`'s Trick-1 test
  already flags; tried first here, and `evaluate_cmos_static` correctly
  rejected it as non-convergent, confirming the oscillation check works
  on this new family of circuit too.) `TG_write` and `TG_hold` are
  gated by opposite, non-overlapping phases -- true break-before-make,
  so no fight ever needs a ratio.

| Role | Components |
|---|---|
| eval network, 3 independent NAND2 gates | 12 (6 strong NMOS + 6 strong PMOS) |
| master latch (`TG_write`+`INV1`+`INV2`+`TG_hold`) | 8 (4 strong NMOS + 4 strong PMOS) |
| slave latch (same shape) | 8 (4 strong NMOS + 4 strong PMOS) |

**Total: 28 transistors, all plain logic strength (no weak devices
anywhere, no ratio to size), 0 resistors, 0 capacitors, 0 diodes** --
8 more than the ratioed design. `sim/budget/cmos/machine_cmos_full.py`.

### Verification

- Truth table: 8/8 correct.
- 500/500 random-tape pass against `run_l0`
  (`sim/budget/cmos/test_machine_cmos_full.py`).
- Clock stopped in either phase: holds indefinitely, same check as the
  ratioed design (`hold_check.py`).
- Local minimality: **20 of the 28 transistors' removals break the
  design**; the other 8 are the "other half" of a transmission gate
  (the NMOS or PMOS side) whose removal this **ideal** switch-level
  model cannot distinguish from keeping it -- an ideal switch has no
  notion of a degraded logic level, so a lone NMOS pass gate conducts a
  "1" just as cleanly here as a full TG does. Real MOSFETs are not
  ideal: a bare NMOS pass gate only passes up to `VDD - Vt` (a
  threshold-dropped, weak high), which is exactly why real transmission
  gates pair both polarities. Both halves are kept for that reason -- a
  real (non-ideal) physical requirement this abstraction cannot
  certify, not a component the model itself demands
  (`minimality_full.py`).

## Bottom line

| Design | Transistors | Strong | Weak | Resistors | Total | Verified |
|---|---|---|---|---|---|---|
| Trick 3 (capacitor-free, resistor-loaded, `static.md`) | 14 | -- | -- | 6 | **20** | 8/8, 500/500 |
| **cmos-ratioed (winner, pure MOSFET)** | **20** | 14 NMOS | 6 PMOS | 0 | **20** | 8/8, 500/500, 20/20 minimal, holds under stopped clock |
| cmos-full (fully complementary, no ratio) | 28 | 28 | 0 | 0 | **28** | 8/8, 500/500, 20/28 strictly minimal (+8 TG-completeness) |

The pure-MOSFET conversion costs **zero extra components** over Trick
3's resistor-loaded design (20 either way) -- a resistor and a
correctly-ratioed weak PMOS keeper are, in this switch-level model,
interchangeable at 1-for-1 cost, confirming `static.md`'s "a closed
transistor always beats a resistor" rule really was already the
strong-beats-weak ratioed rule this task asks to make explicit. Going
fully complementary (eliminating every ratioed fight) costs 8 more
transistors (28), split between losing the eval network's shared-enable
trick (no complementary dual exists for a shared-prefix demux) and
needing a genuine two-inversion break-before-make loop in each latch
stage instead of a single ratioed keeper.

## Suggested discrete part classes

- **Strong NMOS** (every write/pull-down device, and every NMOS half of
  the fully-complementary variant's gates/TGs): **2N7000** or **BSS138**
  -- small-signal, logic-level-gate-drive N-channel MOSFETs, low
  on-resistance.
- **Weak PMOS keeper** (the ratioed design's 6 keepers only): **BSS84**
  -- small-signal P-channel MOSFET. Pick/verify each keeper's on-
  resistance is **>= 5x** the strong NMOS device it is ever fought by
  (the table above lists which fights which); if a particular
  2N7000/BSS138-vs-BSS84 pairing's datasheet on-resistances don't clear
  5x on their own, oversize the NMOS (parallel two, or pick a lower-
  R_on strong part) rather than adding anything to the weak side --
  the weak keeper must stay a single small MOSFET, not a resistor.
- **Fully complementary variant**: every device is plain logic strength
  (no ratio to hit), so any matched small-signal complementary pair
  works, e.g. **BSS138** (N) + **BSS84** (P) sized for switching speed
  only.
- **No series resistor is needed anywhere** in either design -- that is
  the point of this task (0 resistors counted, confirmed by
  construction and by the simulator never invoking a resistor
  primitive at all in `cmos_sim.py`). `o`, `obar`, `r`, and the clock
  phases (`phi1`/`phi1bar`/`phi2`/`phi2bar`) are supplied pre-driven by
  the memory interface and clock drive, excluded from the count by the
  same convention as `static.md`/`tier4.md`; a small gate-series
  resistor is sometimes added on a breadboard prototype purely to damp
  fast-edge ringing, but that is a practical construction nicety
  outside the counted logical design, not something the circuit
  requires.

## Orchestrator note: physical caveats (not modelled by the switch simulator)

* The 20-transistor ratioed design uses 6 always-on PMOS as pull-up resistors. Discrete small-signal PMOS have on-resistances of a few ohms, so each one draws roughly 5 V / 10 Ω ≈ 0.5 A whenever its node is low. That is not usable as is. A keeper must be weak in absolute terms (kilohms): bias the keeper gates near threshold from one shared bias network, or use resistors, which is the 20-part resistor design again.
* The suggested ratio 2N7000/BSS138 vs BSS84 is only about 1–3x at 5 V drive, below the required 5x. Strong devices should be logic-level low-ohm NMOS (tens of milliohms at 4.5 V gate drive) if the ratioed design is kept.
* The fully complementary 28-transistor design has neither problem: no ratio requirement, no static current. It is the recommended pure-transistor build.
