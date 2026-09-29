"""Task 1 checks of the lamp + LDR building blocks (DC hysteresis and inversion)."""
import itertools, random, sys
from model import Net, RANGES, NOMINAL

def settle(net, vs, t=2.0):
    for _ in range(int(t / net.dt)): net.step(vs)

def memory_lamp(VB, Rb, mode, seed=0, dark=True):
    """one lamp + bias resistor from a VB rail: does it hold lit and hold dark?"""
    el = [('R', 'VB', 'x', Rb), ('L', 'x', 'GND', 'L1')]
    res = {}
    for start in (0, 1):
        n = Net(el, {'VB': 0.0}, mode=mode, seed=seed, dark=dark)
        if start: n.set_lamps(['L1'])
        settle(n, {'VB': VB}, 1.0)
        res[start] = n.lit('L1')
    return res[0] is False and res[1] is True

def window(Rb, dark=True):
    """bias window (V) over all vertex corners of the lamp: lit holds above lo, dark holds below hi"""
    lo, hi = 0.0, 1e9
    for Vb in RANGES['Vb']:
        for Iext in RANGES['Iext']:
            for rd in RANGES['rd']:
                lo = max(lo, Vb + Iext * (Rb + rd))
    for Vs in RANGES['Vs']:
        for dv in ((0, RANGES['dark_dv'][1]) if dark else (0,)):
            hi = min(hi, Vs)           # dark effect only raises strike; primed lamp uses Vs
    return lo, hi

def nor_cell(VP, R, mode, seed, xt=0.0, dark=True):
    """lamp A fed from VP through R, shunted by LDR lit by lamp B (B always lit or dark by force)."""
    el = [('R', 'VP', 'a', R), ('L', 'a', 'GND', 'A'), ('LDR', 'a', 'GND', 'S', ['B']),
          ('R', 'VP', 'b', 300e3), ('L', 'b', 'GND', 'B')]
    out = {}
    for bl in (0, 1):
        n = Net(el, {'VP': 0}, mode=mode, seed=seed, xtalk=xt, dark=dark)
        # B is forced: lit (bl=1) or dark (bl=0) by removing/adding its feed through the driver
        vs = {'VP': VP * n.VP / 250.0 if False else n.VP}
        if bl: n.set_lamps(['B'])
        # force B state by fixing: dark case -> disconnect by making B unable to strike (Vs huge)
        if not bl: n.L[n.lname['B']]['Vs'] = 1e9
        settle(n, vs, 1.5)
        out[bl] = (n.lit('A'), n.I[n.lname['A']], n.Vl[n.lname['A']])
    return out

if __name__ == '__main__':
    print('Lamp memory (one lamp + bias R): bias window over lamp ranges, Vb 55-65, Iext 20-100 uA, Vs 85-105')
    for Rb in (20e3, 35e3, 50e3, 80e3):
        lo, hi = window(Rb)
        print('  Rb=%3.0fk: hold-lit needs Vth>=%.1f V, hold-dark needs Vth<=%.1f V, window %.1f V wide, mid %.1f V (+-%.1f%%)'
              % (Rb / 1e3, lo, hi, hi - lo, (hi + lo) / 2, 100 * (hi - lo) / 2 / ((hi + lo) / 2)))
    Rb = 35e3
    lo, hi = window(Rb)
    for VB in (lo - 2, lo + 1, (lo + hi) / 2, hi - 1, hi + 2):
        ok = 0; N = 60
        for s in range(N): ok += memory_lamp(VB, Rb, 'vertex', s)
        print('  VB=%.1f V: bistable at %d/%d vertex corners' % (VB, ok, N))
    print('Inverter/NOR cell (lamp from VP=250 V through R, shunted by LDR lit by lamp B):')
    for R in (220e3, 330e3, 470e3):
        for mode in ('nom', 'vertex'):
            worst = None
            for s in range(1 if mode == 'nom' else 200):
                o = nor_cell(250.0, R, mode, s)
                good = (o[0][0] is True) and (o[1][0] is False)
                if worst is None or not good: worst = (good, o, s)
                if not good: break
            print('  R=%3.0fk %-7s ok=%s  B dark: A lit=%s I=%.2f mA; B lit: A lit=%s V=%.1f V'
                  % (R / 1e3, mode, worst[0], worst[1][0][0], worst[1][0][1] * 1e3, worst[1][1][0], worst[1][1][2]))
