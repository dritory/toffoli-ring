"""Machine A: verified two-instruction skip-flag machine, switch-level.

State: one dynamic bit S on capacitor C_S. S == flagbar ("execute enabled").
Netlist (see machine_a_netlist.txt): a shared switch T_S gates a node K to
GND whenever S=1; three more switches (gated by o, obar, r) each finish a
path from K to an output node, giving NAND(S,x) at that node (active low
for MOVE_P_N/MOVE_M_N, and directly the correct new state for DNODE).
toggle is active-high and is just the wire S (0 components).

Per tick, given current S and this tick's (o, obar, r):
  MOVE_P_N = NAND(S, o)      -> move+ strobe = NOT(MOVE_P_N) = S & o
  MOVE_M_N = NAND(S, obar)   -> move- strobe = NOT(MOVE_M_N) = S & obar
  DNODE    = NAND(S, r)      -> next S (written into C_S) = DNODE
  toggle strobe = S

This matches the reference definition exactly: flagbar=S, so
  toggle = flagbar; move+ = flagbar&o; move- = flagbar&obar; nf = flagbar&r
"""
from switchsim import evaluate

TRANSISTORS = [
    ('S', 'K', 'GND'),          # T_S (shared)
    ('o', 'MOVE_P_N', 'K'),     # T_o
    ('obar', 'MOVE_M_N', 'K'),  # T_obar
    ('r', 'DNODE', 'K'),        # T_r
]
RESISTORS = [
    ('MOVE_P_N', 1),
    ('MOVE_M_N', 1),
    ('DNODE', 1),
]

def tick(S, o, r):
    """One tick of the switch-level CPU. Returns (toggle, move_plus, move_minus, S_next)."""
    obar = 1 - o
    fixed = {'S': S, 'o': o, 'obar': obar, 'r': r}
    net = evaluate(TRANSISTORS, RESISTORS, fixed)
    toggle = S
    move_plus = 1 - net['MOVE_P_N']
    move_minus = 1 - net['MOVE_M_N']
    S_next = net['DNODE']
    return toggle, move_plus, move_minus, S_next

def truth_table():
    """All (o, r, flag) combos; flag = NOT S. Returns list of rows."""
    rows = []
    for o in (0, 1):
        for r in (0, 1):
            for flag in (0, 1):
                S = 1 - flag
                toggle, mp, mm, S_next = tick(S, o, r)
                nf = 1 - S_next  # new flag
                # spec
                if flag:
                    exp_toggle, exp_mp, exp_mm, exp_nf = 0, 0, 0, 0
                else:
                    exp_toggle = 1
                    exp_mp = o
                    exp_mm = 1 - o
                    exp_nf = r
                ok = (toggle, mp, mm, nf) == (exp_toggle, exp_mp, exp_mm, exp_nf)
                rows.append((o, r, flag, toggle, mp, mm, nf, ok))
    return rows

def run_circuit(prog, phys, p):
    """prog: string of 'A'/'B' (o=1 for A, o=0 for B). phys: list of 0/1 cells (mutated).
    p: pointer. Returns final pointer. Mirrors run_l0's semantics but via the
    switch-level circuit tick() function instead of the reference formula."""
    n = len(phys)
    S = 1  # flag=0 initially -> execute enabled
    for ch in prog:
        o = 1 if ch == 'A' else 0
        r = phys[p]
        toggle, mp, mm, S_next = tick(S, o, r)
        if toggle:
            phys[p] ^= 1
        if mp:
            p = (p + 1) % n
        if mm:
            p = (p - 1) % n
        S = S_next
    flag_final = 1 - S
    if flag_final:
        raise AssertionError("flag left set at end of program")
    return p

if __name__ == '__main__':
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Machine A truth table: %d/%d combos correct" % (len(rows) - len(bad), len(rows)))
    if bad:
        for r in bad:
            print("MISMATCH", r)
