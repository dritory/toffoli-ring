"""Machine A: verified two-instruction skip-flag machine, switch-level,
explicit two-phase simulation with true master-slave dynamic storage
(see storage.py for why a single capacitor does not work).

State: S (the slave capacitor) stores flag directly (flag=1 means "skip
pending"). T_S is a PMOS gated by S, so it conducts (execute enabled)
when S=0 -- this costs nothing extra over an NMOS and lets the network's
natural NAND-stack inversion land on the right polarity for the buffer
in storage.py with only one inverter needed overall.

Eval network (always live, every phase, exactly as the orchestrator's
correction requires -- no phase-gating smuggled into T_S/T_o/T_obar/T_r):
  T_S (PMOS, gate=S)   a=K         b=GND     -- conducts iff flag=0
  T_o                  gate=o      a=MOVE_P_N b=K
  T_obar               gate=obar   a=MOVE_M_N b=K
  T_r                  gate=r      a=DNODE    b=K
  R: MOVE_P_N->VDD, MOVE_M_N->VDD, DNODE->VDD

  MOVE_P_N = NAND(flagbar, o)      -> move+ strobe = NOT(MOVE_P_N) = flagbar & o
  MOVE_M_N = NAND(flagbar, obar)   -> move- strobe = NOT(MOVE_M_N) = flagbar & obar
  DNODE    = NAND(flagbar, r)      -> this is flagbar_next; fed to the
                                       master-slave cell in storage.py,
                                       whose one buffering inversion turns
                                       it back into flag_next for S.
  toggle strobe (active LOW on the bare wire S; abstractly
  toggle = NOT(S) = flagbar) -- 0 extra components, same as before.

Total components: eval network (4 transistors: T_S,T_o,T_obar,T_r; 3
resistors) + storage cell (3 transistors, 1 resistor, 2 capacitors) =
7 transistors, 4 resistors, 2 capacitors, 0 diodes = 13.
"""
import storage

EVAL_TRANSISTORS = [
    ('S', 'K', 'GND', 'p'),   # T_S, PMOS: conducts iff S(=flag)==0
    ('o', 'MOVE_P_N', 'K'),   # T_o
    ('obar', 'MOVE_M_N', 'K'),  # T_obar
    ('r', 'DNODE', 'K'),     # T_r
]
EVAL_RESISTORS = [
    ('MOVE_P_N', 1),
    ('MOVE_M_N', 1),
    ('DNODE', 1),
]

COMPONENTS = dict(
    transistors=len(EVAL_TRANSISTORS) + storage.STORAGE_COST['transistors'],
    resistors=len(EVAL_RESISTORS) + storage.STORAGE_COST['resistors'],
    capacitors=storage.STORAGE_COST['capacitors'],
    diodes=0,
)

def tick(flag_S, M_prev, o, r):
    """One tick, both phases explicitly simulated.
    flag_S: current slave value (flag, 1=skip pending).
    M_prev: current master capacitor value (only matters if phi1 were
            ever not fully asserted; kept for completeness/rigor).
    Returns (toggle, move_plus, move_minus, flag_S_next, M_next)."""
    obar = 1 - o
    ef = {'o': o, 'obar': obar, 'r': r}

    net1, M_next = storage.phase1(EVAL_TRANSISTORS, EVAL_RESISTORS, ef, flag_S)
    toggle = 1 - flag_S              # sampled from the stable, pre-write S
    move_plus = 1 - net1['MOVE_P_N']
    move_minus = 1 - net1['MOVE_M_N']

    net2, S_next = storage.phase2(EVAL_TRANSISTORS, EVAL_RESISTORS, ef, M_next)

    return toggle, move_plus, move_minus, S_next, M_next

def truth_table():
    """All (o, r, flag) combos."""
    rows = []
    for o in (0, 1):
        for r in (0, 1):
            for flag in (0, 1):
                toggle, mp, mm, flag_next, _ = tick(flag, 0, o, r)
                if flag:
                    exp_toggle, exp_mp, exp_mm, exp_nf = 0, 0, 0, 0
                else:
                    exp_toggle, exp_mp, exp_mm, exp_nf = 1, o, 1 - o, r
                ok = (toggle, mp, mm, flag_next) == (exp_toggle, exp_mp, exp_mm, exp_nf)
                rows.append((o, r, flag, toggle, mp, mm, flag_next, ok))
    return rows

if __name__ == '__main__':
    print("Machine A components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Machine A truth table: %d/%d combos correct" % (len(rows) - len(bad), len(rows)))
    for r in bad:
        print("MISMATCH", r)
