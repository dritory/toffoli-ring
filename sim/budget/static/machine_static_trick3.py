"""Capacitor-free Machine A: same two-instruction CPU as machine_a11.py
(g = flagbar convention), but with the master-slave storage rebuilt from
static (cross-coupled, resistor-load) feedback instead of capacitors --
Tricks 2 (shared clock tail) + 3 (master folded into the eval network's
own DNODE node) from the brief.

Eval network: identical to machine_a11.py, PLUS one series "enable" tail
transistor T_en (gate=phi1) inserted where T_S used to wire straight to
GND. This is what lets the master stage isolate DNODE from the eval
network during phi2 (in machine_a11 this isolation was T_wm opening
instead; here there is no T_wm -- DNODE itself IS the master node).

  T_S    gate=g       a=K        b=EN     -- (unchanged wiring otherwise)
  T_en   gate=phi1    a=EN       b=GND    -- NEW: eval network's own tail
  T_o    gate=o       a=MOVE_P_N b=K
  T_obar gate=obar    a=MOVE_M_N b=K
  T_r    gate=r       a=DNODE    b=K
  R: MOVE_P_N->VDD, MOVE_M_N->VDD, DNODE->VDD

Master (folds into DNODE, no separate master node):
  Tm2 (always live, no clock): gate=DNODE  a=MBAR  b=GND   R_MBAR: MBAR->VDD
     -- MBAR = NOT(DNODE), a plain inverter; also serves as the master's
        "other side", giving both polarities of g_next for free.
  Tm1 (feedback/hold, phi2-tail only): gate=MBAR a=DNODE b=MTAIL
  T_ph2 (Tm1's tail): gate=phi2  a=MTAIL  b=GND
     -- during phi1, T_en holds the eval chain live and Tm1 is OFF (tail
        open), so DNODE resolves purely from the fresh eval computation
        (no fight). During phi2, T_en opens (eval chain disconnected from
        GND) and Tm1's tail closes: Tm1 (gated by MBAR, which mirrors the
        phi1-final DNODE) now holds DNODE at that same value with no
        competing driver -- a real static latch, not a capacitor.

Slave (S = g, read by T_S as before), written from the master's two
already-differential nodes DNODE/MBAR, with an always-live cross-coupled
hold pair (no separate hold tail needed -- see results/budget/static.md
for why that is race-free under switchsim's ratioed rule):
  Ts1 (hold): gate=Sbar  a=S    b=GND         R_S:    S->VDD
  Ts2 (hold): gate=S     a=Sbar b=GND         R_Sbar: Sbar->VDD
  T_wset   (write S:=1 when DNODE=1): gate=DNODE a=Sbar b=WTAIL_A
  T_ph2a (its own tail): gate=phi2  a=WTAIL_A b=GND
  T_wreset (write S:=0 when MBAR=1):  gate=MBAR  a=S    b=WTAIL_B
  T_ph2b (its own tail): gate=phi2  a=WTAIL_B b=GND

Trick 2 ("share one clock transistor between set and reset") was tried
here first with ONE tail node common to both T_wset and T_wreset, and
REJECTED: switchsim caught it as a genuine race (see
results/budget/static.md, "Trick 2 finding") -- DNODE transitions one
Gauss-Seidel pass before MBAR (its own inverter's output) catches up, so
for one pass both gates can read as simultaneously true, and a literal
shared tail node bridges S to Sbar directly through it (regardless of
the clock), corrupting the hold pair. Each write transistor needs its
OWN tail transistor -- 2, not 1 -- whenever its gate is combinational
output (has gate delay), not a true primary input.

Component count: eval(4)+T_en(1) = 5 transistors, 3 resistors (eval) ;
master: Tm1,Tm2,T_ph2 = 3 transistors, R_MBAR = 1 resistor ;
slave: Ts1,Ts2,T_wset,T_ph2a,T_wreset,T_ph2b = 6 transistors, R_S,R_Sbar
= 2 resistors. TOTAL = 14 transistors + 6 resistors + 0 capacitors = 20.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate_static

def build_transistors():
    return [
        ('S', 'K', 'EN'),          # T_S -- gate is the slave net itself
        ('phi1', 'EN', 'GND'),     # T_en
        ('o', 'MOVE_P_N', 'K'),    # T_o
        ('obar', 'MOVE_M_N', 'K'), # T_obar
        ('r', 'DNODE', 'K'),       # T_r
        ('DNODE', 'MBAR', 'GND'),  # Tm2 (always live)
        ('MBAR', 'DNODE', 'MTAIL'),# Tm1
        ('phi2', 'MTAIL', 'GND'),  # T_ph2
        ('Sbar', 'S', 'GND'),      # Ts1 (always live)
        ('S', 'Sbar', 'GND'),      # Ts2 (always live)
        ('DNODE', 'Sbar', 'WTAIL_A'),  # T_wset
        ('phi2', 'WTAIL_A', 'GND'),    # T_ph2a
        ('MBAR', 'S', 'WTAIL_B'),      # T_wreset
        ('phi2', 'WTAIL_B', 'GND'),    # T_ph2b
    ]

RESISTORS = [
    ('MOVE_P_N', 1), ('MOVE_M_N', 1), ('DNODE', 1),
    ('MBAR', 1), ('S', 1), ('Sbar', 1),
]
FEEDBACK = ['DNODE', 'MBAR', 'S', 'Sbar']

COMPONENTS = dict(transistors=14, resistors=6, capacitors=0, diodes=0)

def phase1(o, r, seed):
    """phi1=1,phi2=0: T_S's gate is literally S, held stable this phase by
    the slave's own always-live hold pair (Ts1/Ts2) -- so the eval
    network reads the OLD, stable S with no external plumbing needed.
    Eval chain computes DNODE=g_next from that S and r; T_ph2/T_ph2b are
    off, so nothing writes S or the master this phase."""
    fixed = {'o': o, 'obar': 1 - o, 'r': r, 'phi1': 1, 'phi2': 0}
    known = evaluate_static(build_transistors(), RESISTORS, fixed, FEEDBACK, seed)
    return known

def phase2(o, r, seed):
    """phi1=0,phi2=1: eval chain disconnected (T_en open); master holds
    via Tm1; slave writes from DNODE/MBAR through the shared write tail."""
    fixed = {'o': o, 'obar': 1 - o, 'r': r, 'phi1': 0, 'phi2': 1}
    known = evaluate_static(build_transistors(), RESISTORS, fixed, FEEDBACK, seed)
    return known

def tick(state, o, r):
    """state: dict with DNODE,MBAR,S,Sbar (g=flagbar convention, S is what
    T_S reads). Returns (toggle, move_plus, move_minus, next_state)."""
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
                state = {'S': g, 'Sbar': 1 - g, 'DNODE': g, 'MBAR': 1 - g}
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
    print("Trick3 static machine components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Truth table: %d/%d correct" % (len(rows) - len(bad), len(rows)))
    for r in bad:
        print("MISMATCH", r)
