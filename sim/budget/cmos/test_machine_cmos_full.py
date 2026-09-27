"""500-random-tape tick-by-tick check of machine_cmos_full against
run_l0, same harness as test_machine_cmos_ratioed.py."""
import random
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'compile'))
from verify_level0_independent import run_l0
import machine_cmos_full as M

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
    circ_phys = list(phys0); circ_p = p0
    circ_state = {'S': 1, 'Sbar': 0, 'DNODE': 1, 'MBAR': 0}  # g=1 (flag=0)
    n = len(phys0)
    for ch in prog:
        if ref_flag:
            ref_flag = 0
        else:
            r_ref = ref_phys[ref_p]
            ref_phys[ref_p] ^= 1
            ref_flag = 1 if ref_phys[ref_p] == 0 else 0
            ref_p = (ref_p + 1) % n if ch == 'A' else (ref_p - 1) % n

        o = 1 if ch == 'A' else 0
        r = circ_phys[circ_p]
        toggle, mp, mm, nstate = M.tick(circ_state, o, r)
        if toggle:
            circ_phys[circ_p] ^= 1
        if mp:
            circ_p = (circ_p + 1) % n
        if mm:
            circ_p = (circ_p - 1) % n
        circ_state = nstate
        circ_flag = 1 - circ_state['S']
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
        print("PASS: cmos-fully-complementary machine matches run_l0 "
              "tick-by-tick")

if __name__ == '__main__':
    main()
