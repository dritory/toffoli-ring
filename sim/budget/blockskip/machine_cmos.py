"""Secondary data point: the same block-skip CPU in fully complementary CMOS
(no ratioed fights).  State = NAND-type SR latch made of two OAI gates,
set/reset gated by phi2 and independent of S (no master stage needed):
    S  = NOT((phi2bar + Kbar + r) . Sb)      set  when phi2 & K & r==0
    Sb = NOT((phi2bar + MKbar)   . S )       reset when phi2 & MK
Strobes (active high):
    'gate' : toggle = NOR(Fbar, S)                      4 T each (restoring)
    'tg'   : toggle = TG(F; ctrl Sb) + NMOS pulldown(S) 3 T each (pass gate)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'jump'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cmos'))
from gatelib import _aoi, _tg
from cmos_sim import evaluate_cmos_static

def _oai(groups, out):
    """out = NOT(AND_g OR(groups[g]))."""
    ts = []
    nodes = [out] + ['%s_n%d' % (out, i) for i in range(1, len(groups))] + ['GND']
    for gi, grp in enumerate(groups):
        for lit in grp: ts.append((lit, nodes[gi], nodes[gi + 1], 'n', 'strong'))
    # pull-up = dual: one series chain per group, all chains in parallel
    for gi, grp in enumerate(groups):
        prev = 'VDD'
        for li, lit in enumerate(grp):
            nxt = out if li == len(grp) - 1 else '%s_p%d_%d' % (out, gi, li)
            ts.append((lit, prev, nxt, 'p', 'strong')); prev = nxt
    return ts

def build(strobes='tg'):
    T = _oai([['phi2bar', 'Kbar', 'r'], ['Sb']], 'S') + _oai([['phi2bar', 'MKbar'], ['S']], 'Sb')
    for op, out in (('F', 'toggle'), ('N', 'move_plus'), ('P', 'move_minus')):
        if strobes == 'gate':
            T += _aoi([[op + 'bar'], ['S']], out)
        else:
            T += _tg('Sb', 'S', op, out) + [('S', out, 'GND', 'n', 'strong')]
    return T

FEEDBACK = ['S', 'Sb']

class Machine:
    def __init__(self, strobes='tg', transistors=None):
        self.T = transistors if transistors is not None else build(strobes)
    def counts(self): return dict(transistors=len(self.T), resistors=0, leds=0)
    def _ev(self, op, r, ck, seed):
        f = {}
        for k, v in op.items(): f[k] = v; f[k + 'bar'] = 1 - v
        f['r'] = r; f['phi2'] = ck; f['phi2bar'] = 1 - ck
        return evaluate_cmos_static(self.T, f, FEEDBACK, seed)
    def tick(self, S, op, r):
        n1 = self._ev(op, r, 0, {'S': S, 'Sb': 1 - S})
        n2 = self._ev(op, r, 1, n1)
        s1 = (n1['toggle'], n1['move_plus'], n1['move_minus'])
        assert s1 == (n2['toggle'], n2['move_plus'], n2['move_minus'])
        return s1 + (n2['S'],)
