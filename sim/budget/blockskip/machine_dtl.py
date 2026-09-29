"""LED diode-transistor logic block-skip CPU, 12 V supply, red LEDs as the
logic diodes, enhancement NMOS (Vth 2..4 V, e.g. IRF510 class) as inverters.

  NAND gate  : AND node (pull-up Ra) with LED per input (anode on node,
               cathode on input) -> ONE level-shift LED -> gate node (bleeder Rg)
               -> NMOS (drain pull-up Rl).  Output = NAND.
  OR node    : LED per input (anode on input, cathode on node) + bleeder to GND.
               No transistor; low is a clean 0 V, high = V_in - Vf.
Latch = NOR-type SR latch, AND-OR-INVERT gates (OR done at the gate node by
one LED per term; AND terms via LED-AND node + one level-shift LED):
  S  = NOT(Sb + phi2.MK)         reset when phi2 & MK
  Sb = NOT(S  + phi2.K.RB)       set   when phi2 & K & r==0,  RB = NOT r (1 T)
An OR node must never feed an AND node (it has no pull-down drive), so all
inter-gate signals are transistor outputs or ring lines.
Strobes (active low): toggle_n = OR(Fbar, S) etc. (LED-OR, bleeder, no T).
Variant 'noclk': phi2 dropped from both terms (ideal-tick only, hazard prone).
"""
import math, itertools
from dtl_dc import solve

VDD = 12.0
RA, RG, RL, RB_ = 4700.0, 10000.0, 1000.0, 22000.0

def netlist(clocked=True):
    E = []   # (kind, ...)
    def led(name, a, c): E.append(('D', a, c, name))
    def res(a, b, v): E.append(('R', a, b, v))
    # RB = NOT r   (transistor driven straight from the data line; RB only feeds an
    # AND-node LED, so its pull-up resistor is unnecessary -- found by minimality search)
    E.append(('M', 'r', 'RB', 'mos_RB'))     # open-drain: no pull-up, the AND-node LED is its load
    # gate S : S = NOT(Sb + phi2.MK)      gate Sb : Sb = NOT(S + phi2.K.RB)
    for out, other, ins, tag in (('S', 'Sb', ['phi2', 'MK'], 'S'),
                                 ('Sb', 'S', ['phi2', 'K', 'RB'], 'B')):
        g = 'g' + tag
        led('or_%s' % tag, other, g)                 # direct OR term (also a level shift)
        if not clocked:
            ins = [i for i in ins if i != 'phi2']
        if len(ins) == 1:
            led('or2_%s' % tag, ins[0], g)           # single literal: direct OR diode
        else:
            a = 'a' + tag
            res('VDD', a, RA)
            for i, x in enumerate(ins): led('and_%s_%d' % (tag, i), a, x)
            led('ls_%s' % tag, a, g)                 # level-shift LED: AND node -> gate node
        res(g, 'GND', RG)
        E.append(('M', g, out, 'mos_' + tag)); res('VDD', out, RL)
    # strobes (active low): LED-OR of op_bar and S, bleeder to GND, no transistor
    for op, out in (('F', 'tgn'), ('N', 'mpn'), ('P', 'mmn')):
        led('or_%s_0' % out, op + 'bar', out); led('or_%s_1' % out, 'S', out)
        res(out, 'GND', RB_)
    return E

def led_names(clocked=True):
    return [e[3] for e in netlist(clocked) if e[0] == 'D']

class Machine:
    """tick(S, op, r) -> (toggle, mp, mm, S').  Analog DC solve per phase;
    logic value = node > VDD/2.  vf: dict LED-name -> Vf (default 2.0)."""
    def __init__(self, clocked=True, vf=None, vth=3.0, default_vf=2.0):
        self.clocked = clocked
        E = netlist(clocked)
        self.el = []
        for e in E:
            if e[0] == 'D': self.el.append(('D', e[1], e[2], (vf or {}).get(e[3], default_vf)))
            elif e[0] == 'M': self.el.append(('M', e[1], e[2], vth))
            else: self.el.append(e)
        self.v = None
        self.counts_ = self.counts()
    def counts(self):
        return dict(transistors=sum(e[0] == 'M' for e in self.el),
                    resistors=sum(e[0] == 'R' for e in self.el),
                    leds=sum(e[0] == 'D' for e in self.el))
    def _fixed(self, op, r, ck):
        f = {'VDD': VDD, 'GND': 0.0, 'r': VDD * r, 'phi2': VDD * ck, 'phi2bar': VDD * (1 - ck)}
        for k, x in op.items(): f[k] = VDD * x; f[k + 'bar'] = VDD * (1 - x)
        return f
    def _guess(self, S):
        g = {'S': VDD * S * 0.9 + 0.1, 'Sb': VDD * (1 - S) * 0.9 + 0.1,
             'aS': 8.0 if S else 2.5, 'aB': 2.5 if S else 8.0,
             'gS': 0.0 if S else 6.0, 'gB': 6.0 if S else 0.0}
        return g
    def levels(self, S, op, r, ck, prev=None):
        f = self._fixed(op, r, ck)
        try:
            return solve(self.el, f, prev or self._guess(S))
        except RuntimeError:
            return solve(self.el, f, self._guess(S), 400,
                         steps=(1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 1e-5, 1e-6, 0.0))
    def tick(self, S, op, r, return_levels=False):
        v1 = self.levels(S, op, r, 0, self._prev(S))
        v2 = self.levels(S, op, r, 1, v1)
        hi = lambda x: int(x > VDD / 2)
        s1 = (1 - hi(v1['tgn']), 1 - hi(v1['mpn']), 1 - hi(v1['mmn']))
        s2 = (1 - hi(v2['tgn']), 1 - hi(v2['mpn']), 1 - hi(v2['mmn']))
        assert s1 == s2, ('strobe glitch', s1, s2)
        Sn = hi(v2['S']); assert Sn == 1 - hi(v2['Sb'])
        self.v = v2
        return s1 + (Sn,) if not return_levels else (s1 + (Sn,), v1, v2)
    def _prev(self, S):
        if self.v is not None and hi_(self.v['S']) == S: return self.v
        return self._guess(S)

def hi_(x): return int(x > VDD / 2)

if __name__ == '__main__':
    for c in (True, False):
        print('clocked' if c else 'noclk', Machine(c).counts())

def transient_ok(m):
    """phi2 = 0 windows in which the opcode/data lines are still moving must not
    write: (a) skip mode, F falling while MK rising (overlap); (b) normal mode,
    K present with r still reading 0."""
    ok = True
    v = m.levels(1, {'F': 1, 'N': 0, 'P': 0, 'K': 0, 'MK': 1}, 0, 0)
    ok &= v['S'] > VDD / 2 and v['tgn'] > VDD / 2
    v = m.levels(0, {'F': 0, 'N': 0, 'P': 0, 'K': 1, 'MK': 0}, 0, 0)
    ok &= v['S'] < VDD / 2
    return bool(ok)
