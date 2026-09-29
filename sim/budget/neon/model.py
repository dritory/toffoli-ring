"""Neon lamp + LDR circuit model (1950s parts): DC hysteresis model of the lamp,
LDR with photo-response and a first-order lag, and a fixed-step time simulator.

LAMP (NE-2 class), per-instance parameters, ranges in RANGES:
  off : open circuit (1e-11 S).  Strikes when the open-circuit voltage across it
        stays above Vs_eff = Vs + dark_dv for a time t_d (dark effect raises the
        strike voltage and slows the strike).
  on  : burning voltage Vb in series with dynamic resistance rd (V = Vb + rd*I).
        Goes out when I < Iext (extinction current) -> hysteresis: it holds at any
        source that still delivers Iext, i.e. down to about Vb, though it needed Vs to start.
  light output = lamp current I.
LDR: conductance G = Gd + (Gl - Gd) * E**gamma, E = sum_j c_ij * I_j / I_NOM
  (c = 1 for the designed optical link, `xtalk` for every other lamp), first-order lag on G
  (tau_r rising, tau_f falling), Gl = 1/Rlit at E = 1 (I_NOM = 0.5 mA), Gd = 1/Rdark.
  Slow memory effect: modelled by lowering Rdark in the corner set.
Diodes: piecewise-linear, Vf and 50 ohm.  Driven lines: Thevenin source (Vsrc, Rsrc).
"""
import math, random
import numpy as np

I_NOM = 0.5e-3
G_OFF = 1e-11
RANGES = {   # (lo, hi)  independent per instance
    'Vs': (85., 105.),      # strike voltage (ambient-lit)
    'dark_dv': (0., 25.),   # dark effect: extra strike voltage when not primed
    'Vb': (55., 65.),       # burning (sustain) voltage
    'rd': (1e3, 3e3),       # dynamic resistance
    'Iext': (20e-6, 100e-6),# extinction current
    'td0': (1e-3, 20e-3),   # strike delay at 20 % overvoltage
    'Rd': (0.5e6, 5e6),     # LDR dark resistance
    'Rlit': (1e3, 10e3),    # LDR lit resistance at 0.5 mA lamp current
    'gamma': (0.7, 0.9),
    'tau_r': (5e-3, 20e-3),
    'tau_f': (20e-3, 60e-3),
    'Rtol': (-0.05, 0.05),  # resistor tolerance
    'Vf': (0.5, 1.0),       # diode forward drop
    'VP': (0.97, 1.03),     # supply scale (+-3 %)
}
NOMINAL = dict(Vs=95., dark_dv=0., Vb=60., rd=2e3, Iext=50e-6, td0=5e-3, Rd=1e6, Rlit=4e3,
               gamma=0.8, tau_r=10e-3, tau_f=40e-3, Rtol=0., Vf=0.7, VP=1.0)

def pick(mode, key, rng, bias=None):
    lo, hi = RANGES[key]
    if mode == 'nom': return NOMINAL[key]
    if mode == 'lo': return lo
    if mode == 'hi': return hi
    if mode == 'vertex': return lo if rng.random() < 0.5 else hi
    if mode == 'uniform': return rng.uniform(lo, hi)
    raise ValueError(mode)

class Net:
    """elements: ('R',a,b,ohm) ('LDR',a,b,name,[lamp names]) ('D',a,b) ('L',a,b,name)
    drivers: node -> Rsrc (voltage set per step). Node 'GND' is 0 V."""
    def __init__(self, elements, drivers, mode='nom', seed=0, over=None, Rsrc=1e3,
                 xtalk=0.0, dt=5e-3, dark=False, VP=250.0):
        rng = random.Random(seed)
        P = lambda k: (over or {}).get(k, pick(mode, k, rng))
        self.dt = dt; self.xtalk = xtalk; self.VP = VP * P('VP')
        names = []
        for e in elements:
            for x in e[1:3]:
                if x != 'GND' and x not in names: names.append(x)
        for d in drivers:
            if d not in names: names.append(d)
        self.idx = {n: i for i, n in enumerate(names)}; self.n = len(names)
        ix = lambda x: -1 if x == 'GND' else self.idx[x]
        self.R, self.LDR, self.D, self.L = [], [], [], []
        self.lname = {}; self.ldrname = {}
        for e in elements:
            if e[0] == 'R':
                self.R.append((ix(e[1]), ix(e[2]), 1.0 / (e[3] * (1 + P('Rtol')))))
            elif e[0] == 'D':
                self.D.append((ix(e[1]), ix(e[2]), P('Vf')))
            elif e[0] == 'L':
                self.lname[e[3]] = len(self.L)
                self.L.append(dict(a=ix(e[1]), b=ix(e[2]), Vs=P('Vs') + (P('dark_dv') if dark else 0.0),
                                   Vb=P('Vb'), g=1 / P('rd'), Iext=P('Iext'),
                                   td0=P('td0') * (3.0 if dark else 1.0), name=e[3]))
            elif e[0] == 'LDR':
                self.ldrname[e[3]] = len(self.LDR)
                self.LDR.append(dict(a=ix(e[1]), b=ix(e[2]), src=list(e[4]), Gd=1 / P('Rd'), Gl=1 / P('Rlit'),
                                     gam=P('gamma'), tr=P('tau_r'), tf=P('tau_f'), name=e[3]))
        self.drv = [(self.idx[d], 1.0 / max(r, 1e-3) if r > 0 else 1e3, d) for d, r in drivers.items()]
        self.dnames = {d: k for k, (_, _, d) in enumerate(self.drv)}
        self.reset()

    def reset(self):
        self.on = [False] * len(self.L); self.tmr = [0.0] * len(self.L)
        self.G = [l['Gd'] for l in self.LDR]
        self.donst = [False] * len(self.D)
        self.I = [0.0] * len(self.L); self.V = np.zeros(self.n)
        self.t = 0.0
        self.Vl = [0.0] * len(self.L)      # voltage across lamp

    def set_lamps(self, on_names):
        for n in on_names: self.on[self.lname[n]] = True
        # start LDRs at their steady values for these lamps
        Itab = [I_NOM if self.L[i]['name'] in on_names else 0.0 for i in range(len(self.L))]
        for k, l in enumerate(self.LDR): self.G[k] = self._gtarget(l, Itab)

    def _gtarget(self, l, I):
        E = 0.0
        for j, lp in enumerate(self.L):
            c = 1.0 if lp['name'] in l['src'] else self.xtalk
            if c and I[j] > 0: E += c * I[j] / I_NOM
        E = min(E, 3.0)
        return l['Gd'] + (l['Gl'] - l['Gd']) * E ** l['gam']

    def solve(self, vs):
        """vs: dict driver -> volts.  Updates self.V, self.I (lamp currents), diode states."""
        n = self.n
        base = np.zeros((n, n)); bi = np.zeros(n)
        def stamp(a, b, g):
            if a >= 0: base[a, a] += g
            if b >= 0: base[b, b] += g
            if a >= 0 and b >= 0: base[a, b] -= g; base[b, a] -= g
        for a, b, g in self.R: stamp(a, b, g)
        for k, l in enumerate(self.LDR): stamp(l['a'], l['b'], self.G[k])
        for i, g, d in self.drv: base[i, i] += g; bi[i] += g * vs[d]
        for k, l in enumerate(self.L):
            if self.on[k]:
                stamp(l['a'], l['b'], l['g'])
                if l['a'] >= 0: bi[l['a']] += l['g'] * l['Vb']
                if l['b'] >= 0: bi[l['b']] -= l['g'] * l['Vb']
            else: stamp(l['a'], l['b'], G_OFF)
        st = list(self.donst)
        for it in range(12):
            G = base.copy(); I = bi.copy()
            for k, (a, b, vf) in enumerate(self.D):
                g = 1 / 50.0 if st[k] else G_OFF
                if a >= 0: G[a, a] += g
                if b >= 0: G[b, b] += g
                if a >= 0 and b >= 0: G[a, b] -= g; G[b, a] -= g
                if st[k]:
                    if a >= 0: I[a] += g * vf
                    if b >= 0: I[b] -= g * vf
            V = np.linalg.solve(G, I)
            new = list(st)
            for k, (a, b, vf) in enumerate(self.D):
                va = V[a] if a >= 0 else 0.0; vb = V[b] if b >= 0 else 0.0
                if st[k]: new[k] = (va - vb - vf) > 0.0
                else: new[k] = (va - vb) > vf
            if new == st: break
            st = new
        self.donst = st; self.V = V
        for k, l in enumerate(self.L):
            va = V[l['a']] if l['a'] >= 0 else 0.0; vb = V[l['b']] if l['b'] >= 0 else 0.0
            self.Vl[k] = va - vb
            self.I[k] = (va - vb - l['Vb']) * l['g'] if self.on[k] else 0.0

    def node(self, name): return 0.0 if name == 'GND' else float(self.V[self.idx[name]])

    def step(self, vs):
        """advance one dt with driver voltages vs"""
        dt = self.dt
        self.solve(vs)
        # lamps
        changed = False
        for k, l in enumerate(self.L):
            if self.on[k]:
                if self.I[k] < l['Iext']:
                    self.on[k] = False; self.tmr[k] = 0.0; changed = True
            else:
                v = self.Vl[k]
                if v > l['Vs']:
                    ov = (v - l['Vs']) / l['Vs']
                    td = l['td0'] * min(10.0, 0.2 / max(ov, 0.02))
                    self.tmr[k] += dt / td
                    if self.tmr[k] >= 1.0: self.on[k] = True; self.tmr[k] = 0.0; changed = True
                else: self.tmr[k] = max(0.0, self.tmr[k] - dt / 20e-3)   # ionisation decays
        # LDR lag on conductance
        for k, l in enumerate(self.LDR):
            gt = self._gtarget(l, self.I)
            tau = l['tr'] if gt > self.G[k] else l['tf']
            self.G[k] += (gt - self.G[k]) * (1 - math.exp(-dt / tau))
        self.t += dt
        return changed

    def lit(self, name): return self.on[self.lname[name]]
