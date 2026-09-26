"""Master-slave dynamic storage WITHOUT a buffering inverter.

tier4.md's storage.py needs a buffer (T_buf + R_buf) between M and S only
because it chose the slave S to store `flag`, while the eval network's
NAND-stack naturally produces DNODE = flagbar_next -- an extra inversion
was needed to get back to flag_next.

Here S stores `g = flagbar` directly instead. Then:
  g_next = NOT(flag_next) = (g==1) ? NOT(r) : 1 = NAND(g, r)
and NAND(g, r) is exactly what the eval network's NAND-stack (gated by
g instead of flag) already produces as DNODE (see machine_a11.py). So
DNODE == g_next with NO further inversion needed, and M can be wired
straight to S with a plain transmission transistor -- no buffer, no
R_buf.

  DNODE --T_wm(gate=phi1)--> M (capacitor)
  M --T_ws(gate=phi2)--> S (capacitor)         [direct transfer, M is a
                                                 fixed/held value by the
                                                 time phi2 closes, since
                                                 T_wm has already opened
                                                 -- no capacitor-to-
                                                 capacitor path is ever
                                                 live at the same time as
                                                 the network still
                                                 driving it, and S's
                                                 resolution depends only
                                                 on the M-S union, never
                                                 on what the still-live
                                                 network computes for
                                                 DNODE this phase, so no
                                                 loop -- verified by
                                                 running this through
                                                 switchsim.evaluate()]

Cost: T_wm, T_ws (2 transistors) + C_M, C_S (2 capacitors) = 4.
(tier4.md's storage.py cost 6: 3 transistors + 1 resistor + 2 capacitors.)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate

STORAGE_TRANSISTORS = [
    ('phi1', 'DNODE', 'M'),   # T_wm
    ('phi2', 'M', 'S'),       # T_ws -- direct transfer, no buffer
]
STORAGE_RESISTORS = []
STORAGE_COST = dict(transistors=2, resistors=0, capacitors=2, diodes=0)

def phase1(eval_transistors, eval_resistors, eval_fixed, S_prev):
    """S (the slave) is NOT written this phase (T_ws's gate phi2=0), so it
    is supplied externally (S_prev, its held charge) exactly like
    storage.py does. T_wm closed (phi1=1): M := DNODE, computed from the
    old, stable S_prev."""
    fixed = dict(eval_fixed)
    fixed['S'] = S_prev
    fixed['phi1'] = 1
    fixed['phi2'] = 0
    net = evaluate(eval_transistors + STORAGE_TRANSISTORS,
                    eval_resistors + STORAGE_RESISTORS, fixed)
    return net, net['M']

def phase2(eval_transistors, eval_resistors, eval_fixed, M_captured):
    """T_wm open (phi1=0): M supplied externally (held charge), isolated
    from the still-live network. T_ws closed (phi2=1): S is derived by
    connectivity, resolving straight to M_captured (S is never
    pre-fixed here -- the 'floating net' check in evaluate() would catch
    it if this chain broke)."""
    fixed = dict(eval_fixed)
    fixed['M'] = M_captured
    fixed['phi1'] = 0
    fixed['phi2'] = 1
    net = evaluate(eval_transistors + STORAGE_TRANSISTORS,
                    eval_resistors + STORAGE_RESISTORS, fixed)
    return net, net['S']
