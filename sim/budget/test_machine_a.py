"""Run the verified macros on the Machine A switch-level circuit, tick by
tick against sim/compile/verify_level0_independent.run_l0, on 500 random
dual-rail tapes."""
import random
import sys
sys.path.insert(0, '../compile')
from verify_level0_independent import run_l0
import machine_a as MA

MACRO = {'FLIP': 'ABB', 'NEXT': 'ABBAAA', 'PREV': 'BAABBBABBABB',
         'CNEXT': 'ABBAAB', 'CPREV': 'ABBABABAABBB'}

def random_dual_rail_tape(n_logical, rng):
    bits = [rng.randint(0, 1) for _ in range(n_logical)]
    phys = []
    for b in bits:
        phys += [b, 1 - b]
    return phys

def tick_by_tick_compare(prog, phys0, p0):
    """Steps both simulators one instruction at a time, comparing state
    after every tick. phys0 is copied for each simulator."""
    ref_phys = list(phys0); ref_p = p0; ref_flag = 0
    circ_phys = list(phys0); circ_p = p0; circ_S = 1
    n = len(phys0)
    for ch in prog:
        # reference (run_l0's own per-tick logic, inlined so we can compare after each tick)
        if ref_flag:
            ref_flag = 0
        else:
            ref_phys[ref_p] ^= 1
            ref_flag = 1 if ref_phys[ref_p] == 0 else 0
            ref_p = (ref_p + 1) % n if ch == 'A' else (ref_p - 1) % n
        # circuit
        o = 1 if ch == 'A' else 0
        r = circ_phys[circ_p]
        toggle, mp, mm, S_next = MA.tick(circ_S, o, r)
        if toggle:
            circ_phys[circ_p] ^= 1
        if mp:
            circ_p = (circ_p + 1) % n
        if mm:
            circ_p = (circ_p - 1) % n
        circ_S = S_next
        circ_flag = 1 - circ_S
        if (ref_phys != circ_phys) or (ref_p != circ_p) or (ref_flag != circ_flag):
            return False, (ref_phys, ref_p, ref_flag, circ_phys, circ_p, circ_flag)
    return True, None

def main():
    rng = random.Random(20260926)
    n_logical = 6  # ring of 6 logical bits = 12 physical cells
    trials = 500
    fails = 0
    for i in range(trials):
        name = rng.choice(list(MACRO.keys()))
        prog = MACRO[name]
        phys = random_dual_rail_tape(n_logical, rng)
        p0 = rng.randrange(len(phys))
        # p0 must be even (points at a logical-bit's "true" cell) to match how
        # run_l0/verify_sweep normally position the pointer; but run_l0 itself
        # works from any starting cell, so we allow any p0.
        ok, info = tick_by_tick_compare(prog, phys, p0)
        if not ok:
            fails += 1
            print("FAIL", name, "p0=", p0, "phys=", phys, info)
            if fails > 5:
                break
    print("trials=%d fails=%d" % (trials, fails))
    if fails == 0:
        print("PASS: Machine A circuit matches run_l0 tick-by-tick on all trials")

if __name__ == '__main__':
    main()
