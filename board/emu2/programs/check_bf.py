import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import *
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bf

def interp(src, inputs=(), maxsteps=5_000_000):
    ops = bf.tokens(src); jump = {}; st = []
    for i, c in enumerate(ops):
        if c == "[": st.append(i)
        elif c == "]": j = st.pop(); jump[i] = j; jump[j] = i
    tape = {}; p = 0; pc = 0; out = []; inp = list(inputs); steps = 0
    while pc < len(ops) and steps < maxsteps:
        c = ops[pc]; steps += 1
        if c == "+": tape[p] = (tape.get(p, 0) + 1) & 255
        elif c == "-": tape[p] = (tape.get(p, 0) - 1) & 255
        elif c == ">": p += 1
        elif c == "<": p -= 1
        elif c == ".": out.append(tape.get(p, 0))
        elif c == ",": tape[p] = inp.pop(0) if inp else 0
        elif c == "[" and not tape.get(p, 0): pc = jump[pc]
        elif c == "]" and tape.get(p, 0): pc = jump[pc]
        pc += 1
    return out, {k: v for k, v in tape.items() if v}

def run_bf(src, opt=True, tape8=False, btn=0, maxc=3_000_000):
    text = bf.compile_bf(src, opt=opt, tape8=tape8)
    P = asm.assemble_text(text, "bf")
    cpu = emu.CPU(P.words, P.data_image(), debug=False)
    cpu.wlog = []; cpu.btn = btn
    cpu.run(maxc)
    assert cpu.halted, "program did not finish"
    out = [v for a, v in cpu.wlog if a == isa.LED]
    tape = {a - bf.TAPE: cpu.mem[a] for a in range(bf.TAPE, bf.TAPE + 700) if cpu.mem[a]}
    return P, cpu, out, tape

TESTS = {
    "hello": open(os.path.join(PROG, "hello.bf")).read(),
    "mul": "++++[>+++++<-]>.",
    "wrap": "-.+.",
    "clear": "+++++[-]>++[-]<.>.",
    "nested": "++[>+++[>++<-]<-]>>.",
    "far": "+" + ">" * 300 + "++<" + "<" * 299 + "+++.>" + ">" * 299 + ".",
    "input": ",.>,<.",
}

def main():
    rows = []
    for name, src in TESTS.items():
        for opt in (True, False):
            for t8 in (False, True):
                if t8 and name == "far": continue
                P, cpu, out, tape = run_bf(src, opt=opt, tape8=t8, btn=5)
                ref, rtape = interp(src, inputs=[5, 5])
                assert out == ref, (name, opt, t8, out, ref)
                if not t8 or True: assert tape == rtape, (name, opt, t8, tape, rtape)
                rows.append((name, opt, t8, len(P.words), cpu.cycle))
    h = [r for r in rows if r[0] == "hello"]
    print("bf: %d programs x modes match the Python reference interpreter (output and tape)" % len(rows))
    for r in h: print("bf hello: opt=%s tape8=%s words=%d cycles=%d" % r[1:])
    P, cpu, out, tape = run_bf(TESTS["hello"])
    print("bf hello output:", repr(bytes(out).decode()))
    assert bytes(out) == b"Hello World!\n"
    return rows

if __name__ == "__main__":
    main()
