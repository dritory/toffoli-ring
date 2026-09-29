"""LED-DTL machine (analog DC solve per phase) vs ref.py: truth table and 500
random programs/tapes tick-by-tick, plus (Vf, Vth) corner runs."""
import random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from machine_dtl import Machine, led_names
from test_nmos import truth_table, random_tapes

if __name__ == '__main__':
    for clocked in (True, False):
        m = Machine(clocked)
        n, bad = truth_table(m)
        t, f = random_tapes(m, trials=500)
        print('clocked' if clocked else 'noclk', m.counts_, 'truth %d/%d' % (n - len(bad), n),
              'random %d/%d' % (t - f, t), flush=True)
    for vf, vth in ((1.8, 2.0), (2.2, 4.0), (1.8, 4.0), (2.2, 2.0)):
        m = Machine(True, vf={k: vf for k in led_names(True)}, vth=vth)
        n, bad = truth_table(m); t, f = random_tapes(m, trials=100, seed=7, ticks=60)
        print('corner Vf=%.1f Vth=%.1f: truth %d/%d random %d/%d' % (vf, vth, n - len(bad), n, t - f, t), flush=True)
