"""
Level 0: the target hardware.

Cyclic bit tape, one pointer, one skip flag, cyclic program of 1-bit
instructions, one per tick.

  Fetch: if flag is set, this instruction does nothing and the flag clears.
  Otherwise (both A and B):
    A: flip the cell under the pointer; set flag iff the cell is now 0;
       move the pointer +1.
    B: same, but move the pointer -1.

Tape encoding: every logical bit x is stored as two physical cells (x, not
x); the pointer rests on the x cell (offset 0 of the pair).

This module is a from-scratch simulator written directly from that
description (HANDOVER B / the task prompt), independent of sim/twoop, used
to re-verify the five macros before building anything on top of them.
"""
from dataclasses import dataclass
from typing import List
import random

A = "A"
B = "B"


@dataclass
class Level0State:
    tape: List[int]   # cyclic array of physical bits
    ptr: int
    flag: int

    def copy(self):
        return Level0State(list(self.tape), self.ptr, self.flag)


def step(state: Level0State, instr: str) -> None:
    """One tick, in place."""
    n = len(state.tape)
    if state.flag == 1:
        state.flag = 0
        return
    if instr == A:
        d = 1
    elif instr == B:
        d = -1
    else:
        raise ValueError(instr)
    p = state.ptr
    state.tape[p] ^= 1
    state.flag = 1 if state.tape[p] == 0 else 0
    state.ptr = (p + d) % n


def run(state: Level0State, program: str) -> None:
    for ch in program:
        step(state, ch)


# --- (x, not x) encoding, logical <-> physical -----------------------------

def encode_logical_tape(bits: List[int]) -> List[int]:
    """Each logical bit x -> physical pair (x, 1-x)."""
    phys = []
    for x in bits:
        phys.append(x)
        phys.append(1 - x)
    return phys


def decode_logical_tape(phys: List[int]) -> List[int]:
    assert len(phys) % 2 == 0
    out = []
    for i in range(0, len(phys), 2):
        x, xbar = phys[i], phys[i + 1]
        assert x == 1 - xbar, f"encoding invariant broken at group {i//2}: ({x},{xbar})"
        out.append(x)
    return out


def logical_ptr_to_phys(logical_ptr: int) -> int:
    """Logical pointer rests on the x cell of its pair -> physical index."""
    return 2 * logical_ptr


# --- the five macros (as given, and as independently re-derived) ----------

MACROS = {
    "FLIP":  "ABB",
    "NEXT":  "ABBAAA",
    "PREV":  "BAABBBABBABB",
    "CNEXT": "ABBAAB",
    "CPREV": "ABBABABAABBB",
}


def run_macro(state: Level0State, name: str) -> None:
    run(state, MACROS[name])


# --- verification -----------------------------------------------------------

def random_logical_tape(n_groups: int, rng: random.Random) -> List[int]:
    return [rng.randint(0, 1) for _ in range(n_groups)]


def verify_macro(name: str, n_groups: int, trials: int, rng: random.Random,
                  logical_ptr: int = 0) -> int:
    """For each trial: build a random cyclic logical tape of n_groups bits,
    place the (physical) pointer at logical_ptr's x-cell, flag=0, run the
    macro, and check its expected logical effect. Returns #passed."""
    passed = 0
    for _ in range(trials):
        bits = random_logical_tape(n_groups, rng)
        phys = encode_logical_tape(bits)
        st = Level0State(phys, logical_ptr_to_phys(logical_ptr) % len(phys), 0)
        cur_bit = bits[logical_ptr]
        run_macro(st, name)
        if st.flag != 0:
            continue
        try:
            new_bits = decode_logical_tape(st.tape)
        except AssertionError:
            continue
        n = n_groups
        if name == "FLIP":
            want_bits = list(bits)
            want_bits[logical_ptr] ^= 1
            want_ptr = logical_ptr
        elif name == "NEXT":
            want_bits = bits
            want_ptr = (logical_ptr + 1) % n
        elif name == "PREV":
            want_bits = bits
            want_ptr = (logical_ptr - 1) % n
        elif name == "CNEXT":
            want_bits = bits
            want_ptr = (logical_ptr + 1) % n if cur_bit == 1 else logical_ptr
        elif name == "CPREV":
            want_bits = bits
            want_ptr = (logical_ptr - 1) % n if cur_bit == 1 else logical_ptr
        else:
            raise ValueError(name)
        if new_bits == want_bits and st.ptr == logical_ptr_to_phys(want_ptr) % len(phys):
            passed += 1
    return passed


if __name__ == "__main__":
    rng = random.Random(12345)
    trials = 2000
    print("Level-0 macro re-verification (independent simulator, random cyclic tapes)")
    print(f"trials per macro: {trials}, tape sizes: 3..16 groups, random logical rest position")
    for name in ["FLIP", "NEXT", "PREV", "CNEXT", "CPREV"]:
        total = 0
        ok = 0
        for n_groups in range(3, 17):
            for _ in range(trials // 14 + 1):
                lp = rng.randint(0, n_groups - 1)
                total += 1
                ok += verify_macro(name, n_groups, 1, rng, logical_ptr=lp)
        print(f"  {name:6s} = {MACROS[name]:14s} len={len(MACROS[name]):2d}  {ok}/{total} passed")
