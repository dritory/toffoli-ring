"""(1) Why the phi2 tail: opcode lines change non-simultaneously at a tick
boundary.  Skip mode, F falling while MK rising (transient F=MK=1):
unclocked -> S is reset early and a strobe pulses; clocked -> phi2=0 in
the window, nothing happens.
(2) Local minimality: remove every subset (size 1..3) of the components and
re-run the truth table (+ short random check); a simulator error (floating
net, contention, oscillation) counts as 'breaks'."""
import itertools, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R
from machine_nmos import Machine, build, FEEDBACK
from switchsim import evaluate_static
from test_nmos import truth_table, run_pair

def transient(clocked):
    m = Machine(clocked)
    op = {'F': 1, 'N': 0, 'P': 0, 'K': 0, 'MK': 1}   # overlap of F falling / MK rising
    fixed = dict(op); fixed['r'] = 0; fixed['phi2'] = 0
    n = evaluate_static(m.T, m.R, fixed, FEEDBACK, {'Q': 1, 'Qb': 0})
    return 'Q=%d toggle_strobe=%d' % (n['Q'], 1 - n['TGN'])

def works(T, Rr, clocked):
    m = Machine(clocked, T, Rr)
    try:
        n, bad = truth_table(m)
        if bad: return False
        rng = random.Random(1)
        for _ in range(60):
            L = rng.randint(4, 9)
            prog = [R.encode(rng.choice(R.OPS)) for _ in range(L)]
            ok, _ = run_pair(m, prog, [rng.randint(0, 1) for _ in range(5)], 0, 0, 30)
            if not ok: return False
        return True
    except Exception:
        return False

def minimality(clocked, kmax=3):
    T, Rr = build(clocked)
    items = [('T', i) for i in range(len(T))] + [('R', i) for i in range(len(Rr))]
    res = {}
    for k in range(1, kmax + 1):
        surv = []
        for sub in itertools.combinations(range(len(items)), k):
            drop = set(items[j] for j in sub)
            T2 = [t for i, t in enumerate(T) if ('T', i) not in drop]
            R2 = [t for i, t in enumerate(Rr) if ('R', i) not in drop]
            if works(T2, R2, clocked): surv.append(sub)
        res[k] = surv
    return len(items), res

if __name__ == '__main__':
    print('transient F=MK=1 in skip mode, phi2=0:')
    print('  clocked  :', transient(True))
    print('  unclocked:', transient(False))
    for c in (True, False):
        n, res = minimality(c)
        print('clocked' if c else 'noclk', 'components', n,
              {k: len(v) for k, v in res.items()}, 'surviving removals (k: count)')
