# Block-skip CPU from neon lamps and LDRs (no transistors, no ICs)

ISA and reference: `results/budget/blockskip.md`, `sim/budget/blockskip/ref.py`.
Code: `sim/budget/neon/` (`model.py` lamp/LDR/time-step model, `cpu.py` netlist + tick harness,
`test_blocks.py`, `margins.py`, `test_cpu.py`, `tsearch.py`, `run500.py`, `sweeps.py`, `extras.py`,
`corners.py`). Logs: `results/budget/neon_*.log`.

## Result

| | lamps | LDRs | resistors | diodes | total |
|---|---|---|---|---|---|
| **Design N (clamp reset), verified** | 7 | 7 | 7 | 2 | **23** |
| N-gated (reset also gated by phi2), verified (truth table, 100 programs, nominal only) | 8 | 8 | 8 | 2 | 26 |

No transistors. All 7 resistors have the same value (320 kohm). Supply +300 V, tick 1.0 s (1 Hz),
worst corner found needs 0.7 s. Passes the 40-case truth table and 500 random programs x 80 ticks
against `ref.py` at 8 corners (list below), with strict end-of-tick criteria.
Not counted, as in the other designs: data memory, program storage, clock drive, power. The lines
below are interface assumptions, not free: opcode lines, r and the phi2 rail are 0/+300 V lines that
source or sink about 1 mA each; the memory reads the three strobe lamps with its own LDRs.

## 1. Models (`model.py`)

Verified building blocks (`test_blocks.py`):
* Hysteresis lamp as a one-part memory: a lamp with bias resistor Rb from a bias rail holds both
  states when the Thevenin bias voltage is between `Vb_max + Iext_max*(Rb+rd)` and `Vs_min`, i.e.
  69-85 V for Rb = 35k (window 16 V, bias 77 V +-10 %; 74-85 V for Rb = 80k). Bistable at 60/60
  random vertex corners inside the window, 43/60 and 48/60 just outside.
  Setting it through a series LDR does NOT work for dark LDRs of 1 Mohm: dark leakage from the phi2 rail
  raises the lamp node above strike (or the set path cannot reach 140 V). Best margin over Rb, Rset, bias
  with lit current after strike limited to 2 mA: -2.7 V at 1 Mohm dark, +9.9 V at 10 Mohm dark
  (`python3 test_blocks.py set`). So the flag is a two-lamp NOR latch instead. (A one-lamp flag with
  10 Mohm LDRs and a 73 V bias rail would be 20 parts; only the block level is checked, not the full CPU.)
* Inversion/NOR: a lamp fed from the supply through R and shunted by an LDR that is lit by another lamp.
  Lit LDR (<= 10 kohm) holds the lamp at 2-9 V, far below sustain; dark LDR leaves it striking. OR of
  the inputs = several shunt LDRs in parallel, an AND-enable = feed the lamp from a line, or clamp
  its node with a diode to the line.

Parameter ranges (each instance independent; corners are vertices of these ranges):

| Item | Range |
|---|---|
| Lamp strike Vs | 85-105 V; dark effect +0..25 V and strike delay x3 (worst case: all lamps unprimed) |
| Lamp burning Vb | 55-65 V, dynamic resistance rd 1-3 kohm |
| Extinction current Iext | 20-100 uA (lamp goes out when the current falls below it) |
| Strike delay t_d | 1-20 ms at 20 % overvoltage; longer at less (t_d = td0*0.2/overvoltage, max x10) |
| LDR dark | 1-10 Mohm (0.3-0.5 Mohm as the memory-effect stress case) |
| LDR lit | 1-10 kohm at 0.5 mA lamp current; conductance ~ light^gamma, gamma 0.7-0.9 |
| LDR lag | first order on conductance, rise 5-20 ms, fall 20-60 ms |
| Resistors, supply | +-5 %, +-3 % (+-10 % also tested at nominal) |
| Diodes | Vf 0.5-1.0 V, 50 ohm |
| Lines | 0/VP, source impedance 1 kohm (5k, 20k tested) |
| Optical crosstalk | 0 (design assumption); every lit lamp lights every other LDR with fraction x |

Time step: dt = 5 ms. Each step solves the resistive network (diodes piecewise linear, lit lamp =
Vb + rd, unlit lamp open), then updates: lamp strike timer (accumulates while the open-circuit voltage
exceeds Vs+dark, reset slowly otherwise), instant extinction below Iext, LDR conductance by the exact
exponential step toward the value set by the light (lamp current / 0.5 mA).

## 2. Circuit (design N)

Lit lamp = 1, about 0.75 mA at 300 V through 320 kohm. `LDR(x)` = LDR across a lamp, lit by lamp x.

```
 skip flag (NOR latch)                 LS  lit = S=1    LSb lit = S=0
   VP -R- s  : LS  , shunts LDR(LSb), diode s->MB  (MB low = MK active: clamp = reset)
   VP -R- sb : LSb , shunts LDR(LS) , LDR(LK)                         (LK lit = set)
 set condition   PHI -R- k : LK , diode k->K (K low clamps), shunt LDR(Lr)
                 => LK lit = phi2 AND K AND NOT r
 r inversion     r -R- Lr    (Lr lit when r=1)
 strobes         F -R- LF ,  N -R- LN ,  P -R- LP ,  each shunted by LDR(LS)
                 => strobe lit = op AND NOT S
```
Lamps LS LSb LF LN LP LK Lr; LDRs: 3 strobe shunts, LDR(LSb), LDR(LS), LDR(LK), LDR(Lr) (7);
resistors: one ballast per lamp (7); diodes: reset clamp, LK clamp (2). One LS lamp lights four LDRs (the
three strobes and the LSb shunt) in one light-tight housing.

Behaviour: strobe lamps are lit only when the opcode line is high and S=0 (LS dark). Set: in phi2, K high and r=0
strikes LK, which shunts LSb, LSb goes out, its LDR(LSb) decays, LS strikes, LDR(LS) shunts LSb.
Reset: MK low-active clamp puts LS out at once and LSb strikes when LDR(LS) has decayed. K and MK are one-hot, so
set and reset never coincide. phi2 is a rail (0/300 V) high from 0.4 T to T minus 10 ms; it is free gating of the set
path (r settles before it). Strobes are valid in the last 10 % of the tick (memory samples there); S never changes
in a tick where F, N, P are active, as in the other designs.
Reset is not gated (clamp diode instead of lamp+LDR+resistor+diode): the LDR lag (>= 20 ms fall) filters
skew between a falling F and a rising MK.

Alternatives not run in full: interface with r in both polarities removes Lr, its resistor and LDR (a
second clamp diode on LK), 21 parts, not simulated; optical inputs from memory lamps not simulated.

## 3. Worst-case margins (static DC, `margins.py`, 150 random vertex corners x 40 cases, dark effect on)

Design point (VP 300 V, 0.75 mA, LDR dark >= 1 Mohm, crosstalk 0):

| Margin | Worst | Meaning |
|---|---|---|
| hold | 5.3 x | lit-lamp current / its extinction current (need > 1) |
| strike | +44 V | open-circuit voltage of a lamp that must strike minus (Vs + dark effect) (need > 0) |
| quench | +46 V | burning voltage minus open-circuit voltage of a lamp that must be dark (need > 0) |
| no false strike | +76 V | Vs minus the same open-circuit voltage |
| highest lamp current | 0.8 mA | |

Sensitivities (same table, worst over cases): crosstalk 1e-6 / 3e-6 / 1e-5: strike +38 / +30 / +8.7 V (so optical
isolation better than about 3e-6, -55 dB, is needed for a margin of 30 V; 1e-4 kills the worst corner
statically, although the time-domain corners pass at 1e-4). Rlit for all LDRs 10 / 30 / 60 / 100 kohm: quench +47 / +32 / +12 / -12 V
(lamp dimming is tolerated up to about 60 kohm lit). Dark LDR 0.5 Mohm: strike -5.9 V at 0.75 mA (fails), +14.9 V at 1.0 mA.
Same at VP 250 V: strike +4.9 V (too little), so 300 V.

## 4. Whole-CPU checks (analog time-domain model vs `ref.py`)

Pass criterion per tick: strobes sampled in the last 10 % of the tick equal the reference, and the lamp state
at tick end equals S'. Truth table: 40 cases (S x 5 opcodes x r, with r equal to and different from the previous r),
each on a fresh machine; S=1 reached by a K tick with r=0.

500 random programs x 80 ticks (`run500.py`, T = 1.0 s, 3 ms line skew, 1 kohm line impedance, seed as in the other tests):

| Corner | Truth | 500 programs | Worst spurious strobe lamp-on | Worst late strobe |
|---|---|---|---|---|
| nom | 40/40 | 500/500 | 5 ms | 5 ms |
| slow (tau 20/60 ms, td 20 ms, dark +25 V, Vs 105, Vb 65, Iext 100 uA, Rlit 10k, VP -3 %, R +5 %) | 40/40 | 500/500 | 5 ms | 20 ms |
| fast (tau 5/20 ms, td 1 ms, Vs 85, Vb 55, Iext 20 uA, Rlit 1k, VP +3 %, R -5 %) | 40/40 | 500/500 | 5 ms | 5 ms |
| weak (Rdark 1M, Rlit 10k, Vs 105 + 25 dark, VP -3 %, R +5 %) | 40/40 | 500/500 | 5 ms | 5 ms |
| hot (Vb 55, Iext 100 uA, Vs 85, VP +3 %, R -5 %, Rlit 10k) | 40/40 | 500/500 | 5 ms | 5 ms |
| random vertex corner v1 (all parameters random at range ends, dark on) | 40/40 | 500/500 | 5 ms | 20 ms |
| random vertex corner v3 | 40/40 | 500/500 | 5 ms | 20 ms |
| hardened: slow + Rdark 0.5 Mohm, lamp current 1.0 mA (R 240k) | 40/40 | 500/500 | 5 ms | 25 ms |

(One time step is 5 ms, so "5 ms" is one step: a line-skew glitch that the lag of the LDR filtered to at most one step.)

Sweeps at T = 1.0 s (truth table + 30 programs x 60 ticks each, all pass unless stated):
* line skew up to 3 / 30 / 100 / 200 / 400 ms at nominal, fast and slow corners: pass. The strobe window
  is the last 10 %, so skew up to about 0.4 T is harmless; a spurious strobe lamp-on inside the tick is
  ignored by a memory that samples only at the end of the tick.
* optical crosstalk 1e-6 ... 1e-4 at nominal, slow and weak corners: pass (1e-4 too at the nominal, slow corners;
  the static worst-vertex margin is the stricter one).
* aged lamps: Vs 120 V (weak corner, also LDR lit resistance x3): pass; slow corner with Vs 115 V: pass.
* line impedance 1k / 5k / 20k: pass. Supply x0.90 / 0.95 / 1.05 / 1.10 at nominal: pass.
* LDR memory effect: Rdark 0.5 Mohm at 0.75 mA: 11/30 (fails); 0.3 Mohm: fails to hold state at all. With 1.0 mA lamps:
  0.5 Mohm passes (500/500), 0.3 Mohm 11/30.

## 5. Voltage and speed

* One supply, +300 V DC (regulation +-3 % in the corner set, nominal case passes +-10 %); phi2 rail and the five
  line drivers swing 0/300 V. 250 V is too low for the dark effect (strike margin +4.9 V). With at most three lamps lit
  at once (flag, one of Lr/LK, one strobe): about 2.2 mA, 0.7 W from the supply plus 1 mA per line while its clamp diode conducts.
* Speed. Shortest tick that passes truth table + 30 programs per corner (steps 0.3, 0.4, ..., 0.8 s): nominal 0.4 s,
  slow 0.6 s, weak 0.4 s, hot 0.3 s, fast 0.3 s, random vertex corners 0.3-0.7 s (v1, v3: 0.7 s, v5: 0.5 s). The limit is
  the latch flip inside phi2: LK strike (<= 20 ms) + LDR(LK) rise + LSb out + LDR(LS-shunt of LSb) decay
  (about 3 tau_f, up to 180 ms) + LS strike + LDR rise, which has to finish before the end of the tick; plus the earlier
  settling of r through Lr -> LDR -> LK. Rule of thumb: T_min is roughly 10 to 12 times the LDR fall time. Chosen T = 1.0 s
  (40 % margin over the worst found), i.e. 1 tick per second: 8-bit counter 40 s per increment, echo 10 s per pass,
  BB(2,2) 262 s per Turing-machine step. The fast corner (tau 5/20 ms) passed at the shortest tick tried, 0.3 s.

## 6. Practical problems and how the design tolerates them

* Lamp aging (strike voltage rises, sputtering dims the lamp): strike margin +44 V covers a strike rise
  beyond 105 + 25 V worst case; Vs = 120 V with 25 V dark effect passes. Dimming raises the lit LDR resistance:
  quench margin still +12 V at 60 kohm lit; at 100 kohm the shunt no longer quenches (-12 V).
* Dark effect / strike delay: included in every corner (strike +25 V, delay x3, up to 20 ms x 3). The design gets its margin from
  the 0.75 mA / 300 V supply point (worst open-circuit voltage of a lamp that must strike: about 174 V with two 1 Mohm dark LDRs across it, VP -3 %, R +5 %). No priming lamp needed there;
  a radioactive-primed or lit pilot lamp would remove 25 V of the requirement but it must not light the LDRs.
* LDR dark resistance and memory effect: the critical weakness. Two dark LDRs shunt the latch lamps, so a
  memory-effect drop to 0.5 Mohm dark after long illumination makes strike margin negative at 0.75 mA. Mitigation verified: 1.0 mA
  lamps (R 240 kohm), Rdark 0.5 Mohm passes 500/500; 0.3 Mohm still fails. Choose cells with dark resistance well above 1 Mohm.
* LDR lag: slowest, sets the clock (above). Slow decay tails longer than 60 ms scale T linearly.
* Optical crosstalk: needs light-tight lamp+LDR housings (one per lamp with its LDRs) with leakage below about 3e-6.
  Steady stray light is the killer because conductance rises as light^0.8.
* Not modelled: temperature (strike voltage and LDR resistance), lamp flicker and statistical strike jitter beyond the delay range, lamp ionisation
  memory beyond the simple timer, the memory-side LDRs that read the strobe lamps (their lag adds to the sample window), LDR noise.
* Interface assumptions that cost real hardware: five lines and the phi2 rail able to source/sink about 1 mA at 300 V; memory samples strobes only in the
  last 10 % of the tick and takes r settled by 0.4 T.

## Verified / not verified

Verified: truth table (40 cases), 500 random programs tick by tick at 8 corners (7 named/random + hardened) against `ref.py` with
the analog model; static margins over 150 random vertex corners (dark effect on) x 40 cases; sweeps above; T_min at 10 corners.
Not verified: physical parts data (parameter ranges are the assumed ranges), one-lamp flag in the full CPU, r-both-polarities and optical-input
variants, global minimality (no removal search was run for the neon parts), the memory interface.
