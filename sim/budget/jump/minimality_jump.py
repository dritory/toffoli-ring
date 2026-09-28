"""Local minimality: remove each transistor one at a time and check the
design still passes. Single-level variant (152T): full 56-case
exhaustive truth table per removal (cheap enough). Labelled variant
(270T): a 40-case representative subset per removal (every mode x
opcode combination, 2 label values, both r values) -- not the full 896,
to keep this tractable; noted in results/budget/jump.md."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import machine_jump as M
import machine_jump_labeled as ML
import jump_ref as R
from test_machine_jump import circ_state_for as circ_state_for_single, MODES
from test_machine_jump_labeled import circ_state_for as circ_state_for_labeled

def check_single(transistors):
    for SF, SB, SK in MODES:
        for op in R.OPS:
            for r in (0, 1):
                opcode = R.encode(op)
                ref = R.tick({'SF': SF, 'SB': SB, 'SK': SK}, opcode, r)
                try:
                    circ = M.tick_with(circ_state_for_single(SF, SB, SK), opcode, r,
                                        transistors)
                except Exception:
                    return False
                if ref[:5] != circ[:5]:
                    return False
                c_sf, c_sb, c_sk = M.mode_of(circ[5])
                if (ref[5]['SF'], ref[5]['SB'], ref[5]['SK']) != (c_sf, c_sb, c_sk):
                    return False
    return True

def check_labeled(transistors):
    modes = MODES
    for SF, SB, SK in modes:
        for TL in (0, 3):
            for op in R.OPS:
                for A in (0, 3):
                    for r in (0, 1):
                        opcode = R.encode(op, A)
                        ref_state = {'SF': SF, 'SB': SB, 'SK': SK, 'TL': TL}
                        ref = R.tick_labeled(ref_state, opcode, r)
                        try:
                            circ = ML.tick_with(circ_state_for_labeled(SF, SB, SK, TL),
                                                 opcode, r, transistors)
                        except Exception:
                            return False
                        if ref[:5] != circ[:5]:
                            return False
                        c_sf, c_sb, c_sk = ML.mode_of(circ[5])
                        c_tl = ML.label_of(circ[5])
                        if (ref[5]['SF'], ref[5]['SB'], ref[5]['SK'], ref[5]['TL']) != \
                           (c_sf, c_sb, c_sk, c_tl):
                            return False
    return True

def minimality(build, check, feedback):
    full = build()
    n = len(full)
    breaks = 0
    survivors = []
    for i in range(n):
        reduced = full[:i] + full[i + 1:]
        try:
            ok = check(reduced)
        except Exception:
            ok = False
        if ok:
            survivors.append((i, full[i]))
        else:
            breaks += 1
    return n, breaks, survivors

if __name__ == '__main__':
    n, breaks, survivors = minimality(lambda: M.TRANSISTORS, check_single, M.FEEDBACK)
    print("single-level: %d/%d removals break the design" % (breaks, n))
    for i, t in survivors:
        print("  SURVIVES removal:", i, t)

    n2, breaks2, survivors2 = minimality(lambda: ML.TRANSISTORS, check_labeled, ML.FEEDBACK)
    print("labelled (40-case subset): %d/%d removals break the design" % (breaks2, n2))
    for i, t in survivors2:
        print("  SURVIVES removal:", i, t)
