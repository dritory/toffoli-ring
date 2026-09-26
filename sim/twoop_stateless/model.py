"""
Stateless two-instruction pointer-machine model (HANDOVER-B.md section 6).

Machine: cyclic bit tape, one pointer, no flag, no other CPU state.
An instruction ("bundle") is at most one flip (toggle cell under pointer) and
at most one move (+1 or -1; unconditional or conditional on the cell under
the pointer AT THE MOMENT the move is evaluated), in either order:

  order 'FM' (flip then move): flip happens first (on the cell at the
      pointer's current position), then the move condition is evaluated on
      the (now-flipped) cell at that same position, then the pointer moves.
  order 'MF' (move then flip): the move condition is evaluated on the
      cell at the pointer's current position (pre-flip), the pointer moves
      (or doesn't), then the cell under the pointer *now* (the arrival cell,
      which is the same cell if the move didn't fire) is flipped.

A bundle is represented as a 4-tuple (flip: bool, direction: +1|-1,
cond: None|0|1, order: None|'FM'|'MF'); order is meaningless (and ignored)
when flip is False, and 'order' only distinguishes FM vs MF when both a
flip and a move are present.
"""

import itertools

CONDS = (None, 0, 1)


def gen_bundles(direction):
    """All 9 bundles carrying a move in the given direction (+1 or -1)."""
    out = []
    for cond in CONDS:
        out.append((False, direction, cond, None))   # no flip
        out.append((True, direction, cond, 'FM'))     # flip, then move
        out.append((True, direction, cond, 'MF'))     # move, then flip
    return out


def bundle_str(b):
    flip, d, cond, order = b
    move = ('+1' if d == 1 else '-1') + ('' if cond is None else f'?{cond}')
    if not flip:
        return move
    if order == 'FM':
        return f'flip;{move}'
    else:
        return f'{move};flip'


def gen_pairs():
    """
    Candidate pairs per section 6: one bundle carries +1, the other -1,
    at least one move is conditional, at least one bundle has a flip.
    Returns list of (A, B) bundle tuples. A always carries the +1 move,
    B always carries the -1 move (word letters are still just 'A'/'B'
    strings; which physical direction each stands for is recorded here).
    """
    plus = gen_bundles(+1)
    minus = gen_bundles(-1)
    pairs = []
    for A in plus:
        for B in minus:
            condA, condB = A[2], B[2]
            flipA, flipB = A[0], B[0]
            if condA is None and condB is None:
                continue  # need at least one conditional move
            if not flipA and not flipB:
                continue  # need at least one flip
            pairs.append((A, B))
    return pairs


def apply_letter(bundle, tape, ptr):
    """
    Apply one bundle to (tape: list[int], ptr: int) in place on `tape`.
    Returns (tape, new_ptr) on success, or None if the pointer would leave
    the tape array bounds (used by callers as the "left the window" signal).
    """
    flip, d, cond, order = bundle
    n = len(tape)
    if flip and order == 'FM':
        tape[ptr] ^= 1
        cell = tape[ptr]
        if cond is None or cell == cond:
            new_ptr = ptr + d
            if new_ptr < 0 or new_ptr >= n:
                return None
            ptr = new_ptr
        return tape, ptr
    elif flip and order == 'MF':
        cell = tape[ptr]
        if cond is None or cell == cond:
            new_ptr = ptr + d
            if new_ptr < 0 or new_ptr >= n:
                return None
            ptr = new_ptr
        tape[ptr] ^= 1
        return tape, ptr
    else:
        cell = tape[ptr]
        if cond is None or cell == cond:
            new_ptr = ptr + d
            if new_ptr < 0 or new_ptr >= n:
                return None
            ptr = new_ptr
        return tape, ptr


# ---------------------------------------------------------------------
# Encodings
# ---------------------------------------------------------------------
# A pattern is a tuple of length g over {'x','n','0','1'}:
#   'x' = the logical data bit itself
#   'n' = the complement of the logical data bit (dual-rail partner cell)
#   '0','1' = fixed constant cell
# The same pattern is used, verbatim, in every group on the tape (no phase
# bit / position dependence).

def gen_encodings():
    """
    Returns list of (family, g, pattern) covering:
      none (g=1); dual-rail complementary (x,n) and (n,x); dual-rail with
      a constant (x,1),(1,x),(x,0),(0,x); period-3 with one data cell and
      two constants, all 4 base arrangements x all 3 rotations.
    Rest position is NOT included here; callers loop rest in range(g).
    """
    enc = []
    enc.append(('none', 1, ('x',)))
    for patt in [('x', 'n'), ('n', 'x')]:
        enc.append(('dual', 2, patt))
    for patt in [('x', '1'), ('1', 'x'), ('x', '0'), ('0', 'x')]:
        enc.append(('scratch', 2, patt))
    bases = [('x', '0', '1'), ('x', '1', '0'), ('x', '0', '0'), ('x', '1', '1')]
    for b in bases:
        for r in range(3):
            patt = b[r:] + b[:r]
            enc.append(('period3', 3, patt))
    return enc


def pattern_str(pattern):
    return '(' + ','.join(pattern) + ')'


def materialize(xval, pattern):
    out = []
    for ch in pattern:
        if ch == 'x':
            out.append(xval)
        elif ch == 'n':
            out.append(1 - xval)
        else:
            out.append(int(ch))
    return out


def decode_group(cells, pattern):
    """Decode one group's logical bit; return None if invalidly encoded."""
    xi = pattern.index('x')
    xv = cells[xi]
    for i, ch in enumerate(pattern):
        if ch == '0' and cells[i] != 0:
            return None
        if ch == '1' and cells[i] != 1:
            return None
        if ch == 'n' and cells[i] != (1 - xv):
            return None
    return xv


def decode3(tape, pattern, g):
    out = []
    for gi in range(3):
        seg = tape[gi * g:(gi + 1) * g]
        d = decode_group(seg, pattern)
        if d is None:
            return None
        out.append(d)
    return tuple(out)


TARGETS = ('FLIP', 'NEXT', 'PREV', 'CFLIP', 'CNEXT', 'CPREV')


def check_target(target, final_states, start_ptr, g, pattern, valuations):
    """final_states: list of 8 (tape_tuple, ptr), aligned with `valuations`
    (list of 8 (xl0,xm0,xr0) initial logical-bit assignments)."""
    for (tape, ptr), (xl0, xm0, xr0) in zip(final_states, valuations):
        d = decode3(tape, pattern, g)
        if d is None:
            return False
        xl1, xm1, xr1 = d
        if target == 'FLIP':
            ok = (xl1 == xl0 and xr1 == xr0 and xm1 == (1 - xm0) and ptr == start_ptr)
        elif target == 'NEXT':
            ok = (xl1 == xl0 and xm1 == xm0 and xr1 == xr0 and ptr == start_ptr + g)
        elif target == 'PREV':
            ok = (xl1 == xl0 and xm1 == xm0 and xr1 == xr0 and ptr == start_ptr - g)
        elif target == 'CFLIP':
            ok = (xl1 == xl0 and xr1 == xr0 and xm1 == 0 and ptr == start_ptr)
        elif target == 'CNEXT':
            want = start_ptr + g if xm0 == 1 else start_ptr
            ok = (xl1 == xl0 and xm1 == xm0 and xr1 == xr0 and ptr == want)
        elif target == 'CPREV':
            want = start_ptr - g if xm0 == 1 else start_ptr
            ok = (xl1 == xl0 and xm1 == xm0 and xr1 == xr0 and ptr == want)
        else:
            raise ValueError(target)
        if not ok:
            return False
    return True


VALUATIONS = list(itertools.product([0, 1], repeat=3))


def initial_states(pattern, g):
    """8 (tape_tuple, ptr) states, ptr always at the window's rest cell
    for whatever `rest` the caller has chosen (caller adds rest to g)."""
    states = []
    for (xl, xm, xr) in VALUATIONS:
        tape = materialize(xl, pattern) + materialize(xm, pattern) + materialize(xr, pattern)
        states.append(tape)
    return states


def search_combo(pair, pattern, g, rest, max_len=12, early_stop=True):
    """
    BFS over words in {A,B}* up to length max_len for one (pair, encoding,
    rest) combination. Prunes any word (and its extensions) as soon as any
    of the 8 branch pointers would leave the 3g-cell window. Returns dict
    target -> shortest word (str) or None.
    """
    A, B = pair
    start_ptr = g + rest
    base_tapes = initial_states(pattern, g)
    init_states = [(tuple(t), start_ptr) for t in base_tapes]

    found = {t: None for t in TARGETS}
    visited = {tuple(init_states)}
    frontier = [("", init_states)]

    for length in range(1, max_len + 1):
        new_frontier = []
        for word, states in frontier:
            for letter, bundle in (('A', A), ('B', B)):
                new_states = []
                ok = True
                for tape, ptr in states:
                    tape_list = list(tape)
                    res = apply_letter(bundle, tape_list, ptr)
                    if res is None:
                        ok = False
                        break
                    new_states.append((tuple(res[0]), res[1]))
                if not ok:
                    continue
                key = tuple(new_states)
                if key in visited:
                    continue
                visited.add(key)
                new_word = word + letter
                for t in TARGETS:
                    if found[t] is None and check_target(t, new_states, start_ptr, g, pattern, VALUATIONS):
                        found[t] = new_word
                new_frontier.append((new_word, new_states))
        frontier = new_frontier
        if not frontier:
            break
        if early_stop and all(v is not None for v in found.values()):
            break
    return found
