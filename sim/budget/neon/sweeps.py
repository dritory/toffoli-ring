"""Sensitivity sweeps at the chosen T: line skew, optical crosstalk, LDR memory effect,
lamp aging, line source impedance.  Each row: truth table + 30 random programs x 60 ticks."""
import sys, io, contextlib, time
from test_cpu import *
from cpu import DESIGN
from corners import CORNERS
T = 1.0
def trial(label, trials=30, **kw):
    base = dict(CORNERS[kw.pop("corner", "nom")])
    over = dict(base.get('over', {})); over.update(kw.pop('over', {}))
    args = dict(base, over=over); design = dict(DESIGN); design.update(kw.pop('design', {})); args.update(kw)
    mk = lambda i=0: Cpu('clamp', T=T, **design, **args)
    try: n, bad = truth_table(mk)
    except AssertionError:
        print('%-46s cannot hold its initial state (LSb will not stay lit)' % label, flush=True); return
    with contextlib.redirect_stdout(io.StringIO()):
        t, f = random_tapes(mk, trials=trials, ticks=60)
    m = mk(); 
    print('%-46s truth %d/%d random %d/%d' % (label, n - len(bad), n, t - f, t), flush=True)
if __name__ == '__main__':
    which = sys.argv[1]
    if which == 'skew':
        for c in ('nom', 'fast', 'slow'):
            for sk in (0.003, 0.03, 0.1, 0.2, 0.4):
                trial('%s corner, line skew up to %d ms' % (c, sk * 1e3), corner=c, skew=sk)
    if which == 'xtalk':
        for c in ('nom', 'slow', 'weak'):
            for xt in (1e-6, 3e-6, 1e-5, 3e-5, 1e-4):
                trial('%s corner, optical crosstalk %.0e' % (c, xt), corner=c, xtalk=xt, skew=0.003)
    if which == 'stress':
        trial('slow + LDR memory effect Rdark=0.5M', corner='slow', over=dict(Rd=0.5e6), skew=0.003)
        trial('slow + LDR memory effect Rdark=0.3M', corner='slow', over=dict(Rd=0.3e6), skew=0.003)
        trial('slow + Rdark=0.5M, lamp current 1.0 mA', corner='slow', over=dict(Rd=0.5e6), design=dict(I=1.0e-3), skew=0.003)
        trial('slow + Rdark=0.3M, lamp current 1.0 mA', corner='slow', over=dict(Rd=0.3e6), design=dict(I=1.0e-3), skew=0.003)
        trial('weak + aged lamps (Vs 120, Rlit x3)', corner='weak', over=dict(Vs=120., Rlit=30e3), skew=0.003)
        trial('slow + aged lamps (Vs 115)', corner='slow', over=dict(Vs=115.), skew=0.003)
        for rs in (1e3, 5e3, 20e3):
            trial('slow, line source impedance %dk' % (rs / 1e3), corner='slow', Rsrc=rs, skew=0.003)
        for vp in (0.90, 0.95, 1.05, 1.10):
            trial('nom, supply x%.2f' % vp, corner='nom', over=dict(VP=vp), skew=0.003)
