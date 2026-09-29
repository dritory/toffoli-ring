"""Gate-level word search: shortest word over a bundle menu that implements an
exact logical gate on encoded groups (S=0 in, S=0 out, all other cells
bit-for-bit restored, pointer delta as specified).  BFS over distinct
transformations (dedupe)."""
import itertools
from macro import B, run, templates

def gate_specs(d=1, d2=2):
    """name -> (positions of groups relative to cur, fn(xs)->(new xs, dptr groups))
    xs indexes groups by offset list `offs` (sorted)."""
    return {
      'NOT':   dict(offs=[0], f=lambda x: ({0: x[0] ^ 1}, 0)),
      'RESET': dict(offs=[0], f=lambda x: ({0: 0}, 0)),
      'CNOT%+d' % d: dict(offs=[0, d], f=lambda x, d=d: ({d: x[d] ^ x[0]}, 0)),
      'TOFF%+d%+d' % (d, d2): dict(offs=[0, d, d2], f=lambda x, d=d, d2=d2: ({d2: x[d2] ^ (x[0] & x[d])}, 0)),
      'CMOV+': dict(offs=[0], f=lambda x: ({0: 0}, 1) if x[0] else ({}, 0)),
      'CMOV-': dict(offs=[0], f=lambda x: ({0: 0}, -1) if x[0] else ({}, 0)),
      'NEXT': dict(offs=[0], f=lambda x: ({}, 1)),
      'PREV': dict(offs=[0], f=lambda x: ({}, -1)),
    }

def find(letters, spec, g, tab, rest, L=16, mode='a', pad=1, cap=200000, prefix=()):
    offs = spec['offs']; lo = min(offs + [0]) - pad; hi = max(offs + [0]) + pad
    # also allow room for cmov
    lo = min(lo, -1 - pad + 0) if any(k in spec.get('room', '') for k in '-') else lo
    groups = list(range(lo, hi + 1)); ng = len(groups); W = ng * g
    base = -lo * g + rest       # pointer start
    combos = list(itertools.product((0, 1), repeat=ng))
    def pack(xs):
        t = 0
        for i, x in enumerate(xs):
            for j, bit in enumerate(tab[x]): t |= bit << (i * g + j)
        return t
    init = tuple((pack(xs) << 8) | (base << 1) for xs in combos)
    exp = []
    for xs in combos:
        val = {o: xs[o - lo] for o in offs}
        upd, dp = spec['f'](val)
        xs2 = list(xs)
        for o, v in upd.items(): xs2[o - lo] = v
        exp.append((pack(xs2) << 8) | ((base + dp * g) << 1))
    exp = tuple(exp)
    for li in prefix:
        new = []
        for v in init:
            t2, p2, S2, ok = run(letters[li], v >> 8, (v >> 1) & 127, v & 1, W, mode)
            assert ok
            new.append((t2 << 8) | (p2 << 1) | S2)
        init = tuple(new)
    pre = tuple(prefix)
    if init == exp: return pre
    seen = {init: pre}; frontier = [(init, pre)]
    for depth in range(L):
        nxt = []
        for st, w in frontier:
            for li, b in enumerate(letters):
                new = []
                for v in st:
                    t2, p2, S2, ok = run(b, v >> 8, (v >> 1) & 127, v & 1, W, mode)
                    if not ok: new = None; break
                    new.append((t2 << 8) | (p2 << 1) | S2)
                if new is None: continue
                k = tuple(new)
                if k in seen: continue
                seen[k] = w + (li,)
                if k == exp: return w + (li,)
                nxt.append((k, w + (li,)))
        frontier = nxt
        if not frontier or len(seen) > cap: break
    return None

def best(letters, spec, L=16, mode='a', gmax=3, cap=30000, first=True):
    """word over encodings in order of group size (first hit if first=True,
    else shortest): (len, encname, g, rest, word)"""
    res = None
    for gg in range(1, gmax + 1):
        for name, g, tab in templates():
            if g != gg: continue
            for rest in range(g):
                w = find(letters, spec, g, tab, rest, L if res is None else min(L, res[0] - 1), mode, cap=cap)
                if w is not None and (res is None or len(w) < res[0]):
                    res = (len(w), name, g, rest, w)
                    if first: return res
    return res
