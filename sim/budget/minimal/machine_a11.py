"""Machine A, 11-component variant: same behaviour as sim/budget/machine_a.py
(verified there at 13 components), but the slave capacitor S stores
g = flagbar (not flag), which lets the eval network's own NAND-stack
output (DNODE) land exactly on g_next with no buffering inversion
needed -- see storage_nobuf.py. Saves T_buf + R_buf (2 components) over
tier4.md's design.

Eval network (unchanged topology from machine_a.py, only S's stored
polarity and T_S's transistor kind change to match):
  T_S (NMOS, gate=S=g)  a=K        b=GND   -- conducts iff g==1 (flag==0)
  T_o                   gate=o     a=MOVE_P_N b=K
  T_obar                gate=obar  a=MOVE_M_N b=K
  T_r                    gate=r     a=DNODE   b=K
  R: MOVE_P_N->VDD, MOVE_M_N->VDD, DNODE->VDD

  MOVE_P_N = NAND(g, o)   -> move+ strobe = NOT(MOVE_P_N) = g & o
  MOVE_M_N = NAND(g, obar) -> move- strobe = NOT(MOVE_M_N) = g & obar
  DNODE    = NAND(g, r)    = g_next (see storage_nobuf.py derivation)
  toggle strobe: bare wire S=g (active high on g = flagbar), same
  0-cost polarity trick as machine_a.py's bare-wire toggle.

Total: eval (4 transistors, 3 resistors) + storage_nobuf (2 transistors,
2 capacitors) = 6 transistors, 3 resistors, 2 capacitors, 0 diodes = 11.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import storage_nobuf as storage

EVAL_TRANSISTORS = [
    ('S', 'K', 'GND'),        # T_S, NMOS: conducts iff S(=g=flagbar)==1
    ('o', 'MOVE_P_N', 'K'),   # T_o
    ('obar', 'MOVE_M_N', 'K'),  # T_obar
    ('r', 'DNODE', 'K'),      # T_r
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
    """flag_S here is g = flagbar (1 means execute enabled, i.e. flag==0).
    Returns (toggle, move_plus, move_minus, flag_S_next, M_next), all in
    the SAME g=flagbar convention for flag_S_next, so callers must track
    g, not flag, across ticks (see test_machine_a11.py for the flag<->g
    conversion at the reference-comparison boundary)."""
    obar = 1 - o
    ef = {'o': o, 'obar': obar, 'r': r}

    net1, M_next = storage.phase1(EVAL_TRANSISTORS, EVAL_RESISTORS, ef, flag_S)
    g = flag_S
    toggle = g                        # toggle iff flag==0, sampled pre-write
    move_plus = 1 - net1['MOVE_P_N']
    move_minus = 1 - net1['MOVE_M_N']

    net2, S_next = storage.phase2(EVAL_TRANSISTORS, EVAL_RESISTORS, ef, M_next)

    return toggle, move_plus, move_minus, S_next, M_next

def truth_table():
    """All (o, r, flag) combos, flag being the TRUE flag (converted to/from
    g=flagbar at the call boundary so the table reads exactly like
    machine_a.py's)."""
    rows = []
    for o in (0, 1):
        for r in (0, 1):
            for flag in (0, 1):
                g = 1 - flag
                toggle, mp, mm, g_next, _ = tick(g, 0, o, r)
                flag_next = 1 - g_next
                if flag:
                    exp_toggle, exp_mp, exp_mm, exp_nf = 0, 0, 0, 0
                else:
                    exp_toggle, exp_mp, exp_mm, exp_nf = 1, o, 1 - o, r
                ok = (toggle, mp, mm, flag_next) == (exp_toggle, exp_mp, exp_mm, exp_nf)
                rows.append((o, r, flag, toggle, mp, mm, flag_next, ok))
    return rows

if __name__ == '__main__':
    print("Machine A11 components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Machine A11 truth table: %d/%d combos correct" % (len(rows) - len(bad), len(rows)))
    for r in bad:
        print("MISMATCH", r)
