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

## Proposed architecture (to be confirmed by the emulator work below)

* Harvard: program memory 1K × 16-bit words (SRAM loaded by the ESP32), data memory 256 bytes (SRAM), display 32 bytes as latches with LEDs on their outputs.
* Registers: accumulator A, index or second register B, program counter (10 bits), instruction register (16 bits), flags Z and C.
* Instruction word: 4-bit opcode, 1-bit mode (immediate or memory), 8-bit operand, spare bits. About 16 instructions: LDI, LD, ST, ADD, SUB, AND, OR, XOR, SHL, SHR, JMP, JZ, JC, IN, OUT, RETI (plus CALL/RET if the games need them).
* Hardwired control, one instruction per two clock phases (fetch, execute), so slow mode shows exactly two visible steps per instruction.
* Interrupts: one vector. A button press sets its request latch; if interrupts are enabled, the next fetch saves PC and flags into shadow registers (with LEDs) and jumps to the vector; RETI restores them. The handler reads the button port to see which button fired.
* Chip estimate: 25–35 74HC chips plus two SRAMs and LED drivers. LEDs: about 256 for the display plus about 120 for registers, buses and control.

## Tasks

1. ISA specification and a cycle-accurate emulator (Python, plus a JavaScript copy for the web page later), with interrupts and the display.
2. Assembler.
3. Programs in the emulator: counter, Game of Life on 16 × 16, Snake with 4 buttons, Pong with 2 buttons, a scrolling text. Measure instructions per frame and the clock needed for 10–30 frames per second. Change the ISA if a game needs something missing; every addition must be justified by a program.
4. Gate-level design in 74HC parts, simulated against the emulator instruction by instruction.
5. Board plan: block placement on A4, LED count, power budget, silkscreen diagram.
6. The web loader page: edit, assemble, upload, and a live mirror of the board's LEDs.
