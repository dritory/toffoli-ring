"""Skip-one NMOS: truth table over both master seeds + removal minimality."""
import itertools, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R
from machine_nmos_skip1 import Machine, build
from test_nmos import run_pair

def tt(m):
    for S in (0, 1):
        for D in (0, 1):
            for name in R.OPS:
                for r in (0, 1):
                    op = R.encode(name)
                    m.st = {'S': S, 'Sbar': 1 - S, 'DNODE': D, 'MBAR': 1 - D}
                    if tuple(m.tick(S, op, r)) != tuple(R.tick_skip1(S, op, r)):
                        return False
    return True

def works(T, Rr):
    m = Machine(T, Rr)
    try:
        if not tt(m): return False
        rng = random.Random(2)
        for _ in range(40):
            L = rng.randint(4, 9)
            prog = [R.encode(rng.choice(R.OPS)) for _ in range(L)]
            m = Machine(T, Rr)
            ok, _ = run_pair(m, prog, [rng.randint(0, 1) for _ in range(5)], 0, 0, 30, R.tick_skip1)
            if not ok: return False
        return True
    except Exception:
        return False

if __name__ == '__main__':
    T, Rr = build()
    print('full design works:', works(T, Rr))
    items = [('T', i) for i in range(len(T))] + [('R', i) for i in range(len(Rr))]
    for k in (1, 2, 3):
        surv = 0
        for sub in itertools.combinations(range(len(items)), k):
            d = set(items[j] for j in sub)
            if works([t for i, t in enumerate(T) if ('T', i) not in d],
                     [t for i, t in enumerate(Rr) if ('R', i) not in d]):
                surv += 1
        print('components', len(items), 'k=%d removable subsets: %d' % (k, surv))
