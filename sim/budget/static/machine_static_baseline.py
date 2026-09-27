"""Capacitor-free Machine A, Trick 5: the straightforward static
master-slave baseline (no folding of the eval network into the master --
contrast with machine_static_trick3.py). Master and slave are each a
plain resistor-load cross-coupled pair (Trick 1), always-live so they
hold with no dedicated hold-tail, written through DATA-gated pull-downs
that are each given their OWN tail transistor (see "Trick 2 finding" in
results/budget/static.md for why a shared tail is unsafe here: DNODE and
its inverter DBAR -- or M and Mbar -- can transiently coincide for one
Gauss-Seidel pass, and a literal shared tail node would bridge the two
written latch nodes together through it).

Eval network: UNCHANGED from machine_a11.py (T_S wired straight to GND,
no enable tail needed -- nothing ever writes back into DNODE here, so
there is no isolation to build).

  T_S gate=S a=K b=GND   T_o gate=o a=MOVE_P_N b=K
  T_obar gate=obar a=MOVE_M_N b=K   T_r gate=r a=DNODE b=K
  R: MOVE_P_N->VDD, MOVE_M_N->VDD, DNODE->VDD

DBAR generation (DNODE needs both polarities to write a plain SR latch;
the eval network's own NAND-stack only gives one):
  T_inv gate=DNODE a=DBAR b=GND      R_DBAR: DBAR->VDD

Master (captures DNODE during phi1):
  Tm1 gate=Mbar a=M    b=GND    (hold, always live)
  Tm2 gate=M    a=Mbar b=GND    (hold, always live)
  R_M: M->VDD   R_Mbar: Mbar->VDD
  T_wsetM   gate=DNODE a=Mbar b=WM_A   T_ph1a gate=phi1 a=WM_A b=GND
  T_wresetM gate=DBAR  a=M    b=WM_B   T_ph1b gate=phi1 a=WM_B b=GND

Slave (S = g, read by T_S; written from M/Mbar during phi2):
  Ts1 gate=Sbar a=S    b=GND    (hold, always live)
  Ts2 gate=S    a=Sbar b=GND    (hold, always live)
  R_S: S->VDD   R_Sbar: Sbar->VDD
  T_wsetS   gate=M    a=Sbar b=WS_A   T_ph2a gate=phi2 a=WS_A b=GND
  T_wresetS gate=Mbar a=S    b=WS_B   T_ph2b gate=phi2 a=WS_B b=GND

Component count: eval = 4 transistors + 3 resistors.
DBAR: 1 transistor + 1 resistor.
Master: 6 transistors (Tm1,Tm2,T_wsetM,T_ph1a,T_wresetM,T_ph1b) + 2
resistors (R_M,R_Mbar).
Slave: 6 transistors (Ts1,Ts2,T_wsetS,T_ph2a,T_wresetS,T_ph2b) + 2
resistors (R_S,R_Sbar).
TOTAL = 4+1+6+6 = 17 transistors, 3+1+2+2 = 8 resistors, 0 capacitors
= 25.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate_static

def build_transistors():
    return [
        ('S', 'K', 'GND'),           # T_S
        ('o', 'MOVE_P_N', 'K'),      # T_o
        ('obar', 'MOVE_M_N', 'K'),   # T_obar
        ('r', 'DNODE', 'K'),         # T_r
        ('DNODE', 'DBAR', 'GND'),    # T_inv
        ('Mbar', 'M', 'GND'),        # Tm1
        ('M', 'Mbar', 'GND'),        # Tm2
        ('DNODE', 'Mbar', 'WM_A'),   # T_wsetM
        ('phi1', 'WM_A', 'GND'),     # T_ph1a
        ('DBAR', 'M', 'WM_B'),       # T_wresetM
        ('phi1', 'WM_B', 'GND'),     # T_ph1b
        ('Sbar', 'S', 'GND'),        # Ts1
        ('S', 'Sbar', 'GND'),        # Ts2
        ('M', 'Sbar', 'WS_A'),       # T_wsetS
        ('phi2', 'WS_A', 'GND'),     # T_ph2a
        ('Mbar', 'S', 'WS_B'),       # T_wresetS
        ('phi2', 'WS_B', 'GND'),     # T_ph2b
    ]

RESISTORS = [
    ('MOVE_P_N', 1), ('MOVE_M_N', 1), ('DNODE', 1), ('DBAR', 1),
    ('M', 1), ('Mbar', 1), ('S', 1), ('Sbar', 1),
]
FEEDBACK = ['M', 'Mbar', 'S', 'Sbar']

COMPONENTS = dict(transistors=17, resistors=8, capacitors=0, diodes=0)

def phase1(o, r, seed):
    fixed = {'o': o, 'obar': 1 - o, 'r': r, 'phi1': 1, 'phi2': 0}
    return evaluate_static(build_transistors(), RESISTORS, fixed, FEEDBACK, seed)

def phase2(o, r, seed):
    fixed = {'o': o, 'obar': 1 - o, 'r': r, 'phi1': 0, 'phi2': 1}
    return evaluate_static(build_transistors(), RESISTORS, fixed, FEEDBACK, seed)

def tick(state, o, r):
    n1 = phase1(o, r, state)
    g = state['S']
    toggle = g
    move_plus = 1 - n1['MOVE_P_N']
    move_minus = 1 - n1['MOVE_M_N']
    n2 = phase2(o, r, n1)
    next_state = {k: n2[k] for k in FEEDBACK}
    return toggle, move_plus, move_minus, next_state

def truth_table():
    rows = []
    for o in (0, 1):
        for r in (0, 1):
            for flag in (0, 1):
                g = 1 - flag
                state = {'S': g, 'Sbar': 1 - g, 'M': g, 'Mbar': 1 - g}
                toggle, mp, mm, nstate = tick(state, o, r)
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
    print("Baseline static machine components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Truth table: %d/%d correct" % (len(rows) - len(bad), len(rows)))
    for r in bad:
        print("MISMATCH", r)
