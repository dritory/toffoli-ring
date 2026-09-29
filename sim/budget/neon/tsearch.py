"""Find the shortest tick period T that passes (truth table + random programs) per corner."""
import sys, time, io, contextlib
from test_cpu import *
from cpu import DESIGN
from corners import CORNERS, vertex

if __name__ == '__main__':
    names = sys.argv[1].split(','); Ts = [float(x) for x in sys.argv[2].split(',')]
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    for nm in names:
        for T in Ts:
            c = dict(CORNERS[nm]) if nm in CORNERS else vertex(int(nm[1:]))
            seed = c.pop('seed', 0)
            mk = lambda i=0: Cpu('clamp', T=T, skew=0.003, seed=seed, **DESIGN, **c)
            t0 = time.time()
            n, bad = truth_table(mk)
            with contextlib.redirect_stdout(io.StringIO()):
                t, f = random_tapes(mk, trials=trials, ticks=60)
            print('%-6s T=%.2f truth %d/%d random %d/%d  (%.0fs)' % (nm, T, n - len(bad), n, t - f, t, time.time() - t0), flush=True)
            if not bad and f == 0: break
