"""Removal minimality of the LED-DTL block-skip CPU: every subset of size 1..3
of the 28 components removed (open circuit); the design 'still works' only if
the full 20-case truth table passes at three (Vf, Vth) corners."""
import itertools, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R
from machine_dtl import Machine, led_names, transient_ok
from test_nmos import truth_table

def works(drop, clocked=True):
    for vf, vth in ((2.0, 3.0), (1.8, 4.0), (2.2, 2.0)):
        try:
            m = Machine(clocked, vf={k: vf for k in led_names(clocked)}, vth=vth)
            m.el = [e for i, e in enumerate(m.el) if i not in drop]
            if truth_table(m)[1]: return False
            if clocked and not transient_ok(m): return False
        except Exception:
            return False
    return True

if __name__ == '__main__':
    clocked = '--noclk' not in sys.argv
    n = len(Machine(clocked).el)
    for k in (1, 2, 3):
        surv = [s for s in itertools.combinations(range(n), k) if works(set(s), clocked)]
        print('clocked' if clocked else 'noclk', n, 'components; removable subsets of size', k, ':', len(surv), surv[:5], flush=True)
