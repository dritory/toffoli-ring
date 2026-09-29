"""Run all four programs on reference and switch-level machine; print results."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ref as R, programs as P
from machine_nmos import Machine
from tm import make_bb22_tm, TMConfig, run_tm

def counter(m):
    prog = P.counter_prog(); L = len(prog)
    data = [0] + [1] * 8; dp = 0
    val = lambda d: sum((1 - d[1 + i]) << i for i in range(8))
    seq = []
    for k in range(1, 300):
        data, dp, _ = P.lockstep(m, prog, data, dp, L)
        assert dp == 0 and val(data) == k % 256, (k, val(data), dp)
    return L

def echo_copy(m):
    # echo: [out,in]; harness pokes `in` between passes
    prog = P.echo_prog(); L = len(prog); data = [1, 0]; dp = 0
    for bit in (1, 0, 0, 1, 1, 0):
        data[1] = bit
        data, dp, _ = P.lockstep(m, prog, data, dp, L)
        assert data[0] == bit and dp == 0
    # copy 8 bits: [d0 s0 d1 s1 ...], one bit per pass
    src = [1, 0, 1, 1, 0, 0, 1, 0]; dst0 = [1, 1, 0, 1, 0, 1, 1, 1]
    data = []; [data.extend([d, s]) for d, s in zip(dst0, src)]
    dp = 0
    for k in range(8):
        data, dp, _ = P.lockstep(m, P.copy_prog(), data, dp, L)
    assert data[0::2] == src and data[1::2] == src, data
    return L

def bb(m, ngroups=6):
    prog = P.bb22_prog(); L = len(prog)
    data, dp = P.bb22_tape(ngroups, 2)
    tm = make_bb22_tm(); cfg = TMConfig([0] * ngroups, 2, 'A')
    trace = run_tm(tm, cfg, 10, stop_on_halt=False)
    steps = 0
    for k in range(1, 9):
        data, dp, _ = P.lockstep(m, prog, data, dp, L)
        tape, hd, st = P.tm_view(data, ngroups)
        c = trace[k]
        assert tape == c.tape and st == ('HALT' if c.state == 'HALT' else c.state), (k, tape, st, c)
        if st != 'HALT': assert hd == c.head, (k, hd, c.head)
        if st != 'HALT': steps = k
    return L, steps + 1, tape

if __name__ == '__main__':
    m = Machine()
    print('counter: program length / ticks per increment', counter(m), '(256+ increments, wraps)')
    print('echo/copy: length', echo_copy(m))
    print('bb22: length, steps-to-halt, final tape', bb(m))
