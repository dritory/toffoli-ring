"""Hand-written demo programs, run on BOTH the reference simulator and
the switch-level machine, tick-by-tick compared, with ticks-per-
operation reported.

(1) 8-bit ripple-carry binary counter increment (single-level).
(2) echo an input cell to an output cell forever (single-level).
(3) copy an 8-bit block forever (single-level).
(4) a nested loop (labelled variant): inner loop clears each cell to 0,
    outer loop advances through the ring -- the outer JB(label=1) must
    skip past the inner MARK(label=2) to find its own mark, which is
    exactly the nesting labels are for.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import jump_ref as R
import machine_jump as M
import machine_jump_labeled as ML

def encode_prog(mnemonics):
    return [R.encode(m) for m in mnemonics]

def encode_prog_labeled(pairs):
    return [R.encode(m, a) for (m, a) in pairs]

# ---------------------------------------------------------------- (1) counter

COUNTER_PROG = encode_prog([
    'MARK',   # 0  loop top
    'FLIP',   # 1
    'SKIPZ',  # 2  skip next iff r==0 (bit became 0 => carry)
    'JF',     # 3  taken iff r==1 (no carry, done) -> seek to exit mark
    'NEXT',   # 4  carry: advance to next (more significant) bit
    'JB',     # 5  carry: loop back to MARK
    'MARK',   # 6  exit
    'MARK',   # 7  trailing pad, gives the harness an unambiguous "done"
              #    position distinct from 0 (never actually executed)
])

def run_counter_increment(machine_tick, initial_bits, max_ticks=200):
    """initial_bits: list of 0/1, LSB at index 0. Runs one increment
    starting with the data pointer at the LSB. Returns (ticks_used,
    final_bits). A 9th "guard" cell (always reset to 0) is appended
    after the 8 counter bits so an all-1s overflow ripples into the
    guard and stops there (r=1, no carry) instead of wrapping the data
    ring around and corrupting bit 0 a second time; the guard is
    dropped from the returned bits, matching ordinary fixed-width
    wraparound (carry-out discarded)."""
    data = list(initial_bits) + [0]
    state = R.initial_state() if machine_tick is R.tick else M.initial_state()
    prog_p = 0
    data_p = 0
    n_prog = len(COUNTER_PROG)
    n_data = len(data)
    for t in range(max_ticks):
        opcode = COUNTER_PROG[prog_p]
        r = data[data_p]
        toggle, mp, mm, pp, pm, state = machine_tick(state, opcode, r)
        if toggle: data[data_p] ^= 1
        if mp: data_p = (data_p + 1) % n_data
        if mm: data_p = (data_p - 1) % n_data
        if pp: prog_p = (prog_p + 1) % n_prog
        if pm: prog_p = (prog_p - 1) % n_prog
        if prog_p == 7:
            # landed one past the exit MARK (position 6) -> done
            return t + 1, data[:-1]
    raise AssertionError("counter increment did not terminate")

def bits_to_int(bits):
    v = 0
    for i, b in enumerate(bits):
        v |= b << i
    return v

def int_to_bits(v, width):
    return [(v >> i) & 1 for i in range(width)]

def demo_counter():
    width = 8
    results = []
    for start in [0, 1, 3, 7, 15, 31, 63, 127, 254, 255]:
        bits0 = int_to_bits(start, width)
        t_ref, ref_bits = run_counter_increment(R.tick, bits0)
        t_circ, circ_bits = run_counter_increment(M.tick, bits0)
        assert ref_bits == circ_bits, (start, ref_bits, circ_bits)
        assert t_ref == t_circ, (start, t_ref, t_circ)
        expect = (start + 1) % (2 ** width)
        assert bits_to_int(ref_bits) == expect, (start, ref_bits)
        results.append((start, t_ref))
    return results

# ------------------------------------------------------------------- (2) echo

ECHO_PROG = encode_prog([
    'MARK',   # 0  MarkTOP
    'SKIPZ',  # 1  test input (pos 0 of data ring)
    'JF',     # 2  input==1 -> seek fwd to MarkB
    'NEXT',   # 3  input==0: move to output
    'SKIPZ',  # 4  force output to 0
    'FLIP',   # 5
    'PREV',   # 6  back to input
    'JB',     # 7  back to MarkTOP
    'MARK',   # 8  MarkB
    'NEXT',   # 9  input==1: move to output
    'SKIPZ',  # 10 force output to 1 (SKIPZ;FLIP;FLIP trick)
    'FLIP',   # 11
    'FLIP',   # 12
    'PREV',   # 13 back to input
    'JF',     # 14 forward-wrap back to MarkTOP
])

def run_program(machine_tick, prog, state0, data, prog_p0, data_p0, ticks,
                 io=None):
    prog_p = prog_p0; data_p = data_p0
    n_prog = len(prog); n_data = len(data)
    state = state0
    trace = []
    for t in range(ticks):
        opcode = prog[prog_p]
        r = data[data_p]
        toggle, mp, mm, pp, pm, state = machine_tick(state, opcode, r)
        if toggle: data[data_p] ^= 1
        if mp: data_p = (data_p + 1) % n_data
        if mm: data_p = (data_p - 1) % n_data
        if pp: prog_p = (prog_p + 1) % n_prog
        if pm: prog_p = (prog_p - 1) % n_prog
        if io: io(t, data, data_p, prog_p)
        trace.append((toggle, mp, mm, pp, pm))
    return state, prog_p, data_p, trace

def demo_echo():
    # data ring: [input, output]; drive input externally between passes.
    data_ref = [0, 1]
    data_circ = [0, 1]
    st_ref = R.initial_state()
    st_circ = M.initial_state()
    pp_r = pp_c = 0
    dp_r = dp_c = 0
    total_ticks = 0
    schedule = [0, 1, 1, 0, 0, 0, 1]  # external input values, one per pass
    per_pass_ticks = []
    for val in schedule:
        data_ref[0] = val; data_circ[0] = val
        # run until one full pass back to MarkTOP (prog_p wraps to 0)
        ticks_this_pass = 0
        for t in range(30):
            opcode = ECHO_PROG[pp_r]
            r_r = data_ref[dp_r]; r_c = data_circ[dp_c]
            assert pp_r == pp_c and r_r == r_c, (val, t, pp_r, pp_c, r_r, r_c)
            to_r, mp_r, mm_r, pp1, pm1, st_ref = R.tick(st_ref, opcode, r_r)
            to_c, mp_c, mm_c, pp2, pm2, st_circ = M.tick(st_circ, opcode, r_c)
            assert (to_r, mp_r, mm_r, pp1, pm1) == (to_c, mp_c, mm_c, pp2, pm2)
            if to_r: data_ref[dp_r] ^= 1
            if to_c: data_circ[dp_c] ^= 1
            if mp_r: dp_r = (dp_r + 1) % 2
            if mm_r: dp_r = (dp_r - 1) % 2
            if mp_c: dp_c = (dp_c + 1) % 2
            if mm_c: dp_c = (dp_c - 1) % 2
            if pp1: pp_r = (pp_r + 1) % len(ECHO_PROG)
            if pm1: pp_r = (pp_r - 1) % len(ECHO_PROG)
            if pp2: pp_c = (pp_c + 1) % len(ECHO_PROG)
            if pm2: pp_c = (pp_c - 1) % len(ECHO_PROG)
            ticks_this_pass += 1
            total_ticks += 1
            if pp_r == 0:
                break
        assert data_ref == data_circ == [val, val], (val, data_ref, data_circ)
        per_pass_ticks.append((val, ticks_this_pass))
    return per_pass_ticks

# ------------------------------------------------------------- (3) block copy

COPY_PROG = encode_prog([
    'MARK',   # 0  MarkTOP
    'SKIPZ',  # 1  test src_i
    'JF',     # 2  src_i==1 -> MarkB
    'NEXT',   # 3  src==0: move to dst_i
    'SKIPZ',  # 4  force dst_i to 0
    'FLIP',   # 5
    'NEXT',   # 6  advance to src_{i+1}
    'JB',     # 7  back to MarkTOP
    'MARK',   # 8  MarkB
    'NEXT',   # 9  src==1: move to dst_i
    'SKIPZ',  # 10 force dst_i to 1
    'FLIP',   # 11
    'FLIP',   # 12
    'NEXT',   # 13 advance to src_{i+1}
    'JF',     # 14 forward-wrap back to MarkTOP
])

def demo_block_copy():
    n = 8
    src = [1, 0, 1, 1, 0, 0, 1, 0]
    data0 = []
    for b in src:
        data0 += [b, 0]  # interleave: src_i, dst_i(=0)
    data_ref = list(data0); data_circ = list(data0)
    st_ref = R.initial_state(); st_circ = M.initial_state()
    pp_r = pp_c = 0; dp_r = dp_c = 0
    ticks = 0
    for t in range(200):
        opcode = COPY_PROG[pp_r]
        r_r = data_ref[dp_r]; r_c = data_circ[dp_c]
        assert pp_r == pp_c and r_r == r_c
        to_r, mp_r, mm_r, pp1, pm1, st_ref = R.tick(st_ref, opcode, r_r)
        to_c, mp_c, mm_c, pp2, pm2, st_circ = M.tick(st_circ, opcode, r_c)
        assert (to_r, mp_r, mm_r, pp1, pm1) == (to_c, mp_c, mm_c, pp2, pm2)
        if to_r: data_ref[dp_r] ^= 1
        if to_c: data_circ[dp_c] ^= 1
        if mp_r: dp_r = (dp_r + 1) % len(data0)
        if mm_r: dp_r = (dp_r - 1) % len(data0)
        if mp_c: dp_c = (dp_c + 1) % len(data0)
        if mm_c: dp_c = (dp_c - 1) % len(data0)
        if pp1: pp_r = (pp_r + 1) % len(COPY_PROG)
        if pm1: pp_r = (pp_r - 1) % len(COPY_PROG)
        if pp2: pp_c = (pp_c + 1) % len(COPY_PROG)
        if pm2: pp_c = (pp_c - 1) % len(COPY_PROG)
        ticks += 1
        if dp_r == 0 and t > 0 and pp_r == 0:
            break
    dst = [data_ref[2 * i + 1] for i in range(n)]
    assert dst == src, (src, dst)
    assert data_ref == data_circ
    return ticks, src, dst

# ------------------------------------------------------- (4) labelled nesting

NEST_PROG = encode_prog_labeled([
    ('MARK', 1),   # 0  outer top
    ('MARK', 2),   # 1  inner top
    ('FLIP', 0),   # 2  flip current cell
    ('SKIPZ', 0),  # 3  test (flipped) cell; skip next iff r==0
    ('JB', 2),     # 4  if r==1: loop back to inner top (label 2)
    ('NEXT', 0),   # 5  advance to next cell
    ('JB', 1),     # 6  back to outer top (label 1) -- must skip inner mark
])

def demo_nested():
    data0 = [1, 0, 1, 1, 0, 1, 0, 0]
    data_ref = list(data0); data_circ = list(data0)
    st_ref = R.initial_state_labeled(); st_circ = ML.initial_state()
    pp_r = pp_c = 0; dp_r = dp_c = 0
    ticks = 0
    outer_ticks = []
    last_outer_tick = 0
    for t in range(400):
        opcode = NEST_PROG[pp_r]
        r_r = data_ref[dp_r]; r_c = data_circ[dp_c]
        assert pp_r == pp_c and r_r == r_c
        to_r, mp_r, mm_r, pp1, pm1, st_ref = R.tick_labeled(st_ref, opcode, r_r)
        to_c, mp_c, mm_c, pp2, pm2, st_circ = ML.tick(st_circ, opcode, r_c)
        assert (to_r, mp_r, mm_r, pp1, pm1) == (to_c, mp_c, mm_c, pp2, pm2)
        if to_r: data_ref[dp_r] ^= 1
        if to_c: data_circ[dp_c] ^= 1
        if mp_r: dp_r = (dp_r + 1) % len(data0)
        if mp_c: dp_c = (dp_c + 1) % len(data0)
        if pp1: pp_r = (pp_r + 1) % len(NEST_PROG)
        if pm1: pp_r = (pp_r - 1) % len(NEST_PROG)
        if pp2: pp_c = (pp_c + 1) % len(NEST_PROG)
        if pm2: pp_c = (pp_c - 1) % len(NEST_PROG)
        ticks += 1
        if pp_r == 0 and t > 0:
            outer_ticks.append(ticks - last_outer_tick)
            last_outer_tick = ticks
        if dp_r == 0 and t > 0 and pp_r == 0 and len(outer_ticks) >= len(data0):
            break
    assert all(b == 0 for b in data_ref), data_ref
    assert data_ref == data_circ
    return ticks, outer_ticks

if __name__ == '__main__':
    print("=== (1) 8-bit ripple-carry counter increment ===")
    for start, t in demo_counter():
        print("  start=%3d -> +1, ticks=%2d" % (start, t))

    print("=== (2) echo input->output ===")
    for val, t in demo_echo():
        print("  input=%d, ticks this pass=%d" % (val, t))

    print("=== (3) copy 8-bit block ===")
    ticks, src, dst = demo_block_copy()
    print("  src=%r dst=%r ticks=%d" % (src, dst, ticks))

    print("=== (4) labelled nested loop ===")
    ticks, outer_ticks = demo_nested()
    print("  total ticks=%d, ticks per outer iteration=%r" % (ticks, outer_ticks))

    print("ALL PROGRAM DEMOS PASS (reference == switch-level, tick-by-tick)")
