"""Reproduces the ORIGINAL (wrong) single-capacitor design directly
against the corrected switchsim.evaluate() and shows it is rejected.
Kept as a standing regression check: if someone "simplifies" the master-
slave cell back down to one capacitor, this is what should happen."""
from switchsim import evaluate

# Single capacitor S, T1..T4 always live (not phase-gated), T5 (write,
# gate=phi_write) shorts the eval network's own output straight back
# into S -- no buffer, no second storage node.
BUGGY_TRANSISTORS = [
    ('S', 'K', 'GND'),
    ('o', 'MOVE_P_N', 'K'),
    ('obar', 'MOVE_M_N', 'K'),
    ('r', 'DNODE', 'K'),
    ('phi_write', 'DNODE', 'S'),   # T5: the bug
]
BUGGY_RESISTORS = [('MOVE_P_N', 1), ('MOVE_M_N', 1), ('DNODE', 1)]

def main():
    try:
        net = evaluate(BUGGY_TRANSISTORS, BUGGY_RESISTORS,
                        {'o': 0, 'obar': 1, 'r': 1, 'phi_write': 1})
        print("BUG NOT CAUGHT (should not happen):", net.get('S'), net.get('DNODE'))
    except ValueError as e:
        print("Correctly rejected the single-capacitor design:", e)

if __name__ == '__main__':
    main()
