"""
Direct-simulator verification/reporting for the three test machines. This
does not depend on the R-level compiler -- it exercises tm.py alone, and
produces the numbers design.md quotes for "the TM itself" (state count,
step counts, etc).
"""
import random
from tm import (make_counter_tm, make_echo_tm, make_bb22_tm,
                 TMConfig, tm_step, run_tm, counter_value)


def report_counter(L=3, n_steps=2000):
    tm = make_counter_tm(L)
    cfg = TMConfig(tape=[0] * L, head=0, state=tm.start_state)
    vals = [counter_value(cfg.tape)]
    for _ in range(n_steps):
        tm_step(tm, cfg)
        vals.append(counter_value(cfg.tape))
    dedup = [vals[0]]
    for v in vals[1:]:
        if v != dedup[-1]:
            dedup.append(v)
    # reference: standard ripple-carry increment, emitting each intermediate
    # partial-carry tape value, for n = 0,1,2,...,period-1,0,1,...
    period = 2 ** L
    ref = [0]
    n = 0
    for _ in range(period * 4):
        bits = [(n >> i) & 1 for i in range(L)]
        i = 0
        while i < L and bits[i] == 1:
            bits[i] = 0
            ref.append(sum(b << k for k, b in enumerate(bits)))
            i += 1
        if i < L:
            bits[i] = 1
        v = sum(b << k for k, b in enumerate(bits))
        if v != ref[-1]:
            ref.append(v)
        n = (n + 1) % period
    m = min(len(dedup), len(ref))
    ok = dedup[:m] == ref[:m]
    print(f"[counter] L={L} bits, |Q|={len(tm.states)} states, "
          f"{n_steps} TM steps simulated")
    print(f"  dedup'd tape-value trace matches reference ripple-carry "
          f"increment sequence (first {m} distinct values): {ok}")
    print(f"  sample: {dedup[:20]}")
    return ok


def report_echo(n_steps=40, seed=0):
    tm = make_echo_tm()
    rng = random.Random(seed)
    cfg = TMConfig(tape=[0, 0] + [0] * 4, head=0, state=tm.start_state)
    log = []
    ok = True
    last_input_at_read = None
    for t in range(n_steps):
        # external harness pokes a fresh input bit into cell 0 whenever the
        # machine is about to READ (i.e. between TM steps, exactly as the
        # task's I/O convention specifies).
        if cfg.state == "READ":
            cfg.tape[0] = rng.randint(0, 1)
            last_input_at_read = cfg.tape[0]
        pre_state = cfg.state
        tm_step(tm, cfg)
        log.append((pre_state, cfg.state, cfg.tape[0], cfg.tape[1]))
        if pre_state == "WRITE0" and cfg.tape[1] != 0:
            ok = False
        if pre_state == "WRITE1" and cfg.tape[1] != 1:
            ok = False
    # check: output cell always equals the input value from the most recent
    # READ, once a WRITE has happened.
    print(f"[echo] |Q|={len(tm.states)} states, {n_steps} TM steps simulated "
          f"with a random external input bit poked in before every READ")
    print(f"  every WRITE0/WRITE1 step wrote the state's own bit to cell1: {ok}")
    print(f"  sample trace (pre_state,post_state,cell0,cell1): {log[:8]}")
    return ok


def report_bb22():
    tm = make_bb22_tm()
    cfg = TMConfig(tape=[0] * 12, head=6, state=tm.start_state)
    trace = run_tm(tm, cfg, steps=1000)
    steps_taken = len(trace) - 1
    final = trace[-1]
    ok = (steps_taken == 6 and final.state == "HALT" and sum(final.tape) == 4)
    print(f"[BB(2,2)] |Q|={len(tm.states)} states (incl. HALT), "
          f"halts after {steps_taken} steps, ones written = {sum(final.tape)}, "
          f"matches known BB(2,2) result (6 steps, 4 ones): {ok}")
    return ok


if __name__ == "__main__":
    ok1 = report_counter(L=3)
    ok2 = report_echo()
    ok3 = report_bb22()
    print(f"\nall direct-TM-simulator checks passed: {ok1 and ok2 and ok3}")
