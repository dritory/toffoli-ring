"""Resistor-load NMOS + static latch netlist generator for a bundle menu, same
rules as sim/budget/blockskip/machine_nmos.py (mark semantics 'a': S=1 & mark
-> S:=0, bundle suppressed).  Only bundles whose moves come last are
hardware-feasible (the data interface exposes only the cell under the
pointer); tests may follow a flip (then they see NOT r).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate_static
from macro import B

FEEDBACK = ['Q', 'Qb']

def ref_tick(b, S, r):
    """behavioural reference: (toggle, mp, mm, S')"""
    if S: return 0, 0, 0, (0 if b.mark else 1)
    cell, tog, mp, mm, S2 = r, 0, 0, 0, 0
    for op in b.ops:
        if op == 'F': cell ^= 1; tog ^= 1
        elif op[0] == 'T':
            if cell == int(op[1]): S2 = 1
        elif op == 'P': mp = 1
        else: mm = 1
    return tog, mp, mm, S2

def feasible(b):
    mv = False
    for op in b.ops:
        if op in 'PM': mv = True
        elif mv: return False
    return True

def build(menu):
    """returns transistors [(gate,a,b)], resistors [(net,1)], line names"""
    T = [('Qb', 'Q', 'GND'), ('Q', 'Qb', 'GND')]
    R = ['Q', 'Qb']
    names = ['L%d' % i for i in range(len(menu))]
    strobes = {'F': 'TGN', 'P': 'MPN', 'M': 'MMN'}
    used = set()
    setgrp = {}          # required r value -> list of (line, gated)
    reset = []
    for nm, b in zip(names, menu):
        assert feasible(b), b
        fb = False
        for op in b.ops:
            if op == 'F':
                T.append((nm, strobes['F'], 'Q')); used.add('F'); fb = True
            elif op == 'P': T.append((nm, strobes['P'], 'Q')); used.add('P')
            elif op == 'M': T.append((nm, strobes['M'], 'Q')); used.add('M')
            elif op[0] == 'T':
                req = int(op[1]) ^ int(fb)      # r value that fires
                setgrp.setdefault(req, []).append((nm, b.mark))
        if b.mark: reset.append(nm)
    for s in used: R.append(strobes[s])
    need_rb = 0 in setgrp
    if need_rb: T.append(('r', 'RB', 'GND')); R.append('RB')
    for req, lst in setgrp.items():
        sig = 'r' if req == 1 else 'RB'
        xs = 'XS%d' % req
        for nm, gated in lst:
            if gated:       # mark+test letter: set path only when S=0 (gate Qb)
                T.append((nm, 'Qb', 'Y_' + nm)); T.append(('Qb', 'Y_' + nm, xs))
            else:
                T.append((nm, 'Qb', xs))
        T.append((sig, xs, 'X'))
    for nm in reset: T.append((nm, 'Q', 'X'))
    if setgrp or reset: T.append(('phi2', 'X', 'GND'))
    return T, [(n, 1) for n in R], names

class Machine:
    def __init__(self, menu):
        self.menu = menu
        self.T, self.R, self.names = build(menu)
    def counts(self): return dict(T=len(self.T), R=len(self.R))
    def _ev(self, idx, r, phi2, seed):
        fixed = {n: int(i == idx) for i, n in enumerate(self.names)}
        fixed['r'] = r; fixed['phi2'] = phi2
        return evaluate_static(self.T, self.R, fixed, FEEDBACK, seed)
    def tick(self, S, idx, r):
        seed = {'Q': S, 'Qb': 1 - S}
        n1 = self._ev(idx, r, 0, seed); n2 = self._ev(idx, r, 1, n1)
        g = lambda n, k: 1 - n[k] if k in n else 0
        s1 = (g(n1, 'TGN'), g(n1, 'MPN'), g(n1, 'MMN'))
        s2 = (g(n2, 'TGN'), g(n2, 'MPN'), g(n2, 'MMN'))
        assert n2['Q'] == 1 - n2['Qb']
        return s1 + (n2['Q'],), s1 == s2
