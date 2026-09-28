"""Behavioural reference simulator for the jump ISA (both variants), and
the program-ring/data-ring harness used to run whole hand-written
programs. This module is pure Python booleans -- no transistors -- and
is the ground truth `test_machine_jump*.py` checks the switch-level
circuit against.

ISA (single-level variant), 7 instructions, one-hot opcode:
  FLIP   (F)  toggle data bit
  NEXT   (N)  move data pointer +1
  PREV   (P)  move data pointer -1
  SKIPZ  (K)  skip next instruction iff r==0
  JB     (JB) seek backward to nearest MARK
  JF     (JF) seek forward to nearest MARK
  MARK   (MK) no-op marker / seek target

CPU state: SF (seeking forward), SB (seeking backward), SK (one-tick
skip pending). At most one is ever set -- enforced by construction, not
assumed. "normal" = none set.

Labelled variant: MARK/JB/JF also carry an L-bit label (opcode['A'], an
int 0..2**L-1). A seek stops only at a MARK whose label equals the
label the JB/JF that started the seek was carrying (latched into a
target-label register TL when the seek starts). Adds TL to the state.

Both tick() functions share one external interface, the same one
`machine_jump.tick`/`machine_jump_labeled.tick` implement in switches:
  tick(state, opcode, r) -> (toggle, move_plus, move_minus,
                              prog_plus, prog_minus, next_state)
opcode is a dict with keys 'F','N','P','K','JF','JB','MK' (0/1), plus
'A' (int) for the labelled variant.
"""

OPS = ['F', 'N', 'P', 'K', 'JF', 'JB', 'MK']

ALIAS = {'FLIP': 'F', 'NEXT': 'N', 'PREV': 'P', 'SKIPZ': 'K',
         'JF': 'JF', 'JB': 'JB', 'MARK': 'MK'}

def encode(mnemonic, label=0):
    """mnemonic (full name or short OPS code) -> one-hot opcode dict
    (+ label field 'A')."""
    op = ALIAS.get(mnemonic, mnemonic)
    assert op in OPS, mnemonic
    d = {k: (1 if k == op else 0) for k in OPS}
    d['A'] = label
    return d

# ---------------------------------------------------------------- single-level

def initial_state():
    return {'SF': 0, 'SB': 0, 'SK': 0}

def tick(state, opcode, r):
    SF, SB, SK = state['SF'], state['SB'], state['SK']
    F, N, P, K = opcode['F'], opcode['N'], opcode['P'], opcode['K']
    JF, JB, MK = opcode['JF'], opcode['JB'], opcode['MK']
    normal = (not SF) and (not SB) and (not SK)

    toggle = 1 if (normal and F) else 0
    move_plus = 1 if (normal and N) else 0
    move_minus = 1 if (normal and P) else 0
    prog_plus = 0
    prog_minus = 0
    SF_next = SB_next = SK_next = 0

    if normal:
        if JB:
            prog_minus = 1
            SB_next = 1
        else:
            prog_plus = 1
            if JF:
                SF_next = 1
            elif K and r == 0:
                SK_next = 1
    elif SF:
        prog_plus = 1
        SF_next = 0 if MK else 1
    elif SB:
        if MK:
            prog_plus = 1
            SB_next = 0
        else:
            prog_minus = 1
            SB_next = 1
    elif SK:
        prog_plus = 1

    next_state = {'SF': SF_next, 'SB': SB_next, 'SK': SK_next}
    return toggle, move_plus, move_minus, prog_plus, prog_minus, next_state

# -------------------------------------------------------------------- labelled

def initial_state_labeled(L=2):
    return {'SF': 0, 'SB': 0, 'SK': 0, 'TL': 0}

def tick_labeled(state, opcode, r):
    SF, SB, SK, TL = state['SF'], state['SB'], state['SK'], state['TL']
    F, N, P, K = opcode['F'], opcode['N'], opcode['P'], opcode['K']
    JF, JB, MK, A = opcode['JF'], opcode['JB'], opcode['MK'], opcode['A']
    normal = (not SF) and (not SB) and (not SK)

    toggle = 1 if (normal and F) else 0
    move_plus = 1 if (normal and N) else 0
    move_minus = 1 if (normal and P) else 0
    prog_plus = 0
    prog_minus = 0
    SF_next = SB_next = SK_next = 0
    TL_next = TL

    if normal:
        if JB:
            prog_minus = 1
            SB_next = 1
            TL_next = A
        else:
            prog_plus = 1
            if JF:
                SF_next = 1
                TL_next = A
            elif K and r == 0:
                SK_next = 1
    elif SF:
        prog_plus = 1
        match = MK and (A == TL)
        SF_next = 0 if match else 1
    elif SB:
        match = MK and (A == TL)
        if match:
            prog_plus = 1
            SB_next = 0
        else:
            prog_minus = 1
            SB_next = 1
    elif SK:
        prog_plus = 1

    next_state = {'SF': SF_next, 'SB': SB_next, 'SK': SK_next, 'TL': TL_next}
    return toggle, move_plus, move_minus, prog_plus, prog_minus, next_state

# --------------------------------------------------------- whole-machine runner

def run(tick_fn, state0, program, data, prog_p0, data_p0, max_ticks,
        io=None):
    """Drive `tick_fn` (either the reference tick/tick_labeled, or a
    switch-level machine's tick) against a program ring (`program`, a
    list of opcode dicts) and a data ring (`data`, a list of 0/1 bits,
    mutated in place), for up to `max_ticks` ticks. Returns
    (final_state, prog_p, data_p, ticks_used). `io` is an optional
    callback io(tick_no, data, data_p) for live-I/O demos (echo)."""
    state = state0
    prog_p = prog_p0
    data_p = data_p0
    n_prog = len(program)
    n_data = len(data)
    for t in range(max_ticks):
        opcode = program[prog_p]
        r = data[data_p]
        toggle, mp, mm, pp, pm, state = tick_fn(state, opcode, r)
        if toggle:
            data[data_p] ^= 1
        if mp:
            data_p = (data_p + 1) % n_data
        if mm:
            data_p = (data_p - 1) % n_data
        if pp:
            prog_p = (prog_p + 1) % n_prog
        if pm:
            prog_p = (prog_p - 1) % n_prog
        if io:
            io(t, data, data_p)
    return state, prog_p, data_p, max_ticks
