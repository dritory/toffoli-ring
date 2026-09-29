"""Extra checks: (1) gated-reset variant (26 parts) truth table + 100 programs, (2) static margins with
badly aged (dim) LDR lighting, Rlit up to 60 / 100 kohm."""
import io, contextlib
from test_cpu import *
from cpu import DESIGN, Cpu, netlist, counts
from margins import run
mk = lambda i=0: Cpu('gated', T=1.0, skew=0.003, **DESIGN)
n, bad = truth_table(mk)
with contextlib.redirect_stdout(io.StringIO()):
    t, f = random_tapes(mk, trials=100)
print('gated-reset variant', counts(netlist('gated')), 'truth %d/%d random %d/%d (nominal, T=1.0)' % (n - len(bad), n, t - f, t), flush=True)
for rl in (10e3, 30e3, 60e3, 100e3):
    o = run('clamp', 60, VP=DESIGN['VP'], I=DESIGN['I'], over=dict(Rlit=rl))
    print('Rlit = %.0f k (all LDRs):' % (rl / 1e3), ' | '.join('%s %.1f' % (k, o[k][0]) for k in o), flush=True)
