# Instruction encoding (Endre's design, v3)

32-bit instruction word, every field on a hex digit:

| Hex digit | Bits | Field | Meaning |
|---|---|---|---|
| 1 | 31–28 | opcode (4) | which of the 16 instructions |
| 2 | 27 | restore (1) | RET: also restore the flags (RETI) |
| 2 | 26–24 | select (3) | JUMP: condition (always, zero, not zero, carry, no carry). LOOKUP: table (MUL, MULH, DIV, MOD). |
| 3 | 23 | keep (1) | arithmetic and logic: write the result to A (off = flags only, CMP and TEST) |
| 3 | 22–20 | reg (3) | LOAD and POP: destination register. STORE and PUSH: source register. |
| 4 | 19 | carry (1) | ADD, SUB, SHL, SHR: bring in the old carry (ADC, SBC, ROL, ROR) |
| 4 | 18–16 | source (3) | operand: constant #n, [addr], [X], [X+], register A, counter, X-low, X-high |
| 5–8 | 15–0 | address (16) | address, constant, or jump target |

Total 32 bits, no spare.

## Opcodes

The top bit splits arithmetic from data and control. (Assumed: 0 = arithmetic, 1 = data and control; to confirm.)

| Code | Opcode | Code | Opcode |
|---|---|---|---|
| 0 | ADD | 8 | LOAD |
| 1 | SUB | 9 | STORE |
| 2 | SHL | A | PUSH |
| 3 | SHR | B | POP |
| 4 | AND | C | JUMP |
| 5 | OR | D | DJNZ |
| 6 | XOR | E | CALL |
| 7 | LOOKUP | F | RET |

Patterns that fall out: in the arithmetic half, bit 2 splits the carry users (0–3: add, subtract, shifts) from the logic and table ops (4–7). In the other half, bit 2 splits memory instructions (8–B) from control instructions (C–F).

## Registers (reg field)

| Code | Register |
|---|---|
| 0 | A |
| 1 | counter |
| 2 | X-low |
| 3 | X-high |
| 4 | whole 16-bit X (for `LOAD X, #addr`) |
| 5 | SP (data stack pointer) |
| 6 | RSP (return stack pointer) |
| 7 | spare (candidate: the flags) |

Every register can be loaded and stored with LOAD and STORE. Only the four 8-bit working registers (A, counter, X-low, X-high) can also be the operand of a calculation.

## Sources (source field)

The top bit (value 4) chooses memory or register; for registers the low two bits are the register code, so the same wires serve both fields.

| Code | Source |
|---|---|
| 0 | constant #n |
| 1 | [addr] |
| 2 | [X] |
| 3 | [X+] |
| 4 | register A |
| 5 | register counter |
| 6 | register X-low |
| 7 | register X-high |

## Jump conditions (select field on JUMP)

Three bits: [not, carry, zero]. Rule: jump = not XOR ((zero AND Z) OR (carry AND C)).

| Code | Meaning |
|---|---|
| 000 | never (no jump) |
| 001 | if zero |
| 010 | if carry |
| 011 | if zero or carry |
| 100 | always |
| 101 | if not zero |
| 110 | if not carry |
| 111 | if neither zero nor carry |

## LOOKUP tables (select field on LOOKUP)

| Code | Table | Bit meaning |
|---|---|---|
| 0 | MUL (low byte of A × operand) | bit 1 = 0: multiply |
| 1 | MULH (high byte) | bit 0 = 1: second result byte |
| 2 | DIV (quotient of A ÷ operand) | bit 1 = 1: divide |
| 3 | MOD (remainder) | |
| 4–7 | free for later tables | |

The select bits go straight to the top address lines of the table memory, so the table choice needs no decoding.

## Usage table

Fields: R = restore, S = select, K = keep, G = reg, Y = carry, O = source, @ = address. "op" means the operand chosen by the source field (with the address field when the source is a constant or [addr]).

| Code | Opcode | Fields used | Does | Flags |
|---|---|---|---|---|
| 0 | ADD | K Y O @ | A = A + op (+ C if Y) | Z, C |
| 1 | SUB | K Y O @ | A = A − op (− borrow if Y) | Z, C (C = borrow: 1 when the result went below 0) |
| 2 | SHL | K Y | A shifted left by one; bit 7 to C; bit 0 = C if Y else 0 | Z, C |
| 3 | SHR | K Y | A shifted right by one; bit 0 to C; bit 7 = C if Y else 0 | Z, C |
| 4 | AND | K O @ | A = A and op | Z |
| 5 | OR | K O @ | A = A or op | Z |
| 6 | XOR | K O @ | A = A xor op | Z |
| 7 | LOOKUP | S K O @ | A = table[S](A, op) | Z |
| 8 | LOAD | G O @ | register G = op; G = 4 loads all of X from the 16-bit constant | none |
| 9 | STORE | G O @ | memory at [addr], [X] or [X+] = register G | none |
| A | PUSH | G | data stack: SP − 1, then memory[SP] = G | none |
| B | POP | G | G = memory[SP], then SP + 1 | none |
| C | JUMP | S @ | if condition S: PC = address | none |
| D | DJNZ | @ | counter − 1; if counter ≠ 0: PC = address | none |
| E | CALL | S @ | if condition S: push PC + 1 on the return stack, PC = address | none |
| F | RET | R S | if condition S: PC = pop return stack; if R, also restore flags | restored if R |

Interrupt entry (hardware, no opcode): push PC and flags on the return stack, jump to the vector.

Decisions: C after SUB means borrow, so CMP then "jump if carry" means "less than". CALL and RET take the same condition field as JUMP (100 = always). Shifts act on A only (default, since the user had no preference: shifting a memory value is LOAD then SHL).

