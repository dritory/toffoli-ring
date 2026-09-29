"""Compile baseline programs (FLIP NEXT PREV IFZ MARK) to a flat bundle menu
via exact macros, run both machines in lock step (whole encoded tape, pointer,
S compared after every baseline instruction), count ticks."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'blockskip'))
from nmos_gen import ref_tick
import ref as BR
from macro import B, templates

PR = ['FLIP', 'NEXT', 'PREV', 'IFZ', 'END']
class Derived:
    def __init__(self, menu, words, g, tab, rest):
        self.menu, self.words, self.g, self.tab, self.rest = menu, words, g, tab, rest
    def enc(self, logical):
        t = []
        for x in logical: t += list(self.tab[x])
        return t
    def compile(self, prog):
        m = {'FLIP': 'FLIP', 'NEXT': 'NEXT', 'PREV': 'PREV', 'IFZ': 'IF', 'MARK': 'END'}
        return [self.words[m[i]] for i in prog]

def lockstep(D, prog, logical, dp, passes=1, tick_fn=None):
    """returns ticks used; asserts equivalence"""
    tick_fn = tick_fn or ref_tick
    n = len(logical); phys = D.enc(logical); ptr = dp * D.g + D.rest; S = 0
    ring = BR_ring = [BR.encode(i) for i in prog]
    lg = list(logical); ldp = dp; lS = 0; ticks = 0
    words = D.compile(prog); N = len(phys)
    for _ in range(passes):
        for op, w in zip(ring, words):
            t, mp, mm, lS = BR.tick(lS, op, lg[ldp])
            if t: lg[ldp] ^= 1
            ldp = (ldp + mp - mm) % n
            for li in w:
                b = D.menu[li]
                tg, p, m_, S = tick_fn(b, S, phys[ptr])
                if tg: phys[ptr] ^= 1
                ptr = (ptr + p - m_) % N; ticks += 1
            assert phys == D.enc(lg), ('tape', prog[:3])
            assert ptr == ldp * D.g + D.rest and S == lS, ('ptr/S', ptr, ldp, S, lS)
    return ticks
