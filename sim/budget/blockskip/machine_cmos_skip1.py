"""CMOS skip-one variant: master-slave bit (gatelib._regbit, 16 T) fed by
D = NOR3(S, Kbar, r) (6 T) + strobes ('tg' 9 T / 'gate' 12 T).  Strobes are
read in phi1 (S changes in phi2)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from machine_cmos import _aoi, _tg, evaluate_cmos_static
from gatelib import _regbit

def build(strobes='tg'):
    T = _aoi([['S_S'], ['Kbar'], ['r']], 'D')
    reg, fb = _regbit('D', 'S')
    T += reg
    for op, out in (('F', 'toggle'), ('N', 'move_plus'), ('P', 'move_minus')):
        if strobes == 'gate': T += _aoi([[op + 'bar'], ['S_S']], out)
        else: T += _tg('S_SB', 'S_S', op, out) + [('S_S', out, 'GND', 'n', 'strong')]
    return T, fb

class Machine:
    def __init__(self, strobes='tg', transistors=None):
        T, self.fb = build(strobes)
        self.T = transistors if transistors is not None else T
        self.st = None
    def counts(self): return dict(transistors=len(self.T), resistors=0, leds=0)
    def _ev(self, op, r, p, seed):
        f = {}
        for k, v in op.items(): f[k] = v; f[k + 'bar'] = 1 - v
        f['r'] = r; f['phi1'] = int(p == 1); f['phi1bar'] = int(p != 1)
        f['phi2'] = int(p == 2); f['phi2bar'] = int(p != 2)
        return evaluate_cmos_static(self.T, f, self.fb, seed)
    def tick(self, S, op, r):
        seed = {'S_M': 0, 'S_MB': 1, 'S_S': S, 'S_SB': 1 - S}
        if self.st is not None and self.st['S_S'] == S: seed = self.st
        n1 = self._ev(op, r, 1, seed); n2 = self._ev(op, r, 2, n1); self.st = n2
        return (n1['toggle'], n1['move_plus'], n1['move_minus'], n2['S_S'])
