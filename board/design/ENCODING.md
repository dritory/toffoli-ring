# Instruction encoding (Endre's design, v2)

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

Still to decide: numbering of opcodes, register codes, source codes and condition codes; which fields each opcode uses.
