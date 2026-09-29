"""Neon/LDR block-skip CPU (variant 'clamp': two-lamp NOR latch, reset by clamp diode,
set gated by the phi2 rail) and a per-tick harness against ref.py.

Interface (all electrical lines 0 / VP, Thevenin source Rsrc):
  F N P K   opcode lines (true polarity), MB = NOT MK (active low), r data line, PHI = phi2 rail
  outputs   strobe lamps LF LN LP lit = strobe active; the memory reads them with its own LDRs
Netlist notes:  every logic lamp is fed from VP (or a line) through a ballast resistor and is
shunted by LDRs lit by other lamps (NOR); a lit lamp = 1 = about 0.5 mA.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'blockskip'))
import ref as R
from model import Net

RB = 330e3   # ballast of every lamp

def netlist(variant='clamp'):
    E = []
    R_ = lambda a, b: E.append(('R', a, b, RB))
    # skip flag S: LS lit = S=1, LSb lit = S=0 (NOR latch)
    R_('VP', 's'); E.append(('L', 's', 'GND', 'LS'))
    E.append(('LDR', 's', 'GND', 'a', ['LSb']))              # LSb lit shunts LS
    R_('VP', 'sb'); E.append(('L', 'sb', 'GND', 'LSb'))
    E.append(('LDR', 'sb', 'GND', 'b', ['LS']))              # LS lit shunts LSb
    E.append(('LDR', 'sb', 'GND', 'set', ['LK']))            # set condition shunts LSb
    if variant == 'clamp':
        E.append(('D', 's', 'MB'))                           # MB low (MK active) clamps LS off
    else:  # 'gated': reset condition lamp LM = phi2 & MK
        R_('PHI', 'm'); E.append(('L', 'm', 'GND', 'LM')); E.append(('D', 'm', 'MK'))
        E.append(('LDR', 's', 'GND', 'rst', ['LM']))
    # set condition lamp LK = phi2 & K & NOT r
    R_('PHI', 'k'); E.append(('L', 'k', 'GND', 'LK')); E.append(('D', 'k', 'K'))
    E.append(('LDR', 'k', 'GND', 'rL', ['Lr']))
    R_('r', 'rl'); E.append(('L', 'rl', 'GND', 'Lr'))       # Lr lit when r=1 (inversion of r)
    # strobes: lamp fed by the opcode line, shunted by LDR lit by LS  (= op AND NOT S)
    for op, nm in (('F', 'LF'), ('N', 'LN'), ('P', 'LP')):
        R_(op, 'x' + op); E.append(('L', 'x' + op, 'GND', nm))
        E.append(('LDR', 'x' + op, 'GND', 's' + op, ['LS']))
    return E

DRIVERS = ['VP', 'PHI', 'F', 'N', 'P', 'K', 'MK', 'MB', 'r']

def counts(E):
    c = dict(lamps=0, ldrs=0, resistors=0, diodes=0)
    for e in E:
        c[{'L': 'lamps', 'LDR': 'ldrs', 'R': 'resistors', 'D': 'diodes'}[e[0]]] += 1
    c['total'] = sum(c.values())
    return c

class Cpu:
    """tick(S, op, r) -> (toggle, mp, mm, S').  Analog time-domain simulation of one tick
    period T (s); the analog state (lamps, LDR conductances) carries over between ticks."""
    def __init__(self, variant='clamp', T=0.6, phi_start=0.4, skew=0.0, seed=0, Rsrc=1e3,
                 xtalk=0.0, mode='nom', over=None, dark=False, dt=5e-3, VP=250.0):
        self.E = netlist(variant)
        drv = {d: (0 if d in ('VP',) else Rsrc) for d in DRIVERS if d != 'MK'}
        if variant != 'clamp': drv['MK'] = Rsrc
        self.net = Net(self.E, drv, mode=mode, seed=seed, over=over, xtalk=xtalk, dt=dt, dark=dark, VP=VP)
        self.T = T; self.phi_start = phi_start; self.skew = skew
        import random; self.rng = random.Random(seed + 991)
        self.dt = dt; self.started = False
        self.stats = dict(glitch_ms_max=0.0, late_ms_max=0.0, ticks=0)
        self.op = None; self.r = None
    def lines(self, op, r, phi):
        VP = self.net.VP
        d = dict(VP=VP, PHI=VP * phi, F=VP * op['F'], N=VP * op['N'], P=VP * op['P'], K=VP * op['K'],
                 MB=VP * (1 - op['MK']), r=VP * r, MK=VP * op['MK'])
        return {k: v for k, v in d.items() if k in self.net.dnames}
    def settle_init(self, r0):
        net = self.net
        net.set_lamps(['LSb'])                       # S = 0
        idle = {'F': 0, 'N': 0, 'P': 0, 'K': 0, 'MK': 0}
        for _ in range(int(2.0 / self.dt)): net.step(self.lines(idle, r0, 0))
        assert net.lit('LSb') and not net.lit('LS'), 'init state'
        self.op = idle; self.r = r0; self.started = True
    def tick(self, S, op, r):
        net = self.net; dt = self.dt; T = self.T
        if not self.started: self.settle_init(r)
        pop, pr = self.op, self.r
        sk = {k: self.rng.uniform(0, self.skew) for k in ('F', 'N', 'P', 'K', 'MK', 'r')}
        nsteps = int(round(T / dt)); ts = nsteps - 1
        exp = (op['F'] * (1 - S), op['N'] * (1 - S), op['P'] * (1 - S))
        strobe = None; glitch = [0.0, 0.0, 0.0]; late = [0.0, 0.0, 0.0]
        for i in range(nsteps):
            t = i * dt
            cur = {k: (op[k] if t >= sk[k] else pop[k]) for k in ('F', 'N', 'P', 'K', 'MK')}
            rr = r if t >= sk['r'] else pr
            phi = 1 if (self.phi_start * T <= t < T - 2 * dt) else 0
            net.step(self.lines(cur, rr, phi))
            lit = (net.lit('LF'), net.lit('LN'), net.lit('LP'))
            for j in range(3):
                if lit[j] and not exp[j]: glitch[j] += dt
                if exp[j] and not lit[j] and t < 0.9 * T: late[j] += dt
            if i == ts: strobe = tuple(int(x) for x in lit)
        self.op = op; self.r = r
        self.stats['ticks'] += 1
        self.stats['glitch_ms_max'] = max(self.stats['glitch_ms_max'], 1e3 * max(glitch))
        self.stats['late_ms_max'] = max(self.stats['late_ms_max'], 1e3 * max(late))
        Sn = int(net.lit('LS'))
        return strobe + (Sn,)

if __name__ == '__main__':
    for v in ('clamp', 'gated'):
        print(v, counts(netlist(v)))
