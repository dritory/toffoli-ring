"""Bundle machine with block-skip semantics and exact-macro search.

Bundle = ordered sub-ops from {F flip, T0/T1 skip-test (set S' iff cell==v at
that moment), P/M move +1/-1} plus an optional MARK flag.  Tick-level guard as
in sim/twoop: S is sampled at fetch.
  S=1, no mark : bundle suppressed, S stays 1 (block skip).
  S=1, mark    : mode 'a': S:=0, rest of the bundle suppressed (marker tick).
                 mode 'b': S:=0 and the bundle then runs as if S were 0.
  S=0          : ops run in order; a test sets S'=1; mark is a no-op.
Macro requirements (window = current group +- `half` groups, all logical
assignments):  FLIP NEXT PREV IF(skip iff x==0) act exactly when S=0 (S'=0 for
FLIP/NEXT/PREV) and are TRANSPARENT when S=1 (tape, pointer unchanged, S stays
1, i.e. no mark letter can be executed inside a block body).  END = MARK
macro: S=1 -> identity, S'=0; S=0 -> identity, S'=0.
"""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'twoop'))
from enc import ENCODINGS

class B:
    def __init__(self, ops, mark=False):
        self.ops, self.mark = tuple(ops), mark
    def __repr__(self):
        s = ','.join(self.ops) + ('+K' if self.mark else '')
        return '(' + s + ')' if s else 'nop'
    def key(self): return (self.ops, self.mark)

def all_bundles():
    out = []
    for f in (0, 1):
        for t in (None, 'T0', 'T1'):
            for m in (None, 'P', 'M'):
                items = [x for x in ('F' if f else None, t, m) if x]
                seen = set()
                for perm in itertools.permutations(items):
                    if perm in seen: continue
                    seen.add(perm)
                    for k in (False, True):
                        if not perm and not k: continue
                        out.append(B(perm, k))
    return out

def run(b, tape, ptr, S, W, mode='a'):
    if S:
        if not b.mark: return tape, ptr, 1, True
        if mode == 'a': return tape, ptr, 0, True
    S2 = 0
    for op in b.ops:
        if op == 'F': tape ^= 1 << ptr
        elif op[0] == 'T':
            if ((tape >> ptr) & 1) == int(op[1]): S2 = 1
        else:
            ptr += 1 if op == 'P' else -1
            if ptr < 0 or ptr >= W: return 0, 0, 0, False
    return tape, ptr, S2, True

def templates():
    """all (g, f) with f(x)->tuple; closed under complement of x, deduped."""
    seen, out = set(), []
    for name, (g, f) in ENCODINGS.items():
        for comp in (0, 1):
            tab = tuple(f(x ^ comp) for x in (0, 1))
            if (g, tab) in seen: continue
            seen.add((g, tab)); out.append((name + ('~' if comp else ''), g, tab))
    return out

PRIMS = ('FLIP', 'NEXT', 'PREV', 'IF', 'END')

def search(letters, g, tab, rest, L=8, half=1, mode='a', want=PRIMS):
    """BFS over words on `letters` (list of B), dedupe by transformation.
    Returns {prim: word(tuple of letter idx) or None}."""
    ng = 2 * half + 1; W = ng * g; p0 = half * g + rest
    combos = list(itertools.product((0, 1), repeat=ng))
    def pack(xs):
        t = 0
        for i, x in enumerate(xs):
            for j, bit in enumerate(tab[x]): t |= bit << (i * g + j)
        return t
    inits = [pack(xs) for xs in combos]
    cur = half
    conds = [(t, p0, S) for t in inits for S in (0, 1)]
    found = {p: None for p in want}
    def check(word, states):
        for prim in want:
            if found[prim] is not None: continue
            ok = True
            for idx, xs in enumerate(combos):
                t0, s0, s1 = inits[idx], states[2 * idx], states[2 * idx + 1]
                x = xs[cur]
                if prim == 'END':
                    if s0 != (t0, p0, 0) or s1 != (t0, p0, 0): ok = False; break
                    continue
                if s1 != (t0, p0, 1): ok = False; break
                if prim == 'FLIP':
                    xs2 = list(xs); xs2[cur] ^= 1
                    exp = (pack(xs2), p0, 0)
                elif prim == 'NEXT': exp = (t0, p0 + g, 0)
                elif prim == 'PREV': exp = (t0, p0 - g, 0)
                else: exp = (t0, p0, int(x == 0))
                if s0 != exp: ok = False; break
            if ok: found[prim] = word
    seen = {tuple(conds): ()}
    frontier = [((), tuple(conds))]
    for depth in range(1, L + 1):
        nxt = []
        for word, st in frontier:
            for li, b in enumerate(letters):
                new = []
                for (t, p, S) in st:
                    t2, p2, S2, ok = run(b, t, p, S, W, mode)
                    if not ok: new = None; break
                    new.append((t2, p2, S2))
                if new is None: continue
                key = tuple(new)
                if key in seen: continue
                w = word + (li,); seen[key] = w
                check(w, key); nxt.append((w, key))
        frontier = nxt
        if all(found[p] is not None for p in want) or not frontier: break
    return found

def search_all_enc(letters, L=8, half=1, mode='a', want=PRIMS, gmax=3):
    """Try every (encoding, rest); return list of (encname, g, rest, found)
    where all `want` prims found (shortest total length first)."""
    good = []
    for name, g, tab in templates():
        if g > gmax: continue
        for rest in range(g):
            f = search(letters, g, tab, rest, L, half, mode, want)
            if all(v is not None for v in f.values()):
                good.append((sum(len(v) for v in f.values()), name, g, rest, f))
    good.sort(key=lambda z: z[0])
    return good
