# Emulator, assembler and benchmark programs for the ENCODING.md machine

Everything here follows `board/design/ENCODING.md` (v3). All numbers below come from `measure.py` and the check scripts (`python3 run_all.py [--measure]`). Cycles are clock cycles, one instruction per clock. "Frame" means one pass of the main loop with the 60 Hz tick always ready (the wait loop costs about 3 cycles per frame and is included).

## Files

| File | What |
|---|---|
| `isa.py` | encoding fields, memory map and every tunable constant (constants at the top) |
| `emu.py` | cycle-accurate emulator, devices, ILI9341-like LCD model, PNG writer |
| `emu.js`, `runjs.js` | same semantics in JavaScript (Node; no debug-mode checks), runner used by the tests |
| `asm.py` | assembler with listing (`python3 asm.py prog.asm [listing.txt]`) |
| `programs/*.asm` | counter, snake, pong, life, scroll, raycast; `programs/bf.py` (+ `hello.bf`); `programs/lib/` (table start-up routine, LCD macros, font, raycast tables) |
| `programs/check_*.py` | functional checks against reference models |
| `tests/` | unit tests, Python-vs-JS per-cycle comparison |
| `measure.py`, `run_all.py`, `make_listings.py` | measurements, run everything, write `listings/*.lst` |
| `frames/*.png` | rendered LCD frames (snake, pong, life, scroll, raycast_1..4, raycast_full) |

## Verification

* `tests/test_unit.py`: encodings of every alias (hex groups), assembler rejects, ALU/carry/borrow/shift semantics, DJNZ (256 iterations from 0), stacks, CALL/RET conditions, interrupt entry and RETI flag restore, LOOKUP tables, LCD windows.
* `tests/test_equiv.py`: Python and JS run the same program; a hash of the full state (PC, A, C, X, SP, RSP, Z, C and every memory write) is mixed in every cycle and compared every 250 cycles, plus final memory, LCD and LED digests. 40 random programs of 20000 cycles each (random fields, random button events, interrupts enabled in 70 %): 40/40 identical. All 16 opcodes executed (histogram checked). Memory-map constants in `isa.py` and `emu.js` compared automatically.
* `tests/test_programs_equiv.py`: the same per-cycle comparison on all six programs and the compiled Brainfuck hello world, including the real table start-up (no fast path): all identical (1.25 to 1.7 M cycles each).
* Programs are checked against reference models: Snake (159 moves, position, direction, score, board array and LCD cells every move, LFSR food positions, button interrupts), Pong (400 frames, state every frame, full LCD every 25 frames), Life (60 generations, memory and LCD), scroller (240 frames, every pixel of the band against a font model), Brainfuck (26 program/mode combinations against a Python interpreter; output "Hello World!\n"), raycaster (198 frames with scripted buttons; position and angle every frame and all 16000 view pixels against an integer model of the same algorithm).
* The raycaster model shares its algorithm with the assembly; it checks the implementation, not the picture quality. The frames look right (`frames/raycast_*.png`); wall edges show 1 to 2 pixel jitter from the 8-bit distance quantisation.

## Program sizes and speed

Words include the 41-word table start-up routine where the program uses LOOKUP (Pong, Life, scroller, raycaster). Data bytes are initialised or reserved data memory (array regions count in full).

| Program | Words (own code) | Data bytes | Cycles | 10 fps clock (avg / worst) | 30 fps clock (avg / worst) |
|---|---|---|---|---|---|
| counter | 10 | 1 | 8 per count | n/a | n/a |
| Snake (16x15 board, 16x16 px cells, buttons by interrupt) | 222 | 508 | per step: 1671 to 1701 (avg 1677); a step erases the tail and draws the head: 2 x 256 pixels | 0.017 MHz | 0.05 MHz |
| Pong (40x30 cells of 8x8 px) | 245 (204) | 22 | per frame: 525 to 5476 (avg 1897) | 0.02 / 0.05 MHz | 0.06 / 0.16 MHz |
| Game of Life (40x30, only changed cells redrawn) | 178 (137) | 16430 | per generation: 51928 to 73089 (avg 59027) | 0.59 / 0.73 MHz | 1.77 / 2.19 MHz |
| Scrolling text (5x7 font at 4x, 320x28 band, 1 font column per frame) | 239 (198) | 632 | per frame: 31988 to 32263 (avg 32142) | 0.32 MHz | 0.96 MHz |
| Raycaster (160x100 view, 16x16 map, 3 wall colours with side shading) | 495 (454) | 9242 | per frame: 73692 to 102773 (avg 85901) | 0.86 / 1.03 MHz | 2.58 / 3.08 MHz |
| Brainfuck hello world (compiled, optimised) | 160 | 30000-cell tape | 1406 for the whole program | n/a | n/a |

Brainfuck compiler (`programs/bf.py`), hello world, words / cycles: optimised 16-bit tape 160 / 1406; optimised 256-cell page tape (`--tape8`) 164 / 1659; unoptimised 305 / 2518; unoptimised page tape 309 / 2708. Optimisations: run-length merging of `+ - < >`, `[-]` as one clear, reuse of the Z flag before `]` after `+`/`-`. `.` writes the LED port (the test reads the write log), `,` reads the button port. `>` is one word (a dummy `LOAD A,[X+]`), `<` costs 7 words (16-bit decrement).

The 10 and 30 fps clocks are cycles per frame times the frame rate. Snake and Pong are tick-limited games, not limited by the clock. Snake steps every 8 ticks (7.5 steps/s).

## Start-up (LOOKUP tables)

The CPU fills the four tables through the write ports (`init_tables`, `programs/lib/init_tables.inc`, 41 words): **1,123,566 cycles** (about 17 per entry of the 262,144 entries) = 1.12 s at 1 MHz, 0.28 s at 4 MHz, 0.056 s at 20 MHz. Measured once with the real routine, the result compared with the fast path. After start-up: Pong ready at 1,126,280 cycles, raycaster at 1,374,837 (the extra 251 K cycles draw the static screen and status bar). `emu.CPU(..., fast_tables=True)` fills the tables directly for tests.

## Where the encoding forced a workaround (measured)

Counts come from a dynamic profile of whole frames (`measure.py`): the share of executed instructions (equal to cycles) that sit in a pattern, and static word counts. Nothing here is a bug; each item says what a different field or mode would have changed.

1. **LCD pixel streaming dominates, and the loop-closing DJNZ is a third of it.** Share of cycles that are `STORE` to the LCD data port / the DJNZ closing a 2-store pixel loop: Snake 61.9 % / 30.5 %, Pong 51.8 % / 24.4 %, raycaster 43.2 % / 21.6 %, scroller 55.5 % / 0 % (unrolled by macro, 8 words per 4 pixels), Life 9.6 % / 4.5 %. Two bus writes per pixel are forced by the 8-bit LCD bus; the third cycle is the loop. In the raycaster that is 16000 cycles of an 85901-cycle frame (18.6 %); unrolling costs code, an instruction with a repeat count would not.
2. **Pointer setup, no `[X+offset]` and no X arithmetic.** Instructions that load XL/XH/X as a share of cycles: Life 18.3 % (the 3x3 sum reloads XH and XL for each of its three rows, 6 of 15 sum instructions), scroller 8.4 %, raycaster 4.5 % (6 angle-table lookups per ray, 5 words each: `LOAD A,[cah]; ADD #page; MOVE XH,A; LOAD A,[X]; STORE`, about 31 cycles per ray, 5000 per frame = 6 %), snake 0.7 %, Pong 0.4 %. The programs avoid 16-bit address arithmetic by page-aligning arrays (index in XL, array in XH); that costs memory layout, not cycles.
3. **Read-modify-write on memory takes 3 instructions** (`LOAD A,[m]; op; STORE [m],A`). Share of executed instructions: scroller 8.2 %, Life 2.1 % (all of it `+1`), raycaster 1.3 %, Pong 0.6 %, snake 0.1 %. A memory-destination form would save 2 cycles each. Static: 4 / 9 / 6 / 14 / 17 triples (snake / Pong / Life / scroller / raycaster).
4. **STORE cannot take a constant**, so each LCD command or data byte costs two words (`LOAD A,#k; STORE [port],A`). Static pairs: snake 26, Pong 16, Life 13, scroller 21, raycaster 70 (14 % of its code), including about 4 in the start-up routine. Dynamic share is small (snake 0.8 %, Pong 1.9 %, Life 0.4 %, others about 0 %) because pixels dominate the time.
5. **LOAD sets no flags**, so a load followed by a branch needs `TEST #255` (alias, 1 word). 1 to 4 static pairs per program, at most 0.2 % of cycles.
6. **Shifts move one bit.** Snake's cell position needs 4 x `SHL` (4 words/cycles); `MUL #16` would be 1 but needs the tables. Dynamic share 0.2 %. The raycaster uses `MULH #16` as a 4-bit right shift and `MUL #16` as a left shift, one word each.
7. **Zero-length loops:** DJNZ from 0 runs 256 times, so the pixel-run routine starts with `TEST #255; RET Z` (2 words per call; the conditional RET makes this cheap).
8. **16-bit signed add** (raycaster walking): sign extension of a byte uses `TEST #0x80` (flags: Z only, so C survives from the low-byte ADD), `LOAD A,#0`, `JUMP Z`, `LOAD A,#0xFF`, `ADC`. It works only because logic ops leave C alone, as ENCODING.md states.
9. **16-bit compare in the DDA loop** costs 3 to 8 instructions (compare high bytes first, low bytes only on equality). Not measured against an alternative.

Not a workaround: `LOAD X,#imm16`, conditional RET/CALL, `[X+]`, MOVE as LOAD with a register source, MUL/MULH/DIV/MOD as one word, hardware flag save on interrupt (handler is `PUSH A; LOAD A,[IRQ_CAUSE]; OR [pend]; STORE; POP A; RETI`, 6 words plus 1 cycle entry) all saved code in these programs.

## Proposals for the user (choices the design left open)

All are constants or small functions in `isa.py` / `emu.py` / `emu.js` / `asm.py`, easy to change.

Memory map (`isa.py`):
* Data stack page 0x0100 to 0x01FF; devices at 0xFF00 to 0xFFFF; assembler places variables from 0x0200.
* `BTN` 0xFF00 read: button state (bit 0 up, 1 down, 2 left, 3 right). `IRQ_EN` 0xFF01 r/w: 4 enable bits. `IRQ_CAUSE` 0xFF02 read: buttons that caused the last interrupt, latched at entry; any write clears the pending latches. `FRAME` 0xFF03: reads 1 if a 60 Hz tick happened since the last read, and clears it (tick period `TICK_CYCLES` = 16667 at 1 MHz; override per run). `RNG` 0xFF04: 16-bit LFSR (taps 0xB400, seed 0xACE1), 8 steps per read. `LCD_CMD` 0xFF10, `LCD_DATA` 0xFF11 (write). `LED` 0xFF20 r/w.
* **Table write ports `TBL0` to `TBL3` at 0xFF30 to 0xFF33** (write only, each with an auto-incrementing 16-bit pointer, wrapping to 0 after 65536 writes). The design says the CPU fills the tables but lists no write path; this is the smallest one. Table address = operand << 8 | A (the two select bits above it), so filling in operand-major order streams all four tables in order. Tables 4 to 7 read as 0.
* Reset: PC 0, SP 0 (first PUSH writes 0x01FF), RSP 0 (first CALL writes slot 255), flags 0. Interrupt vector 0x0001 (a JUMP goes there; reset code is at 0x0000, so programs start `JUMP start; JUMP irq`).
* Return stack: 256 entries (RSP is 8 bits), each entry = PC + Z + C. CALL stores the flags too, so a RETI after a plain CALL restores the flags from call time.

Interrupts: button rising edges set a latch; when `latch AND enable` is non-zero the next clock is the entry (it replaces one fetch): cause = latch AND enable, those latch bits clear, PC and flags go to the return stack, PC = vector. No hidden global mask, so a new press can nest; the handler should read `IRQ_CAUSE` first. If you prefer an I flag, say so.

LCD (`emu.py`): 320 x 240, ILI9341-like. `0x2A` column window and `0x2B` row window (4 data bytes each: start high/low, end high/low), `0x2C` memory write (cursor to window start; two data bytes per pixel, RGB565 high byte first; wraps inside the window), `0x36` MADCTL with only bit 5 (row/column exchange, cursor walks down first; used for column rendering by the scroller and raycaster). Everything else is ignored. One byte per clock, no busy time. `emu.save_frame` writes PNGs (no Pillow needed).

Instruction details:
* LOAD ignores keep and carry bits; shifts ignore the source field and do not step `[X+]`.
* Register code 7 is the flags `F` (bit 0 = Z, bit 1 = C): `LOAD F`, `STORE F`, `PUSH F`, `POP F`.
* `LOAD X` takes only a 16-bit constant (any other source is rejected by the assembler; the emulator zero-extends). `STORE X`, `PUSH X`, `POP X` rejected (they would need two bytes). `POP SP` and `POP RSP` rejected. `LOAD XL,[X+]` and `LOAD XH,[X+]` rejected (X changes twice).
* STORE with a constant or register source is rejected by the assembler; the emulator treats it as a no-op. Kept as is: STORE and PUSH of A, C, XL, XH, SP, RSP, F.
* `LOAD G, [X+]` and `STORE [X+], G` step X after the access.
* Fetch beyond the loaded program reads word 0 (`ADD #0` with keep off: only the flags change). A `JUMP` to itself halts the emulator unless button events are still pending.
* NOP is `JUMP always` to the next line (as in HANDOVER-E); the encoding also has `JUMP never` (select 000) which would do the same.
* The assembler accepts condition names Z, NZ, C, NC, ZC, HI, NEVER and the readings EQ, NE, LT (carry after CMP), GE, LE, GT.

Loader and memory: **the programs assume the loader also writes the initial data memory** (strings, font, map, trig tables). The handover says only the loader writes program memory and the CPU cannot write it; there is no instruction that reads program memory, so initialised data must be loaded into data memory by the ESP32 (or every byte would cost two instructions). Please confirm.

Assembler: syntax destination first; `.code/.data/.org/.equ/.byte/.word/.space/.string/.include/.macro`. Macros are the only multi-word lines and are tagged `[macro NAME]` in the listing (LCDCMD, LCDBYTE and a few program-local ones). `.data` regions are named by their label; overlaps, the stack page and the device page are refused; `emu.CPU(debug=True, regions=...)` raises on writes outside declared regions and on stack overflow or underflow of both stacks.

## Problems and open points in ENCODING.md found while building

* No CPU write path to the table memory and no interrupt acknowledge mechanism are specified (proposals above). The table memory is 4 x 64 K = 256 KB; the fill takes 1.12 M clocks.
* Register code 4 (whole X) is only defined for LOAD with a constant; STORE, PUSH, POP of it are undefined (rejected).
* STORE with source 0 or 4 to 7 and PUSH/POP with the select/source fields have no defined meaning (no-ops in the emulator).
* Return-stack entry width: the interrupt entry needs PC and flags; a call entry needs only PC. One entry format for both is assumed.
* Division by zero in the DIV/MOD tables is undefined; the start-up routine writes quotient 255 and remainder = A.
* The opcode table says top bit "assumed, to confirm"; the emulator and assembler use it as written.

## Performance of the tools

Python runs about 1 M cycles/s (the start-up routine takes about 1 s); JS is faster. `run_all.py` takes about 2 minutes, `measure.py` 25 s.
