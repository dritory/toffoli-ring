"""Behavioural reference for the block-skip ISA (and the skip-one variant).

ISA: FLIP NEXT PREV IFZ MARK, one-hot opcode dict with keys F,N,P,K,MK
(K = IFZ).  One state bit S (skip mode).  Program ring advances +1 every
tick (so there is no prog_plus/prog_minus output).

  block-skip:  S=0: F->toggle, N->move_plus, P->move_minus,
                    K & r==0 -> S'=1; MK no-op.
               S=1: everything suppressed; MK -> S'=0 (MK itself a no-op).
  skip-one:    S=0: as above, S'=1 iff K & r==0.
               S=1: the instruction is suppressed (including a K), S'=0.

tick(S, op, r) -> (toggle, move_plus, move_minus, S')
"""
OPS = ['F', 'N', 'P', 'K', 'MK']
ALIAS = {'FLIP': 'F', 'NEXT': 'N', 'PREV': 'P', 'IFZ': 'K', 'MARK': 'MK'}

def encode(m):
    op = ALIAS.get(m, m)
    assert op in OPS, m
    return {k: int(k == op) for k in OPS}

def tick(S, op, r):
    if S:
        return 0, 0, 0, (0 if op['MK'] else 1)
    return op['F'], op['N'], op['P'], int(bool(op['K']) and r == 0)

def tick_skip1(S, op, r):
    if S:
        return 0, 0, 0, 0
    return op['F'], op['N'], op['P'], int(bool(op['K']) and r == 0)

def step(tick_fn, S, prog, pp, data, dp):
    """One machine tick on ring `prog` (list of opcode dicts) and cyclic
    `data`; mutates data; returns (S, pp, dp)."""
    t, mp, mm, S = tick_fn(S, prog[pp], data[dp])
    if t: data[dp] ^= 1
    if mp: dp = (dp + 1) % len(data)
    if mm: dp = (dp - 1) % len(data)
    return S, (pp + 1) % len(prog), dp
