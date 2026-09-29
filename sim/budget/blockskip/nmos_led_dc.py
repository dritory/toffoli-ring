"""DC check of the NMOS block-skip CPU with an indicator LED in series with
every pull-up resistor: VDD = 5 V, R = 1 kohm, red LED Vf 1.8..2.2 V (at 20 mA),
logic-level NMOS Vth 0.8..2.0 V (BSS138 class), Ron 2 ohm.  Solves the full
netlist (all 40 state/opcode/r cases x 2 phases) and reports worst levels.
Covers static DC only."""
import itertools, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R
from machine_nmos import build
from dtl_dc import solve, _diode
import dtl_dc

VDD = 5.0
def elements(clocked, vf, vth, rval=1000.0):
    T, Rs = build(clocked); el = []
    for g, a, b in T: el.append(('N', g, a, b, vth))
    for net, _ in Rs:
        el.append(('D', 'VDD', 'led_' + net, vf)); el.append(('R', 'led_' + net, net, rval))
    return el

def run(clocked=True, vf=2.0, vth=1.5):
    el = elements(clocked, vf, vth)
    worst = {'hi': 9, 'lo': 0, 'gate_on': 9, 'gate_off': 9}
    bad = 0; ledI = 0.0
    for S in (0, 1):
        for name in R.OPS:
            for r in (0, 1):
                op = R.encode(name); ref = R.tick(S, op, r)
                seed = {'Q': VDD * S, 'Qb': VDD * (1 - S)}
                v1 = None
                for ck in (0, 1):
                    f = {'VDD': VDD, 'GND': 0.0, 'r': VDD * r, 'phi2': VDD * ck}
                    for k, x in op.items(): f[k] = VDD * x
                    g0 = dict(seed) if v1 is None else v1
                    for n in ('RB', 'TGN', 'MPN', 'MMN'): g0.setdefault(n, VDD * 0.8)
                    v = solve(el, f, g0, 300, steps=(1e-2, 1e-3, 1e-4, 1e-5, 0.0)); 
                    if ck == 0: v1 = v; s1 = tuple(int(v[n] < VDD / 2) for n in ('TGN', 'MPN', 'MMN'))
                sn = int(v['Q'] > VDD / 2)
                if s1 + (sn,) != tuple(ref): bad += 1
                for n in ('Q', 'Qb', 'RB', 'TGN', 'MPN', 'MMN'):
                    for vv in (v1, v):
                        x = vv[n]
                        if x > VDD / 2: worst['hi'] = min(worst['hi'], x)
                        else: worst['lo'] = max(worst['lo'], x)
                # gate levels: every net used as a gate
                for n in ('Q', 'Qb', 'RB'):
                    x = v[n]
                    if x > VDD / 2: worst['gate_on'] = min(worst['gate_on'], x - vth)
                    else: worst['gate_off'] = min(worst['gate_off'], vth - x)
    return bad, worst

if __name__ == '__main__':
    for clocked in (True,):
        for vf, vth in ((1.8, 0.8), (2.0, 1.5), (2.2, 2.0), (1.8, 2.0), (2.2, 0.8)):
            bad, w = run(clocked, vf, vth)
            print('Vf=%.1f Vth=%.1f: truth-table failures %d | worst high %.2f V, worst low %.3f V, '
                  'gate margin to Vth: on >= %.2f V, off >= %.2f V' %
                  (vf, vth, bad, w['hi'], w['lo'], w['gate_on'], w['gate_off']), flush=True)
