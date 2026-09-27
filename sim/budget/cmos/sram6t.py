"""First test bed for cmos_sim.evaluate_cmos_static: the classic 6T SRAM
cell (2 cross-coupled CMOS inverters + 2 NMOS access transistors), pure
MOSFET, no resistors -- the textbook example of an allowed ratioed write
(strong NMOS access transistor overpowers the WEAK PMOS pull-up it is
writing against) and, mutated, of the two disallowed fight kinds the
extension must reject.

Cell (Q, QB cross-coupled; BL/BLB/WL modelled as ordinary fixed nets --
the write driver and address decoder are memory-interface circuitry,
outside the counted budget, exactly like o/r/phi1/phi2 elsewhere in this
project):

  PMOS1 gate=QB a=VDD b=Q   kind=p strength=weak   (keeper)
  NMOS1 gate=QB a=Q   b=GND kind=n strength=strong  (pull-down)
  PMOS2 gate=Q  a=VDD b=QB  kind=p strength=weak    (keeper)
  NMOS2 gate=Q  a=QB  b=GND kind=n strength=strong  (pull-down)
  ACC1  gate=WL a=BL  b=Q   kind=n strength=strong  (access)
  ACC2  gate=WL a=BLB b=QB  kind=n strength=strong  (access)

6 transistors, 0 resistors/capacitors/diodes -- matches "6T" exactly.
Each inverter never fights itself (PMOS/NMOS share a gate, exactly one
conducts), so the only ratioed fight is access-vs-keeper during a write
that changes the cell -- precisely the industry-standard 6T write
mechanism (the required "pull-up ratio": access transistor sized to
overpower the PMOS pull-up it opposes).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cmos_sim import evaluate_cmos_static

FEEDBACK = ['Q', 'QB']

def good_cell():
    return [
        ('QB', 'VDD', 'Q', 'p', 'weak'),    # PMOS1
        ('QB', 'Q', 'GND', 'n', 'strong'),  # NMOS1
        ('Q', 'VDD', 'QB', 'p', 'weak'),    # PMOS2
        ('Q', 'QB', 'GND', 'n', 'strong'),  # NMOS2
        ('WL', 'BL', 'Q', 'n', 'strong'),   # ACC1
        ('WL', 'BLB', 'QB', 'n', 'strong'), # ACC2
    ]

def bad_cell_strong_keeper():
    """Mutation: PMOS1's role rebuilt (wrongly) as an unconditionally-on
    STRONG pull-up instead of the correct weak keeper -- gate tied
    directly to GND-as-a-primary-input is not even needed: tying it to
    VDD (an NMOS, always on since gate=1 forever) makes the point just as
    well and needs no extra net. This directly fights ACC1 whenever a
    write tries to force Q low (WL=1, BL=0): both are 'strong', both are
    gated only by FIXED nets (VDD, WL), so neither can ever yield --
    a genuine, permanent short, not a transient Gauss-Seidel artifact."""
    return [
        ('VDD', 'Q', 'VDD', 'n', 'strong'), # bad "keeper": always on (gate=VDD=1 forever)
        ('QB', 'Q', 'GND', 'n', 'strong'),  # NMOS1 (unchanged)
        ('Q', 'VDD', 'QB', 'p', 'weak'),    # PMOS2
        ('Q', 'QB', 'GND', 'n', 'strong'),  # NMOS2
        ('WL', 'BL', 'Q', 'n', 'strong'),   # ACC1
        ('WL', 'BLB', 'QB', 'n', 'strong'), # ACC2
    ]

def settle(transistors, WL, BL, BLB, seed):
    fixed = {'WL': WL, 'BL': BL, 'BLB': BLB}
    return evaluate_cmos_static(transistors, fixed, FEEDBACK, seed)

def test_hold():
    for q in (0, 1):
        seed = {'Q': q, 'QB': 1 - q}
        # WL=0: access transistors open; BL/BLB left undriven (real SRAM
        # bit lines float or are precharged between accesses -- neither
        # is a gate anywhere here, so they need not resolve).
        got = settle(good_cell(), WL=0, BL=0, BLB=0, seed=seed)
        assert got['Q'] == q and got['QB'] == 1 - q, (q, got)
        # Re-run several times with the clock (WL) "stopped" at 0 and the
        # settled state fed back as the next seed: must reproduce itself
        # indefinitely, not drift.
        state = seed
        for _ in range(5):
            state = settle(good_cell(), WL=0, BL=0, BLB=0, seed=state)
            assert state['Q'] == q and state['QB'] == 1 - q
    print("PASS hold (both states, 5x repeated with WL held low)")

def test_write():
    for old_q in (0, 1):
        for new_q in (0, 1):
            seed = {'Q': old_q, 'QB': 1 - old_q}
            got = settle(good_cell(), WL=1, BL=new_q, BLB=1 - new_q, seed=seed)
            assert got['Q'] == new_q and got['QB'] == 1 - new_q, \
                (old_q, new_q, got)
    print("PASS write 0 and 1 (from both prior states, ratioed access "
          "beats weak keeper every time)")

def test_strong_strong_contention():
    seed = {'Q': 1, 'QB': 0}
    try:
        settle(bad_cell_strong_keeper(), WL=1, BL=0, BLB=1, seed=seed)
        raise AssertionError("expected a contention error, got none")
    except ValueError as e:
        assert 'strong-vs-strong' in str(e), e
        print("PASS strong-vs-strong contention correctly raised:", e)

def test_bad_keeper_loses_hold():
    """Same bad keeper, but WL=0 (no write in progress, just holding
    Q=0/QB=1): unlike a real contention error, this one does not surface
    as a raised exception -- the transient strong-vs-strong tie between
    the always-on bad "keeper" and NMOS1 (gated by QB=1) resolves itself
    over a few Gauss-Seidel passes exactly like the SRAM write's own
    transient tie does, but it settles to the WRONG state (Q snaps to 1
    unconditionally, since the always-on strong device beats NMOS1 the
    instant QB's own resolution lags by even one pass) -- i.e. the cell
    silently forgets Q=0 and always powers up as Q=1 regardless of
    history. This is exactly why the rule requires the keeper to be
    WEAK: a strong keeper does not just risk a one-off contention, it
    makes the node incapable of holding one of its two values at all."""
    seed = {'Q': 0, 'QB': 1}
    got = settle(bad_cell_strong_keeper(), WL=0, BL=0, BLB=0, seed=seed)
    assert got['Q'] == 1 and got['QB'] == 0, got
    print("PASS bad (strong) keeper demonstrably loses Q=0 on hold -- "
          "settles to Q=1 regardless of the seed, confirming the keeper "
          "must be weak, not just 'anything that beats a resistor'")

def test_weak_weak_contention():
    # Isolated minimal case (clearer than trying to force it out of the
    # cell's regenerative dynamics): a net pulled toward VDD only by a
    # permanently-on WEAK PMOS and toward GND only by a permanently-on
    # WEAK NMOS, both gated by fixed nets -- neither ever wins, and
    # nothing else drives the node, so it can never settle.
    bad = [
        ('GND', 'X', 'VDD', 'p', 'weak'),  # gate=GND(0): PMOS always on
        ('VDD', 'X', 'GND', 'n', 'weak'),  # gate=VDD(1): NMOS always on
    ]
    try:
        evaluate_cmos_static(bad, {}, [], {})
        raise AssertionError("expected a contention error, got none")
    except ValueError as e:
        assert 'weak-vs-weak' in str(e), e
        print("PASS weak-vs-weak contention correctly raised:", e)

if __name__ == '__main__':
    test_hold()
    test_write()
    test_strong_strong_contention()
    test_bad_keeper_loses_hold()
    test_weak_weak_contention()
    print("6T SRAM cell: all cmos_sim extension checks pass")
