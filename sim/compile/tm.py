"""
Generic Turing machine model + direct simulator, and the three test
machines: a binary counter, an echo machine, and a halting (busy-beaver
style) machine.

A TM here is: a finite set of states Q (strings), a binary tape alphabet
{0,1}, and a transition table

    trans[(state, symbol)] = (new_symbol, direction, new_state)

with direction in {-1, 0, +1}. A state with trans[(q,0)] == (0,0,q) and
trans[(q,1)] == (1,0,q) for all symbols is a *halting* state: it idles
(rereads/rewrites the same symbol, does not move, stays in the same state)
forever once entered, per the task's definition of "halting state that
idles".

The tape is a finite cyclic array (this matches the target hardware's
cyclic bit tape exactly -- there is no separate "infinite tape" model to
approximate).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


Direction = int  # -1, 0, +1


@dataclass
class TM:
    states: List[str]
    halt_states: List[str]
    trans: Dict[Tuple[str, int], Tuple[int, Direction, str]]
    start_state: str

    def is_halting(self, q: str) -> bool:
        return q in self.halt_states


@dataclass
class TMConfig:
    tape: List[int]
    head: int
    state: str

    def copy(self):
        return TMConfig(list(self.tape), self.head, self.state)


def tm_step(tm: TM, cfg: TMConfig) -> None:
    n = len(cfg.tape)
    sym = cfg.tape[cfg.head]
    new_sym, d, new_state = tm.trans[(cfg.state, sym)]
    cfg.tape[cfg.head] = new_sym
    cfg.head = (cfg.head + d) % n
    cfg.state = new_state


def run_tm(tm: TM, cfg: TMConfig, steps: int, stop_on_halt: bool = True) -> List[TMConfig]:
    """Returns the list of configs [cfg0, cfg1, ..., cfgK] (K <= steps),
    stopping early once a halting state is reached (its config is included
    once, as the final entry) if stop_on_halt."""
    trace = [cfg.copy()]
    for _ in range(steps):
        if stop_on_halt and tm.is_halting(cfg.state):
            break
        tm_step(tm, cfg)
        trace.append(cfg.copy())
    return trace


# ---------------------------------------------------------------------------
# Test machine (a): binary counter, width L bits, LSB at cell 0.
#
# States: C_0..C_{L-1} ("ripple-carry currently at logical position i", head
# sits on cell i) and, for each i in 1..L-1, RET_i_1..RET_i_{L-i} ("carry
# just stopped at position i after writing a 1; coasting back to the LSB by
# continuing in the same (+1) direction for the remaining L-i cells").
#
# C_i, symbol=1: write 0, move +1, go to C_{(i+1) mod L}   (carry continues)
# C_i, symbol=0: write 1, i==0: move 0, go to C_0 (already home)
#                          i>0 : move +1, go to RET_i_1 (coast home)
# RET_i_j (any symbol): pass through unchanged, move +1,
#                        go to RET_i_{j+1} if j < L-i, else C_0.
#
# This TM never halts ("runs forever"): after each ripple-carry completes
# (taking between 1 and L steps) it is immediately back at C_0, ready to
# start incrementing again from the (freshly written) LSB. Because the
# physical/group tape is itself cyclic with exactly L groups, "coast home"
# and "wrap the physical tape" are the same cyclic address space -- no
# extra marker cell is needed.
# ---------------------------------------------------------------------------

def make_counter_tm(L: int) -> TM:
    assert L >= 2
    states = [f"C{i}" for i in range(L)]
    trans = {}
    for i in range(L):
        trans[(f"C{i}", 1)] = (0, +1, f"C{(i + 1) % L}")
        if i == 0:
            trans[(f"C{i}", 0)] = (1, 0, "C0")
        else:
            n_ret = L - i - 1  # number of coast states needed to land back on position 0
            if n_ret == 0:
                trans[(f"C{i}", 0)] = (1, +1, "C0")
            else:
                trans[(f"C{i}", 0)] = (1, +1, f"RET{i}_1")
                for j in range(1, n_ret + 1):
                    nxt = f"RET{i}_{j + 1}" if j < n_ret else "C0"
                    states.append(f"RET{i}_{j}")
                    trans[(f"RET{i}_{j}", 0)] = (0, +1, nxt)
                    trans[(f"RET{i}_{j}", 1)] = (1, +1, nxt)
    return TM(states=states, halt_states=[], trans=trans, start_state="C0")


def counter_value(tape: List[int]) -> int:
    """LSB at index 0."""
    v = 0
    for i, b in enumerate(tape):
        v |= (b << i)
    return v


# ---------------------------------------------------------------------------
# Test machine (b): echo machine.
#
# One reserved I/O group at tape position 0: bit at position 0 is "input"
# (written externally, between TM steps, by the test harness -- the TM
# itself only ever reads it), bit at position 1 is "output" (the TM writes
# here). Every step, the machine copies the current input bit to the output
# bit, then returns to position 0 (net pointer motion zero per step, from
# the outside), and idles otherwise. Since this must be exactly one TM
# transition per group-visit and the TM's own moves are what get compiled,
# we spread the copy over 2 states so each TM step is a single-cell
# read-or-write with a single-cell move, matching the "one pass = one
# logical tape-bit move" primitive granularity used everywhere else here:
#
#   READ  (head at cell 0, the input cell): remember nothing (no state
#         bits needed -- the value just travels on the move), move +1 to
#         cell 1 (output), write nothing yet; state -> WRITE0 or WRITE1
#         depending on the input symbol read.
#   WRITE0/WRITE1 (head at cell 1, the output cell): write 0 or 1
#         (matching the state), move -1 back to cell 0; state -> READ.
#
# This never halts either. "Echo" here means: whatever the external
# harness pokes into cell 0 before a READ step shows up in cell 1 one full
# (READ,WRITE) cycle (2 TM steps) later.
# ---------------------------------------------------------------------------

def make_echo_tm() -> TM:
    states = ["READ", "WRITE0", "WRITE1"]
    trans = {
        ("READ", 0): (0, +1, "WRITE0"),   # symbol at cell0 unchanged; remember 0
        ("READ", 1): (1, +1, "WRITE1"),   # remember 1
        ("WRITE0", 0): (0, -1, "READ"),
        ("WRITE0", 1): (0, -1, "READ"),   # write 0 regardless of old output bit
        ("WRITE1", 0): (1, -1, "READ"),
        ("WRITE1", 1): (1, -1, "READ"),   # write 1 regardless of old output bit
    }
    return TM(states=states, halt_states=[], trans=trans, start_state="READ")


# ---------------------------------------------------------------------------
# Test machine (c): 2-state, 2-symbol busy beaver (the standard sigma(2)=4,
# S(2)=6 machine), plus an explicit idling HALT state so halting is visible
# as "the state slots settle into the HALT one-hot pattern and never change
# again", per the task's requirement to detect halting by reading the state
# slots.
#
# Standard transition table (Radó's BB(2,2), one common labelling):
#   A,0 -> write 1, move R, go to B
#   A,1 -> write 1, move L, go to B
#   B,0 -> write 1, move L, go to A
#   B,1 -> write 1, move R, go to HALT
# Runs for exactly 6 steps before halting (4 ones written, well-known).
# ---------------------------------------------------------------------------

def make_bb22_tm() -> TM:
    states = ["A", "B", "HALT"]
    trans = {
        ("A", 0): (1, +1, "B"),
        ("A", 1): (1, -1, "B"),
        ("B", 0): (1, -1, "A"),
        ("B", 1): (1, +1, "HALT"),
        ("HALT", 0): (0, 0, "HALT"),
        ("HALT", 1): (1, 0, "HALT"),
    }
    return TM(states=states, halt_states=["HALT"], trans=trans, start_state="A")


if __name__ == "__main__":
    # quick smoke test of the direct simulator only
    L = 3
    tm = make_counter_tm(L)
    cfg = TMConfig(tape=[0] * L, head=0, state=tm.start_state)
    vals = []
    for _ in range(20):
        vals.append(counter_value(cfg.tape))
        tm_step(tm, cfg)
    print("counter values sampled once per TM step (not once per increment):", vals)

    tm = make_bb22_tm()
    cfg = TMConfig(tape=[0] * 12, head=6, state=tm.start_state)
    trace = run_tm(tm, cfg, steps=20)
    print(f"BB(2,2): halted after {len(trace) - 1} steps, "
          f"ones written = {sum(trace[-1].tape)}, final state = {trace[-1].state}")

    tm = make_echo_tm()
    cfg = TMConfig(tape=[1, 0] + [0] * 6, head=0, state=tm.start_state)
    trace = run_tm(tm, cfg, steps=6)
    print("echo trace (cell0=input, cell1=output):",
          [(c.state, c.tape[0], c.tape[1]) for c in trace])
