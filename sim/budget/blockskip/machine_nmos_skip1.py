"""Skip-one variant (IFZ suppresses exactly the next instruction) in the same
technology.  A one-tick delay needs a real master-slave: the next-state
S' = K & r==0 & !S depends on S itself, so the trick3 structure is used
(master folded into the eval node DNODE, differential slave with two tails).

  eval   : DNODE -(Kbar || r || S)- EN -phi1- GND   (DNODE = 1 iff K, r=0, S=0)
  master : Tm2 (DNODE->MBAR), Tm1 (MBAR holds DNODE low, tail phi2)
  slave  : cross-coupled S/Sb + wset(DNODE) + wreset(MBAR), one tail each
  strobes: pass transistor to S, as in machine_nmos.py
Strobes are valid in phi1 only here (S falls in phi2 of a skipped tick).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate_static

FEEDBACK = ['DNODE', 'MBAR', 'S', 'Sbar']

def build():
    T = [('Kbar', 'DNODE', 'EN'), ('r', 'DNODE', 'EN'), ('S', 'DNODE', 'EN'),
         ('phi1', 'EN', 'GND'),
         ('DNODE', 'MBAR', 'GND'), ('MBAR', 'DNODE', 'MTAIL'), ('phi2', 'MTAIL', 'GND'),
         ('Sbar', 'S', 'GND'), ('S', 'Sbar', 'GND'),
         ('DNODE', 'Sbar', 'WA'), ('phi2', 'WA', 'GND'),
         ('MBAR', 'S', 'WB'), ('phi2', 'WB', 'GND'),
         ('F', 'TGN', 'S'), ('N', 'MPN', 'S'), ('P', 'MMN', 'S')]
    R = ['DNODE', 'MBAR', 'S', 'Sbar', 'TGN', 'MPN', 'MMN']
    return T, [(n, 1) for n in R]

class Machine:
    def __init__(self, transistors=None, resistors=None):
        T, R = build()
        self.T = transistors if transistors is not None else T
        self.R = resistors if resistors is not None else R
        self.st = None
    def counts(self):
        return dict(transistors=len(self.T), resistors=len(self.R), leds=len(self.R))
    def _ev(self, op, r, ph, seed):
        fixed = {k: v for k, v in op.items()}
        fixed['Kbar'] = 1 - op['K']; fixed['r'] = r
        fixed['phi1'] = int(ph == 1); fixed['phi2'] = int(ph == 2)
        return evaluate_static(self.T, self.R, fixed, FEEDBACK, seed)
    def tick(self, S, op, r):
        seed = {'S': S, 'Sbar': 1 - S, 'DNODE': 0, 'MBAR': 1}
        if self.st is not None and self.st['S'] == S:
            seed = self.st
        n1 = self._ev(op, r, 1, seed)
        n2 = self._ev(op, r, 2, n1)
        self.st = n2
        return (1 - n1['TGN'], 1 - n1['MPN'], 1 - n1['MMN'], n2['S'])
