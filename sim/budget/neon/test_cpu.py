"""Truth table + random-program tick test of the neon CPU (analog time-domain model)
against ref.py.  A tick passes when the strobes sampled at the end of the tick equal the
reference and the skip lamp state at the end of the tick equals the reference S'."""
import sys, os, random, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'blockskip'))
import ref as R
from cpu import Cpu, counts

def truth_table(mk, verbose=False):
    """each (S, opcode, r) case run on a fresh machine: S=1 is reached by a K tick with r=0;
    the r value of the preparation tick is both equal to and different from the test r."""
    n = 0; bad = []
    for S in (0, 1):
        for name in R.OPS:
            for r in (0, 1):
                for rp in (0, 1):
                    m = mk()
                    op = R.encode(name)
                    if S:
                        m.tick(0, R.encode('K'), 0)              # r=0 -> S becomes 1
                        # (S=1 reference for the next tick)
                    else:
                        m.tick(0, R.encode('F' if rp else 'N'), rp)   # some non-skipping tick
                    # in prep for S=0 the F/N tick toggles/moves data but only the machine input r matters
                    got = m.tick(S, op, r); exp = R.tick(S, op, r)
                    n += 1
                    if tuple(got) != tuple(exp): bad.append((S, name, r, rp, got, exp))
    return n, bad

def run_program(m, prog, d0, pp0, dp0, ticks):
    d = list(d0); S = 0; pp = pp0; dp = dp0; nd = len(d0); n = len(prog)
    for t in range(ticks):
        op = prog[pp]
        exp = R.tick(S, op, d[dp]); got = m.tick(S, op, d[dp])
        if tuple(got) != tuple(exp): return False, ('signals', t, got, exp)
        if exp[0]: d[dp] ^= 1
        dp = (dp + exp[1] - exp[2]) % nd; S = exp[3]; pp = (pp + 1) % n
    return True, None

def random_tapes(mk, trials=500, seed=20260929, ticks=80, log=None):
    rng = random.Random(seed); fails = 0
    for i in range(trials):
        n = rng.randint(4, 14); nd = rng.randint(3, 10)
        prog = [R.encode(rng.choices(R.OPS, [3, 2, 2, 3, 3])[0]) for _ in range(n)]
        m = mk(i)
        ok, info = run_program(m, prog, [rng.randint(0, 1) for _ in range(nd)],
                               rng.randrange(n), rng.randrange(nd), ticks)
        if not ok:
            fails += 1; print('FAIL', i, info, flush=True)
        if log and (i + 1) % 50 == 0: print('  ', i + 1, 'programs, fails', fails, flush=True)
    return trials, fails

if __name__ == '__main__':
    T = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6
    t0 = time.time()
    mk = lambda i=0: Cpu('clamp', T=T)
    n, bad = truth_table(mk)
    print('T=%.2f truth %d/%d' % (T, n - len(bad), n), bad[:3], '%.0fs' % (time.time() - t0), flush=True)
