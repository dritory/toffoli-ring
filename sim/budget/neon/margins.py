"""Static (DC) margins of the neon CPU over random vertex corners of all parameter ranges.
For each of the 40 logic cases (S, opcode, r, phi2) the settled post-state is solved with the
expected lamps lit and the LDR conductances at their steady values for that lighting.
  hold   : I_lamp / Iext for every lamp that must be lit           (need > 1)
  strike : V_open - (Vs + dark_dv) for every lamp that must be lit  (need > 0, V)
           (V_open = voltage across the lamp forced off, same lighting)
  quench : Vb - V_open for every lamp that must be dark             (need > 0, V)
  nostrike: Vs - V_open, same lamps (primed lamps, no dark effect)   (need > 0, V)
  Imax   : highest lit-lamp current (mA)"""
import sys, os, random, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'blockskip'))
import ref as R
from model import Net, I_NOM
from cpu import netlist, DRIVERS

def expected_lamps(S, name, r, phi, variant):
    op = R.encode(name)
    on = set()
    on.add('LS' if S else 'LSb')
    if r: on.add('Lr')
    if phi and op['K'] and not r: on.add('LK')
    if not S:
        for nm, o in (('LF', 'F'), ('LN', 'N'), ('LP', 'P')):
            if op[o]: on.add(nm)
    # post-state of the flip: K & r=0 & phi2 sets S; MK resets
    if phi and op['K'] and not r: on.discard('LSb'); on.discard('LS'); on.add('LS')
    if op['MK']: on.discard('LS'); on.add('LSb')
    if variant != 'clamp' and phi and op['MK']: on.add('LM')
    if not S or (phi and op['K'] and not r):
        pass
    # strobes are suppressed by the post-state S
    Spost = 'LS' in on
    for nm in ('LF', 'LN', 'LP'):
        if Spost: on.discard(nm)
    return on

def settle_dc(net, vs, on):
    net.on = [l['name'] in on for l in net.L]
    for k in range(len(net.L)): net.I[k] = 0.0
    for _ in range(40):
        net.solve(vs)
        Gold = list(net.G)
        for k, l in enumerate(net.LDR): net.G[k] = net._gtarget(l, net.I)
        if max(abs(a - b) / b for a, b in zip(Gold, net.G)) < 1e-6: break
    net.solve(vs)

def margins_for(net, variant, tally, sample_tag):
    VP = net.VP
    for S in (0, 1):
        for name in R.OPS:
            op = R.encode(name)
            for r in (0, 1):
                for phi in (0, 1):
                    on = expected_lamps(S, name, r, phi, variant)
                    vs = dict(VP=VP, PHI=VP * phi, F=VP * op['F'], N=VP * op['N'], P=VP * op['P'],
                              K=VP * op['K'], MB=VP * (1 - op['MK']), r=VP * r, MK=VP * op['MK'])
                    vs = {k: v for k, v in vs.items() if k in net.dnames}
                    settle_dc(net, vs, on)
                    Gfix = list(net.G)
                    for k, l in enumerate(net.L):
                        nm = l['name']
                        if nm in on:
                            hold = net.I[k] / l['Iext']
                            tally['hold'].append((hold, nm, S, name, r, phi))
                            tally['Imax'].append((net.I[k] * 1e3, nm, S, name, r, phi))
                            net.on[k] = False; net.solve(vs); Vo = net.Vl[k]; net.on[k] = True
                            tally['strike'].append((Vo - (l['Vs0'] + l['dv']), nm, S, name, r, phi))
                            net.solve(vs)
                        else:
                            Vo = net.Vl[k]
                            tally['quench'].append((l['Vb'] - Vo, nm, S, name, r, phi))
                            tally['nostrike'].append((l['Vs0'] - Vo, nm, S, name, r, phi))

def run(variant='clamp', N=300, xtalk=0.0, seed0=0, Rsrc=1e3, over=None, VP=250.0, I=0.5e-3):
    tally = {k: [] for k in ('hold', 'strike', 'quench', 'nostrike', 'Imax')}
    E = netlist(variant, VP, I)
    drv = {d: (0 if d == 'VP' else Rsrc) for d in DRIVERS if d != 'MK' or variant != 'clamp'}
    for s in range(N):
        mode = 'nom' if s == 0 else 'vertex'
        net = Net(E, drv, mode=mode, seed=seed0 + s, xtalk=xtalk, dark=True, over=over, VP=VP)
        margins_for(net, variant, tally, s)
    out = {}
    for k, v in tally.items():
        out[k] = max(v) if k == 'Imax' else min(v)
    return out

if __name__ == '__main__':
    from cpu import DESIGN
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    for I, rd in ((DESIGN['I'], 1e6), (1.0e-3, 1e6), (DESIGN['I'], 0.5e6), (1.0e-3, 0.5e6)):
        for xt in (0.0, 1e-6, 3e-6, 1e-5):
            o = run('clamp', N, xtalk=xt, VP=DESIGN['VP'], I=I, over=dict(Rd=rd) if rd < 1e6 else None)
            print('I=%.2f mA Rdark>=%.1fM xtalk %.0e:' % (I * 1e3, rd / 1e6 if rd < 1e6 else 1.0, xt),
                  ' | '.join('%s %.1f (%s S%d %s r%d phi%d)' % ((k, o[k][0]) + o[k][1:]) for k in o), flush=True)
