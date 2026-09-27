"""Pure-MOSFET, fewest-transistor Machine A: Trick 3's structure (master
folded into the eval network's own DNODE, slave latch) unchanged, with
every one of the 6 resistors in
`sim/budget/static/machine_static_trick3.py` replaced 1:1 by a weak
PMOS keeper (gate tied to GND, so permanently ON, weakly pulling its
net to VDD) -- this is the direct "no resistors allowed" conversion:
switchsim.evaluate_static's "a closed transistor always beats a
resistor" rule was already exactly the strong-beats-weak ratioed rule
this module's evaluator (`cmos_sim.evaluate_cmos_static`) enforces
explicitly, so nothing about Trick3's topology or timing needed to
change -- only each resistor's realization.

Every transistor that used to just be gated normally (T_S, T_o, T_obar,
T_r, T_en, Tm1, Tm2, T_ph2, Ts1, Ts2, T_wset, T_ph2a, T_wreset, T_ph2b)
is 'strong' (an NMOS write/pull-down device in the sense the brief
means it); every new keeper (KP_MOVE_P, KP_MOVE_M, KP_DNODE, KP_MBAR,
KP_S, KP_SBAR) is a 'weak' PMOS, gate tied to GND.

Total: 20 transistors (14 strong NMOS + 6 weak PMOS), 0 resistors, 0
capacitors, 0 diodes -- same total component count as Trick3 (20), now
with the resistor budget spent as transistors instead, as the fewest-
transistor pure-MOSFET realization of that same structure.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cmos_sim import evaluate_cmos_static

def build_transistors():
    return [
        # -- eval network (unchanged topology from Trick3) --
        ('S', 'K', 'EN', 'n', 'strong'),          # T_S
        ('phi1', 'EN', 'GND', 'n', 'strong'),     # T_en
        ('o', 'MOVE_P_N', 'K', 'n', 'strong'),    # T_o
        ('obar', 'MOVE_M_N', 'K', 'n', 'strong'), # T_obar
        ('r', 'DNODE', 'K', 'n', 'strong'),       # T_r
        # -- master (folds into DNODE) --
        ('DNODE', 'MBAR', 'GND', 'n', 'strong'),  # Tm2 (always live)
        ('MBAR', 'DNODE', 'MTAIL', 'n', 'strong'),# Tm1
        ('phi2', 'MTAIL', 'GND', 'n', 'strong'),  # T_ph2
        # -- slave --
        ('Sbar', 'S', 'GND', 'n', 'strong'),      # Ts1 (always live)
        ('S', 'Sbar', 'GND', 'n', 'strong'),      # Ts2 (always live)
        ('DNODE', 'Sbar', 'WTAIL_A', 'n', 'strong'),  # T_wset
        ('phi2', 'WTAIL_A', 'GND', 'n', 'strong'),    # T_ph2a
        ('MBAR', 'S', 'WTAIL_B', 'n', 'strong'),      # T_wreset
        ('phi2', 'WTAIL_B', 'GND', 'n', 'strong'),    # T_ph2b
        # -- weak PMOS keepers, one per former resistor (gate=GND -> always on) --
        ('GND', 'MOVE_P_N', 'VDD', 'p', 'weak'),  # KP_MOVE_P
        ('GND', 'MOVE_M_N', 'VDD', 'p', 'weak'),  # KP_MOVE_M
        ('GND', 'DNODE', 'VDD', 'p', 'weak'),     # KP_DNODE
        ('GND', 'MBAR', 'VDD', 'p', 'weak'),      # KP_MBAR
        ('GND', 'S', 'VDD', 'p', 'weak'),         # KP_S
        ('GND', 'Sbar', 'VDD', 'p', 'weak'),      # KP_SBAR
    ]

FEEDBACK = ['DNODE', 'MBAR', 'S', 'Sbar']

COMPONENTS = dict(transistors=20, resistors=0, capacitors=0, diodes=0)
STRONG = 14
WEAK = 6

def phase1(o, r, seed, transistors=None):
    fixed = {'o': o, 'obar': 1 - o, 'r': r, 'phi1': 1, 'phi2': 0}
    return evaluate_cmos_static(transistors or build_transistors(), fixed,
                                 FEEDBACK, seed)

def phase2(o, r, seed, transistors=None):
    fixed = {'o': o, 'obar': 1 - o, 'r': r, 'phi1': 0, 'phi2': 1}
    return evaluate_cmos_static(transistors or build_transistors(), fixed,
                                 FEEDBACK, seed)

def tick(state, o, r, transistors=None):
    n1 = phase1(o, r, state, transistors)
    g = state['S']
    toggle = g
    move_plus = 1 - n1['MOVE_P_N']
    move_minus = 1 - n1['MOVE_M_N']
    n2 = phase2(o, r, n1, transistors)
    next_state = {k: n2[k] for k in FEEDBACK}
    return toggle, move_plus, move_minus, next_state

def truth_table(transistors=None):
    rows = []
    for o in (0, 1):
        for r in (0, 1):
            for flag in (0, 1):
                g = 1 - flag
                state = {'S': g, 'Sbar': 1 - g, 'DNODE': g, 'MBAR': 1 - g}
                toggle, mp, mm, nstate = tick(state, o, r, transistors)
                g_next = nstate['S']
                flag_next = 1 - g_next
                if flag:
                    exp = (0, 0, 0, 0)
                else:
                    exp = (1, o, 1 - o, r)
                got = (toggle, mp, mm, flag_next)
                rows.append((o, r, flag, got, exp, got == exp))
    return rows

if __name__ == '__main__':
    print("cmos-ratioed machine components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()),
          "(%d strong NMOS + %d weak PMOS)" % (STRONG, WEAK))
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Truth table: %d/%d correct" % (len(rows) - len(bad), len(rows)))
    for r in bad:
        print("MISMATCH", r)
