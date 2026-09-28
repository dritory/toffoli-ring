"""Switch-level, fully complementary CMOS implementation of the
single-level jump ISA (FLIP/NEXT/PREV/SKIPZ/JB/JF/MARK). Built entirely
from gatelib's _inv/_aoi/_regbit -- the same NAND/TG/latch primitives
machine_cmos_full.py uses -- reusing evaluate_cmos_static for
switch-level evaluation. No ratioed fights anywhere (every device
'strong'; the strength field is kept only because evaluate_cmos_static
requires it).

Opcode encoding: 7 bits, one-hot (F,N,P,K,JF,JB,MK), each supplied by
the program ring in both polarities (interface, excluded from the
transistor count) -- see results/budget/jump.md for why one-hot (wide,
free ring bits) beats a dense binary encoding (narrow, but needs a real
3-to-8 decoder inside the counted CPU).

CPU state: 3 bits (SF, SB, SK), each one machine_cmos_full-style
master-slave latch (16T). At most one is ever 1; enforced by the
next-state logic itself (see jump_ref.tick, which this circuit mirrors
term-for-term), not merely assumed.

Data memory interface: read bit `r` only (single rail -- 'as before').
`rbar` is derived on-chip (1 inverter) since SKIPZ needs it.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cmos'))
from gatelib import _inv, _aoi, _and_true, _sop_true, _regbit
from cmos_sim import evaluate_cmos_static

OPS = ['F', 'N', 'P', 'K', 'JF', 'JB', 'MK']

def build_transistors():
    t = []
    t += _inv('r', 'rbar')

    t_sf, fb_sf = _regbit('SF_COMB', 'SF')
    t_sb, fb_sb = _regbit('SB_COMB', 'SB')
    t_sk, fb_sk = _regbit('SK_COMB', 'SK')
    t += t_sf + t_sb + t_sk

    norm = ['SF_SB', 'SB_SB', 'SK_SB']  # current-state complements (free from the latches)

    # next-state
    t += _sop_true([norm + ['JF'], ['SF_S', 'MKbar']], 'SF_COMB')
    t += _sop_true([norm + ['JB'], ['SB_S', 'MKbar']], 'SB_COMB')
    t += _sop_true([norm + ['K', 'rbar']], 'SK_COMB')

    # data-memory strobes
    t += _and_true(norm + ['F'], 'toggle')
    t += _and_true(norm + ['N'], 'move_plus')
    t += _and_true(norm + ['P'], 'move_minus')

    # program-memory strobes
    t += _sop_true([norm + ['JBbar'], ['SF_S'], ['SB_S', 'MK'], ['SK_S']], 'prog_plus')
    t += _sop_true([norm + ['JB'], ['SB_S', 'MKbar']], 'prog_minus')

    return t, fb_sf + fb_sb + fb_sk

TRANSISTORS, FEEDBACK = build_transistors()
COMPONENTS = dict(transistors=len(TRANSISTORS), resistors=0, capacitors=0, diodes=0)

def _opcode_fixed(opcode):
    d = {}
    for op in OPS:
        v = opcode[op]
        d[op] = v
        d[op + 'bar'] = 1 - v
    return d

def phase1(opcode, r, seed, transistors=None):
    fixed = _opcode_fixed(opcode)
    fixed['r'] = r
    fixed['phi1'] = 1; fixed['phi1bar'] = 0
    fixed['phi2'] = 0; fixed['phi2bar'] = 1
    return evaluate_cmos_static(transistors or TRANSISTORS, fixed, FEEDBACK, seed)

def phase2(opcode, r, seed, transistors=None):
    fixed = _opcode_fixed(opcode)
    fixed['r'] = r
    fixed['phi1'] = 0; fixed['phi1bar'] = 1
    fixed['phi2'] = 1; fixed['phi2bar'] = 0
    return evaluate_cmos_static(transistors or TRANSISTORS, fixed, FEEDBACK, seed)

def tick(state, opcode, r):
    return tick_with(state, opcode, r, TRANSISTORS)

def tick_with(state, opcode, r, transistors):
    n1 = phase1(opcode, r, state, transistors)
    toggle = n1['toggle']
    move_plus = n1['move_plus']
    move_minus = n1['move_minus']
    prog_plus = n1['prog_plus']
    prog_minus = n1['prog_minus']
    n2 = phase2(opcode, r, n1, transistors)
    next_state = {k: n2[k] for k in FEEDBACK}
    return toggle, move_plus, move_minus, prog_plus, prog_minus, next_state

def mode_of(state):
    """Convenience: (SF, SB, SK) from a full feedback-net state dict."""
    return state['SF_S'], state['SB_S'], state['SK_S']

def initial_state():
    # SF=SB=SK=0 (normal mode). Feedback nets must all be seeded
    # consistently: '_S' true, '_SB' false (Qbar), master nets follow.
    st = {}
    for pfx in ('SF', 'SB', 'SK'):
        st[pfx + '_M'] = 0; st[pfx + '_MB'] = 1
        st[pfx + '_S'] = 0; st[pfx + '_SB'] = 1
    return st

if __name__ == '__main__':
    print("machine_jump (single-level) components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
