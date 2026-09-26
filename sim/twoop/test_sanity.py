"""
Sanity tests required by the task, run before any exhaustive search.

python3 test_sanity.py
"""
import sys

from machine import Bundle, Op, FLIP, MOVE, SKIP, ALWAYS, EQ0, EQ1, run_word
from enc import ENCODINGS


def mk_move(d, cond=ALWAYS):
    return Op(MOVE, dir=d, cond=cond)


def assert_true(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)
    print("PASS:", msg)


# ---------------------------------------------------------------------------
# Test 1: A = (flip, then +1), B = (-1), no skip, no encoding.
#   AB  is exact FLIP
#   ABA is exact NEXT
#   B   is exact PREV
# ---------------------------------------------------------------------------

A = Bundle((Op(FLIP), mk_move(+1)))
B = Bundle((mk_move(-1),))

g, template = ENCODINGS["none"]
W = 3 * g
ptr0 = g + 0  # rest = 0, only rest position for g=1

# Interpretation note: this pair has NO skip-test in either bundle, so the
# flag can never become 1 in any program built only from A and B (flag = 0
# is an invariant). The formal flag_in=1 exactness clause is therefore
# vacuous/unreachable for this pair; we test only flag_in=0 here, matching
# the task's own framing of this pair as the "near-solution" whose only gap
# is SKIPZ (which needs a skip-test to exist at all). We also record, for
# information, what flag_in=1 actually produces (it is NOT a no-op: a
# flagless pair's macros are only "exact" relative to the reachable flag=0
# state space).
flag_in1_is_identity_for_AB = True
for xl in (0, 1):
    for xc in (0, 1):
        for xr in (0, 1):
            win = list(template(xl)) + list(template(xc)) + list(template(xr))

            # flag_in = 0 branch: the primitives must hold exactly.
            w, p, f, ok = run_word([A, B], win, ptr0, 0)
            assert_true(ok, "AB stays in window (flag_in=0)")
            expected = list(template(xl)) + list(template(1 - xc)) + list(template(xr))
            assert_true(w == expected and p == ptr0 and f == 0,
                        f"AB: FLIP exact from flag_in=0 (xl={xl},xc={xc},xr={xr})")

            w, p, f, ok = run_word([A, B, A], win, ptr0, 0)
            assert_true(ok, "ABA stays in window (flag_in=0)")
            assert_true(w == win and p == ptr0 + g and f == 0,
                        f"ABA: NEXT exact from flag_in=0 (xl={xl},xc={xc},xr={xr})")

            w, p, f, ok = run_word([B], win, ptr0, 0)
            assert_true(ok, "B stays in window (flag_in=0)")
            assert_true(w == win and p == ptr0 - g and f == 0,
                        f"B: PREV exact from flag_in=0 (xl={xl},xc={xc},xr={xr})")

            # flag_in = 1 branch: unreachable in practice (no skip-test
            # anywhere in this pair), but check/record what it does.
            w1, p1, f1, ok1 = run_word([A, B], win, ptr0, 1)
            if not (ok1 and w1 == win and p1 == ptr0 and f1 == 0):
                flag_in1_is_identity_for_AB = False

print("Test 1 (base near-solution) passed for all 8 windows, flag_in=0.")
print(f"  (informational: flag_in=1 branch of AB is a pure no-op: {flag_in1_is_identity_for_AB} "
      f"-- expected False, since A's bundle would be skipped and B's -1 move still fires, "
      f"but this branch is unreachable for a pair with no skip-test at all)")

# ---------------------------------------------------------------------------
# Test 2: hand-checked dead ends.
#   B = (skip iff cell = 0, then -1) under (x,1), rest on x (rest=0):
#     AB is FLIP from flag_in=0 but FAILS from flag_in=1
#     ABAB is an identity word, but neither A.ABAB nor B.ABAB is FLIP
# ---------------------------------------------------------------------------

A2 = Bundle((Op(FLIP), mk_move(+1)))
B2 = Bundle((Op(SKIP, v=0), mk_move(-1)))

g2, template2 = ENCODINGS["(x,1)"]
assert g2 == 2
ptr0_2 = g2 + 0  # rest = 0 -> pointer on the x cell of the current group

# AB: check flag_in = 0 gives FLIP for every combo
ab_is_flip_flag0 = True
ab_is_flip_flag1 = True
for xl in (0, 1):
    for xc in (0, 1):
        for xr in (0, 1):
            win = list(template2(xl)) + list(template2(xc)) + list(template2(xr))
            w, p, f, ok = run_word([A2, B2], win, ptr0_2, 0)
            expected = list(template2(xl)) + list(template2(1 - xc)) + list(template2(xr))
            if not (ok and w == expected and p == ptr0_2 and f == 0):
                ab_is_flip_flag0 = False
            w1, p1, f1, ok1 = run_word([A2, B2], win, ptr0_2, 1)
            if not (ok1 and w1 == win and p1 == ptr0_2 and f1 == 0):
                ab_is_flip_flag1 = False

assert_true(ab_is_flip_flag0, "AB (dead-end pair) is FLIP from flag_in=0 under (x,1) rest=0")
assert_true(not ab_is_flip_flag1, "AB (dead-end pair) FAILS the flag_in=1 identity requirement (as documented)")

# ABAB should be an identity word (flag_in=0 -> no change, delta 0, flag 0)
abab_is_identity = True
for xl in (0, 1):
    for xc in (0, 1):
        for xr in (0, 1):
            win = list(template2(xl)) + list(template2(xc)) + list(template2(xr))
            w, p, f, ok = run_word([A2, B2, A2, B2], win, ptr0_2, 0)
            if not (ok and w == win and p == ptr0_2 and f == 0):
                abab_is_identity = False
assert_true(abab_is_identity, "ABAB (dead-end pair) is an identity word under (x,1) rest=0")

# neither A.ABAB nor B.ABAB is FLIP
for prefix_name, prefix in (("A.ABAB", [A2, A2, B2, A2, B2]), ("B.ABAB", [B2, A2, B2, A2, B2])):
    is_flip = True
    for xl in (0, 1):
        for xc in (0, 1):
            for xr in (0, 1):
                win = list(template2(xl)) + list(template2(xc)) + list(template2(xr))
                w, p, f, ok = run_word(prefix, win, ptr0_2, 0)
                expected = list(template2(xl)) + list(template2(1 - xc)) + list(template2(xr))
                if not (ok and w == expected and p == ptr0_2 and f == 0):
                    is_flip = False
                w1, p1, f1, ok1 = run_word(prefix, win, ptr0_2, 1)
                if not (ok1 and w1 == win and p1 == ptr0_2 and f1 == 0):
                    is_flip = False
    assert_true(not is_flip, f"{prefix_name} (dead-end pair) is NOT an exact FLIP")

print("Test 2 (hand-checked dead ends) passed.")

# ---------------------------------------------------------------------------
# Test 3: second hand-checked dead end.
#   B = (-1, then skip iff arrival = 0) under (1,x):
#     ABAB from x=0 branch is exactly the SKIPZ zero-branch, but the x=1
#     branch flips x and ends at -1 (i.e. ABAB is NOT an exact SKIPZ).
# ---------------------------------------------------------------------------

A3 = Bundle((Op(FLIP), mk_move(+1)))
B3 = Bundle((mk_move(-1), Op(SKIP, v=0)))

g3, template3 = ENCODINGS["(1,x)"]
ptr0_3 = g3 + 1  # rest on x (x is the second cell, index 1, of (1,x))

skipz_ok = True
zero_branch_ok = True
for xl in (0, 1):
    for xc in (0, 1):
        for xr in (0, 1):
            win = list(template3(xl)) + list(template3(xc)) + list(template3(xr))
            w, p, f, ok = run_word([A3, B3, A3, B3], win, ptr0_3, 0)
            expected_skipz_flag = 1 if xc == 0 else 0
            is_this_combo_skipz = ok and w == win and p == ptr0_3 and f == expected_skipz_flag
            if not is_this_combo_skipz:
                skipz_ok = False
            if xc == 0 and not is_this_combo_skipz:
                zero_branch_ok = False

assert_true(zero_branch_ok, "ABAB (2nd dead-end pair) matches SKIPZ on the x=0 branch under (1,x)")
assert_true(not skipz_ok, "ABAB (2nd dead-end pair) is NOT an exact SKIPZ (x=1 branch breaks it)")

print("Test 3 (2nd hand-checked dead end) passed.")
print()
print("ALL SANITY TESTS PASSED")
