"""Removal minimality (all subsets of size 1..3) for the CMOS block-skip CPU.
Transmission-gate halves are expected survivors only if the ideal switch
model cannot tell a lone pass transistor from a TG (documented caveat)."""
import itertools, random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R
from machine_cmos import Machine, build
from test_nmos import truth_table, run_pair

def works(T, strobes):
    try:
        m = Machine(strobes, T)
        if truth_table(m)[1]: return False
        rng = random.Random(3)
        for _ in range(40):
            prog = [R.encode(rng.choice(R.OPS)) for _ in range(rng.randint(4, 9))]
            if not run_pair(m, prog, [rng.randint(0, 1) for _ in range(5)], 0, 0, 30)[0]: return False
        return True
    except Exception:
        return False

for strobes in ('tg', 'gate'):
    T = build(strobes); out = {}
    for k in (1, 2, 3):
        surv = [s for s in itertools.combinations(range(len(T)), k)
                if works([t for i, t in enumerate(T) if i not in s], strobes)]
        out[k] = surv
    print(strobes, len(T), {k: len(v) for k, v in out.items()}, out[1])
