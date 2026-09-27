"""'Latches must hold with the clock stopped in any phase': feed the same
phase repeatedly (holding phi1 or phi2 asserted indefinitely instead of
alternating) with the same o,r and the previously-settled state fed back
as the seed each time, for both cmos machines, both phases, both flag
polarities. A genuine static latch reproduces itself indefinitely; a
capacitor-based or race-prone design would drift or raise."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import machine_cmos_ratioed as R
import machine_cmos_full as F

def check(mod, name):
    for phase_name, phase_fn in (('phi1', mod.phase1), ('phi2', mod.phase2)):
        for g in (0, 1):
            state = {'S': g, 'Sbar': 1 - g, 'DNODE': g, 'MBAR': 1 - g}
            for o in (0, 1):
                for r in (0, 1):
                    st = dict(state)
                    for rep in range(6):
                        st = phase_fn(o, r, st)
                    # compare against a 7th application: must be a fixed point
                    st2 = phase_fn(o, r, st)
                    for k in ('DNODE', 'MBAR', 'S', 'Sbar'):
                        assert st2[k] == st[k], \
                            (name, phase_name, g, o, r, k, st, st2)
    print("PASS %s: holds indefinitely under a stopped clock, both "
          "phases, both flag polarities, all (o,r)" % name)

if __name__ == '__main__':
    check(R, "cmos-ratioed")
    check(F, "cmos-full")
