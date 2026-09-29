"""Netlist verification for a bundle menu: truth table + 500 random programs
tick by tick against ref_tick; then baseline programs via macros."""
import random, sys
from nmos_gen import *
from translate import Derived, lockstep
import programs as P
from macro import templates

def truth(m):
    bad = 0; clean = True
    for S in (0, 1):
        for i, b in enumerate(m.menu):
            for r in (0, 1):
                got, cl = m.tick(S, i, r)
                bad += got != ref_tick(b, S, r); clean &= cl
    return bad, clean

def random_progs(m, n=500, seed=20260929, ticks=80):
    rng = random.Random(seed); fails = 0; K = len(m.menu)
    for _ in range(n):
        L = rng.randint(4, 14); nd = rng.randint(3, 10)
        ring = [rng.randrange(K) for _ in range(L)]
        d1 = [rng.randint(0, 1) for _ in range(nd)]; d2 = list(d1)
        p1 = p2 = rng.randrange(nd); S1 = S2 = 0; pp = rng.randrange(L)
        for t in range(ticks):
            b = m.menu[ring[pp]]
            a = ref_tick(b, S1, d1[p1]); c, _ = m.tick(S2, ring[pp], d2[p2])
            if a != c: fails += 1; break
            if a[0]: d1[p1] ^= 1
            if c[0]: d2[p2] ^= 1
            p1 = (p1 + a[1] - a[2]) % nd; p2 = (p2 + c[1] - c[2]) % nd
            S1, S2 = a[3], c[3]; pp = (pp + 1) % L
            if d1 != d2 or p1 != p2: fails += 1; break
    return n, fails

def report(name, menu, words=None, enc=None):
    m = Machine(menu)
    try: bad, clean = truth(m)
    except ValueError:
        print(f'{name}: {m.counts()} single-latch netlist RACES (mark+test letter needs master/slave)'); return m
    n, f = random_progs(m)
    print(f'{name}: {m.counts()} truth-table mismatches {bad}, strobes glitch-free {clean}, random {n-f}/{n}')
    return m
