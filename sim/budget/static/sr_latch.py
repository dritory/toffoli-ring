"""Test bed for switchsim's static-feedback extension (evaluate_static),
tried first on a plain resistor-load cross-coupled SR latch (Trick 1):

  T_Q    gate=Qbar  a=Q     b=GND      R_Q:    Q->VDD
  T_Qbar gate=Q     a=Qbar  b=GND      R_Qbar: Qbar->VDD
  T_set  gate=S     a=Qbar  b=GND      (pull-down write: S=1 -> Q:=1)
  T_rst  gate=R     a=Q     b=GND      (pull-down write: R=1 -> Q:=0)

2 transistors + 2 resistors for the bistable pair itself, no sizing
dependence (per switchsim's ratioed rule: a closed transistor path to a
rail always beats a resistor, never "the bigger one wins"). T_set/T_rst
are the 2 extra write pull-downs mentioned in the brief -- not counted
as part of the latch primitive itself, just the harness used to drive it
in this test.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import evaluate_static

TRANSISTORS = [
    ('Qbar', 'Q', 'GND'),      # T_Q
    ('Q', 'Qbar', 'GND'),      # T_Qbar
    ('S', 'Qbar', 'GND'),      # T_set
    ('R', 'Q', 'GND'),         # T_rst
]
RESISTORS = [('Q', 1), ('Qbar', 1)]
FEEDBACK = ['Q', 'Qbar']

def step(S, R, seed):
    return evaluate_static(TRANSISTORS, RESISTORS, {'S': S, 'R': R},
                            FEEDBACK, seed)

def main():
    # Hold: S=R=0 must reproduce whatever Q/Qbar already were.
    seed = {'Q': 1, 'Qbar': 0}
    known = step(0, 0, seed)
    assert (known['Q'], known['Qbar']) == (1, 0), known
    seed = {'Q': 0, 'Qbar': 1}
    known = step(0, 0, seed)
    assert (known['Q'], known['Qbar']) == (0, 1), known
    print("hold: OK (both states reproduce themselves with S=R=0)")

    # Set / reset from either starting state.
    for start in ({'Q': 0, 'Qbar': 1}, {'Q': 1, 'Qbar': 0}):
        known = step(1, 0, start)
        assert (known['Q'], known['Qbar']) == (1, 0), (start, known)
        known = step(0, 1, start)
        assert (known['Q'], known['Qbar']) == (0, 1), (start, known)
    print("set/reset: OK from both starting states")

    # S=R=1 (both asserted): NOR-style latch forces Q=Qbar=0, an invalid
    # (non-complementary) state -- not itself a stable point of the S=R=0
    # circuit that follows it.
    known = step(1, 1, {'Q': 1, 'Qbar': 0})
    assert (known['Q'], known['Qbar']) == (0, 0), known
    print("S=R=1: OK, forces Q=Qbar=0 (invalid/non-complementary), as expected")

    # Race: release S=R=1 -> S=R=0 simultaneously, seeded from the
    # invalid Q=Qbar=0 state. Two stable points exist for S=R=0
    # ((1,0) and (0,1)) and the seed (0,0) is neither -- must raise.
    try:
        step(0, 0, {'Q': 0, 'Qbar': 0})
        print("RACE NOT CAUGHT (should not happen)")
        raise SystemExit(1)
    except ValueError as e:
        assert 'race' in str(e) or 'metastable' in str(e) or 'oscillation' in str(e), e
        print("race/metastability on simultaneous S=R=1 release: correctly caught:")
        print(" ", e)

    # Oscillation check: a 1-stage inverter ring, Y := NOT(Y) (CMOS
    # inverter, gate=Y for both the PMOS pull-up and the NMOS pull-down,
    # output shorted back to the input) has NO stable point at all --
    # every value of Y demands the opposite value next pass. Must be
    # reported as non-convergence, not silently settle on one value.
    ring_t = [('Y', 'VDD', 'Y', 'p'), ('Y', 'Y', 'GND', 'n')]
    try:
        evaluate_static(ring_t, [], {}, ['Y'], {'Y': 0})
        print("OSCILLATION NOT CAUGHT (should not happen)")
        raise SystemExit(1)
    except ValueError as e:
        print("1-stage inverter ring (Y := NOT Y): correctly caught:", e)

    # Floating-net check: a transistor gated by a net nobody drives (not
    # fixed, not a feedback net, not resistor-loaded) must still be
    # rejected, same as evaluate()'s "no implicit storage" rule.
    stray_t = TRANSISTORS + [('GHOST', 'Q', 'Qbar')]  # GHOST never given a value
    try:
        evaluate_static(stray_t, RESISTORS, {'S': 0, 'R': 0}, FEEDBACK,
                         {'Q': 1, 'Qbar': 0})
        print("FLOATING NET NOT CAUGHT (should not happen)")
        raise SystemExit(1)
    except ValueError as e:
        assert 'floating' in str(e), e
        print("floating gate net (GHOST): correctly caught:", e)

if __name__ == '__main__':
    main()
