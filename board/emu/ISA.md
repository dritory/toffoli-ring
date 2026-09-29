# ISA: the visible 8-bit computer

Single-cycle Harvard RISC. One clock = fetch, decode, execute, write back. 15 instructions.
Everything below is what `isa.py`, `emu.py`, `emu.js` and `asm.py` implement; the control-line tables are generated from `isa.py`.

## 1. Programmer's model

| item | size | notes |
|---|---|---|
| A, B | 8 bit | general registers. Every register instruction can work on either (field D). B is also the index register. |
| PC | 10 bit | 1024 program words. Reset: PC = 0. Interrupt vector: address 1 (put `JMP isr` there). |
| Z, C | 1 bit each | Z = result was zero. C = carry out; after SUB it is "no borrow". |
| Program memory | 1024 x 16 bit | instruction words, read only while running (loaded by the ESP32). |
| Data memory | 256 x 8 bit | 0x00-0xBF RAM (192 bytes), 0xC0-0xDF I/O page, 0xE0-0xFF display RAM (32 bytes). |
| Display | 16 x 16 | byte 0xE0 + 2*row + half; half 0 = columns 0-7 with column 0 in bit 7, half 1 = columns 8-15 with column 15 in bit 0. Writes show at once on the LEDs. Reads return the last value written. |
| Shadow PC, Z, C | 10+1+1 bit | filled on interrupt entry, restored by RETI. A and B are **not** saved. |
| IE | 1 bit | interrupt enable (cleared on entry, set by RETI, writable through 0xC2). |

I/O page (data addresses, register = address & 3; the page repeats every 4 bytes up to 0xDF):

| address | read | write |
|---|---|---|
| 0xC0 | buttons: bit n = button n is held (bits 4-7 = 0) | OUT port (8 LEDs). Programs also use it as the frame marker. |
| 0xC1 | pending press requests, bit n = button n was pressed since acknowledged | acknowledge: every bit written as 1 clears that request |
| 0xC2 | IE (bit 0) | IE = bit 0. Interrupts are off after reset. |
| 0xC3 | 0 | ignored |

A press of button n (debounced in hardware) sets pending bit n. When IE = 1 and any pending bit is set, the next clock is an
interrupt-entry cycle (section 4). Reads of the I/O page have no side effects.

## 2. Instruction word

```
register group (op5 < 16)   15..11 op5 | 10 D | 9..8 S | 7..0 imm8
control group  (op5 >= 16)  15..11 op5 | 10 0 | 9..0 target10
```

* D selects the register R the instruction works on and writes: 0 = A, 1 = B.
* S selects the second operand `src` (register group):

| S | assembler | src | address |
|---|---|---|---|
| 00 | `imm` | imm8 | - |
| 01 | `[imm]` | mem[imm8] | imm8 |
| 10 | `[B+imm]` | mem[(imm8 + B) mod 256] | uses B before the instruction executes |
| 11 | `A` or `B` | the other register (R = A: src = B; R = B: src = A) | - |

* ST uses S only for the address: S = 01 (or 00) direct, 10 indexed. It stores R.
* ROL and ROR ignore S and imm8.
* op5 = 0, 10-15 and 22-31 are unassigned and behave as NOP (no function line is asserted, nothing is written).

## 3. Instruction set (15 instructions)

| mnemonic | op5 | operation | flags set |
|---|---|---|---|
| `LD R, src` | 1 | R = src | Z |
| `ADD R, src` | 2 | R = R + src | Z C |
| `SUB R, src` | 3 | R = R - src, C = 1 when no borrow (R >= src) | Z C |
| `AND R, src` | 4 | R = R and src | Z |
| `OR R, src` | 5 | R = R or src | Z |
| `XOR R, src` | 6 | R = R xor src | Z |
| `ROL R` | 7 | rotate R left through carry: R = R<<1 + C, C = old R7 | Z C |
| `ROR R` | 8 | rotate R right through carry: R = C<<7 + R>>1, C = old R0 | Z C |
| `ST [addr], R` | 9 | mem[addr] = R | - |
| `JMP label` | 16 | PC = target | - |
| `JZ label` | 17 | if Z: PC = target | - |
| `JNZ label` | 18 | if not Z: PC = target | - |
| `JC label` | 19 | if C: PC = target (after SUB: R >= src) | - |
| `JNC label` | 20 | if not C: PC = target (after SUB: R < src) | - |
| `RETI` | 21 | PC = shadow PC, Z,C = shadow flags, interrupts on | Z C (restored) |

Flag rules (one line per flag on the board: UPZ and UPC):

* Z is updated by LD, ADD, SUB, AND, OR, XOR, ROL, ROR from the 8-bit result. ST and jumps leave it alone.
* C is updated only by ADD, SUB, ROL, ROR. LD, AND, OR, XOR, ST keep C, so a carry survives loads and stores between rotates
  (used for 16-bit rotates in Life and the scroller).
* Clear carry: `ADD A, 0`. Set carry: `SUB A, 0`.
* Compare without a compare instruction: `SUB` and test C (C = 1: R >= src) or Z. There is no CMP: no program needed it
  (section 8).
* Conditions after SUB: equal = Z; unsigned R >= src = C; unsigned R < src = not C.

Register-to-register: `LD B, A` and `LD A, B` copy; `ADD A, B` etc. work. `OP R, R` is not encodable (use ROL/ROR).

## 4. Interrupt sequence

At the start of a clock, if IE = 1 and any pending bit is set, the clock is an **interrupt-entry cycle** instead of executing
the instruction at PC: shadow PC = PC, shadow Z,C = Z,C, PC = 1, IE = 0; nothing else changes (the fetched instruction is
discarded, its control lines are gated off, line INT lights). `RETI` restores PC and flags from the shadow registers and
sets IE = 1; if a request is already pending the next clock enters the handler again. Interrupts never occur in the middle
of an instruction. Latency: at most one instruction (1 clock). The handler must save/restore A itself (and B if it uses it).
Measured in Snake: entry + `JMP isr` + handler + RETI = 21 clocks.

Reset: PC = 0, A = B = 0, Z = C = 0, IE = 0, pending = 0, OUT = 0. The display and RAM are not cleared by hardware.

## 5. Control lines

Every line has an LED. The diode matrix (fed by three 74HC138 that decode op5 into one row per instruction) drives the function lines; the operand lines come
straight from S and D with a few gates (only for op5 < 16).

| line | meaning |
|---|---|
| SRC_IMM | operand Y = imm8 (S = 00) |
| SRC_MEM | operand Y = data memory at ADDR (S = 01 or 10) |
| SRC_REG | operand Y = the other register (S = 11) |
| IDX | ADDR = imm8 + B (S = 10), else ADDR = imm8 |
| ADDER | result = X + Y' + cin (the 74HC283 pair) |
| INV | Y' = not Y, cin = 1 (subtract) |
| AND, OR, XOR | result = X and/or/xor Y |
| ROL, ROR | result = X rotated left/right through C |
| PASS | result = Y |
| WR | write the result into R (clock to A if R_B = 0, to B if R_B = 1) |
| MEMW | write R to data memory at ADDR |
| UPZ, UPC | load Z, C from this result |
| BR | this is a jump: PC = IR[9:0] when the condition holds |
| BR_Z, BR_C | condition uses Z / C (neither: always) |
| BR_NOT | invert the condition |
| RETI | PC and Z,C from the shadow registers, IE = 1 |
| R_B | R is B (= IR bit 10, register group only) |
| INT | interrupt-entry cycle (from the interrupt logic, not the opcode); forces every write/jump line above to 0 |

X = R (A or B). ADDR = imm8 + (IDX ? B : 0), computed by a second 8-bit adder before the data memory.

### 5.1 Lines asserted by each instruction (function lines, from the diode matrix)

| instr | op5 | ADDER | INV | AND | OR | XOR | ROL | ROR | PASS | WR | MEMW | UPZ | UPC | BR | BR_Z | BR_C | BR_NOT | RETI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LD | 01 (00001) |  |  |  |  |  |  |  | x | x |  | x |  |  |  |  |  |  |
| ADD | 02 (00010) | x |  |  |  |  |  |  |  | x |  | x | x |  |  |  |  |  |
| SUB | 03 (00011) | x | x |  |  |  |  |  |  | x |  | x | x |  |  |  |  |  |
| AND | 04 (00100) |  |  | x |  |  |  |  |  | x |  | x |  |  |  |  |  |  |
| OR | 05 (00101) |  |  |  | x |  |  |  |  | x |  | x |  |  |  |  |  |  |
| XOR | 06 (00110) |  |  |  |  | x |  |  |  | x |  | x |  |  |  |  |  |  |
| ROL | 07 (00111) |  |  |  |  |  | x |  |  | x |  | x | x |  |  |  |  |  |
| ROR | 08 (01000) |  |  |  |  |  |  | x |  | x |  | x | x |  |  |  |  |  |
| ST | 09 (01001) |  |  |  |  |  |  |  |  |  | x |  |  |  |  |  |  |  |
| JMP | 16 (10000) |  |  |  |  |  |  |  |  |  |  |  |  | x |  |  |  |  |
| JZ | 17 (10001) |  |  |  |  |  |  |  |  |  |  |  |  | x | x |  |  |  |
| JNZ | 18 (10010) |  |  |  |  |  |  |  |  |  |  |  |  | x | x |  | x |  |
| JC | 19 (10011) |  |  |  |  |  |  |  |  |  |  |  |  | x |  | x |  |  |
| JNC | 20 (10100) |  |  |  |  |  |  |  |  |  |  |  |  | x |  | x | x |  |
| RETI | 21 (10101) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | x |

Diode count for the function lines: **42** (one diode per x), plus the opcode decoders.
Operand lines are added by S/D for op5 < 16:

| S | lines |
|---|---|
| 00 | SRC_IMM |
| 01 | SRC_MEM |
| 10 | SRC_MEM, IDX |
| 11 | SRC_REG |
| D = 1 | R_B (in addition) |

Examples (complete line sets):

| instruction | lines lit |
|---|---|
| `LD A, 5` | SRC_IMM, PASS, WR, UPZ |
| `LD B, A` | SRC_REG, R_B, PASS, WR, UPZ |
| `ADD A, [x]` | SRC_MEM, ADDER, WR, UPZ, UPC |
| `SUB B, 1` | SRC_IMM, R_B, ADDER, INV, WR, UPZ, UPC |
| `XOR A, [B+tab]` | SRC_MEM, IDX, XOR, WR, UPZ |
| `ROL A` | ROL, WR, UPZ, UPC (SRC_IMM also lit, unused) |
| `ST [B+buf], A` | SRC_MEM, IDX, MEMW |
| `JNC label` | BR, BR_C, BR_NOT |
| `RETI` | RETI |
| interrupt entry | INT only |

Taken branch: `BR and ((not BR_Z and not BR_C) or (BR_Z and (Z xor BR_NOT)) or (BR_C and (C xor BR_NOT)))`.

## 6. How each instruction executes in one clock

Datapath (all blocks are 74HC parts from HANDOVER-E; counts are for the front side):

```
PC (3 x 161) -> program SRAM -> IR[15:0] -> diode matrix -> control lines
IR[7:0] --+-------------------------------+
B --(IDX gate 2 x 08)--> address adder (2 x 283) --> data SRAM / display / I/O page  (ADDR)
X mux (2 x 157: A|B) --> X ----+
Y mux: imm8 | mem | other reg (4 x 157 + other-reg mux 2 x 157) --> XOR with INV (2 x 86) --> Y'
X, Y' --> 283 pair (sum, carry) ; logic unit (4 x 153 as per-bit 2-input LUT: AND OR XOR PASS) ; ROL/ROR wiring
result mux (rotate direction 2 x 157, then logic|rotate, then sum: 4 more x 157) --> A / B (574)      Z detect (4078) and C --> flag flip-flops (74)
PC next = PC + 1 (161 count) or load from IR[9:0] / shadow PC (3 x 157, INT forces 0 and sets bit 0) 
```

* **Clocking, two phases.** The rising edge of CLK advances PC (and so the instruction word). During the high half the
  decode, address adder, memory read, ALU and branch condition settle. On the **falling** edge A/B, Z/C, the shadow registers
  and the OUT port are clocked (enable gated with the inverted clock, so the enables settle before the pulse); the data-memory
  write strobe is the low half of CLK gated with MEMW, ending at the next rising edge. One clock period = one instruction.
* **Branch:** the condition uses the flags latched on the previous falling edge; the load into PC happens on the next rising edge.
* **Store** does not touch A/B/flags, so ADDR (imm + B) is stable through the low phase even though registers clock on the falling edge.
* **Interrupt entry:** INT (= IE and any pending) is a flip-flop output, stable in the high half; it gates WR, MEMW, UPZ, UPC,
  BR and RETI to 0 and sets the PC load mux to the vector. Shadow registers clock on the falling edge.
* **Timing budget (5 V 74HC):** program SRAM 15 ns + decode 40 + IDX gate/adder 60 + data SRAM 15 + Y mux 2 x 20 + XOR 15 +
  adder 60 + result mux 40 + Z detect 30 + setup ~ 320 ns of the high half. 1 MHz (500 ns half period) fits with margin at 5 V;
  at 3.3 V HC the same path is about 1.5x slower, marginal at 1 MHz. The games need only 1 kHz - 80 kHz (see REPORT.md).

## 7. Assembler summary

See the header of `asm.py`: labels, `.equ`, `.data`/`.text`/`.org`, `.byte/.word/.ascii/.asciz/.space`, `.macro/.endm`, comments with `;`.
`.data` fills the initial image of data RAM (addresses 0x00-0xBF); the loader writes it together with the program.
Operands: `LD A, 5`, `LD A, [x]`, `LD A, [B+tab]`, `LD B, A`, `ST [B+buf], A`, `ROR A`, `JNZ loop`.

## 8. Design history: why these 15

Start (HANDOVER-E): LDI, LD, ST, ADD, SUB, AND, OR, XOR, SHL, SHR, JMP, JZ, JC, IN, OUT, RETI (+ CALL/RET if needed).
Changes made while writing the five programs:

* LDI + LD merged into LD with the S field (immediate, direct, indexed, register). Same hardware, one opcode.
* IN/OUT removed: the ports sit in the data address space (0xC0-0xC2), so `LD A,[0xC0]` reads the buttons and `ST [0xC0],A` writes OUT.
  Interrupt enable and acknowledge are port writes as well, so there is no EI/DI.
* SHL/SHR replaced by ROL/ROR through carry: the 16-bit row rotations in Life and the scroller need the carry; a plain shift is
  `ADD A,0` (clear C) + rotate.
* Register B made a full second register (D field) instead of index-only: needed for loop counters that also index memory.
* JNZ and JNC added (free: BR_NOT reuses the flag mux).
* Added: indexed addressing `[B+imm]` (Life, Snake, Pong, scroller), `LD B,A` (register operand, S = 11).
* A CMP instruction was in the first draft of this ISA and was **removed** again once the programs were rewritten (a SUB whose result is
  dead does the same job at no cost).
* Not added, because no program needs it: CALL/RET (largest program 376 of 1024 words with macros), ADC/SBC, SHR/SHL with zero fill, EI/DI,
  push/pop, multiply, self-modifying code.

Details, numbers and the program-to-instruction table are in REPORT.md.
