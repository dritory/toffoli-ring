"""
Core simulator for the two-instruction, one-flag pointer machine described in
HANDOVER-B.md.

Tape: cyclic bit tape, one pointer, one pending-skip flag. One instruction
per tick. If the flag is set on fetch, the instruction does nothing and the
flag is cleared. Otherwise the instruction's *bundle* runs its sub-ops in a
fixed order. A bundle has at most one flip, at most one move (+1/-1,
unconditional or conditioned on the cell value under the pointer AT THAT
MOMENT), and at most one skip-test (set flag iff cell == v at that moment).

This module works with a small local window (list of bits) plus a pointer
index into that window plus the flag. Bundles never touch more than the
cell they start on and (if they move) the single neighbour cell they land
on, so a 3-cell window suffices to fully characterise one bundle's effect.
For macro (word) search we use wider windows (three whole encoding groups)
and prune any branch that would walk the pointer outside the window.
"""

from dataclasses import dataclass
from itertools import permutations
from typing import List, Optional, Tuple

# --- sub-op representation -------------------------------------------------

FLIP = "flip"
MOVE = "move"
SKIP = "skip"

ALWAYS = "always"
EQ0 = "eq0"
EQ1 = "eq1"


@dataclass(frozen=True)
class Op:
    kind: str
    dir: Optional[int] = None   # for MOVE: +1 or -1
    cond: Optional[str] = None  # for MOVE: ALWAYS/EQ0/EQ1
    v: Optional[int] = None     # for SKIP: 0 or 1

    def __repr__(self):
        if self.kind == FLIP:
            return "flip"
        if self.kind == MOVE:
            sign = "+1" if self.dir == 1 else "-1"
            if self.cond == ALWAYS:
                return f"move{sign}"
            return f"move{sign}(iff={self.cond[-1]})"
        if self.kind == SKIP:
            return f"skip(v={self.v})"
        raise ValueError


@dataclass(frozen=True)
class Bundle:
    ops: Tuple[Op, ...]  # fixed execution order

    def __repr__(self):
        if not self.ops:
            return "nop"
        return "(" + ",".join(repr(o) for o in self.ops) + ")"

    def has_move_dir(self, d):
        return any(o.kind == MOVE and o.dir == d for o in self.ops)

    def mirror(self):
        """Swap +1/-1 move directions."""
        new_ops = tuple(
            Op(MOVE, dir=-o.dir, cond=o.cond) if o.kind == MOVE else o
            for o in self.ops
        )
        return Bundle(new_ops)

    def complement(self):
        """Swap eq0/eq1 move conditions and skip v=0/1."""
        def flip_cond(c):
            return {EQ0: EQ1, EQ1: EQ0, ALWAYS: ALWAYS}[c]
        new_ops = []
        for o in self.ops:
            if o.kind == MOVE:
                new_ops.append(Op(MOVE, dir=o.dir, cond=flip_cond(o.cond)))
            elif o.kind == SKIP:
                new_ops.append(Op(SKIP, v=1 - o.v))
            else:
                new_ops.append(o)
        return Bundle(tuple(new_ops))


def all_bundles() -> List[Bundle]:
    """Enumerate every bundle: at most one flip, one move, one skip-test,
    in any order (up to 3! orders when all three are present)."""
    flip_opts = [None, Op(FLIP)]
    move_opts = [None]
    for d in (1, -1):
        for c in (ALWAYS, EQ0, EQ1):
            move_opts.append(Op(MOVE, dir=d, cond=c))
    skip_opts = [None, Op(SKIP, v=0), Op(SKIP, v=1)]

    bundles = []
    for f in flip_opts:
        for m in move_opts:
            for s in skip_opts:
                present = [op for op in (f, m, s) if op is not None]
                for perm in set(permutations(present)):
                    bundles.append(Bundle(tuple(perm)))
    return bundles


# --- bundle execution on a small local window ------------------------------

def run_bundle_on_window(bundle: Bundle, window: List[int], ptr: int):
    """Execute one bundle (flag assumed 0 on entry -- caller handles the
    flag-set no-op case). Returns (new_window, new_ptr, flag_out, ok) where
    ok is False if the pointer would leave the window."""
    w = list(window)
    p = ptr
    flag_out = 0
    n = len(w)
    for op in bundle.ops:
        if op.kind == FLIP:
            w[p] ^= 1
        elif op.kind == MOVE:
            cur = w[p]
            do_move = (
                op.cond == ALWAYS
                or (op.cond == EQ0 and cur == 0)
                or (op.cond == EQ1 and cur == 1)
            )
            if do_move:
                p += op.dir
                if p < 0 or p >= n:
                    return None, None, None, False
        elif op.kind == SKIP:
            flag_out = 1 if w[p] == op.v else 0
    return w, p, flag_out, True


def bundle_signature(bundle: Bundle):
    """Effect table over a 3-cell window (positions 0,1,2, start ptr=1),
    for flag_in = 0 only (flag_in = 1 is always a pure no-op for every
    bundle, so it never distinguishes bundles). Used to dedupe bundles."""
    sig = []
    for l in (0, 1):
        for c in (0, 1):
            for r in (0, 1):
                w = [l, c, r]
                nw, np_, fo, ok = run_bundle_on_window(bundle, w, 1)
                if not ok:
                    sig.append(("OOB",))
                else:
                    sig.append((tuple(nw), np_ - 1, fo))
    return tuple(sig)


def dedupe_bundles(bundles: List[Bundle]):
    seen = {}
    out = []
    for b in bundles:
        sig = bundle_signature(b)
        if sig not in seen:
            seen[sig] = b
            out.append(b)
    return out


# --- instruction fetch (the flag-gated wrapper) ----------------------------

def step(bundle: Bundle, window: List[int], ptr: int, flag: int):
    """One tick: fetch `bundle`; if flag set, no-op and clear flag; else run
    the bundle. Returns (window, ptr, flag, ok)."""
    if flag == 1:
        return list(window), ptr, 0, True
    nw, np_, fo, ok = run_bundle_on_window(bundle, window, ptr)
    if not ok:
        return None, None, None, False
    return nw, np_, fo, True


def run_word(word: List[Bundle], window: List[int], ptr: int, flag: int):
    """Run a sequence of bundles (a macro word). Returns (window, ptr, flag,
    ok)."""
    w, p, f = list(window), ptr, flag
    for b in word:
        w, p, f, ok = step(b, w, p, f)
        if not ok:
            return None, None, None, False
    return w, p, f, True
