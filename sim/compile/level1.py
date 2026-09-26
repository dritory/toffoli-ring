"""
Level 1: the reference machine R.

Cyclic program over the alphabet {F, N, P, CN, CP} acting on a logical bit
tape with a single pointer. No flag at this level -- the flag is internal
to the level-0 macros that implement each letter. Semantics:

  F  : flip the bit under the pointer.
  N  : pointer += 1 (unconditional).
  P  : pointer -= 1 (unconditional).
  CN : if the bit under the pointer == 1: pointer += 1; else: no-op.
  CP : if the bit under the pointer == 1: pointer -= 1; else: no-op.

R has no jumps: a program is a fixed sequence of letters, executed once per
"pass" (or forever, cyclically, per HANDOVER-B). Conditional moves (CN, CP)
are the only source of data dependence.

This module also compiles an R program down to level 0 (by substituting the
five verified macros from level0.py, using the (x, x-bar) encoding with the
logical pointer resting on the x cell) and cross-checks that running the
level-0 substitution against the level-0 simulator reproduces exactly what
the direct R simulator computes, logical bit for logical bit, after every
letter (not just at the end of the word) -- since our compiled gadgets are
themselves R words, the pointer's position measured *in logical bits* must
agree at every step, even though intermediate level-0 states (mid-macro) do
not correspond to any logical-tape state.
"""
from dataclasses import dataclass
from typing import List
import random

import level0 as L0

LETTERS = ["F", "N", "P", "CN", "CP"]


@dataclass
class R_State:
    tape: List[int]
    ptr: int

    def copy(self):
        return R_State(list(self.tape), self.ptr)


def step(state: R_State, letter: str) -> None:
    n = len(state.tape)
    if letter == "F":
        state.tape[state.ptr] ^= 1
    elif letter == "N":
        state.ptr = (state.ptr + 1) % n
    elif letter == "P":
        state.ptr = (state.ptr - 1) % n
    elif letter == "CN":
        if state.tape[state.ptr] == 1:
            state.ptr = (state.ptr + 1) % n
    elif letter == "CP":
        if state.tape[state.ptr] == 1:
            state.ptr = (state.ptr - 1) % n
    else:
        raise ValueError(letter)


def run(state: R_State, program) -> None:
    for letter in program:
        step(state, letter)


# --- compiling an R word down to level 0 -----------------------------------

_R_TO_L0_MACRO = {"F": "FLIP", "N": "NEXT", "P": "PREV", "CN": "CNEXT", "CP": "CPREV"}


def compile_to_level0(program) -> str:
    """R word (list/str of letters, 'CN'/'CP' as 2-char tokens) -> level-0
    program (string over 'A','B')."""
    out = []
    for letter in program:
        out.append(L0.MACROS[_R_TO_L0_MACRO[letter]])
    return "".join(out)


def parse_r_word(s: str) -> List[str]:
    """Parse a string like 'FNCNPCPF' into ['F','N','CN','P','CP','F']."""
    out = []
    i = 0
    while i < len(s):
        if s[i:i + 2] in ("CN", "CP"):
            out.append(s[i:i + 2])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return out


# --- cross-check against level 0 --------------------------------------------

def cross_check(program, n_groups: int, trials: int, rng: random.Random) -> int:
    """Run `program` on a random logical tape both directly (R_State) and via
    substitution into level 0, and check the logical tape + logical pointer
    agree after EVERY letter of the word (not just at the end). Returns the
    number of trials that passed fully."""
    passed = 0
    for _ in range(trials):
        bits = [rng.randint(0, 1) for _ in range(n_groups)]
        lp = rng.randint(0, n_groups - 1)

        r_st = R_State(list(bits), lp)
        phys = L0.encode_logical_tape(bits)
        l0_st = L0.Level0State(phys, L0.logical_ptr_to_phys(lp) % len(phys), 0)

        ok = True
        for letter in program:
            step(r_st, letter)
            L0.run(l0_st, L0.MACROS[_R_TO_L0_MACRO[letter]])
            if l0_st.flag != 0:
                ok = False
                break
            try:
                dec = L0.decode_logical_tape(l0_st.tape)
            except AssertionError:
                ok = False
                break
            if dec != r_st.tape:
                ok = False
                break
            if l0_st.ptr != L0.logical_ptr_to_phys(r_st.ptr) % len(phys):
                ok = False
                break
        if ok:
            passed += 1
    return passed


if __name__ == "__main__":
    rng = random.Random(999)
    prog = parse_r_word("FNCNPCPFNCNFPCP")
    n = cross_check(prog, n_groups=10, trials=500, rng=rng)
    print(f"cross-check R vs level0 substitution, random word, 500 trials: {n}/500 passed")
