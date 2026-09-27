"""Local-minimality check for machine_cmos_ratioed: removing any single
one of the 20 transistors must break the truth table or raise a
simulator error (floating net / contention / oscillation) in at least
one of the 8 (o,r,flag) rows."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import machine_cmos_ratioed as M

def check(transistors):
    try:
        rows = M.truth_table(transistors)
    except (ValueError, KeyError) as e:
        return False, str(e)
    bad = [r for r in rows if not r[-1]]
    return (len(bad) == 0), bad

def main():
    full = M.build_transistors()
    ok_full, info = check(full)
    assert ok_full, ("full design itself failed:", info)
    print("full design: 8/8 OK")
    failures = 0
    for i in range(len(full)):
        trimmed = full[:i] + full[i + 1:]
        ok, info = check(trimmed)
        tag = full[i]
        if ok:
            print("STILL WORKS without removing", i, tag, "-- NOT locally minimal!")
        else:
            failures += 1
    print("%d/%d single-component removals break the design (local "
          "minimality holds)" % (failures, len(full)))
    assert failures == len(full)

if __name__ == '__main__':
    main()
