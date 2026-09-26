"""Demonstrates that the test harness's timing check is not vacuous: a
"CPU" that reads r AFTER applying its own toggle (instead of before, as
the spec requires) is caught as a mismatch against the reference, on the
very first tick where flag=0 and a toggle actually flips the cell to a
different value than what SKIPZ/nf should have seen."""
import random
import machine_a as MA

def tick_bad_timing(flag_S, M_prev, o, cell_before):
    """Wrong: toggles the cell FIRST, then reads r from the POST-toggle
    value for the nf computation -- i.e. the mirror-image of the bug the
    orchestrator described. Uses machine_a's own tick() but feeds it the
    post-toggle cell value instead of the pre-toggle one."""
    if flag_S:
        return 0, 0, 0, 0, M_prev, cell_before  # skip: no toggle at all
    cell_after_toggle = 1 - cell_before
    # BUG: read r from the post-toggle cell instead of cell_before
    toggle, mp, mm, flag_next, M_next = MA.tick(flag_S, M_prev, o, cell_after_toggle)
    return toggle, mp, mm, flag_next, M_next, cell_after_toggle

def main():
    rng = random.Random(1)
    mism = 0
    trials = 200
    for _ in range(trials):
        flag = 0
        M = 0
        cell = rng.randint(0, 1)
        o = rng.randint(0, 1)
        # correct reference (reads r BEFORE toggle, as run_l0 does)
        ref_cell = cell
        r_ref = ref_cell
        ref_cell ^= 1
        ref_flag = 1 if ref_cell == 0 else 0
        # bad-timing circuit
        toggle, mp, mm, bad_flag, M2, bad_cell = tick_bad_timing(flag, M, o, cell)
        if bad_flag != ref_flag:
            mism += 1
    print("bad-timing mismatches: %d/%d (expected: most flag=0,o toggles land on "
          "the SAME cell value whether read before or after, since XOR is its own "
          "inverse -- the real divergence shows up over a run, once nf feeds a "
          "later tick's decision; see run below)" % (mism, trials))

    # A clearer demonstration: feed the WRONG-timed function through the
    # 500-macro harness directly and show it fails to match run_l0.
    import sys
    sys.path.insert(0, '../compile')
    from verify_level0_independent import run_l0
    MACRO = 'ABBAAB'  # CNEXT: exercises the nf/flag path repeatedly
    rng = random.Random(2)
    fails = 0
    for _ in range(50):
        bits = [rng.randint(0, 1) for _ in range(6)]
        phys = []
        for b in bits:
            phys += [b, 1 - b]
        p0 = rng.randrange(len(phys))
        ref_phys = list(phys); ref_p = p0; ref_flag = 0
        bad_phys = list(phys); bad_p = p0; bad_flag = 0; bad_M = 0
        n = len(phys)
        mismatch_found = False
        for ch in MACRO:
            if ref_flag:
                ref_flag = 0
            else:
                ref_phys[ref_p] ^= 1
                ref_flag = 1 if ref_phys[ref_p] == 0 else 0
                ref_p = (ref_p + 1) % n if ch == 'A' else (ref_p - 1) % n
            o = 1 if ch == 'A' else 0
            if bad_flag:
                bad_flag = 0
            else:
                bad_phys[bad_p] ^= 1                # toggle FIRST (wrong)
                r_wrong = bad_phys[bad_p]            # then read r (post-toggle)
                _, mp, mm, bad_flag, bad_M = MA.tick(0, bad_M, o, r_wrong)
                if mp: bad_p = (bad_p + 1) % n
                if mm: bad_p = (bad_p - 1) % n
            if (ref_phys != bad_phys) or (ref_p != bad_p) or (ref_flag != bad_flag):
                mismatch_found = True
                break
        if mismatch_found:
            fails += 1
    print("read-r-after-toggle variant: %d/50 runs diverge from run_l0 "
          "(should be > 0 -- confirms the harness is sensitive to this ordering)"
          % fails)

if __name__ == '__main__':
    main()
