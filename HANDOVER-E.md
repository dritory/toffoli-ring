# Handover E: the visible 8-bit computer (A4 board)

Separate from the minimal-computer research. Goal: an educational and art piece. An 8-bit computer on one A4 board where every register, bus and control line has LEDs, the silkscreen draws the block diagram, programs upload from a web page, and simple games run with button interrupts.

## Requirements

* 8-bit data path. Logic chips allowed (74HC family). Discrete parts not required.
* Board A4 (210 × 297 mm), one PCB.
* Display: 16 × 16 LED matrix that is memory-mapped RAM (32 bytes); the LEDs show the stored bits directly.
* Input: 4 buttons, each can raise an interrupt; also readable as an input port.
* Clock: single step, slow (0.5–20 Hz) to watch phases, fast (up to about 1 MHz) for games. Knob and step button.
* Loader: ESP32 in a marked corner, web page upload of assembled programs, not part of the computer (bus-isolated while running).
* Every register, both buses, flags, program counter, instruction register, ALU inputs and outputs, and each control line has an LED. Silkscreen labels each block like a textbook diagram.

## User decisions so far

* Classic accumulator architecture (the user designs the instruction set on paper; the agent's set is in board/spoilers/).
* Wide instruction words are fine; memory is cheap. Control-word style encoding with bus-safety fields decoded on board is under consideration.
* Brainfuck runs by compiling to the native instructions in the assembler, not as the instruction set.
* Main screen: a 320×240 RGB LCD with its own screen memory (ILI9341-class, 8-bit 8080 parallel bus), driven through an output port: set a window, then stream pixels; the LCD auto-increments. The 16×16 LED matrix stays as the "see the memory" display.
* Stretch goal: a Doom-like raycaster demake (160×100 3D view, static status bar). This implies requirements for the design: data memory beyond 256 bytes (a page register for 64 KB), fast table lookup (multiply by square tables, trig and reciprocal tables), call and return, a longer program counter (4–8K words). Estimated 7 frames/s at 1 MHz, about 25 at 4 MHz (unverified).

## Instruction set (decided: 14 opcodes plus 2 spare, 4-bit field)

The user designs the details and encodings on paper; this fixes the scope.

| Group | Opcodes |
|---|---|
| Data | LOAD, STORE |
| Arithmetic | ADD, SUB, LOOKUP |
| Logic and shifts | AND, OR, XOR, SHL, SHR |
| Control | JUMP (condition: always, zero, not zero, carry, no carry), CALL, RET, DJNZ |

Fields shared by the data, arithmetic and logic instructions:
* Operand mode: constant, memory, indexed [B+offset], post-increment [B+], stack ([--SP] for store, [SP++] for load), register (the other register).
* Destination (2 bits): A, B, none (flags only), spare.
* Use-carry bit on ADD, SUB, SHL, SHR for multi-byte arithmetic.

LOOKUP: a function-table unit. A table memory addressed by A, B and a table-select field in the instruction; results go to A (and B for two-byte results). Table 0: 8×8 multiply (16-bit product). Table 1: 8÷8 divide (quotient and remainder). Further tables (sine, reciprocal, squares) as needed. The CPU fills the tables itself at start-up (incremental addition and subtraction, about a second in total at 1 MHz), so the ESP32 never computes. Silkscreen block: "FUNCTION TABLE".

RET has a bit that also restores the flags (return from interrupt).

### Aliases (assembler nicknames, one word each)

Every alias is exactly one machine instruction with some fields fixed. The card prints the 14 opcodes first and the aliases underneath with their expansions; the assembler listing and the phone view always show the real instruction next to the alias.

| Alias | Machine instruction |
|---|---|
| MOVE B,A / MOVE A,B | LOAD with destination B/A, register operand |
| CMP x | SUB x, destination none |
| TEST x | AND x, destination none |
| MUL / DIV | LOOKUP table 0 / table 1 |
| PUSH A / POP A | STORE A,[--SP] / LOAD A,[SP++] |
| NOT A | XOR A,0xFF |
| RETI | RET with restore-flags bit |
| NOP | JUMP to the next line |

Memory-mapped devices (no instructions): buttons and interrupt enable, 60 Hz frame tick, hardware random-number generator, LCD data and command port, LED output port.

Hardware implied: stack pointer (up/down counter), B built from up/down counters (DJNZ, post-increment), function-table memory with a visible block showing inputs and outputs, destination decode with a "none" option, register operand path.

Stopping rule for any further opcode (all three must hold): it cuts cycles or code by at least about 5% in one benchmark program (Snake, Pong, Life, raycaster, compiled Brainfuck), measured in the emulator; it is not expressible as an alias of an existing opcode; and the whole set still fits one labelled box on the silkscreen.

## Memory (decided)

* 8-bit data, 16-bit addresses.
* Program memory: 64K words, 16-bit program counter. Separate from data memory (Harvard). The CPU cannot write program memory; only the loader writes it while the CPU is stopped.
* Data memory: 64 KB. Direct addressing: the full 16-bit data address is carried in the instruction word.
* Instruction word: 32 bits (four 8-bit program memory chips, SMD). Worst case is about 26 bits (opcode 4, operand mode 3, destination 2, carry 1, address 16), jumps about 23 (opcode 4, condition 3, target 16); no instruction carries two addresses. Spare bits available.
* Open: how indexed addressing forms its address (16-bit base in the instruction plus 8-bit B needs a 16-bit adder in the visible CPU; B as a 16-bit pointer needs a wider B instead).

Design principle: the visible CPU spends chips where the computing happens (ALU, registers, flags, decode, program counter, address forming). Width and storage go to cheap SMD memory; loading, clocking and observation go to the ESP32, which never computes.

## Build rules (decided)

* Front side: through-hole parts that make up the visible CPU (kit-friendly), each with its LEDs. Back side: SMD support parts (memory chips, buffers, display driving, ESP32).
* The ESP32 never computes program results. It only loads programs, drives the clock (stop, single-step, speed), and observes the buses to show the current instruction and source line on a phone. The silkscreen says so.
* Single-cycle Harvard RISC: each clock fetches one instruction from program memory and executes it; the instruction word drives control directly, so single-step shows one whole instruction per press.
* Control decode as a through-hole diode matrix with an LED per control line, so the decoding is visible and hand-traceable.

## Honesty rules

* The native instruction format (the bit layout the hardware executes) is the instruction set. It is published in full and printed on the silkscreen next to the instruction LEDs, so the machine can be hand-programmed from the board alone.
* The assembler only translates: one assembly line becomes one instruction word. Anything that expands to several words is marked as a macro.
* Bits that could cause bus fights are encoded as small fields and decoded on the board, so no instruction word can damage the hardware.
* The ESP32 loads, clocks and observes; it never takes part in execution.
* Part and chip counts include every chip on the board, including decoding and support.

## Assembly (decided, pending user confirmation)

* JLCPCB assembles all SMD parts: every LED (0805 or 1206, a few hundred), resistors, memory chips, buffers, display driving, ESP32 module, power.
* Only the visible logic chips are through-hole: about 20–25 DIP 74HC chips in sockets, hand-soldered (or JLC through-hole assembly). About 400–500 joints including sockets.
* The diode-matrix decoder: through-hole diodes if the look is worth about 200 joints, otherwise SMD diodes in a labelled grid.

## Proposed architecture (SPOILER: an agent's proposal, see board/spoilers/)

* (Superseded by the Memory section above.) Harvard: program memory 1K × 16-bit words, data memory 256 bytes, display 32 bytes as latches with LEDs on their outputs.
* Registers: accumulator A, index or second register B, program counter (10 bits), instruction register (16 bits), flags Z and C.
* Instruction word: 4-bit opcode, 1-bit mode (immediate or memory), 8-bit operand, spare bits. About 16 instructions: LDI, LD, ST, ADD, SUB, AND, OR, XOR, SHL, SHR, JMP, JZ, JC, IN, OUT, RETI (plus CALL/RET if the games need them).
* Hardwired control, single-cycle: one clock per instruction.
* Interrupts: one vector. A button press sets its request latch; if interrupts are enabled, the next fetch saves PC and flags into shadow registers (with LEDs) and jumps to the vector; RETI restores them. The handler reads the button port to see which button fired.
* Chip estimate: 25–35 74HC chips plus two SRAMs and LED drivers. LEDs: about 256 for the display plus about 120 for registers, buses and control.

## Tasks

1. ISA specification and a cycle-accurate emulator (Python, plus a JavaScript copy for the web page later), with interrupts and the display.
2. Assembler.
3. Programs in the emulator: counter, Game of Life on 16 × 16, Snake with 4 buttons, Pong with 2 buttons, a scrolling text. Measure instructions per frame and the clock needed for 10–30 frames per second. Change the ISA if a game needs something missing; every addition must be justified by a program.
4. Gate-level design in 74HC parts, simulated against the emulator instruction by instruction.
5. Board plan: block placement on A4, LED count, power budget, silkscreen diagram.
6. The web loader page: edit, assemble, upload, and a live mirror of the board's LEDs.

## Visible parts estimate (front, through-hole)

| Block | Parts | LEDs |
|---|---|---|
| Program counter (10 bit) | 3 × 74HC161 | 10 |
| Instruction word | (from program SRAM on the back) | 16 |
| Control decode | diode matrix (about 60–100 diodes) + 1–2 × 74HC138 | about 16 |
| Registers A, B | 2 × 74HC574 | 16 |
| ALU (add, subtract, AND, OR, XOR, shift) | 2 × 74HC283, 74HC86, 74HC08, 74HC32, 2–4 × 74HC157 | 8 result |
| Flags Z, C | 74HC74, zero detect (74HC4078 or diodes) | 2 |
| Interrupts (4 buttons) | 74HC74 × 2 request latches, 2 × 74HC574 shadow PC and flags | 4 + 16 |
| Input and output ports | 74HC244, 74HC574 | 8 + 8 |

About 20–25 through-hole chips plus the diode matrix. Back side: program SRAM, data SRAM, bus buffers for loading (74HC245), display memory and 16 × 16 matrix driving, ESP32, power.
