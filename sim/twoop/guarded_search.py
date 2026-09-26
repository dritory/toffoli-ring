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
unbounded tape (see orchestrator's formula). Vectorized over ALL valuations
at once with numpy (one lane per valuation) since the window can be large
for g=1.
"""
import math

import numpy as np

from machine import FLIP, MOVE, SKIP, ALWAYS, EQ0, EQ1


def window_half_width_groups(L, g):
    return math.ceil((L // 2) / g) + 1


GUARDED_TARGETS = ("FLIP", "NEXT", "PREV", "CFLIP", "CNEXT", "CPREV")


def apply_bundle_vec(tape, ptr, flag, alive, ops, W):
    """tape: (N,W) int8 (mutated in place -- caller must pass a fresh copy
    per BFS node). ptr: (N,) int64. flag: (N,) int8. alive: (N,) bool.
    Returns (tape, new_ptr, new_flag, new_alive)."""
    active0 = alive
    gated = active0 & (flag == 1)
    real_active = active0 & ~gated

    new_flag = flag.copy()
    new_flag[gated] = 0

    cur_ptr = ptr.copy()
    fo = np.zeros(tape.shape[0], dtype=np.int8)
    newly_dead = np.zeros(tape.shape[0], dtype=bool)

    for op in ops:
        mask = real_active & ~newly_dead
        idxs = np.nonzero(mask)[0]
        if idxs.size == 0:
            continue
        if op.kind == FLIP:
            tape[idxs, cur_ptr[idxs]] ^= 1
        elif op.kind == MOVE:
            curvals = tape[idxs, cur_ptr[idxs]]
            if op.cond == ALWAYS:
                domove = np.ones(idxs.size, dtype=bool)
            elif op.cond == EQ0:
                domove = (curvals == 0)
            else:
                domove = (curvals == 1)
            newpos = cur_ptr[idxs] + np.where(domove, op.dir, 0)
            oob = (newpos < 0) | (newpos >= W)
            if oob.any():
                newly_dead[idxs[oob]] = True
            good = ~oob
            cur_ptr[idxs[good]] = newpos[good]
        elif op.kind == SKIP:
            curvals = tape[idxs, cur_ptr[idxs]]
            fo[idxs] = (curvals == op.v).astype(np.int8)

    alive2 = alive & ~newly_dead
    ptr2 = ptr.copy()
    still_active = real_active & ~newly_dead
    ptr2[still_active] = cur_ptr[still_active]
    flag2 = new_flag.copy()
    flag2[still_active] = fo[still_active]
    return tape, ptr2, flag2, alive2


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
    combos_bits = ((idxarr[:, None] >> bitarr[None, :]) & 1).astype(np.int8)  # (N, ngroups)

    t0 = np.array(template(0), dtype=np.int8)  # (g,)
    t1 = np.array(template(1), dtype=np.int8)  # (g,)
    tape0_3d = np.where(combos_bits[:, :, None] == 1, t1[None, None, :], t0[None, None, :])
    tape0 = tape0_3d.reshape(N, W)
    xc = combos_bits[:, cur_slot]  # (N,)

    cur_start = cur_slot * g
    expected_flip = tape0.copy()
    toggled = np.where(xc[:, None] == 1, t0[None, :], t1[None, :])  # toggle(xc)
    expected_flip[:, cur_start:cur_start + g] = toggled

    expected_cflip = tape0.copy()
    expected_cflip[:, cur_start:cur_start + g] = t0[None, :]  # always template(0)

    letters = {"A": bundleA, "B": bundleB}
    found = {p: None for p in want}

    def check(word_str, tape, ptr, flag, alive):
        # alive is guaranteed all-True here (pruned words never reach check)
        if not np.all(flag == 0):
            return
        pending = [p for p in found if found[p] is None]
        for prim in pending:
            if prim == "FLIP":
                ok = np.array_equal(tape, expected_flip) and np.all(ptr == ptr0)
            elif prim == "NEXT":
                ok = np.array_equal(tape, tape0) and np.all(ptr == ptr0 + g)
            elif prim == "PREV":
                ok = np.array_equal(tape, tape0) and np.all(ptr == ptr0 - g)
            elif prim == "CFLIP":
                ok = np.array_equal(tape, expected_cflip) and np.all(ptr == ptr0)
            elif prim == "CNEXT":
                ok = np.array_equal(tape, tape0) and np.array_equal(ptr, ptr0 + g * xc)
            elif prim == "CPREV":
                ok = np.array_equal(tape, tape0) and np.array_equal(ptr, ptr0 - g * xc)
            else:
                raise ValueError(prim)
            if ok:
                found[prim] = (word_str, len(word_str))

    root = (tape0.copy(), np.full(N, ptr0, dtype=np.int64),
            np.zeros(N, dtype=np.int8), np.ones(N, dtype=bool))

    frontier = [("", root)]
    for depth in range(1, L + 1):
        if all(found[p] is not None for p in want):
            break
        next_frontier = []
        for prefix, (tape, ptr, flag, alive) in frontier:
            for ch in ("A", "B"):
                bundle = letters[ch]
                new_tape = tape.copy()
                new_ptr, new_flag, new_alive_ptr = None, None, None
                nt, np_, nf, na = apply_bundle_vec(new_tape, ptr.copy(), flag.copy(),
                                                    alive.copy(), bundle.ops, W)
                if not na.all():
                    continue
                word = prefix + ch
                check(word, nt, np_, nf, na)
                next_frontier.append((word, (nt, np_, nf, na)))
        frontier = next_frontier
        if not frontier:
            break

    return found
