"""Machine B: reference 4-op machine (FLIP, NEXT, PREV, SKIPZ), dual-rail
opcode from program memory, single-rail data tape. Same corrected
two-phase master-slave storage as machine_a.py (see storage.py).

Opcode encoding (b1,b0): FLIP=00 NEXT=01 PREV=10 SKIPZ=11.
State: S (slave) stores flag directly; T_S is a PMOS gated by S
(conducts iff flag=0). r is single-rail; the SKIPZ chain's last switch
is a PMOS gated directly by r (conducts iff r=0) -- an ordinary MOSFET,
no separate inverter needed to test r==0.

Eval network (always live):
  T_S (PMOS,gate=S)      a=K          b=GND
  T2 gate=b1bar  a=TOGGLE_N  b=N1     T3 gate=b0bar  a=N1  b=K
  T4 gate=b1bar  a=MOVE_P_N  b=N2     T5 gate=b0     a=N2  b=K
  T6 gate=b1     a=MOVE_M_N  b=N3     T7 gate=b0bar  a=N3  b=K
  T8 gate=b1     a=DNODE     b=N4     T9 gate=b0     a=N4  b=N5
  T10 (PMOS) gate=r  a=N5  b=K                -- conducts iff r=0
  R: TOGGLE_N,MOVE_P_N,MOVE_M_N,DNODE -> VDD

  TOGGLE_N=NAND(flagbar,is_FLIP)   -> toggle  = NOT(TOGGLE_N)  = flagbar & is_FLIP
  MOVE_P_N=NAND(flagbar,is_NEXT)   -> move+   = NOT(MOVE_P_N)  = flagbar & is_NEXT
  MOVE_M_N=NAND(flagbar,is_PREV)   -> move-   = NOT(MOVE_M_N)  = flagbar & is_PREV
  DNODE   =NAND(flagbar,is_SKIPZ,r==0) -> fed to storage.py's master-slave
                                            cell, which buffers/inverts it
                                            back into flag_next for S.

Total components: eval network (10 transistors: T_S + 8 decode NMOS +
1 PMOS-on-r; 4 resistors) + storage cell (3 transistors, 1 resistor, 2
capacitors) = 13 transistors, 5 resistors, 2 capacitors, 0 diodes = 20.
"""
import storage

TRANSISTORS = [
    ('S', 'K', 'GND', 'p'),            # T_S shared, PMOS
    ('b1bar', 'TOGGLE_N', 'N_tog1'),   # is_FLIP chain
    ('b0bar', 'N_tog1', 'K'),
    ('b1bar', 'MOVE_P_N', 'N_mp1'),    # is_NEXT chain
    ('b0', 'N_mp1', 'K'),
    ('b1', 'MOVE_M_N', 'N_mm1'),       # is_PREV chain
    ('b0bar', 'N_mm1', 'K'),
    ('b1', 'DNODE', 'N_d1'),           # is_SKIPZ & (r==0) chain
    ('b0', 'N_d1', 'N_d2'),
    ('r', 'N_d2', 'K', 'p'),           # PMOS: conducts iff r==0
]
RESISTORS = [
    ('TOGGLE_N', 1),
    ('MOVE_P_N', 1),
    ('MOVE_M_N', 1),
    ('DNODE', 1),
]

OPCODE = {'FLIP': (0, 0), 'NEXT': (0, 1), 'PREV': (1, 0), 'SKIPZ': (1, 1)}

COMPONENTS = dict(
    transistors=len(TRANSISTORS) + storage.STORAGE_COST['transistors'],
    resistors=len(RESISTORS) + storage.STORAGE_COST['resistors'],
    capacitors=storage.STORAGE_COST['capacitors'],
    diodes=0,
)

def tick(flag_S, M_prev, op, r):
    """One tick, both phases. Returns
    (toggle, move_plus, move_minus, flag_S_next, M_next)."""
    b1, b0 = OPCODE[op]
    ef = {'b1': b1, 'b0': b0, 'b1bar': 1 - b1, 'b0bar': 1 - b0, 'r': r}

    net1, M_next = storage.phase1(TRANSISTORS, RESISTORS, ef, flag_S)
    toggle = 1 - net1['TOGGLE_N']
    move_plus = 1 - net1['MOVE_P_N']
    move_minus = 1 - net1['MOVE_M_N']

    net2, S_next = storage.phase2(TRANSISTORS, RESISTORS, ef, M_next)

    return toggle, move_plus, move_minus, S_next, M_next

def reference(flag, op, r):
    """Direct-from-spec reference (not a circuit)."""
    if flag:
        return 0, 0, 0, 0  # cleared
    if op == 'FLIP':
        return 1, 0, 0, 0
    if op == 'NEXT':
        return 0, 1, 0, 0
    if op == 'PREV':
        return 0, 0, 1, 0
    if op == 'SKIPZ':
        nf = 1 if r == 0 else 0
        return 0, 0, 0, nf
    raise ValueError(op)

def truth_table():
    rows = []
    for op in OPCODE:
        for r in (0, 1):
            for flag in (0, 1):
                got = tick(flag, 0, op, r)[:4]  # drop M_next
                exp = reference(flag, op, r)
                rows.append((op, r, flag, got, exp, got == exp))
    return rows

if __name__ == '__main__':
    print("Machine B components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
    rows = truth_table()
    bad = [row for row in rows if not row[-1]]
    print("Machine B truth table: %d/%d combos correct" % (len(rows) - len(bad), len(rows)))
    for row in bad:
        print("MISMATCH", row)
