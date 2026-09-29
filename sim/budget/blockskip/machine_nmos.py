"""Block-skip CPU in resistor-load NMOS logic with static (cross-coupled)
storage, evaluated with switchsim.evaluate_static (same rules as
static/machine_static_trick3.py: closed transistor path beats a resistor
pull-up, two paths to different rails is contention).

Nets (all opcode lines are primary inputs, TRUE polarity only):
  F N P K MK   one-hot opcode,  r  data bit,  phi2  clock
  Q  = skip flag S,  Qb = NOT S      (cross-coupled pair, R_Q, R_Qb)
  RB = NOT r                          (1 inverter)
Strobes (active low, as MOVE_P_N in trick3):  TGN MPN MMN
  strobe_n = NOT(op & normal) = op_bar | S.  Built as ONE pass transistor
  from the strobe net to Q (gate = op): when op=1 the net follows Q, when
  op=0 the resistor pulls it high.  1 T + 1 R per strobe.
State write, phi2 only, one shared tail (K and MK are one-hot => the two
branches can never both conduct, so sharing the tail is safe):
  set   S:=1  : Qb -K- RB -X          (K & r==0)
  reset S:=0  : Q  -MK-    X
  tail        : X -phi2- GND
Variant 'noclk' drops the tail (9 T): ideal-tick only, hazard prone.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate_static

FEEDBACK = ['Q', 'Qb']

def build(clocked=True):
    T = [('Qb', 'Q', 'GND'), ('Q', 'Qb', 'GND'),      # hold pair
         ('r', 'RB', 'GND'),                           # RB = NOT r
         ('K', 'Qb', 'XS'), ('RB', 'XS', 'X'),         # set stack
         ('MK', 'Q', 'X'),                             # reset stack
         ('F', 'TGN', 'Q'), ('N', 'MPN', 'Q'), ('P', 'MMN', 'Q')]
    if clocked:
        T.append(('phi2', 'X', 'GND'))
    else:
        T = [(g, a, ('GND' if b == 'X' else b)) for g, a, b in T]
        T = [(g, ('GND' if a == 'X' else a), b) for g, a, b in T]
    R = ['Q', 'Qb', 'RB', 'TGN', 'MPN', 'MMN']
    return T, [(n, 1) for n in R]

class Machine:
    def __init__(self, clocked=True, transistors=None, resistors=None):
        T, R = build(clocked)
        self.T = transistors if transistors is not None else T
        self.R = resistors if resistors is not None else R
        self.clocked = clocked
    def counts(self):
        return dict(transistors=len(self.T), resistors=len(self.R),
                    leds=len(self.R))
    def _ev(self, op, r, phi2, seed):
        fixed = dict(op); fixed['r'] = r; fixed['phi2'] = phi2
        return evaluate_static(self.T, self.R, fixed, FEEDBACK, seed)
    def tick(self, S, op, r, check_glitch=True):
        seed = {'Q': S, 'Qb': 1 - S}
        n1 = self._ev(op, r, 0, seed)
        n2 = self._ev(op, r, 1, n1)
        s1 = (1 - n1['TGN'], 1 - n1['MPN'], 1 - n1['MMN'])
        if check_glitch:
            s2 = (1 - n2['TGN'], 1 - n2['MPN'], 1 - n2['MMN'])
            assert s1 == s2, ('strobe glitch in phi2', s1, s2)
        assert n2['Q'] == 1 - n2['Qb']
        return s1 + (n2['Q'],)

if __name__ == '__main__':
    for c in (True, False):
        print('clocked' if c else 'noclk', Machine(c).counts())
