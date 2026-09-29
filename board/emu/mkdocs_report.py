#!/usr/bin/env python3
"""Generate REPORT.md: measurements are recomputed from the emulator, test output is captured live."""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure, frames
from runprog import load
from isa import *

M = measure.collect()
FR = frames.all_frames()
tests = subprocess.run([sys.executable, os.path.join(HERE, 'test_equiv.py')], capture_output=True, text=True, cwd=HERE).stdout.strip()
checks = subprocess.run([sys.executable, os.path.join(HERE, 'check_programs.py')], capture_output=True, text=True, cwd=HERE).stdout.strip()

names = list(M)
# static opcode use table
ops = ['LD', 'ST', 'ADD', 'SUB', 'AND', 'OR', 'XOR', 'ROL', 'ROR', 'JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'RETI']
use = '| instr | ' + ' | '.join(names) + ' |\n|---|' + '---|' * len(names) + '\n'
for o in ops:
    use += '| %s | ' % o + ' | '.join('%d / %d' % (M[n]['static'].get(o, 0), M[n]['dynamic'].get(o, 0)) for n in names) + ' |\n'

perf = '| program | words | frame = | cycles per frame min / mean / max | 10 fps: mean / worst | 30 fps: mean / worst |\n|---|---|---|---|---|---|\n'
for n in names:
    r = M[n]
    perf += '| %s | %d | %s | %d / %.0f / %d | %.1f / %.1f kHz | %.1f / %.1f kHz |\n' % (
        n, r['words'], r['frame_is'], r['cyc_min'], r['cyc_mean'], r['cyc_max'],
        10 * r['cyc_mean'] / 1e3, 10 * r['cyc_max'] / 1e3, 30 * r['cyc_mean'] / 1e3, 30 * r['cyc_max'] / 1e3)

life, _ = load('life')
sym = life.symbols
# loop body sizes from the listing: p2 .. its closing JC
addr_end = [a for a, w, ln, t in life.listing if t.startswith('JC p2')][0]
p2body = addr_end - sym['p2'] + 1
addr_end1 = [a for a, w, ln, t in life.listing if t.startswith('JC p1')][0]
p1body = addr_end1 - sym['p1'] + 1
life_unrolled = 32 * p2body + 16 * p1body
p2idx = [w for a, w, ln, t in life.listing if sym['p2'] <= a <= addr_end and (w >> 11) < 16 and ((w >> 8) & 3) == 2]
p2offs = len(set(w & 255 for w in p2idx))
import re
gens = re.search(r'(\d+) generations', checks).group(1)
snake, _ = load('snake')
npix = sum(1 for a, w, ln, t in snake.listing if False)
S = M['snake']; P = M['pong']; Lf = M['life']; Sc = M['scroll']; C = M['counter']

def frac(a, b):
    return '%.0f%%' % (100.0 * a / b)

REPORT = f"""# Emulator, assembler and games: results

Everything is in `board/emu/`. Reproduce: `python3 test_equiv.py` (Python vs JavaScript), `python3 check_programs.py` (programs vs
independent models), `python3 measure.py`, `python3 frames.py`, `python3 mkdocs_isa.py && python3 mkdocs_report.py`.

| file | what |
|---|---|
| `ISA.md` | instruction set, control lines per instruction, one-clock argument (generated from `isa.py`) |
| `isa.py` | opcode and control-line tables shared by emulator and assembler |
| `emu.py` / `emu.js` | cycle-accurate emulator, Python and JavaScript port (browser or node); driven by the same control-line table |
| `asm.py` | two-pass assembler: labels, `.equ`, `.data`/`.text`/`.org`, `.byte/.word/.ascii/.asciz/.space`, macros, expressions, comments; `-l` listing, `-o` JSON image |
| `programs/*.asm` | counter, life, snake, pong, scroll |
| `scripts.py` | scripted button presses for each run |
| `test_equiv.py`, `check_programs.py`, `runjs.js` | tests |
| `runprog.py`, `measure.py`, `frames.py` | run, measure, capture frames |

## Final instruction set: 15 instructions

`LD  ADD  SUB  AND  OR  XOR  ROL  ROR  ST  JMP  JZ  JNZ  JC  JNC  RETI`

Register instructions take R = A or B and a second operand: immediate, `[addr]`, `[B+addr]` or the other register.
Ports (buttons, pending requests, interrupt enable, OUT) are memory mapped at 0xC0-0xC2, so there is no IN, OUT, EI or DI.
No CMP, CALL/RET, ADC, SHR/SHL, push/pop. Full details: `ISA.md`.

## Tests

Python and JavaScript emulators, same program and the same button script, state compared after **every** cycle (pc, A, B, Z, C,
IE, pending, shadow PC and flags, OUT, buttons, a position-weighted checksum of all RAM, the control-line mask) and the full 256-byte RAM every 1000 cycles.
Node v22 was available. The last ten entries run random 16-bit words (so every opcode including unassigned ones, all addressing
modes, and interrupt entries) with random button events. As a check of the test itself, a deliberate one-line carry error in `emu.js`
made 7 of 16 runs fail.

```
{tests}
```

Functional checks against independent Python models:

```
{checks}
```

## Programs and measurements

"Frame" is what the program marks with a write to the OUT port. Cycles = instructions here, except that each interrupt entry costs one extra
cycle (Snake: {S['isr_cycles']} cycles per button press including the handler; {S['isr_count']} presses in the scripted run).
Frame cost is independent of the clock: the clock knob is the game-speed knob (no timer, no delay loops).

{perf}
Clock needed = frames per second x cycles per frame. "Worst" uses the longest frame seen in the scripted run. Snake has no fixed
worst case: after eating, the new food cell is drawn by retrying an LFSR until it lands on an empty cell (about 32 cycles per retry).

Program size and instruction use, static count / executed count in the scripted run:

{use}
Program memory used: counter {C['words']}, life {Lf['words']}, snake {S['words']}, pong {P['words']}, scroll {Sc['words']} of 1024 words
(macros expanded). Data RAM initial image: life {Lf['data_bytes']} bytes, snake {S['data_bytes']}, pong {P['data_bytes']}, scroll {Sc['data_bytes']} (font and text), of 192.

### How the programs work (short)

* **counter**: 16-bit counter in row 0; each frame rows 0-14 copy down one row (30-byte indexed loop), so the display is the count history.
* **life**: bit-sliced on 8 cells at a time. Phase 1 copies the 16 rows and builds west/east neighbour planes with 16-bit rotates
  through carry (ROR/ROL chained through LD, which keeps C). Phase 2 loops over the 32 display bytes: three full/half adders sum the
  8 neighbour planes, then `new = (carry-weight-2 count == 1) and (weight-1 bit or alive)`. Wraps at all four edges. Identical to a
  reference torus model for {gens} generations in the check above.
* **snake**: position packed as `yyyyxxxx`, so the display byte is `0xE0 + pos>>3` and the mask is looked up by `pos&7`. Direction
  tables `DELTA`/`KEEP` give the wrapping move without branches. Body is a 64-entry ring buffer. Four buttons -> interrupt handler
  stores the requested direction (reversal is ignored by the main loop). Eating grows and places new food with an 8-bit LFSR.
  Self collision flashes the display and restarts.
* **pong**: left paddle from buttons 0/1 read from the input port, right paddle a computer player that moves at most every second
  frame. Ball position is packed too, so a move is `BP += VX + VY`. Score is in the OUT LEDs (left high nibble, right low nibble).
* **scroll**: message and 5x7 font A-Z in the data image; each frame one new font column enters at the right and all 16 rows shift
  left by one pixel with ROL chains (carry passes the pixel from the right byte to the left byte).

### Text frames

Buttons in the scripts: 0 up, 1 down, 2 left, 3 right (Snake); 0 up, 1 down (Pong).

**counter** (row 0 = newest count, older counts below; 16 bits, bit 15 at the left)
```
{FR['counter']}
```
**life** (glider top left, R-pentomino; wrapping torus; frame = generation)
```
{FR['life']}
```
**snake** (starts heading right with food ahead; buttons: down at cycle 1530, left 2100, right 2400 (ignored, reverse), up 2700, right 3300, down 3700, left 4200)
```
{FR['snake']}
```
**snake, self collision** (three quick turns make the head run into its own body: display inverts as a flash, then restarts with length 5)
```
{FR['snake@death']}
```
**pong** (left paddle driven by scripted buttons, right paddle by the program; 9 lit pixels at every frame)
```
{FR['pong']}
```
**scroll** ("HELLO TOFFOLI RING", one pixel per frame)
```
{FR['scroll']}
```

## Which program justified which instruction or feature

| instruction / feature | justified by | evidence |
|---|---|---|
| `LD`, `ST` | all | |
| `ADD`, `SUB`, `JMP`, `JZ`, `JNZ`, `JC` | all | loops, counters, compares, `SUB` + `JC/JNC` replaces CMP |
| `AND`, `OR`, `XOR` | life (bit-sliced adders), snake/pong (masks, pixel set/clear: `OR` then `XOR` clears a bit) | life executes {Lf['dynamic']['AND']} AND, {Lf['dynamic']['OR']} OR, {Lf['dynamic']['XOR']} XOR per 24 generations |
| `ROL` | life (east plane), scroll (row shifts) | scroll: {Sc['static']['ROL']} static ROL |
| `ROR` | life (west plane), snake and pong (`pos >> 3` for the display byte), scroll (column bits), LFSR | |
| `JNC` | counter, snake (LFSR), pong (bounds tests) | free in hardware: BR_NOT is shared with JNZ; could be rewritten with `JC` + `JMP` at +1 instruction on rare paths |
| `RETI`, shadow PC/flags, pending latches | snake (four buttons via interrupt) | the interrupt is required by the handover; snake would also work by polling the pending register once per frame (about +2 cycles per frame plus the same handler code inline), so in Snake the interrupt buys immediate response, not fewer cycles. A press costs {S['isr_cycles']} clocks in total |
| indexed addressing `[B+imm]` | life, snake, pong, scroll, counter | {frac(Lf['idx_dyn'], Lf['total_instr'])} of all executed instructions in life, {frac(C['idx_dyn'], C['total_instr'])} in counter, {frac(S['idx_dyn'], S['total_instr'])} in snake use it. Life's inner loop is {p2body} words with {len(p2idx)} indexed operands at {p2offs} different offsets from one B; unrolled 32 times it would take about {life_unrolled} words (program memory: 1024), and without the immediate offset each access needs an extra `ADD B`/`SUB B` (estimate: +10 to +20 instructions on {p2body} per byte). Table lookups (mask, delta, keep, font) and the ring buffer are impossible without an index register |
| operand = other register (`LD B, A`) | snake, pong, scroll | the only use is `LD B, A` ({S['sreg_static']} + {P['sreg_static']} + {Sc['sreg_static']} static sites, {frac(S['sreg_dyn'], S['total_instr'])} / {frac(P['sreg_dyn'], P['total_instr'])} / {frac(Sc['sreg_dyn'], Sc['total_instr'])} of executed instructions). Without it: `ST tmp,A` + `LD B,tmp`, about +5 % cycles. **This is the weakest justification**; dropping it saves about 4 chips (see below) |
| memory-mapped I/O (no IN/OUT/EI/DI) | all | saves 4 opcodes; OUT is the frame marker in every program |
| `LD` sets Z, keeps C | pong, scroll (`LD` then `JZ`), life/scroll (C survives loads between rotates) | |

Not needed by any program, so not added:

* **CALL/RET**: the biggest program is {P['words']} words of 1024 with `PIXADDR`/paddle macros expanded inline. A subroutine would save
  words, not cycles (it adds a link register and a PC mux input).
* **CMP**: in the first ISA draft. After rewriting, all compares are `SUB` with a dead result, or a descending loop; life got 48
  cycles per generation faster (2527 to 2479), the others are unchanged. Removed.
* **ADC/SBC, SHR/SHL with zero fill, INC/DEC, NOT, NEG, swap**: `ADD A,0` clears C for shifts; `XOR A,0xFF` is NOT; `LD A,0` + `SUB` is NEG.
* **EI/DI**: port write to 0xC2. **IN/OUT**: memory mapped.
* **Multiply**: the only product (`ch*5` in scroll) is `ADD A,0`, `ROL`, `ROL`, `ADD`.

## What does not fit the single-cycle hardware as estimated in HANDOVER-E

1. **Chip count is about 53, not 25-35.** Breakdown (74HC, front side, no SRAM/display drivers): PC 3 x 161 + load mux 3 x 157; A, B 2 x 574;
   operand muxes 8 x 157 (X 2, Y two levels 4, other register 2); address adder 2 x 283 + IDX gating 2 x 08; subtract inverters 2 x 86; ALU adder 2 x 283;
   logic unit 4 x 153 used as a per-bit two-input look-up table (AND, OR, XOR, PASS need no gate chips); result mux 6 x 157 (rotate direction 2, logic/rotate 2, sum 2);
   flags 3; interrupts (pending/IE flip-flops, shadow PC+flags 2 x 574, gating) 7; I/O (244, 574, 138) 4; control decode (3 x 138 + S/D gates) 5.
   The second (address) adder alone is 4 chips. Ways to cut: drop the register operand (-4 chips, +5 % cycles), drop the offset of `[B+imm]` (-4 chips, but Life needs roughly +25 %
   cycles (estimate) and every table lookup needs an `ADD B,base` first).
2. **Critical path is `LD A,[B+imm]` chained into the ALU**: two 8-bit adders and the data SRAM in series, about 320 ns at 5 V. 1 MHz is possible at 5 V,
   marginal at 3.3 V. The games need only 1-80 kHz, so this only limits the fast end of the clock knob.
3. **Two-phase clocking.** PC clocks on the rising edge, A/B/flags/shadow/OUT on the falling edge (gated with the inverted clock), the data-memory write in the low half.
   With single-step, A/B LEDs change half a step after the PC LEDs. Purely single-edge 74HC574 registers with gated enables would glitch, because the enables change right after the PC edge.
4. **No instruction register.** In a Harvard machine with asynchronous program SRAM the "IR" is the SRAM output; the 16 IR LEDs sit on that bus. The SRAM must be asynchronous.
5. **Display readback.** Programs read the display (Snake collision test, Life copy, pixel set/clear). The LED latches can't be read back, so the display
   region needs a write-through copy in the data SRAM (writes go to both, reads come from the SRAM).
6. **Loader must also write data RAM.** The font, mask and direction tables and the text are initial data (`.data`). The ESP32 has to load them into
   data SRAM (addresses below 0xC0) at upload time, not only program memory. Programs that modify their tables would need a reload before a re-run from reset.
7. **Interrupt entry discards the fetched instruction** (it is re-fetched after RETI, because the saved PC points at it). A and B are not saved by hardware:
   the handler saves A in RAM and must not use B (Snake does exactly that). Buttons must be debounced in hardware (RC + Schmitt or an SR latch); a press in the same clock as an acknowledge write may be lost.
8. **No timer.** Game speed is the clock rate. At 1 MHz Snake would run at about {round(1000000 / S['cyc_mean'], -2):.0f} moves per second. Playable speeds are 0.7-2.8 kHz (Snake), 1-5 kHz (Pong), 1.5-4.6 kHz
   (scroll); the 0.5-20 Hz range shows every phase of the computer. If fast clock plus playable speed is wanted, either add a 30 Hz tick bit to the button port
   or add a software delay loop (about 10 instructions).
9. **Snake limits**: maximum length 63 (ring of 64), no win detection, food search has no worst-case bound.
10. **Undefined behaviour is silent**: unassigned opcodes are NOPs, `ST` with S = 11 stores to the direct address, an initial-data byte above 0xBF is refused by the assembler.
"""
open(os.path.join(HERE, 'REPORT.md'), 'w').write(REPORT)
print('REPORT.md written', len(REPORT))
