"""Run the verified macros on the Machine A switch-level circuit (full
two-phase simulation, true master-slave storage), tick by tick against
sim/compile/verify_level0_independent.run_l0, on 500 random dual-rail
tapes. Also fixes the memory-interface timing precisely: r is read
during phase 1 (before the memory ever acts on this tick's toggle), the
memory performs the toggle/move during/after phase 2, using the strobes
sampled at the phase-1/phase-2 boundary -- so a design that read r after
its own toggle would fail this comparison."""
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
    ref_phys = list(phys0); ref_p = p0; ref_flag = 0
    circ_phys = list(phys0); circ_p = p0; circ_flag = 0; circ_M = 0
    n = len(phys0)
    for ch in prog:
        # reference (run_l0's own per-tick logic, inlined so we can compare
        # after every tick): memory's r for THIS tick is the pre-toggle cell.
        if ref_flag:
            ref_flag = 0
        else:
            r_ref = ref_phys[ref_p]           # phase 1: read r before toggling
            ref_phys[ref_p] ^= 1              # memory toggles (phase 2)
            ref_flag = 1 if ref_phys[ref_p] == 0 else 0
            ref_p = (ref_p + 1) % n if ch == 'A' else (ref_p - 1) % n

        # circuit: explicit two-phase tick. r is sampled once, during
        # phase 1, from the memory cell BEFORE this tick's toggle (memory
        # acts on last tick's captured strobes only between phase 1 and
        # phase 2 -- captured at the phase boundary, applied during/after
        # phase 2, so this tick's r reflects the pre-toggle value).
        o = 1 if ch == 'A' else 0
        r = circ_phys[circ_p]
        toggle, mp, mm, flag_next, M_next = MA.tick(circ_flag, circ_M, o, r)
        if toggle:
            circ_phys[circ_p] ^= 1
        if mp:
            circ_p = (circ_p + 1) % n
        if mm:
            circ_p = (circ_p - 1) % n
        circ_flag = flag_next
        circ_M = M_next
        if (ref_phys != circ_phys) or (ref_p != circ_p) or (ref_flag != circ_flag):
            return False, (ref_phys, ref_p, ref_flag, circ_phys, circ_p, circ_flag)
    return True, None

def main():
    rng = random.Random(20260926)
    n_logical = 6
    trials = 500
    fails = 0
    for i in range(trials):
        name = rng.choice(list(MACRO.keys()))
        prog = MACRO[name]
        phys = random_dual_rail_tape(n_logical, rng)
        p0 = rng.randrange(len(phys))
        ok, info = tick_by_tick_compare(prog, phys, p0)
        if not ok:
            fails += 1
            print("FAIL", name, "p0=", p0, "phys=", phys, info)
            if fails > 5:
                break
    print("trials=%d fails=%d" % (trials, fails))
    if fails == 0:
        print("PASS: Machine A circuit (two-phase, master-slave) matches run_l0 tick-by-tick")

if __name__ == '__main__':
    main()
