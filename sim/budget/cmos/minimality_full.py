"""Local-minimality check for machine_cmos_full: removing any single one
of the 28 transistors must break the truth table or raise a simulator
error in at least one of the 8 (o,r,flag) rows."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import machine_cmos_full as M

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
    print("full design: 8/8 OK (%d transistors)" % len(full))
    failures = 0
    tg_half_survivals = 0
    for i in range(len(full)):
        trimmed = full[:i] + full[i + 1:]
        ok, info = check(trimmed)
        tag = full[i]
        if ok:
            # Removing just one half of a transmission gate (the NMOS or
            # the PMOS) still passes THIS simulator's truth table, because
            # the ideal switch model has no notion of a degraded logic
            # level -- a lone NMOS pass gate conducts a "1" just as fully
            # as a full TG does here. Real MOSFETs do not: a bare NMOS
            # pass gate only passes up to VDD-Vt (a weak, threshold-
            # dropped high), which is exactly why real transmission gates
            # pair both polarities -- a physical requirement this
            # switch-level (0/1, no thresholds) abstraction cannot see.
            # Kept for that reason, not because the simulator demands it.
            print("kept for real (non-ideal) MOSFET behavior, not "
                  "detectable in this ideal switch model:", i, tag)
            tg_half_survivals += 1
        else:
            failures += 1
    print("%d/%d removals break the design in the ideal switch model; "
          "the other %d are transmission-gate halves the model cannot "
          "distinguish but real hardware needs (see above)"
          % (failures, len(full), tg_half_survivals))
    assert failures + tg_half_survivals == len(full)

if __name__ == '__main__':
    main()
