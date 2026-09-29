"""500 random programs x 80 ticks, tick by tick, analog time-domain model vs ref.py, at a corner."""
import sys, time
from test_cpu import *
from cpu import DESIGN
from corners import CORNERS, vertex
if __name__ == '__main__':
    nm = sys.argv[1]; T = float(sys.argv[2]); trials = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    c = dict(CORNERS[nm]) if nm in CORNERS else vertex(int(nm[1:]))
    seed = c.pop('seed', 0)
    design = dict(DESIGN)
    if len(sys.argv) > 4: design['I'] = float(sys.argv[4]) * 1e-3
    if len(sys.argv) > 5: c['over'] = dict(c.get('over', {}), Rd=float(sys.argv[5]) * 1e6)
    ms = []
    def mk(i=0):
        m = Cpu('clamp', T=T, **design, skew=0.003, seed=seed + i if nm.startswith('v') else 0, **c)
        ms.append(m); return m
    t0 = time.time()
    n, bad = truth_table(mk); ms.clear()
    t, f = random_tapes(mk, trials=trials)
    g = max(m.stats['glitch_ms_max'] for m in ms); l = max(m.stats['late_ms_max'] for m in ms)
    print('%s I=%.2f mA Rdark=%s: T=%.2f: truth %d/%d, random %d/%d passed, worst strobe glitch %.0f ms, worst strobe lateness (before 0.9T) %.0f ms, %.0fs'
          % (nm, design['I'] * 1e3, c.get('over', {}).get('Rd', 'corner'), T, n - len(bad), n, t - f, t, g, l, time.time() - t0), flush=True)
