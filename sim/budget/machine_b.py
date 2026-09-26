"""Machine B: reference 4-op machine (FLIP, NEXT, PREV, SKIPZ), dual-rail
opcode from program memory, single-rail data tape (no dual-rail tape
needed). Switch-level, dynamic storage for the skip flag.

Opcode encoding (b1,b0): FLIP=00 NEXT=01 PREV=10 SKIPZ=11.
State: S on capacitor C_S, S == flagbar ("execute enabled").

r is single-rail from memory. Rather than build a separate inverter to
get rbar, the SKIPZ chain's last switch is a PMOS gated directly by r
(a PMOS conducts when its gate is LOW, i.e. when r=0) -- an ordinary
MOSFET, still one component, so this needs no extra transistor or
resistor at all versus an NMOS+inverter.

Netlist (see machine_b_netlist.txt): a shared switch T_S gates K to GND
when S=1. Four decode chains each add 2-3 more series switches from K to
an output node:
  TOGGLE_N  <- b1bar, b0bar     (is_FLIP)   => strobe = S & is_FLIP
  MOVE_P_N  <- b1bar, b0        (is_NEXT)   => strobe = S & is_NEXT
  MOVE_M_N  <- b1,   b0bar      (is_PREV)   => strobe = S & is_PREV
  DNODE     <- b1,   b0, r(PMOS)(is_SKIPZ & r==0) => S_next = DNODE directly
"""
from switchsim import evaluate

TRANSISTORS = [
    ('S', 'K', 'GND'),                 # T_S shared
    ('b1bar', 'TOGGLE_N', 'N_tog1'),   # is_FLIP chain
    ('b0bar', 'N_tog1', 'K'),
    ('b1bar', 'MOVE_P_N', 'N_mp1'),    # is_NEXT chain
    ('b0', 'N_mp1', 'K'),
    ('b1', 'MOVE_M_N', 'N_mm1'),       # is_PREV chain
    ('b0bar', 'N_mm1', 'K'),
    ('b1', 'DNODE', 'N_d1'),           # is_SKIPZ & (r==0) chain
    ('b0', 'N_d1', 'N_d2'),
    ('r', 'N_d2', 'K', 'p'),           # PMOS: conducts when r==0
]
RESISTORS = [
    ('TOGGLE_N', 1),
    ('MOVE_P_N', 1),
    ('MOVE_M_N', 1),
    ('DNODE', 1),
]

OPCODE = {'FLIP': (0, 0), 'NEXT': (0, 1), 'PREV': (1, 0), 'SKIPZ': (1, 1)}

def tick(S, op, r):
    """One tick. op in {'FLIP','NEXT','PREV','SKIPZ'}. Returns
    (toggle, move_plus, move_minus, S_next)."""
    b1, b0 = OPCODE[op]
    fixed = {'S': S, 'b1': b1, 'b0': b0, 'b1bar': 1 - b1, 'b0bar': 1 - b0, 'r': r}
    net = evaluate(TRANSISTORS, RESISTORS, fixed)
    toggle = 1 - net['TOGGLE_N']
    move_plus = 1 - net['MOVE_P_N']
    move_minus = 1 - net['MOVE_M_N']
    S_next = net['DNODE']
    return toggle, move_plus, move_minus, S_next

def reference(S, op, r):
    """Direct-from-spec reference (not a circuit): flag=1-S.
    if flag: do nothing, clear flag.
    else: FLIP toggles; NEXT/PREV move; SKIPZ sets flag iff r==0."""
    flag = 1 - S
    if flag:
        return 0, 0, 0, 1  # S_next=1 (flag cleared)
    if op == 'FLIP':
        return 1, 0, 0, 1
    if op == 'NEXT':
        return 0, 1, 0, 1
    if op == 'PREV':
        return 0, 0, 1, 1
    if op == 'SKIPZ':
        nf = 1 if r == 0 else 0
        return 0, 0, 0, 1 - nf
    raise ValueError(op)

def truth_table():
    rows = []
    for op in OPCODE:
        for r in (0, 1):
            for flag in (0, 1):
                S = 1 - flag
                got = tick(S, op, r)
                exp = reference(S, op, r)
                rows.append((op, r, flag, got, exp, got == exp))
    return rows

if __name__ == '__main__':
    rows = truth_table()
    bad = [row for row in rows if not row[-1]]
    print("Machine B truth table: %d/%d combos correct" % (len(rows) - len(bad), len(rows)))
    for row in bad:
        print("MISMATCH", row)
