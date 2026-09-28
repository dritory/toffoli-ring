"""Switch-level, fully complementary CMOS implementation of the
LABELLED jump ISA: MARK/JB/JF each carry an L=2-bit label (A1,A0,
supplied by the ring in both polarities, same convention as the
one-hot opcode bits). A seek stops only at a MARK whose label equals
the label the JB/JF that started the seek carried -- this is what lets
loops nest. The started-seek's label is latched into a 2-bit
target-label register TL when the JB/JF executes, held for the whole
seek (TL never changes mid-seek, since LOAD is only asserted in normal
mode), and compared (XNOR, 2 bits) against the current instruction's
label field on every seek tick.

Same opcode one-hot (F,N,P,K,JF,JB,MK) and same 3-bit mode state
(SF,SB,SK) as machine_jump.py; only the "is this MARK the one we
want" test changes, from a bare MK literal to MK & (A==TL), and the
2-bit TL register is added.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cmos'))
from gatelib import _inv, _aoi, _and_true, _sop_true, _regbit
from cmos_sim import evaluate_cmos_static

OPS = ['F', 'N', 'P', 'K', 'JF', 'JB', 'MK']
L = 2  # label width

def build_transistors():
    t = []
    t += _inv('r', 'rbar')

    t_sf, fb_sf = _regbit('SF_COMB', 'SF')
    t_sb, fb_sb = _regbit('SB_COMB', 'SB')
    t_sk, fb_sk = _regbit('SK_COMB', 'SK')
    t_tl1, fb_tl1 = _regbit('TL1_COMB', 'TL1')
    t_tl0, fb_tl0 = _regbit('TL0_COMB', 'TL0')
    t += t_sf + t_sb + t_sk + t_tl1 + t_tl0

    norm = ['SF_SB', 'SB_SB', 'SK_SB']

    # label compare: EQi = NOT(Ai XOR TLi_S), true polarity directly from
    # the AOI (its two terms are exactly XOR's two satisfying cases).
    t += _aoi([['A1', 'TL1_SB'], ['A1bar', 'TL1_S']], 'EQ1')
    t += _aoi([['A0', 'TL0_SB'], ['A0bar', 'TL0_S']], 'EQ0')
    t += _inv('EQ1', 'EQ1bar')
    t += _inv('EQ0', 'EQ0bar')

    # next-state: "MATCH" (MK & EQ1 & EQ0) replaces the unlabelled
    # variant's bare MK; "not MATCH" = MKbar | EQ1bar | EQ0bar is an OR,
    # so each term that used to carry a bare MKbar literal is split into
    # 3 terms (one per disjunct) -- ordinary sum-of-products expansion.
    t += _sop_true([norm + ['JF'],
                    ['SF_S', 'MKbar'], ['SF_S', 'EQ1bar'], ['SF_S', 'EQ0bar']],
                   'SF_COMB')
    t += _sop_true([norm + ['JB'],
                    ['SB_S', 'MKbar'], ['SB_S', 'EQ1bar'], ['SB_S', 'EQ0bar']],
                   'SB_COMB')
    t += _sop_true([norm + ['K', 'rbar']], 'SK_COMB')

    t += _and_true(norm + ['F'], 'toggle')
    t += _and_true(norm + ['N'], 'move_plus')
    t += _and_true(norm + ['P'], 'move_minus')

    t += _sop_true([norm + ['JBbar'], ['SF_S'],
                    ['SB_S', 'MK', 'EQ1', 'EQ0'], ['SK_S']], 'prog_plus')
    t += _sop_true([norm + ['JB'],
                    ['SB_S', 'MKbar'], ['SB_S', 'EQ1bar'], ['SB_S', 'EQ0bar']],
                   'prog_minus')

    # target-label register: TLi_next = LOAD ? Ai : TLi  (LOAD = normal
    # mode & (JF|JB), i.e. a J instruction just executed)
    t += _aoi([norm + ['JF'], norm + ['JB']], 'LOAD_bar')
    t += _inv('LOAD_bar', 'LOAD')
    t += _sop_true([['LOAD', 'A1'], ['LOAD_bar', 'TL1_S']], 'TL1_COMB')
    t += _sop_true([['LOAD', 'A0'], ['LOAD_bar', 'TL0_S']], 'TL0_COMB')

    return t, fb_sf + fb_sb + fb_sk + fb_tl1 + fb_tl0

TRANSISTORS, FEEDBACK = build_transistors()
COMPONENTS = dict(transistors=len(TRANSISTORS), resistors=0, capacitors=0, diodes=0)

def _opcode_fixed(opcode):
    d = {}
    for op in OPS:
        v = opcode[op]
        d[op] = v; d[op + 'bar'] = 1 - v
    A = opcode['A']
    a1, a0 = (A >> 1) & 1, A & 1
    d['A1'] = a1; d['A1bar'] = 1 - a1
    d['A0'] = a0; d['A0bar'] = 1 - a0
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
    return state['SF_S'], state['SB_S'], state['SK_S']

def label_of(state):
    return (state['TL1_S'] << 1) | state['TL0_S']

def initial_state():
    st = {}
    for pfx in ('SF', 'SB', 'SK', 'TL1', 'TL0'):
        st[pfx + '_M'] = 0; st[pfx + '_MB'] = 1
        st[pfx + '_S'] = 0; st[pfx + '_SB'] = 1
    return st

if __name__ == '__main__':
    print("machine_jump_labeled components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
