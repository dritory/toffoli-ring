"""
Guarded-macro criterion (per orchestrator instruction): compile "SKIPZ X" as
one macro CX; the flag is internal to the macro. A word w implements a
target iff, from flag_in = 0 only, for every window valuation, ALL branches
end with flag_out = 0, the correct encoded tape, and the target's pointer
offset (which may itself depend on the branch, for CNEXT/CPREV).

Targets:
  FLIP:  current group toggled;                 delta 0            (all branches)
  NEXT:  tape unchanged;                         delta +g           (all branches)
  PREV:  tape unchanged;                         delta -g           (all branches)
  CFLIP: current group forced to template(0)     delta 0            (all branches)
         (= "flip iff bit==1": clears the bit; result is template(0) either way)
  CNEXT: tape unchanged;                         delta +g if bit==1 else 0
  CPREV: tape unchanged;                         delta -g if bit==1 else 0

Window: R groups each side of the current group (R depends on L and g, see
window_half_width_groups), which is provably large enough that pruning on
leaving the window cannot reject any word that would in fact be exact on an
unbounded tape (see orchestrator's formula: R = ceil(floor(L/2)/g) + 1).

Performance: vectorized over ALL valuations at once with numpy (one lane
per valuation). The whole window (up to ~21 bits for our L/g combinations)
is bit-packed into a single int64 per lane; every sub-op (flip, move,
skip-test) becomes a handful of elementwise numpy bit ops (shift/and/xor)
on 1-D arrays of length N, rather than 2-D gather/scatter into an (N,W)
cell array -- this was the dominant cost of an earlier version and is
roughly W times cheaper (W up to 21 here).
"""
import math

import numpy as np

from machine import FLIP, MOVE, SKIP, ALWAYS, EQ0, EQ1


def window_half_width_groups(L, g):
    return math.ceil((L // 2) / g) + 1


GUARDED_TARGETS = ("FLIP", "NEXT", "PREV", "CFLIP", "CNEXT", "CPREV")


def _pack(bits_tuple):
    """A tuple of 0/1 cell values -> integer, cell 0 at bit 0 (LSB)."""
    v = 0
    for i, b in enumerate(bits_tuple):
        if b:
            v |= (1 << i)
    return v


def apply_bundle_vec(bits, ptr, flag, alive, ops, W):
    """bits, ptr, flag, alive: (N,) arrays. Every transformation below
    produces a NEW array (no in-place mutation), so the caller's arrays are
    never touched and need not be pre-copied. Returns (new_bits, new_ptr,
    new_flag, new_alive)."""
    gated = alive & (flag == 1)
    real_active = alive & ~gated

    cur_ptr = ptr
    fo = np.zeros_like(flag)
    active_now = real_active

    for op in ops:
        curvals = (bits >> cur_ptr) & 1
        if op.kind == FLIP:
            flipmask = np.where(active_now, np.left_shift(np.int64(1), cur_ptr), np.int64(0))
            bits = bits ^ flipmask
        elif op.kind == MOVE:
            if op.cond == ALWAYS:
                domove = active_now
            elif op.cond == EQ0:
                domove = active_now & (curvals == 0)
            else:
                domove = active_now & (curvals == 1)
            newpos = cur_ptr + np.where(domove, op.dir, 0)
            oob = active_now & ((newpos < 0) | (newpos >= W))
            active_now = active_now & ~oob
            cur_ptr = np.where(active_now, newpos, cur_ptr)
        elif op.kind == SKIP:
            match = (curvals == op.v).astype(fo.dtype)
            fo = np.where(active_now, match, fo)

    alive2 = alive & (~real_active | active_now)
    flag2 = np.where(gated, 0, np.where(real_active, fo, flag))
    return bits, cur_ptr, flag2, alive2


def search_pair_guarded(bundleA, bundleB, g, template, rest, L,
                         want=GUARDED_TARGETS):
    """Returns dict target -> (word_string, length) or None."""
    R = window_half_width_groups(L, g)
    ngroups = 2 * R + 1
    W = ngroups * g
    ptr0 = R * g + rest
    cur_slot = R
    N = 1 << ngroups

    idxarr = np.arange(N, dtype=np.int64)
    bitarr = np.arange(ngroups, dtype=np.int64)
    combos_bits = (idxarr[:, None] >> bitarr[None, :]) & 1  # (N, ngroups), int64

    seg0 = _pack(tuple(template(0)))
    seg1 = _pack(tuple(template(1)))

    tape0 = np.zeros(N, dtype=np.int64)
    for j in range(ngroups):
        contrib = np.where(combos_bits[:, j] == 1, seg1, seg0).astype(np.int64) << (j * g)
        tape0 = tape0 | contrib
    xc = combos_bits[:, cur_slot]  # (N,), 0/1

    cur_start = cur_slot * g
    group_mask = ((1 << g) - 1) << cur_start
    outside_mask = ~group_mask  # numpy int64 bitwise-not; fine for masking via AND

    toggled_seg = np.where(xc == 1, seg0, seg1).astype(np.int64)  # toggle(xc)
    expected_flip = (tape0 & outside_mask) | (toggled_seg << cur_start)
    expected_cflip = (tape0 & outside_mask) | (np.int64(seg0) << cur_start)  # always template(0)

    letters = {"A": bundleA, "B": bundleB}
    found = {p: None for p in want}
    ptr0_cnext = ptr0 + g * xc
    ptr0_cprev = ptr0 - g * xc

    def check(word_str, bits, ptr, flag):
        # (alive is guaranteed all-True here -- pruned words never reach check)
        if not np.all(flag == 0):
            return
        pending = [p for p in found if found[p] is None]
        if not pending:
            return
        same0 = None  # lazily computed, shared by NEXT/PREV/CNEXT/CPREV
        for prim in pending:
            if prim == "FLIP":
                ok = np.all(ptr == ptr0) and np.array_equal(bits, expected_flip)
            elif prim == "CFLIP":
                ok = np.all(ptr == ptr0) and np.array_equal(bits, expected_cflip)
            else:
                if same0 is None:
                    same0 = np.array_equal(bits, tape0)
                if not same0:
                    ok = False
                elif prim == "NEXT":
                    ok = np.all(ptr == ptr0 + g)
                elif prim == "PREV":
                    ok = np.all(ptr == ptr0 - g)
                elif prim == "CNEXT":
                    ok = np.array_equal(ptr, ptr0_cnext)
                elif prim == "CPREV":
                    ok = np.array_equal(ptr, ptr0_cprev)
                else:
                    raise ValueError(prim)
            if ok:
                found[prim] = (word_str, len(word_str))

    root = (tape0, np.full(N, ptr0, dtype=np.int64),
            np.zeros(N, dtype=np.int64), np.ones(N, dtype=bool))

    frontier = [("", root)]
    for depth in range(1, L + 1):
        if all(found[p] is not None for p in want):
            break
        next_frontier = []
        for prefix, (bits, ptr, flag, alive) in frontier:
            for ch in ("A", "B"):
                bundle = letters[ch]
                nb, np_, nf, na = apply_bundle_vec(bits, ptr, flag, alive, bundle.ops, W)
                if not na.all():
                    continue
                word = prefix + ch
                check(word, nb, np_, nf)
                next_frontier.append((word, (nb, np_, nf, na)))
        frontier = next_frontier
        if not frontier:
            break

    return found
