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
| 0 | X-high |
| 1 | X-low |
| 2 | counter |
| 3 | A |
| 4–7 | to decide (e.g. whole 16-bit X for `LOAD X, #addr`) |

## Sources (source field)

High bit 1 selects a register, with the same low bits as the register codes, so the same wires serve both fields.

| Code | Source |
|---|---|
| 0–3 | constant #n, [addr], [X], [X+] (order to confirm) |
| 4 | register X-high |
| 5 | register X-low |
| 6 | register counter |
| 7 | register A |

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

Still to decide: final register codes (see question in conversation), LOOKUP table codes, which fields each opcode uses.
