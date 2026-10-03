"""Python vs JS cycle-by-cycle state hash on the benchmark programs (real start-up, no fast path)."""
import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "programs"))
import asm, isa, bf
from test_equiv import equiv_program, compare

def asm_prog(name):
    P = asm.assemble_file(os.path.join(ROOT, "programs", name + ".asm"))
    return P.words, P.data_image()

CASES = [
    ("counter", 40000, [], 100),
    ("snake", 200000, [[30000, 1], [30010, 0], [90000, 4], [90010, 0], [120000, 2], [120010, 0], [150000, 8], [150010, 0]], 1500),
    ("pong", 1_300_000, [[1_200_000, 2], [1_250_000, 0]], 1),
    ("life", 1_250_000, [], 1),
    ("scroll", 1_250_000, [], 1),
    ("raycast", 1_700_000, [[1_450_000, 1], [1_500_000, 9], [1_550_000, 0]], 1),
]

def main():
    ok = True
    for name, cycles, ev, tick in CASES:
        w, d = asm_prog(name)
        t = time.time()
        r = equiv_program(w, d, cycles, ev, tick=tick, fast=False, label=name)
        print("%-8s %8d cycles  %s  (%.1fs)" % (name, cycles, "IDENTICAL" if r else "MISMATCH", time.time() - t)); ok &= r
    src = open(os.path.join(ROOT, "programs", "hello.bf")).read()
    P = asm.assemble_text(bf.compile_bf(src), "bf")
    r = equiv_program(P.words, P.data_image(), 3000, [], tick=1, fast=False, label="bf")
    print("%-8s %8d cycles  %s" % ("bf hello", 3000, "IDENTICAL" if r else "MISMATCH")); ok &= r
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
