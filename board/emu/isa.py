"""ISA definition shared by emu.py and asm.py. See ISA.md.

Instruction word (16 bits):
  register group (op[4]=0):  op5 | D | S1 S0 | imm8
        [15:11] op5, [10] D (register R: 0=A 1=B), [9:8] S (operand source), [7:0] imm8
  control group  (op[4]=1):  op5 | 0 | target10   ([9:0] jump target)
"""

# Control lines (bit positions). Each has an LED on the board.
LINE_NAMES = [
    'SRC_IMM', 'SRC_MEM', 'SRC_REG', 'IDX',            # operand routing
    'ADDER', 'INV', 'AND', 'OR', 'XOR', 'ROL', 'ROR', 'PASS',   # ALU result select
    'WR', 'MEMW', 'UPZ', 'UPC',                        # write enables
    'BR', 'BR_Z', 'BR_C', 'BR_NOT', 'RETI',            # program counter
    'R_B',                                             # register select (from IR bit 10)
    'INT',                                             # interrupt entry cycle (not from the opcode)
]
L = {n: 1 << i for i, n in enumerate(LINE_NAMES)}

# name: (opcode5, function lines)
OPS = {
    'NOP': (0, []),
    'LD':  (1, ['PASS', 'WR', 'UPZ']),
    'ADD': (2, ['ADDER', 'WR', 'UPZ', 'UPC']),
    'SUB': (3, ['ADDER', 'INV', 'WR', 'UPZ', 'UPC']),
    'AND': (4, ['AND', 'WR', 'UPZ']),
    'OR':  (5, ['OR', 'WR', 'UPZ']),
    'XOR': (6, ['XOR', 'WR', 'UPZ']),
    'ROL': (7, ['ROL', 'WR', 'UPZ', 'UPC']),
    'ROR': (8, ['ROR', 'WR', 'UPZ', 'UPC']),
    'ST':  (9, ['MEMW']),
    'JMP': (16, ['BR']),
    'JZ':  (17, ['BR', 'BR_Z']),
    'JNZ': (18, ['BR', 'BR_Z', 'BR_NOT']),
    'JC':  (19, ['BR', 'BR_C']),
    'JNC': (20, ['BR', 'BR_C', 'BR_NOT']),
    'RETI': (21, ['RETI']),
}
OPCODE = {n: v[0] for n, v in OPS.items()}
OPNAME = {v[0]: n for n, v in OPS.items()}
FUNC = [0] * 32
for _n, (_o, _ls) in OPS.items():
    FUNC[_o] = sum(L[x] for x in _ls)

# S field (IR[9:8]) -> operand lines, only for the register group. S=00 imm, 01 mem[imm],
# 10 mem[imm+B], 11 other register.
SLINES = []
for _d in (0, 1):
    for _s in range(4):
        m = [L['SRC_IMM'], L['SRC_MEM'], L['SRC_MEM'] | L['IDX'], L['SRC_REG']][_s]
        if _d:
            m |= L['R_B']
        SLINES.append(m)   # index = D*4 + S


def decode(ir):
    """Control-line mask asserted by instruction word ir (no interrupt)."""
    op = ir >> 11
    m = FUNC[op]
    if op < 16:
        m |= SLINES[(ir >> 8) & 7]
    # ST with S=00 is treated as direct: SRC_IMM is harmless (no ALU line active)
    return m


# Memory map (data space)
RAM_END = 0xC0      # 0x00-0xBF plain RAM
IO_BASE = 0xC0      # 0xC0-0xDF I/O page, register = addr & 3
IO_BTN, IO_PEND, IO_IE = 0xC0, 0xC1, 0xC2   # read: buttons/pending/ie; write: OUT/ack/ie
DISP_BASE = 0xE0    # 0xE0-0xFF display, byte = DISP_BASE + 2*row + half, bit7 = leftmost
VECTOR = 1          # interrupt vector (program address); reset PC = 0
PROG_WORDS = 1024
