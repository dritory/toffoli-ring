"""Encoding (ENCODING.md v3) and memory map. All tunable constants live here.
emu.js repeats the memory-map constants; tests/test_equiv.py checks they agree."""

# ---- opcodes ----
ADD, SUB, SHL, SHR, AND, OR, XOR, LOOKUP, LOAD, STORE, PUSH, POP, JUMP, DJNZ, CALL, RET = range(16)
OPNAMES = "ADD SUB SHL SHR AND OR XOR LOOKUP LOAD STORE PUSH POP JUMP DJNZ CALL RET".split()

# ---- register codes (reg field) ----
R_A, R_C, R_XL, R_XH, R_X, R_SP, R_RSP, R_F = range(8)
REGNAMES = ["A", "C", "XL", "XH", "X", "SP", "RSP", "F"]

# ---- source codes ----
S_CONST, S_ABS, S_X, S_XINC, S_A, S_C, S_XL, S_XH = range(8)

# ---- jump conditions [not, carry, zero] ----
C_NEVER, C_Z, C_C, C_ZC, C_ALWAYS, C_NZ, C_NC, C_HI = range(8)
# ---- lookup tables ----
T_MUL, T_MULH, T_DIV, T_MOD = range(4)

# ---- memory map (proposals; change here) ----
STACK_PAGE = 0x0100          # data stack: 0x0100..0x01FF, SP is the low byte
DATA_BASE = 0x0200           # assembler places .data variables from here
DEV_BASE = 0xFF00            # 0xFF00..0xFFFF are devices
BTN = 0xFF00                 # read: button state, bit0 up 1 down 2 left 3 right (1 = pressed)
IRQ_EN = 0xFF01              # r/w: bits 0-3 interrupt enable per button
IRQ_CAUSE = 0xFF02           # read: buttons that caused the last interrupt (latched at entry)
FRAME = 0xFF03               # read: 1 if a 60 Hz tick happened since last read (read clears)
RNG = 0xFF04                 # read: next pseudo-random byte (16-bit LFSR, 8 steps per read)
LCD_CMD = 0xFF10             # write: LCD command
LCD_DATA = 0xFF11            # write: LCD data byte
LED = 0xFF20                 # r/w: 8 LED output port
TBL0 = 0xFF30                # write-only table fill ports TBL0..TBL3 (MUL, MULH, DIV, MOD)
BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT = 1, 2, 4, 8

PC_RESET = 0x0000
IRQ_VECTOR = 0x0001          # interrupt entry jumps here (put a JUMP there)
SP_RESET = 0x00              # first PUSH writes 0x01FF
RSP_RESET = 0x00             # first CALL writes return-stack slot 255
RSTACK_DEPTH = 256           # return stack entries (RSP is 8 bits)
TICK_CYCLES = 16667          # CPU clocks per 60 Hz tick (1 MHz clock); override per run
LCD_W, LCD_H = 320, 240

# ---- field helpers ----
def encode(op, R=0, S=0, K=0, G=0, Y=0, O=0, addr=0):
    assert 0 <= op < 16 and R < 2 and S < 8 and K < 2 and G < 8 and Y < 2 and O < 8
    return (op << 28) | (R << 27) | (S << 24) | (K << 23) | (G << 20) | (Y << 19) | (O << 16) | (addr & 0xFFFF)

def decode(w):
    return dict(op=w >> 28, R=(w >> 27) & 1, S=(w >> 24) & 7, K=(w >> 23) & 1,
                G=(w >> 20) & 7, Y=(w >> 19) & 1, O=(w >> 16) & 7, addr=w & 0xFFFF)

def groups(w):
    """Hex digit groups: opcode | restore+select | keep+reg | carry+source | address."""
    return "%X|%X|%X|%X|%04X" % (w >> 28, (w >> 24) & 15, (w >> 20) & 15, (w >> 16) & 15, w & 0xFFFF)

def cond_true(S, Z, C):
    hit = ((S & 1) and Z) or ((S & 2) and C)
    return bool(hit) != bool(S & 4)
