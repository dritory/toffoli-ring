# Instruction encoding (Endre's design, v1)

32-bit instruction word:

| Field | Bits | Meaning |
|---|---|---|
| opcode | 4 | which of the 16 instructions |
| select | 3 | JUMP: condition (always, zero, not zero, carry, no carry). RET: restore flags. LOOKUP: table (MUL, MULH, DIV, MOD). Unused otherwise. |
| reg | 3 | LOAD and POP: destination register. STORE and PUSH: source register. |
| source | 3 | where the operand comes from: constant #n, [addr], [X], [X+], register A, counter, X-low, X-high |
| keep | 1 | arithmetic and logic: write the result to A (off = flags only, CMP and TEST) |
| carry | 1 | ADD, SUB, SHL, SHR: bring in the old carry (ADC, SBC, ROL, ROR) |
| spare | 1 | position not yet chosen |
| address | 16 | address, constant, or jump target |

Total 31 bits plus 1 spare.

Still to decide: bit positions (hex alignment), numbering of opcodes, register codes, source codes and condition codes; which fields each opcode uses.
