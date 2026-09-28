"""Verification of machine_jump_labeled.py against jump_ref.tick_labeled:
  1. Exhaustive truth table over (instruction, r, mode, label register,
     instruction's own label field) -- 4 modes x 4 TL x 7 instructions x
     4 label fields x 2 r = 896 cases.
  2. Tick-by-tick switch-level vs reference on 500 random programs
     (2 distinct labels, so nesting is actually exercised) and data
     tapes, short rings so seeks routinely wrap around.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import machine_jump_labeled as M
import jump_ref as R

MODES = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]

def circ_state_for(SF, SB, SK, TL):
    st = {}
    for pfx, val in (('SF', SF), ('SB', SB), ('SK', SK)):
        st[pfx + '_S'] = val; st[pfx + '_SB'] = 1 - val
        st[pfx + '_M'] = val; st[pfx + '_MB'] = 1 - val
    t1, t0 = (TL >> 1) & 1, TL & 1
    for pfx, val in (('TL1', t1), ('TL0', t0)):
        st[pfx + '_S'] = val; st[pfx + '_SB'] = 1 - val
        st[pfx + '_M'] = val; st[pfx + '_MB'] = 1 - val
    return st

def truth_table():
    rows = []
    for SF, SB, SK in MODES:
        for TL in range(4):
            for op in R.OPS:
                for A in range(4):
                    for r in (0, 1):
                        opcode = R.encode(op, A)
                        ref_state = {'SF': SF, 'SB': SB, 'SK': SK, 'TL': TL}
                        ref_out = R.tick_labeled(ref_state, opcode, r)
                        circ_out = M.tick(circ_state_for(SF, SB, SK, TL), opcode, r)
                        rt, rmp, rmm, rpp, rpm, rns = ref_out
                        ct, cmp_, cmm, cpp, cpm, cns = circ_out
                        c_sf, c_sb, c_sk = M.mode_of(cns)
                        c_tl = M.label_of(cns)
                        ok = ((rt, rmp, rmm, rpp, rpm) == (ct, cmp_, cmm, cpp, cpm)
                              and rns['SF'] == c_sf and rns['SB'] == c_sb
                              and rns['SK'] == c_sk and rns['TL'] == c_tl)
                        rows.append(((SF, SB, SK, TL), op, A, r, ref_out, circ_out, ok))
    return rows

def random_program(rng, n):
    prog = []
    for _ in range(n):
        u = rng.random()
        label = rng.choice([1, 2])  # 2 distinct labels -> real nesting
        if u < 0.20:
            op = 'MK'
        elif u < 0.30:
            op = 'JF'
        elif u < 0.40:
            op = 'JB'
        elif u < 0.55:
            op = 'K'
        else:
            op = rng.choice(['F', 'N', 'P'])
            label = 0
        prog.append(R.encode(op, label))
    return prog

def tick_by_tick_compare(prog, data0, prog_p0, data_p0, ticks):
    ref_state = R.initial_state_labeled()
    circ_state = M.initial_state()
    ref_data = list(data0); circ_data = list(data0)
    ref_pp = prog_p0; circ_pp = prog_p0
    ref_dp = data_p0; circ_dp = data_p0
    n_prog = len(prog); n_data = len(data0)
    for t in range(ticks):
        assert ref_pp == circ_pp, "program pointer desync before tick %d" % t
        opcode = prog[ref_pp]
        r_ref = ref_data[ref_dp]
        r_circ = circ_data[circ_dp]
        assert r_ref == r_circ, "harness desync before tick %d" % t
        r = r_ref
        rt, rmp, rmm, rpp, rpm, ref_state = R.tick_labeled(ref_state, opcode, r)
        ct, cmp_, cmm, cpp, cpm, circ_state = M.tick(circ_state, opcode, r)
        if (rt, rmp, rmm, rpp, rpm) != (ct, cmp_, cmm, cpp, cpm):
            return False, ('signal mismatch', t, (rt, rmp, rmm, rpp, rpm),
                            (ct, cmp_, cmm, cpp, cpm))
        if rt: ref_data[ref_dp] ^= 1
        if ct: circ_data[circ_dp] ^= 1
        if rmp: ref_dp = (ref_dp + 1) % n_data
        if rmm: ref_dp = (ref_dp - 1) % n_data
        if cmp_: circ_dp = (circ_dp + 1) % n_data
        if cmm: circ_dp = (circ_dp - 1) % n_data
        if rpp: ref_pp = (ref_pp + 1) % n_prog
        if rpm: ref_pp = (ref_pp - 1) % n_prog
        if cpp: circ_pp = (circ_pp + 1) % n_prog
        if cpm: circ_pp = (circ_pp - 1) % n_prog
        if ref_data != circ_data or ref_dp != circ_dp or ref_pp != circ_pp:
            return False, ('state mismatch', t, ref_data, ref_dp, ref_pp,
                            circ_data, circ_dp, circ_pp)
        if (ref_state['SF'], ref_state['SB'], ref_state['SK'], ref_state['TL']) != \
           (M.mode_of(circ_state) + (M.label_of(circ_state),)):
            return False, ('mode/label mismatch', t, ref_state, circ_state)
    return True, None

def random_trials(trials=500, seed=20260928):
    rng = random.Random(seed)
    fails = 0
    for i in range(trials):
        n_prog = rng.randint(5, 16)
        n_data = rng.randint(4, 10)
        prog = random_program(rng, n_prog)
        data0 = [rng.randint(0, 1) for _ in range(n_data)]
        prog_p0 = rng.randrange(n_prog)
        data_p0 = rng.randrange(n_data)
        ticks = 60
        ok, info = tick_by_tick_compare(prog, data0, prog_p0, data_p0, ticks)
        if not ok:
            fails += 1
            print("FAIL trial", i, info)
            if fails > 5:
                break
    return trials, fails

if __name__ == '__main__':
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Truth table: %d/%d correct" % (len(rows) - len(bad), len(rows)))
    for r in bad[:10]:
        print("MISMATCH", r)

    trials, fails = random_trials()
    print("random trials=%d fails=%d" % (trials, fails))
    if fails == 0 and not bad:
        print("PASS: machine_jump_labeled matches jump_ref exactly")
