import sys
from translate import *
from nmos_gen import Machine
import programs as P
from analyze_k import parse_b

def net_tick(m):
    def f(b, S, r):
        idx = m.menu.index(b)
        got, _ = m.tick(S, idx, r); return got
    return f

def measure(menu, words, g, tab, rest, use_net=True):
    D = Derived(menu, words, g, tab, rest); m = Machine(menu)
    fn = net_tick(m) if use_net else None
    out = {}
    def clen(prog): return sum(len(D.words[{'FLIP':'FLIP','NEXT':'NEXT','PREV':'PREV','IFZ':'IF','MARK':'END'}[i]]) for i in prog)
    # counter
    prog = P.counter_prog(); lg = [0] + [1] * 8
    lockstep(D, prog, lg, 0, passes=300 if not use_net else 40, tick_fn=fn)
    out['counter'] = (len(prog), clen(prog))
    prog = P.echo_prog(); lg = [0, 1]
    lockstep(D, prog, lg, 0, passes=20, tick_fn=fn); out['echo'] = (len(prog), clen(prog))
    # copy 8 bits: layout d0 s0 d1 s1 ..
    prog = P.copy_prog(); lg = [0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]
    lockstep(D, prog, lg, 0, passes=8, tick_fn=fn); out['copy'] = (len(prog), clen(prog))
    # BB(2,2): 6 TM steps
    prog = P.bb22_prog(); d, dp = P.bb22_tape(6)
    lockstep(D, prog, d, dp, passes=6, tick_fn=fn); out['bb22'] = (len(prog), clen(prog))
    return out
if __name__ == '__main__':
    tabs = {n: (g, t) for n, g, t in templates()}
    M1 = [parse_b(s) for s in ('(+K)', '(P)', '(T0)', '(F,M)')]
    g, tab = tabs['none']
    print(measure(M1, dict(FLIP=(3, 1), NEXT=(1,), PREV=(3, 1, 3), IF=(2,), END=(0,)), g, tab, 0))
