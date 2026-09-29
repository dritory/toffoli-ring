"""ISA4: drop PREV, cyclic data tape, NEXT only.  PREV = NEXT^(N-1).
Counter (interleaved home-marker track) and BB(2,2) by mechanical PREV substitution."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'blockskip'))
import ref as R, programs as P

def run(prog, data, dp, ticks=None, passes=None):
    ring = [R.encode(m) for m in prog]; S = 0; pp = 0; n = len(data); t = 0
    total = ticks if ticks is not None else passes * len(prog)
    for _ in range(total):
        a = R.tick(S, ring[pp], data[dp])
        if a[0]: data[dp] ^= 1
        dp = (dp + a[1] - a[2]) % n; S = a[3]; pp = (pp + 1) % len(prog)
    return data, dp, S

def counter_nextonly(width=8):
    """cells: pairs (n_i, m_i) i=0..width-1 plus home pair (x, 0); n = NOT bit."""
    p = []
    for i in range(width - 1): p += ['FLIP', 'IFZ', 'NEXT', 'NEXT']
    p += ['FLIP', 'MARK', 'NEXT']              # pointer now on a marker cell (m_p)
    p += ['IFZ', 'NEXT', 'NEXT', 'MARK'] * width
    p += ['NEXT']
    return p
def counter_tape(width=8):
    d = []
    for i in range(width): d += [1, 1]
    return d + [1, 0]

def subst_prev(prog, N):
    out = []
    for m in prog: out += ['NEXT'] * (N - 1) if m == 'PREV' else [m]
    return out

if __name__ == '__main__':
    prog = counter_nextonly(); d = counter_tape(); dp = 0
    for k in range(1, 700):
        d, dp, S = run(prog, d, dp, passes=1)
        val = sum((1 - d[2 * i]) << i for i in range(8))
        assert val == k % 256 and dp == 0 and S == 0, (k, val, dp, S)
    print('counter NEXT-only ok, length', len(prog), 'ticks/incr', len(prog), 'cells', len(d))
    base = P.bb22_prog(); print('BB base', len(base), 'PREV count', base.count('PREV'))
    for ng in (6, 12, 24):
        N = ng * P.G
        prog2 = subst_prev(base, N)
        # verify against baseline for a few TM steps
        d1, dp1 = P.bb22_tape(ng); d2 = list(d1); dp2 = dp1
        for step in range(6):
            d1, dp1, _ = run(base, d1, dp1, passes=1)
            d2, dp2, _ = run(prog2, d2, dp2, passes=1)
            assert d1 == d2 and dp1 == dp2
        print('BB NEXT-only groups', ng, 'cells', N, 'length', len(prog2), 'ticks/step', len(prog2))
