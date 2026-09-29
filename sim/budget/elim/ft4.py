"""FT4 = {FT (flip; skip-to-MARK if cell now 0), NEXT, PREV, MARK}: cyclic-tape
runner, hand-written 8-bit counter."""
import sys
from macro import B, run
FT4 = [B(('F','T0')), B(('P',)), B(('M',)), B((), True)]
FT, N, P, MK = 0, 1, 2, 3

def run_ring(ring, tape, ptr, ticks, S=0, pp=0, menu=FT4):
    n = len(tape); t = 0
    W = n
    for _ in range(ticks):
        b = menu[ring[pp]]
        # cyclic tape: emulate with window trick
        if S:
            S = 0 if b.mark else 1
        else:
            S2 = 0
            for op in b.ops:
                if op == 'F': tape[ptr] ^= 1
                elif op[0] == 'T':
                    if tape[ptr] == int(op[1]): S2 = 1
                elif op == 'P': ptr = (ptr + 1) % n
                else: ptr = (ptr - 1) % n
            S = S2
        pp = (pp + 1) % len(ring)
    return tape, ptr, S, pp

def counter_prog(width=8):
    p = [N] + [FT, N] * (width - 1) + [FT, MK, P]
    p += [FT, MK, FT, P, MK] * (width - 1)
    return p

if __name__ == '__main__':
    prog = counter_prog(); tape = [0] + [1] * 8; ptr = 0; S = 0; pp = 0
    for k in range(1, 700):
        tape, ptr, S, pp = run_ring(prog, tape, ptr, len(prog), S, pp)
        val = sum((1 - tape[1 + i]) << i for i in range(8))
        assert val == k % 256 and ptr == 0 and S == 0 and tape[0] == 0, (k, val, ptr, S, tape)
    print('FT4 counter ok: length', len(prog), 'ticks/incr', len(prog))
