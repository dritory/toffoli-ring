"""Truth table + 500 random programs/tapes, tick-by-tick, switch-level
NMOS machine vs ref.py."""
import random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R
from machine_nmos import Machine

def truth_table(m, refn=R.tick):
    bad, n = [], 0
    for S in (0, 1):
        for name in R.OPS:
            for r in (0, 1):
                op = R.encode(name)
                got = m.tick(S, op, r); exp = refn(S, op, r)
                n += 1
                if tuple(got) != tuple(exp): bad.append((S, name, r, got, exp))
    return n, bad

def run_pair(m, prog, d0, pp0, dp0, ticks, refn=R.tick):
    dr, dc = list(d0), list(d0)
    Sr = Sc = 0; ppr = pp0; dpr = dp0; dpc = dp0
    n, nd = len(prog), len(d0)
    for t in range(ticks):
        op = prog[ppr]
        a = refn(Sr, op, dr[dpr]); b = m.tick(Sc, op, dc[dpc])
        if tuple(a) != tuple(b): return False, ('signals', t, a, b)
        if a[0]: dr[dpr] ^= 1
        if b[0]: dc[dpc] ^= 1
        dpr = (dpr + a[1] - a[2]) % nd; dpc = (dpc + b[1] - b[2]) % nd
        Sr, Sc = a[3], b[3]; ppr = (ppr + 1) % n
        if dr != dc or dpr != dpc: return False, ('state', t)
    return True, None

def random_tapes(m, trials=500, seed=20260929, ticks=80, refn=R.tick):
    rng = random.Random(seed); fails = 0
    for i in range(trials):
        n = rng.randint(4, 14); nd = rng.randint(3, 10)
        prog = [R.encode(rng.choices(R.OPS, [3, 2, 2, 3, 3])[0]) for _ in range(n)]
        ok, info = run_pair(m, prog, [rng.randint(0, 1) for _ in range(nd)],
                            rng.randrange(n), rng.randrange(nd), ticks, refn)
        if not ok: fails += 1; print('FAIL', i, info)
    return trials, fails

if __name__ == '__main__':
    for clocked in (True, False):
        m = Machine(clocked)
        n, bad = truth_table(m)
        print('clocked' if clocked else 'noclk', m.counts(),
              'truth %d/%d' % (n - len(bad), n), bad[:3])
        t, f = random_tapes(m)
        print('  random tick-by-tick %d/%d' % (t - f, t))
