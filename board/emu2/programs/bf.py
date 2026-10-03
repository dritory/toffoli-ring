"""Brainfuck -> assembly compiler for the visible computer.
Tape pointer lives in X (16 bit).  + - are LOAD/ADD/STORE on [X]; > is one dummy read [X+] (X steps by one);
< needs a 16-bit subtract.  '.' writes the cell to the LED port, ',' reads the button port.
Options: opt (run-length merging, [-] clear loop, flag reuse before ']'), tape8 (256-cell page-aligned tape)."""
import sys, os, re

TAPE = 0x1000
TAPE_LEN = 30000

def tokens(src):
    ops = [c for c in src if c in "+-<>.,[]"]
    return ops

def compile_bf(src, opt=True, tape8=False, tape=TAPE):
    ops = tokens(src); out = []; E = out.append
    i = 0; loops = []; nloop = 0
    E(".data"); E(".org 0x%04X" % tape); E("tape:   .space %d" % (256 if tape8 else TAPE_LEN)); E(".code")
    E("        JUMP start"); E("        RETI"); E("start:  LOAD X, #tape")
    last_arith = False                 # flags describe the cell value after the previous emitted instruction
    while i < len(ops):
        c = ops[i]; arith = False
        if c in "+-":
            n = 0
            while i < len(ops) and ops[i] in "+-" and opt:
                n += 1 if ops[i] == "+" else -1; i += 1
            if not opt: n = 1 if c == "+" else -1; i += 1
            n &= 255
            if n:
                E("        LOAD A, [X]")
                E("        %s #%d" % (("ADD", n) if n < 128 or not opt else ("SUB", 256 - n)))
                E("        STORE [X], A"); arith = True
            else:
                arith = False
        elif c in "<>":
            d = 0
            while i < len(ops) and ops[i] in "<>" and opt:
                d += 1 if ops[i] == ">" else -1; i += 1
            if not opt: d = 1 if c == ">" else -1; i += 1
            while d:
                step = max(-255, min(255, d)); d -= step
                if tape8:
                    E("        MOVE A, XL"); E("        %s #%d" % (("ADD", step) if step > 0 else ("SUB", -step))); E("        MOVE XL, A")
                elif 0 < step <= 7:
                    for _ in range(step): E("        LOAD A, [X+]")
                else:
                    nloop += 1
                    E("        MOVE A, XL"); E("        %s #%d" % (("ADD", step) if step > 0 else ("SUB", -step)))
                    E("        MOVE XL, A")
                    E("        JUMP NC, k%d" % nloop)          # carry / borrow into the high byte
                    E("        MOVE A, XH"); E("        %s #1" % ("ADD" if step > 0 else "SUB")); E("        MOVE XH, A")
                    E("k%d:" % nloop)
        elif c == ".":
            E("        LOAD A, [X]"); E("        STORE [LED], A"); i += 1
        elif c == ",":
            E("        LOAD A, [BTN]"); E("        STORE [X], A"); i += 1
        elif c == "[":
            if opt and ops[i:i + 3] in (["[", "-", "]"], ["[", "+", "]"]):
                E("        LOAD A, #0"); E("        STORE [X], A"); i += 3; last_arith = False; continue
            nloop += 1; loops.append(nloop)
            E("        LOAD A, [X]"); E("        TEST #255"); E("        JUMP Z, e%d" % nloop); E("b%d:" % nloop); i += 1
        else:  # ]
            n = loops.pop()
            if opt and last_arith:
                E("        JUMP NZ, b%d" % n)       # flags still describe the cell (set by the last ADD/SUB)
            else:
                E("        LOAD A, [X]"); E("        TEST #255"); E("        JUMP NZ, b%d" % n)
            E("e%d:" % n); i += 1
        last_arith = arith
    E("        JUMP $")
    if loops: raise ValueError("unbalanced [")
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    src = open(sys.argv[1]).read()
    sys.stdout.write(compile_bf(src, opt="--noopt" not in sys.argv, tape8="--tape8" in sys.argv))
