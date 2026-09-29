"""Small DC operating-point solver (numpy Newton) for the LED-DTL variant.

Elements
  ('R', a, b, ohm)
  ('D', anode, cathode, Vf)   LED, Shockley n=2, I(20 mA) = Vf-defined knee
  ('M', gate, drain, Vth)     enhancement NMOS, source = GND, smooth switch:
                              G = 1/Ron / (1+exp(-(Vgs-Vth)/0.05)) + 1e-9 S,
                              Ron = 2 ohm, gate draws no current
Fixed nodes (VDD, GND, ring lines, clocks, data bit) are ideal sources.
Covers static DC levels only: no dynamics, no switching speed, no
sub-threshold leakage of the MOSFET beyond G_off, no source impedance of the
ring lines (ideal 0 / VDD)."""
import math
import numpy as np

VT = 0.02585; NID = 2.0; IREF = 0.020
RON = 2.0

def _diode(v, vf):
    isat = IREF / math.exp(vf / (NID * VT))
    vmax = vf + 0.5           # linear continuation above the knee (keeps Newton sane)
    if v > vmax:
        i0 = isat * (math.exp(vmax / (NID * VT)) - 1)
        g0 = isat * math.exp(vmax / (NID * VT)) / (NID * VT)
        return i0 + g0 * (v - vmax), g0
    e = math.exp(v / (NID * VT))
    return isat * (e - 1), isat * e / (NID * VT) + 1e-12

def _mos(vgs, vds, vth):
    x = (vgs - vth) / 0.05
    s = 1 / (1 + math.exp(-max(min(x, 60), -60)))
    G = s / RON + 1e-9
    dG = (s * (1 - s) / 0.05) / RON
    return G * vds, G, dG * vds

def solve(elements, fixed, guess=None, iters=200, gpt=None, _v0=None, steps=(2e-3, 2e-5, 0.0)):
    if gpt is None:
        v = None
        for g in steps:
            v = solve(elements, fixed, guess if v is None else v, iters, g, v)
        return v
    nodes = set(fixed)
    for e in elements:
        nodes.update(e[1:4] if e[0] == 'N' else (e[1:3] if e[0] != 'M' else e[1:3]))
    nodes = sorted(nodes)
    free = [n for n in nodes if n not in fixed]
    idx = {n: i for i, n in enumerate(free)}
    v = {n: fixed[n] for n in fixed}; v['GND'] = 0.0
    for n in free: v[n] = (guess or {}).get(n, 0.0)
    n = len(free)
    vold = dict(v)
    for it in range(iters):
        J = np.zeros((n, n)); F = np.zeros(n)
        def stamp(a, b, i, g):          # current i flows a->b, conductance g
            if a in idx:
                F[idx[a]] += i
                if a in idx: J[idx[a], idx[a]] += g
                if b in idx: J[idx[a], idx[b]] -= g
            if b in idx:
                F[idx[b]] -= i
                J[idx[b], idx[b]] += g
                if a in idx: J[idx[b], idx[a]] -= g
        for e in elements:
            if e[0] == 'R':
                stamp(e[1], e[2], (v[e[1]] - v[e[2]]) / e[3], 1 / e[3])
            elif e[0] == 'D':
                i, g = _diode(v[e[1]] - v[e[2]], e[3]); stamp(e[1], e[2], i, g)
            elif e[0] == 'N':      # symmetric NMOS switch ('N', gate, a, b, vth)
                _, gate, na, nb, vth = e
                lowis_a = v[na] <= v[nb]
                vlow = v[na] if lowis_a else v[nb]
                _, G, dGv = _mos(v[gate] - vlow, 1.0, vth)   # dGv = dG/dVgs
                dv = v[na] - v[nb]; i = G * dv
                # I = G(vg - vlow)*(va - vb)
                dI = {gate: dGv * dv, na: G, nb: -G}
                dI[na if lowis_a else nb] += -dGv * dv
                for nd, sign in ((na, 1.0), (nb, -1.0)):
                    if nd in idx:
                        F[idx[nd]] += sign * i
                        for k2, dd in dI.items():
                            if k2 in idx: J[idx[nd], idx[k2]] += sign * dd
            elif e[0] == 'M':
                _, gate, drain, vth = e
                i, gds, gm = _mos(v[gate], v[drain], vth)
                stamp(drain, 'GND', i, gds)
                if gate in idx and drain in idx: J[idx[drain], idx[gate]] += gm
        for nme in free:
            F[idx[nme]] += gpt * (v[nme] - vold[nme]); J[idx[nme], idx[nme]] += gpt
        for k in range(n): J[k, k] += 1e-9
        try:
            dx = np.linalg.solve(J, -F)
        except np.linalg.LinAlgError:
            raise RuntimeError('singular')
        m = np.max(np.abs(dx)) if n else 0
        if m > 1.0: dx *= 1.0 / m
        for nme in free: v[nme] += dx[idx[nme]]
        if np.max(np.abs(dx)) < 1e-7 and np.max(np.abs(F)) < 1e-8:
            return v
    raise RuntimeError('no DC convergence')
