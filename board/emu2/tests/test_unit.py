"""Semantics checks straight from ENCODING.md (assembler + emulator)."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
import asm, emu, isa
from asm import AsmError

def run(src, n=2000, **kw):
    P = asm.assemble_text(src + "\n        JUMP $\n")
    c = emu.CPU(P.words, P.data_image(), debug=True, **kw); c.run(n); return c, P

def enc(line):
    return asm.assemble_text(line).words[0]

def t_encoding():
    assert isa.groups(enc("LOAD A, #5")) == "8|0|0|0|0005"
    assert isa.groups(enc("LOAD X, #0x1234")) == "8|0|4|0|1234"
    assert isa.groups(enc("LOAD C, A")) == "8|0|1|4|0000"             # MOVE C,A
    assert enc("MOVE C, A") == enc("LOAD C, A")
    assert isa.groups(enc("ADC [0x10]")) == "0|0|8|9|0010"
    assert isa.groups(enc("SBC [X+]")) == "1|0|8|B|0000"
    assert isa.groups(enc("CMP #3")) == "1|0|0|0|0003"                  # keep off
    assert isa.groups(enc("TEST #3")) == "4|0|0|0|0003"
    assert isa.groups(enc("MUL #3")) == "7|0|8|0|0003"
    assert isa.groups(enc("MULH C")) == "7|1|8|5|0000"
    assert isa.groups(enc("DIV [X]")) == "7|2|8|2|0000"
    assert isa.groups(enc("MOD #7")) == "7|3|8|0|0007"
    assert isa.groups(enc("ROL")) == "2|0|8|8|0000" and isa.groups(enc("ROR")) == "3|0|8|8|0000"
    assert isa.groups(enc("NOT")) == "6|0|8|0|00FF"
    assert isa.groups(enc("RETI")) == "F|C|0|0|0000" and isa.groups(enc("RET")) == "F|4|0|0|0000"
    assert isa.groups(enc("NOP")) == "C|4|0|0|0001"
    assert isa.groups(enc("JUMP NZ, 7")) == "C|5|0|0|0007" and isa.groups(enc("CALL C, 9")) == "E|2|0|0|0009"
    assert isa.groups(enc("STORE [X+], XH")) == "9|0|3|3|0000"
    assert isa.groups(enc("PUSH RSP")) == "A|0|6|0|0000" and isa.groups(enc("DJNZ 3")) == "D|0|0|0|0003"
    print("encoding: ok")

def t_rejects():
    for bad in ("STORE #5, A", "STORE A, [X]", "LOAD X, [5]", "PUSH X", "POP SP", "ADD SP", "ADD #300",
                "LOAD XL, [X+]", "STORE [3], X", "FOO", "JUMP QQ, 1", "ADD 5"):
        try: asm.assemble_text(bad + "\nJUMP $"); raise SystemExit("not rejected: " + bad)
        except AsmError: pass
    try: asm.assemble_text(".data\na: .space 4\n.org 0x0100\nb: .space 2\n"); raise SystemExit("stack overlap")
    except AsmError: pass
    try: asm.assemble_text(".data\na: .space 8\n.org 0x0204\nb: .space 8\n"); raise SystemExit("overlap")
    except AsmError: pass
    print("rejects: ok")

def t_alu():
    c, _ = run("LOAD A,#200\nADD #100\n")                   # 300 -> 44, C=1
    assert (c.a, c.cf, c.z) == (44, 1, 0)
    c, _ = run("LOAD A,#5\nSUB #6\n"); assert (c.a, c.cf) == (255, 1)       # borrow
    c, _ = run("LOAD A,#5\nCMP #5\n"); assert (c.a, c.z, c.cf) == (5, 1, 0)
    c, _ = run("LOAD A,#255\nADD #1\nLOAD A,#0\nADC #0\n"); assert c.a == 1  # carry in
    c, _ = run("LOAD A,#0\nSUB #1\nLOAD A,#5\nSBC #1\n"); assert c.a == 3   # borrow in
    c, _ = run("LOAD A,#0x81\nSHL\n"); assert (c.a, c.cf) == (2, 1)
    c, _ = run("LOAD A,#0x81\nSHL\nROL\n"); assert (c.a, c.cf) == (5, 0)
    c, _ = run("LOAD A,#0x01\nSHR\nROR\n"); assert (c.a, c.cf) == (0x80, 0)
    c, _ = run("LOAD A,#0x0F\nNOT\n"); assert c.a == 0xF0
    c, _ = run("LOAD A,#1\nADD #1\nAND #0\n"); assert (c.z, c.cf) == (1, 0)  # logic leaves C alone
    print("alu: ok")

def t_mem():
    c, _ = run(".data\nv: .byte 7,8,9\n.code\nLOAD X,#v\nLOAD A,[X+]\nADD [X+]\nSTORE [X],A\nLOAD XL,#0\n", fast_tables=True)
    assert c.mem[0x202] == 15 and c.x == 0x200
    c, _ = run("LOAD A,#42\nPUSH A\nLOAD A,#1\nPOP C\n"); assert c.c == 42 and c.sp == 0
    c, _ = run("LOAD A,#9\nPUSH A\n"); assert c.mem[0x1FF] == 9 and c.sp == 0xFF
    c, _ = run("LOAD A,#3\nMOVE C,A\nloop: DJNZ loop\n"); assert c.c == 0
    c, _ = run("LOAD C,#0\nLOAD A,#0\nl: ADD #1\nDJNZ l\n"); assert c.a == 0 and c.c == 0   # 256 iterations
    c, _ = run("LOAD A,#200\nMUL #3\n", fast_tables=True); assert c.a == (600 & 255)
    c, _ = run("LOAD A,#200\nMULH #3\n", fast_tables=True); assert c.a == 600 >> 8
    c, _ = run("LOAD A,#200\nDIV #7\n", fast_tables=True); assert c.a == 28
    c, _ = run("LOAD A,#200\nMOD #7\n", fast_tables=True); assert c.a == 4
    c, _ = run("LOAD A,#200\nDIV #0\n", fast_tables=True); assert c.a == 255
    c, _ = run("LOAD SP,#0x40\nLOAD A,#1\nPUSH A\n"); assert c.sp == 0x3F and c.mem[0x13F] == 1
    print("memory: ok")

def t_flow():
    c, _ = run("LOAD A,#1\nCALL f\nLOAD C,#5\nJUMP $\nf: ADD #1\nRET\n"); assert c.a == 2 and c.c == 5 and c.rsp == 0
    c, _ = run("LOAD A,#0\nCMP #0\nCALL NZ,f\nLOAD C,#5\nJUMP $\nf: LOAD A,#9\nRET\n"); assert c.a == 0 and c.c == 5
    # interrupt: entry pushes PC+flags; RETI restores flags
    P = asm.assemble_text("JUMP main\nirq: LOAD A,#1\nADD #0\nRETI\nmain: LOAD A,#15\nSTORE [IRQ_EN],A\nLOAD A,#255\nADD #1\nl: NOP\nNOP\nJUMP l\n")
    c = emu.CPU(P.words, P.data_image())
    c.run(6, stop_on_halt=False)
    c.set_buttons(1)
    c.run(40, stop_on_halt=False)
    assert c.cf == 1 and c.z == 1, "flags restored by RETI"
    assert c.a == 1 and c.cause == 1 and c.rsp == 0
    print("flow: ok")

def t_lcd():
    src = "LOAD A,#0x2A\nSTORE [LCD_CMD],A\nLOAD A,#0\nSTORE [LCD_DATA],A\nLOAD A,#10\nSTORE [LCD_DATA],A\nLOAD A,#0\nSTORE [LCD_DATA],A\nLOAD A,#11\nSTORE [LCD_DATA],A\n" \
          "LOAD A,#0x2B\nSTORE [LCD_CMD],A\nLOAD A,#0\nSTORE [LCD_DATA],A\nLOAD A,#20\nSTORE [LCD_DATA],A\nLOAD A,#0\nSTORE [LCD_DATA],A\nLOAD A,#20\nSTORE [LCD_DATA],A\n" \
          "LOAD A,#0x2C\nSTORE [LCD_CMD],A\nLOAD A,#0xF8\nSTORE [LCD_DATA],A\nLOAD A,#0\nSTORE [LCD_DATA],A\nLOAD A,#0x07\nSTORE [LCD_DATA],A\nLOAD A,#0xE0\nSTORE [LCD_DATA],A\n" \
          "LOAD A,#0x1F\nSTORE [LCD_DATA],A\nSTORE [LCD_DATA],A\n"
    c, _ = run(src)
    fb = c.lcd.fb
    # window is 2 x 1: pixels 1,2 fill (10,20),(11,20); the third wraps to the window start
    assert fb[20 * 320 + 11] == 0x07E0 and fb[20 * 320 + 10] == 0x1F1F and fb[21 * 320 + 10] == 0 and c.lcd.pixels == 3
    print("lcd: ok")

if __name__ == "__main__":
    for t in (t_encoding, t_rejects, t_alu, t_mem, t_flow, t_lcd): t()
