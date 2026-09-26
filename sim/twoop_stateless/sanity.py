"""Sanity checks required by the task, run before the exhaustive search."""

from model import apply_letter, materialize, decode3, check_target, VALUATIONS


def test_ab_is_flip():
    """
    A = (flip, then +1 iff new value = 1)
    B = (-1 iff cell = 1)
    encoding (x,1), rest on x (rest=0).
    Claim: AB is exact FLIP.
    """
    A = (True, +1, 1, 'FM')
    B = (False, -1, 1, None)
    pattern = ('x', '1')
    g = 2
    rest = 0
    start_ptr = g + rest  # = 2, the x-cell of the middle group

    all_ok = True
    details = []
    for xl, xm, xr in VALUATIONS:
        tape = materialize(xl, pattern) + materialize(xm, pattern) + materialize(xr, pattern)
        ptr = start_ptr
        for letter, bundle in (('A', A), ('B', B)):
            res = apply_letter(bundle, tape, ptr)
            if res is None:
                all_ok = False
                details.append((xl, xm, xr, 'LEFT WINDOW'))
                break
            tape, ptr = res
        else:
            d = decode3(tape, pattern, g)
            ok = (d is not None and d[0] == xl and d[2] == xr and d[1] == (1 - xm) and ptr == start_ptr)
            all_ok = all_ok and ok
            details.append((xl, xm, xr, d, ptr, ok))

    # Also run through the generic check_target machinery for a second,
    # independent confirmation.
    states = []
    for xl, xm, xr in VALUATIONS:
        tape = materialize(xl, pattern) + materialize(xm, pattern) + materialize(xr, pattern)
        ptr = start_ptr
        for letter, bundle in (('A', A), ('B', B)):
            tape, ptr = apply_letter(bundle, tape, ptr)
        states.append((tuple(tape), ptr))
    generic_ok = check_target('FLIP', states, start_ptr, g, pattern, VALUATIONS)

    return all_ok and generic_ok, details


def test_crossing_cost():
    """
    Claim: A = (flip, +1 iff new = 1) costs one letter on a 0-cell and two
    letters on a 1-cell to cross, both left as 1.
    Interpreted on a bare 3-cell window [c0, c1, c2] with pointer starting
    at c1 (no encoding needed for this local claim -- it's about A alone
    repeatedly applied to a single starting cell value).
    """
    A = (True, +1, 1, 'FM')
    results = {}
    for start_val in (0, 1):
        tape = [0, start_val, 0]
        ptr = 1
        steps = 0
        crossed = False
        for _ in range(4):
            res = apply_letter(A, tape, ptr)
            steps += 1
            if res is None:
                break
            tape, ptr = res
            if ptr != 1:
                crossed = True
                break
        # value left behind at the original cell (index 1)
        left_value = tape[1]
        results[start_val] = (steps, crossed, left_value)
    ok = (results[0][0] == 1 and results[0][1] and results[0][2] == 1 and
          results[1][0] == 2 and results[1][1] and results[1][2] == 1)
    return ok, results


def run_all():
    print("=== Sanity test 1: AB is exact FLIP under (x,1), rest=x ===")
    ok1, details1 = test_ab_is_flip()
    print("PASS" if ok1 else "FAIL")
    for row in details1:
        print("  ", row)

    print()
    print("=== Sanity test 2: crossing cost of A=(flip,+1 iff new=1) ===")
    ok2, results2 = test_crossing_cost()
    print("PASS" if ok2 else "FAIL")
    for k, v in results2.items():
        print(f"  start={k}: steps_to_cross={v[0]} crossed={v[1]} left_value={v[2]}")

    return ok1, ok2


if __name__ == '__main__':
    run_all()
