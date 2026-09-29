"""The four programs on every machine model (each in lock step with ref.py):
NMOS (full), CMOS (full), NMOS skip-one is a different ISA (not run), LED-DTL
analog (reduced amount of work: it solves a nonlinear DC point per phase)."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import programs as P, ref as R
from tm import make_bb22_tm, TMConfig, run_tm

def val(d): return sum((1 - d[1 + i]) << i for i in range(8))

def run(name, m, n_inc, n_echo, n_tm):
    t0 = time.time()
    prog = P.counter_prog(); L = len(prog); data = [0] + [1] * 8; dp = 0
    for k in range(1, n_inc + 1):
        data, dp, _ = P.lockstep(m, prog, data, dp, L); assert val(data) == k % 256 and dp == 0
    prog = P.echo_prog(); data = [1, 0]; dp = 0
    for bit in [1, 0, 0, 1, 1, 0][:n_echo]:
        data[1] = bit; data, dp, _ = P.lockstep(m, prog, data, dp, len(prog)); assert data[0] == bit
    src = [1, 0, 1, 1, 0, 0, 1, 0]; dst0 = [1, 1, 0, 1, 0, 1, 1, 1]; data = []
    [data.extend([d, s]) for d, s in zip(dst0, src)]; dp = 0
    for k in range(8): data, dp, _ = P.lockstep(m, P.copy_prog(), data, dp, 10)
    assert data[0::2] == src
    prog = P.bb22_prog(); L = len(prog); data, dp = P.bb22_tape(6, 2)
    tr = run_tm(make_bb22_tm(), TMConfig([0] * 6, 2, 'A'), 10, stop_on_halt=False)
    for k in range(1, n_tm + 1):
        data, dp, _ = P.lockstep(m, prog, data, dp, L)
        tape, hd, st = P.tm_view(data, 6)
        assert tape == tr[k].tape and st == tr[k].state, (k, tape, st)
    print('%-8s counter x%d incr, echo x%d, copy 8 bits, BB(2,2) x%d steps: all lock-step OK (%.0fs)'
          % (name, n_inc, n_echo, n_tm, time.time() - t0), flush=True)

if __name__ == '__main__':
    from machine_nmos import Machine as MN
    from machine_cmos import Machine as MC
    from machine_dtl import Machine as MD
    run('NMOS', MN(), 300, 6, 8)
    run('CMOS', MC('tg'), 300, 6, 8)
    run('LED-DTL', MD(True), 3, 3, 2)
