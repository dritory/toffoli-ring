"""Run test programs on the Machine B switch-level circuit (full
two-phase simulation), tick by tick against machine_b.reference, on 500
random single-rail tapes. Same memory timing as test_machine_a.py: r is
read during phase 1, before this tick's own toggle/move is applied."""
import random
import machine_b as MB

PROGRAMS = [
    ['FLIP', 'NEXT', 'FLIP', 'PREV'],
    ['SKIPZ', 'FLIP', 'NEXT', 'SKIPZ', 'FLIP', 'PREV'],
    ['NEXT', 'NEXT', 'SKIPZ', 'PREV', 'FLIP', 'SKIPZ', 'NEXT', 'FLIP'],
    ['SKIPZ', 'SKIPZ', 'FLIP', 'NEXT', 'PREV', 'SKIPZ', 'FLIP'],
]

def tick_by_tick_compare(prog, tape0, p0):
    ref_tape = list(tape0); ref_p = p0; ref_flag = 0
    circ_tape = list(tape0); circ_p = p0; circ_flag = 0; circ_M = 0
    n = len(tape0)
    for op in prog:
        r_ref = ref_tape[ref_p]
        t_ref, mp_ref, mm_ref, flag_ref_next = MB.reference(ref_flag, op, r_ref)
        if t_ref: ref_tape[ref_p] ^= 1
        if mp_ref: ref_p = (ref_p + 1) % n
        if mm_ref: ref_p = (ref_p - 1) % n
        ref_flag = flag_ref_next

        r_c = circ_tape[circ_p]
        t_c, mp_c, mm_c, flag_c_next, M_next = MB.tick(circ_flag, circ_M, op, r_c)
        if t_c: circ_tape[circ_p] ^= 1
        if mp_c: circ_p = (circ_p + 1) % n
        if mm_c: circ_p = (circ_p - 1) % n
        circ_flag = flag_c_next
        circ_M = M_next

        if (ref_tape != circ_tape) or (ref_p != circ_p) or (ref_flag != circ_flag):
            return False, (ref_tape, ref_p, ref_flag, circ_tape, circ_p, circ_flag)
    return True, None

def main():
    rng = random.Random(7654321)
    n = 8
    trials = 500
    fails = 0
    for i in range(trials):
        prog = rng.choice(PROGRAMS)
        tape = [rng.randint(0, 1) for _ in range(n)]
        p0 = rng.randrange(n)
        ok, info = tick_by_tick_compare(prog, tape, p0)
        if not ok:
            fails += 1
            print("FAIL", prog, "p0=", p0, "tape=", tape, info)
            if fails > 5:
                break
    print("trials=%d fails=%d" % (trials, fails))
    if fails == 0:
        print("PASS: Machine B circuit (two-phase, master-slave) matches spec reference")

if __name__ == '__main__':
    main()
