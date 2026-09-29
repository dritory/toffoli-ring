"""DC checks for the LED-DTL block-skip CPU (VDD = 12 V, red LEDs Vf 1.8..2.2 V
at 20 mA, NMOS Vth 2..4 V).  Covers: static DC levels of every gate type over
the LED Vf corners (each LED independently at 1.8 or 2.2), the full machine's
20-case truth table x 2 phases at random (Vf, Vth) samples, and the resulting
worst-case margins.  Does NOT cover: switching speed/dynamics, MOSFET
subthreshold leakage (modelled as 1 nS), ring-line source impedance (ideal
0/12 V), temperature, LED tolerance beyond 1.8..2.2 V."""
import itertools, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R
from machine_dtl import Machine, led_names, VDD
from test_nmos import truth_table

def gate_survey(clocked=True):
    """Worst-case node voltages per gate type, all input combos, all Vf corners
    of the LEDs belonging to that gate (others nominal 2.0 V)."""
    names = led_names(clocked)
    groups = {'S gate (AOI)': [n for n in names if n.endswith('_S')],
              'Sb gate (AOI)': [n for n in names if n.endswith('_B')],
              'strobe OR': [n for n in names if n.startswith('or_t')],
              'strobe OR (N)': [n for n in names if n.startswith('or_m')]}
    out = {}
    for gname, leds in groups.items():
        worst = {}
        for corner in itertools.product((1.8, 2.2), repeat=len(leds)):
            vf = dict(zip(leds, corner))
            m = Machine(clocked, vf=vf, vth=3.0)
            for S in (0, 1):
                for opn in ('F', 'K', 'MK', 'N'):
                    for r in (0, 1):
                        for ck in (0, 1):
                            v = m.levels(S, R.encode(opn), r, ck)
                            for k in ('gS', 'gB', 'S', 'Sb', 'tgn', 'mpn', 'RB'):
                                lo, hi = worst.get(k, (99, -99))
                                worst[k] = (min(lo, v[k]), max(hi, v[k]))
        out[gname] = worst
    return out

def machine_samples(clocked=True, n=60, seed=5):
    rng = random.Random(seed); bad = 0
    stat = {}
    for i in range(n):
        vf = {k: rng.uniform(1.8, 2.2) for k in led_names(clocked)}
        vth = rng.uniform(2.0, 4.0)
        m = Machine(clocked, vf=vf, vth=vth)
        nn, badrows = truth_table(m)
        bad += len(badrows)
        for S in (0, 1):
            for opn in R.OPS:
                for r in (0, 1):
                    for ck in (0, 1):
                        v = m.levels(S, R.encode(opn), r, ck)
                        # gate node voltages vs threshold of THIS sample
                        for g in ('gS', 'gB'):
                            on = v['S' if g == 'gS' else 'Sb'] < 6   # transistor on <=> its output low
                            key = g + ('_on' if on else '_off')
                            stat.setdefault(key, []).append(v[g] - vth if on else vth - v[g])
                        for k in ('S', 'Sb'):
                            stat.setdefault(k + ('_hi' if v[k] > 6 else '_lo'), []).append(v[k])
    return bad, stat

if __name__ == '__main__':
    clocked = '--noclk' not in sys.argv
    print('gate survey (min, max volts per node, over all input combos and Vf corners):')
    for g, w in gate_survey(clocked).items():
        print(' ', g, {k: (round(float(a), 2), round(float(b), 2)) for k, (a, b) in w.items()})
    bad, stat = machine_samples(clocked)
    print('random (Vf, Vth) samples: truth-table failures =', bad)
    for k, v in sorted(stat.items()):
        v = [float(x) for x in v]
        print('  %-7s min %.2f max %.2f' % (k, min(v), max(v)),
              '(margin to Vth, V)' if k.startswith('g') else '')

def led_currents(clocked=True):
    """Nominal Vf=2.0: per LED class, min/max current (mA) over all states."""
    from dtl_dc import _diode
    from machine_dtl import netlist
    m = Machine(clocked)
    names = {}
    E = netlist(clocked); Dn = [e for e in E if e[0] == 'D']
    cls = lambda n: n.split('_')[0] + ('_' + n.split('_')[1] if n.startswith(('or_t', 'or_m')) is False and len(n.split('_')) > 2 and n.split('_')[0] == 'and' else '')
    cur = {}
    for S in (0, 1):
        for opn in R.OPS:
            for r in (0, 1):
                for ck in (0, 1):
                    v = m.levels(S, R.encode(opn), r, ck)
                    for e in Dn:
                        i = _diode(v[e[1]] - v[e[2]], 2.0)[0] * 1e3
                        k = e[3].rsplit('_', 1)[0] if e[3].startswith(('and', 'ls', 'or_S', 'or_B', 'or2')) else 'strobe_or'
                        lo, hi = cur.get(k, (1e9, -1e9)); cur[k] = (min(lo, i), max(hi, i))
    return cur

if __name__ == '__main__':
    print('LED current classes (mA, min..max over all states; ~0 = dark):')
    for k, (a, b) in sorted(led_currents('--noclk' not in sys.argv).items()):
        print('  %-10s %.4f .. %.2f' % (k, a, b))

def write_drive(clocked=True):
    """Loop opened: hold S/Sb at their OLD levels as ideal sources and check the
    gate node that must flip the latch, over all Vf corners (LEDs of the gate
    involved at 1.8/2.2, others 2.0) -- this is the forcing path alone."""
    from dtl_dc import solve
    out = {}
    names = led_names(clocked)
    for what, old, op, r, target, leds in (
            ('set  (S 0->1): gB must rise', 0, 'K', 0, 'gB', [n for n in names if n.endswith('_B')]),
            ('reset(S 1->0): gS must rise', 1, 'MK', 0, 'gS', [n for n in names if n.endswith('_S')])):
        lo = 99
        for corner in itertools.product((1.8, 2.2), repeat=len(leds)):
            vf = dict(zip(leds, corner)); m = Machine(clocked, vf=vf)
            fixed = m._fixed(R.encode(op), r, 1)
            fixed['S'] = 11.0 * old; fixed['Sb'] = 11.0 * (1 - old)
            # drop the two pull-ups / drain transistors of the latch nodes (ideal sources)
            el = [e for e in m.el if not (e[0] == 'M' and e[2] in ('S', 'Sb'))
                  and not (e[0] == 'R' and e[1] == 'VDD' and e[2] in ('S', 'Sb'))]
            v = solve(el, fixed, {})
            lo = min(lo, float(v[target]))
        out[what] = lo
    return out

if __name__ == '__main__':
    print('forcing-path gate drive (V, worst over LED corners; must exceed Vth_max = 4 V):',
          {k: round(v, 2) for k, v in write_drive('--noclk' not in sys.argv).items()})
