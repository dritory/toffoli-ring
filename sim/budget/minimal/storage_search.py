"""Bounded exhaustive search over the STORAGE SUBSYSTEM only: can flag
survive a tick using fewer than 4 components (2 capacitors + 2 isolation
transistors)? The eval network (machine_a11's EVAL_TRANSISTORS/RESISTORS,
producing DNODE = NAND(g, r), g=flagbar) is held fixed -- this is the
same network for any storage scheme, since it is what defines "the flag
must survive the phase in which it is recomputed" per the task. Only the
storage wiring around DNODE/S(/M) varies.

Net alphabet for the storage subsystem: {DNODE, phi1, phi2, S} plus,
only in the 2-capacitor sub-search, {M}. This is a genuine restriction
(a general search would also let the storage wiring introduce brand new
intermediate nets) -- documented, not hidden: seeArraignment "scope"
notes in results/budget/minimal.md.

Subclass A (1 capacitor: only S holds charge, no M):
  budget b in {1,2,3} extra components (transistors + <=1 resistor on S).
  Enumerate every transistor list of length 1..b (kind in n/p, gate/a/b
  in the 4-net alphabet, a!=b, gate can repeat a net), plus 0 or 1 extra
  resistor on S, subject to total component count == b.
  For each candidate: run all 8 (o,r,flag) truth-table cases AND a
  2-tick sequential check (does it stay correct over 2 ticks in a row,
  the earliest point a same-node race can show up), via switchsim's
  strict evaluator (require_all_gates=True, so any hidden storage or
  floating net raises).

Subclass B (2 capacitors: S and M, direct or buffered transfer):
  budget b in {1,2} transistors (no resistor -- a bare capacitor-to-
  capacitor path never needs one), gate in {phi1,phi2}, connecting
  DNODE/M/S in the 3 non-trivial ways. Confirms 2 is necessary (b=1
  fails) and finds the b=2 no-buffer solution used in machine_a11.py.
"""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate
sys.path.insert(0, os.path.dirname(__file__))
import machine_a11 as MA

EVAL_T = MA.EVAL_TRANSISTORS
EVAL_R = MA.EVAL_RESISTORS

def run_candidate(storage_transistors, storage_resistors):
    """Try this storage netlist against machine_a11's eval network. S
    stores g=flagbar (as machine_a11 does). Returns (ok, reason) over the
    full truth table plus a 2-tick chase from each starting g."""
    def phase1(S_prev, o, r):
        fixed = {'o': o, 'obar': 1 - o, 'r': r, 'S': S_prev, 'phi1': 1, 'phi2': 0}
        net = evaluate(EVAL_T + storage_transistors, EVAL_R + storage_resistors,
                        fixed, holdable=frozenset(['M']))
        return net

    def phase2(M_val, o, r):
        fixed = {'o': o, 'obar': 1 - o, 'r': r, 'phi1': 0, 'phi2': 1}
        if M_val is not None:
            fixed['M'] = M_val
        net = evaluate(EVAL_T + storage_transistors, EVAL_R + storage_resistors,
                        fixed, holdable=frozenset(['M']))
        return net

    def one_tick(g, o, r):
        net1 = phase1(g, o, r)
        M_next = net1.get('M')
        net2 = phase2(M_next, o, r)
        if 'S' not in net2:
            return None, "S not resolved in phase2 (floating)"
        return net2['S'], None

    # Truth table: 8 combos, single tick from each starting g.
    for o in (0, 1):
        for r in (0, 1):
            for g in (0, 1):
                flag = 1 - g
                try:
                    g_next, err = one_tick(g, o, r)
                except ValueError as e:
                    return False, "o=%d r=%d g=%d: %s" % (o, r, g, e)
                if err:
                    return False, "o=%d r=%d g=%d: %s" % (o, r, g, err)
                exp_flag_next = 0 if flag else r
                exp_g_next = 1 - exp_flag_next
                if g_next != exp_g_next:
                    return False, "o=%d r=%d g=%d: got g_next=%s want %s" % (o, r, g, g_next, exp_g_next)

    # 2-tick chase (catches same-tick-node races that a single tick,
    # starting fresh, can't expose): run o=1,r=1 then o=1,r=0 from g=1.
    seq = [(1, 1), (1, 0), (0, 1), (0, 0)]
    g = 1
    for (o, r) in seq:
        flag = 1 - g
        try:
            g_next, err = one_tick(g, o, r)
        except ValueError as e:
            return False, "seq @ flag=%d o=%d r=%d: %s" % (flag, o, r, e)
        if err:
            return False, "seq: %s" % err
        exp_flag_next = 0 if flag else r
        exp_g_next = 1 - exp_flag_next
        if g_next != exp_g_next:
            return False, "seq mismatch"
        g = g_next
    return True, None

def subclass_a(budget):
    """1 capacitor (S only). nets: DNODE, phi1, phi2, S. Transistor count
    1..budget, kinds n/p, at most 1 extra resistor on S, total == budget."""
    nets = ['DNODE', 'phi1', 'phi2', 'S']
    winners = []
    tried = 0
    for n_t in range(1, budget + 1):
        n_r = budget - n_t
        if n_r > 1:
            continue  # never try more than 1 resistor
        # all ordered (gate,a,b,kind) tuples with a != b
        base = [(g, a, b, k) for g in nets for a in nets for b in nets
                 for k in ('n', 'p') if a != b]
        for combo in itertools.product(base, repeat=n_t):
            tried += 1
            resistors = [('S', 1)] if n_r == 1 else []
            ok, reason = run_candidate(list(combo), resistors)
            if ok:
                winners.append((combo, resistors))
    return tried, winners

def subclass_b(budget):
    """2 capacitors (S, M). nets: DNODE, phi1, phi2, M, S. No resistor
    (direct capacitor-to-capacitor style only). Transistor count ==
    budget exactly."""
    nets = ['DNODE', 'phi1', 'phi2', 'M', 'S']
    gates = ['phi1', 'phi2']
    tried = 0
    winners = []
    base = [(g, a, b) for g in gates for a in nets for b in nets if a != b]
    for combo in itertools.product(base, repeat=budget):
        tried += 1
        ok, reason = run_candidate(list(combo), [])
        if ok:
            winners.append(combo)
    return tried, winners

if __name__ == '__main__':
    print("=== Subclass A: 1 capacitor (S only), budget = extra components ===")
    for b in (1, 2, 3):
        tried, winners = subclass_a(b)
        print("budget=%d: tried %d candidates, winners=%d" % (b, tried, len(winners)))
        for w in winners[:5]:
            print("   ", w)

    print()
    print("=== Subclass B: 2 capacitors (S, M), budget = transistor count ===")
    for b in (1, 2):
        tried, winners = subclass_b(b)
        print("budget=%d: tried %d candidates, winners=%d" % (b, tried, len(winners)))
        for w in winners[:5]:
            print("   ", w)
