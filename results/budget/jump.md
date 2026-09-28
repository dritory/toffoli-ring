# Jump machine: a real-ISA CPU with seek jumps, fewest transistors

Task: given `results/budget/cmos.md`'s 28-transistor fully-complementary
CMOS machine (2 implicit "instructions", no program memory, no real
loops), design a CPU with an actual fetched instruction stream and
conditional backward/forward seeks, so hand-written programs can loop.
Two variants: single-level (nearest MARK) and labelled (nested loops via
an L-bit label on MARK/JB/JF). Same full-CMOS discipline as
`machine_cmos_full.py`: every gate is plain complementary logic, no
ratioed fights, every transistor counted.

Code: `sim/budget/jump/gatelib.py` (shared NAND/NOR/AOI/TG/latch
builders, reusing `machine_cmos_full.py`'s master-slave latch structure
verbatim), `sim/budget/jump/jump_ref.py` (behavioural reference
simulator, both variants, + program/data-ring runner),
`sim/budget/jump/machine_jump.py` (single-level switch-level machine,
152T), `sim/budget/jump/machine_jump_labeled.py` (labelled switch-level
machine, 270T), `sim/budget/jump/test_machine_jump*.py` (verification),
`sim/budget/jump/minimality_jump.py` (per-transistor removal check),
`sim/budget/jump/programs.py` (the four hand-written demos).

## ISA

Seven instructions, shared by both variants:

| Mnemonic | Effect |
|---|---|
| `FLIP`  | toggle the current data bit |
| `NEXT`  | move the data pointer +1 |
| `PREV`  | move the data pointer -1 |
| `SKIPZ` | skip the next instruction iff `r==0` |
| `JB`    | seek backward to the nearest matching `MARK` |
| `JF`    | seek forward to the nearest matching `MARK` |
| `MARK`  | no-op; a seek target |

A seek (`JB`/`JF`) puts the CPU in seek mode: the program ring steps in
the seek direction every tick, executing nothing (no data effects), no
matter what instruction it passes over, until it steps onto a matching
`MARK`; then normal execution resumes at the instruction after that
`MARK`. `SKIPZ` immediately followed by `JB`/`JF` is a conditional jump
("jump if `r!=0`"): `SKIPZ` only ever skips the *one* next instruction,
so `r==0` skips the jump (falls through, no seek) and `r!=0` executes
it (jump taken). `JB`/`JF` used alone (no preceding `SKIPZ`) is an
unconditional jump.

Labelled variant: `MARK`, `JB` and `JF` each also carry an `L=2`-bit
label field. `JB`/`JF` latches its label into a 2-bit target-label
register when it starts the seek; a seek now stops only at a `MARK`
whose label equals that register (a `MARK` with the wrong label is
passed over exactly like any other non-`MARK` instruction). This is
what lets loops nest: an outer `JB`/`JF` can skip straight past an
inner loop's `MARK` to find its own.

### Encoding: one-hot, not binary -- because the ring is free

Program memory is the excluded interface: the ring supplies every
opcode bit (and its complement) for free, however wide the field is.
The CPU's *decode* logic is what's counted. So the seven instructions
are encoded **one-hot** (7 opcode wires `F,N,P,K,JF,JB,MK`, one set per
instruction, both polarities from the ring) rather than packed into 3
binary bits. One-hot makes every "is this instruction X" test a single
free wire (`F`, or its free complement `Fbar`) instead of a 3-input
pattern match: `toggle`, `move_plus`, `move_minus`, the seek-start
flags, and the seek-stop test (`MK`) all become direct literals inside
the surrounding AOI gates, at zero extra decode transistors. Compare
the alternative: dense binary opcode bits `b2 b1 b0` would need a real
3-to-8 decoder (seven 3-input recognizer gates, ~42 transistors) built
*inside* the counted CPU before any of that logic could run -- more
than the entire single-level machine's total combinational-logic cost
(104T including registers-adjacent logic; see breakdown below). Since
the ring's width is free and the CPU's transistor count is not,
one-hot is strictly cheaper here. The labelled variant's 2-bit label
field is the one place a real (compact) binary field is used, because
it must be *stored* (in the 2-bit target-label register) and compared
for equality, not merely recognized -- a job binary encoding does
naturally (XNOR per bit) and one-hot would not shrink.

## CPU state

Single-level: 3 bits, `SF` (seeking forward), `SB` (seeking backward),
`SK` (one-tick skip pending after a taken `SKIPZ`) -- built so at most
one is ever 1 by construction (not merely assumed), "normal mode" being
all three 0. Labelled variant adds a 2-bit target-label register `TL`.
Every bit is one `machine_cmos_full.py`-style master-slave latch (8T
master + 8T slave = 16T), sampling a comb-logic "D" net during `phi1`
and holding through `phi2` via the same TG/INV1/INV2/TG loop; the
combinational logic is entirely `gatelib._aoi`-built AND-OR-INVERT
networks (which subsume NAND/NOR as 1-input-group special cases), so
every state/control net is either a single-term NAND-N (a plain
conjunction) or a genuine sum-of-products where two or three ways to
reach the next value are OR'd together (e.g. "keep seeking forward" OR
"just started seeking forward").

## Transistor count

| Design | Transistors |
|---|---|
| 28T machine (`machine_cmos_full.py`, 2 implicit instructions, no program memory) | 28 |
| **jump machine, single-level** | **152** |
| **jump machine, labelled (L=2)** | **270** |

Single-level breakdown:

| Block | Transistors |
|---|---|
| `rbar` (data bit complement, `SKIPZ` needs it; data memory gives only `r`) | 2 |
| 3 state registers (`SF`,`SB`,`SK`) x 16T master-slave latch | 48 |
| `SF`/`SB` next-state (2-term AOI + inverter each) | 14 + 14 |
| `SK` next-state (1-term AOI + inverter) | 12 |
| `toggle`/`move_plus`/`move_minus` (1-term AOI + inverter each) | 10 + 10 + 10 |
| `prog_plus` (4-term AOI + inverter) | 18 |
| `prog_minus` (2-term AOI + inverter) | 14 |
| **Total** | **152** |

Labelled adds, on top of the same skeleton: 2 more state-register bits
(`TL1`,`TL0`, 32T), the label-equality test `EQ1`/`EQ0` (2-term AOI
each, 8T, free polarity -- no inverter needed since the AOI's natural
output *is* equality) plus their complements for the "wrong label, keep
seeking" case (2 inverters, 4T), the label-conditioned load logic
(`LOAD`, 18T) and the 2-bit label mux feeding `TL1`/`TL0` (10T each,
20T) -- and `SF`/`SB`'s next-state and `prog_plus`/`prog_minus` grow
from 2-term to 4-term AOIs (each +8T) because "found the mark" is now
"found *a* mark" AND "label matches", and "keep seeking" is now "not a
mark" OR "wrong label" (an OR distributed into extra terms, since AOI
terms are conjunctions).

No ratioed fights anywhere in either variant (every device plain logic
strength) -- both are fully complementary CMOS, same discipline as the
28T comparison machine, not the 20T ratioed one.

## Verification

**Single-level** (`test_machine_jump.py`):
- Exhaustive truth table over (instruction, r, mode): 4 modes x 7
  instructions x 2 r values = **56/56 correct**.
- 500 random programs (4-14 instructions, random FLIP/NEXT/PREV/
  SKIPZ/JB/JF/MARK mix) and data tapes (4-10 cells), tick-by-tick
  switch-level vs `jump_ref.tick`, 60 ticks each, short rings so
  multi-step seeks routinely wrap around the ring: **500/500 pass**.
- Local minimality (`minimality_jump.py`): removing each of the 152
  transistors individually and re-running the full 56-case truth
  table: **122/152 removals break the design**. The 30 survivors split
  into the same two categories `machine_cmos_full.py`'s own minimality
  check already found: 24 are one NMOS or PMOS half of a transmission
  gate (an ideal switch model can't tell a lone NMOS pass transistor
  from a full break-before-make TG, exactly the documented
  `minimality_full.py` finding -- a real, non-ideal-device requirement,
  not a component this abstraction can certify), and 6 are individual
  PMOS legs inside a multi-term AOI pull-up network that had an
  alternate parallel conduction path in this design's particular
  term ordering -- a genuine further-minimization opportunity not
  pursued here.

**Labelled** (`test_machine_jump_labeled.py`):
- Exhaustive truth table over (instruction, r, mode, target-label
  register, instruction's own label field): 4 modes x 4 `TL` values x 7
  instructions x 4 label-field values x 2 r values = **896/896
  correct**.
- 500 random programs (5-16 instructions, 2 distinct labels so nesting
  is actually exercised) and data tapes, tick-by-tick vs
  `jump_ref.tick_labeled`, 60 ticks each: **500/500 pass**.
- Local minimality on a representative 224-case subset per removal
  (full mode x opcode x r range, labels/target reduced to {0,3} instead
  of all 4, for tractability -- not the full 896-case table):
  **210/270 removals break the design**. The 60 survivors are the same
  two categories as the single-level check, scaled up (TG halves across
  5 register bits instead of 3, plus more multi-term AOI gates each
  contributing a couple of parallel-redundant PMOS legs) -- not
  re-verified against the full 896-case table for time, so this is a
  slightly weaker (but still informative) minimality claim than the
  single-level variant's.

## Hand-written programs (`programs.py`, run on both the switch-level
machine and the reference simulator, tick-by-tick identical in every
case)

**(1) 8-bit ripple-carry binary counter, one increment.** Loop body:
`MARK; FLIP; SKIPZ; JF; NEXT; JB; MARK`(exit). Flip the current bit;
if it became 0 (carry, `r==0`) `SKIPZ` falls through to `NEXT;JB` and
the loop repeats one bit up; if it became 1 (`r==1`, done) the skipped
instruction was the `JF`, wait -- concretely: `SKIPZ` skips the `JF`
when `r==0` (carry, continue), so the carry path falls through to
`NEXT;JB`; when `r==1` (done) `SKIPZ` does not skip, `JF` fires and
seeks to the exit `MARK`. A 9th "guard" data cell (reset to 0 before
each increment) sits after the 8 counter bits so an all-1s overflow
ripples into the guard and stops there instead of wrapping the data
ring around and re-flipping bit 0 a second time -- the standard
fixed-width "discard the carry-out" behaviour.

| Starting value | Ticks for `+1` |
|---|---|
| 0 | 7 |
| 1 | 17 |
| 3 | 27 |
| 7 | 37 |
| 15 | 47 |
| 31 | 57 |
| 63 | 67 |
| 127 | 77 |
| 254 (0b11111110) | 7 |
| 255 (all carries, overflow) | 87 |

Each additional carry costs a fixed 10 ticks (`FLIP,SKIPZ,JF-skipped-
tick,NEXT`, then the `JB` seek back to `MARK`, whose length is the
fixed program-ring distance for this loop, 6 ticks); the terminating
bit costs 7 (`MARK-arrival,FLIP,SKIPZ,JF`-seek). Average case (random 8-
bit value, expected ~1 carry) is ~17 ticks/increment. The 28T machine
has no ISA at all to compare against directly -- it has no program
memory, so "increment an 8-bit counter" isn't an operation it can be
asked to perform; the comparison point is qualitative (this machine
*can* run this program, at a real, measured tick cost, because it has
real conditional loops).

**(2) Echo an input cell to an output cell, forever.** `SKIPZ;FLIP`
forces a cell to 0 (skip the flip if it's already 0); `SKIPZ;FLIP;FLIP`
forces a cell to 1 (if already 1, the skip removes one flip so the two
flips that do run cancel; if 0, only the second flip runs) -- both are
jump-free 1-cell idioms. Echo tests the input bit, seeks to whichever
force-recipe applies to the output bit, then returns: one branch via
`JB` (nearest backward `MARK`), the other via `JF` wrapping forward
around the whole 15-instruction program ring back to the same `MARK`
-- the mark that would otherwise sit "in the way" of a naive backward
jump is on the far side of the ring from that direction, so single-
level nearest-mark seeking resolves both without ambiguity. Measured:
**14 ticks/pass when the input already matches or needs the force-to-0
path, 15 ticks/pass for the force-to-1 path** (one extra `FLIP`).

**(3) Copy an 8-bit block.** Identical skeleton to echo (same 15-
instruction shape, same two force-recipes), reading source bit `i` and
writing destination bit `i` before advancing to source bit `i+1`, 8
source/destination pairs interleaved on a 16-cell data ring. One full
pass (all 8 bits): **116 ticks** (source `[1,0,1,1,0,0,1,0]` copied
exactly to destination, verified against the reference bit-for-bit).

**(4) Labelled nested loop.** `MARK L=1` (outer top); `MARK L=2` (inner
top); `FLIP; SKIPZ; JB L=2` (inner loop: flip the current cell, loop
while it reads 1 -- self-terminating in <=2 iterations per cell);
`NEXT; JB L=1` (outer: advance, loop back to the outer top). The outer
`JB L=1`'s nearest backward `MARK` is the *inner* one (`L=2`) -- with a
plain, unlabelled nearest-mark seek this would wrongly land inside the
inner loop; the label check correctly passes over it (label mismatch)
to reach the true outer `MARK`. Verified tick-by-tick against the
labelled reference over a full pass through an 8-cell ring: **120
ticks total, 12 or 18 ticks per outer iteration** (12 when the cell
started at 0 -- one inner iteration; 18 when it started at 1 -- two
inner iterations), all 8 cells correctly cleared to 0.

## Summary

| | Single-level | Labelled (L=2) |
|---|---|---|
| Transistors | 152 | 270 |
| vs 28T base machine | 5.4x | 9.6x |
| Truth table | 56/56 | 896/896 |
| Random tick-by-tick trials | 500/500 | 500/500 |
| Local minimality | 122/152 removals break it | 210/270 removals break it (224-case subset) |
| Counter +1 (typical, ~1 carry) | ~17 ticks | -- |
| Echo, per pass | 14-15 ticks | -- |
| 8-bit block copy, full pass | 116 ticks | -- |
| Nested loop, per outer iteration | -- | 12-18 ticks |
