"""Shared master-slave dynamic storage cell for the skip flag, used by
both Machine A and Machine B.

Why this exists (bug found by the orchestrator in the first pass): a
single capacitor written directly from the live eval network's own
output creates a combinational loop through the network's own gate on
that same capacitor (S <- NAND(S, r) with nothing ever isolating the
write from the read -- an oscillator, and even if it settled, using r
means it can pick up a value the CPU's own toggle already changed).

Fix: two storage nodes, never directly shorted together, plus a
non-destructive buffer between them.

  DNODE (the eval network's own output, always live, = NAND(S, ...) =
         S_next in the flagbar-of-flag convention chosen below)
    --T_wm(gate=phi1)--> M (capacitor)              [master, isolated
                                                       from DNODE the
                                                       instant phi1 ends]
    M --T_buf(gate=M, NMOS, to GND)--> BUF_NODE      [non-destructive
         + R_buf(BUF_NODE->VDD)                       read of M -- a
                                                       robustly-driven
                                                       signal, so the
                                                       next step never
                                                       shorts two
                                                       capacitors
                                                       together]
    BUF_NODE --T_ws(gate=phi2)--> S (capacitor)      [slave]

S is what the eval network reads (T_S's gate). Choosing S to store FLAG
(not flagbar) makes T_S a PMOS (conducts when S=0, i.e. execute enabled)
at no extra component cost, and DNODE (which a NAND-stack always
produces already inverted) then equals flagbar_next = NOT(flag_next)
directly with no further inversion; T_buf's inherent inversion (reading
M and producing NOT(M)) then supplies exactly the one inversion needed
to turn that back into flag_next for the slave. So the whole storage
cell needs exactly one buffering inverter, not two.

phi1, phi2 are the two non-overlapping clock phases (free, from the
drive). Component cost of this cell alone: T_wm, T_buf, T_ws (3
transistors) + R_buf (1 resistor) + C_M, C_S (2 capacitors) = 6.
"""
from switchsim import evaluate

STORAGE_TRANSISTORS = [
    ('phi1', 'DNODE', 'M'),        # T_wm
    ('M', 'BUF_NODE', 'GND'),      # T_buf (NMOS inverter, reads M non-destructively)
    ('phi2', 'BUF_NODE', 'S'),     # T_ws
]
STORAGE_RESISTORS = [
    ('BUF_NODE', 1),
]
STORAGE_COST = dict(transistors=3, resistors=1, capacitors=2, diodes=0)

def phase1(eval_transistors, eval_resistors, eval_fixed, S_prev):
    """Evaluate phase 1: eval network computes DNODE from the OLD S
    (S_prev, supplied explicitly since the slave capacitor is not
    written this phase -- T_ws's gate, phi2, is 0). T_wm's gate, phi1,
    is 1, so M is resolved by connectivity straight from DNODE. Returns
    (net_values, M_next)."""
    fixed = dict(eval_fixed)
    fixed['S'] = S_prev
    fixed['phi1'] = 1
    fixed['phi2'] = 0
    net = evaluate(eval_transistors + STORAGE_TRANSISTORS,
                    eval_resistors + STORAGE_RESISTORS, fixed)
    return net, net['M']

def phase2(eval_transistors, eval_resistors, eval_fixed, M_captured):
    """Evaluate phase 2: T_wm is open (phi1=0), so M must be supplied
    externally (M_captured, its held charge) -- nothing in this live
    phase drives it. T_ws's gate, phi2, is 1, so S is resolved by
    connectivity from BUF_NODE (which depends only on the stable M, not
    on S), and S is NOT pre-fixed: the solver derives it, and the
    'floating net' check in evaluate() would catch it if that chain were
    ever broken. Returns (net_values, S_next)."""
    fixed = dict(eval_fixed)
    fixed['M'] = M_captured
    fixed['phi1'] = 0
    fixed['phi2'] = 1
    net = evaluate(eval_transistors + STORAGE_TRANSISTORS,
                    eval_resistors + STORAGE_RESISTORS, fixed)
    return net, net['S']
