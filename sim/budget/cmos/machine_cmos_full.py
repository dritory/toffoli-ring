"""Fully complementary (no ratioed fights anywhere) variant, for
comparison against machine_cmos_ratioed.py's 20-transistor pure-MOSFET
design. Same overall structure as Trick 3 (master folded into the
eval network's DNODE node, differential slave latch), but every place
that design relied on "strong beats weak" is rebuilt with true
complementary CMOS instead:

- The shared pass-transistor eval network (T_S/T_en/T_o/T_obar/T_r,
  a 1-of-3 demultiplexer fed from one shared enable chain) has no clean
  complementary dual -- the PMOS "mirror" of a shared-prefix demux is
  not a demux -- so it is rebuilt as 3 independent static CMOS NAND2
  gates instead: MOVE_P_N=NAND(g,o), MOVE_M_N=NAND(g,obar),
  DNODE_COMB=NAND(g,r) (same boolean functions machine_a11/Trick3 use,
  see results/budget/minimal.md). Losing the shared prefix is exactly
  why this variant costs more.
- The master and slave are each a standard transmission-gate latch with
  TWO inverters in its feedback loop, not one: `TG_write` copies the
  live input in; `INV1`'s output is both the latch's complementary
  output (MBAR, Sbar) AND feeds `INV2`, whose output is fed back into
  the storage node through `TG_hold`. (A single inverter's output fed
  straight back through a bare TG, with no second inversion, is not a
  latch at all -- it is exactly the 1-stage inverter-ring oscillator
  `results/budget/static.md`'s Trick-1 test already catches; it was
  tried first here and correctly rejected by `evaluate_cmos_static` as
  a genuine non-convergent oscillation, confirming the extension's
  oscillation check works on this new family of circuit too.) With two
  inversions in the loop, `TG_write` and `TG_hold` are gated by opposite
  (non-overlapping) clock phases, so they are never both closed at
  once -- true break-before-make, no fight ever exists to referee.

Every transistor here is plain CMOS logic strength (labelled 'strong'
throughout -- the label is irrelevant to correctness in this design,
since no two same-strength paths to different rails are ever
simultaneously closed by construction).

Transistor count: 3 NAND2 gates x 4 = 12, master latch
(TG_write+INV1+INV2+TG_hold = 8), slave latch (same shape = 8):
12 + 8 + 8 = 28 transistors, 0 resistors/capacitors/diodes -- 8 more
than the ratioed design's 20 (2 extra per latch stage over the naive
6T guess, and 2 latch stages), the real price of never allowing any
ratioed write: a genuinely break-before-make static latch needs two
inversions in its hold loop, not the single ratioed keeper Trick3 gets
away with.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cmos_sim import evaluate_cmos_static

def _nand2(gate_a, gate_b, out, series_node):
    """Standard static-CMOS NAND2: 2 series NMOS to GND, 2 parallel PMOS
    to VDD. Returns the 4 transistors."""
    return [
        (gate_a, out, series_node, 'n', 'strong'),
        (gate_b, series_node, 'GND', 'n', 'strong'),
        (gate_a, 'VDD', out, 'p', 'strong'),
        (gate_b, 'VDD', out, 'p', 'strong'),
    ]

def _inv(gate, out):
    return [
        (gate, 'VDD', out, 'p', 'strong'),
        (gate, out, 'GND', 'n', 'strong'),
    ]

def _tg(ctrl, ctrl_bar, a, b):
    """Transmission gate: NMOS gated by ctrl, PMOS gated by ctrl_bar, both
    bridging the same a<->b -- closed (passes a<->b) exactly when
    ctrl=1/ctrl_bar=0."""
    return [
        (ctrl, a, b, 'n', 'strong'),
        (ctrl_bar, a, b, 'p', 'strong'),
    ]

def build_transistors():
    t = []
    t += _nand2('S', 'o', 'MOVE_P_N', 'NA')
    t += _nand2('S', 'obar', 'MOVE_M_N', 'NB')
    t += _nand2('S', 'r', 'DNODE_COMB', 'NC')
    # master: samples DNODE_COMB during phi1, holds through phi2.
    # Loop has TWO inversions (DNODE->MBAR->DNODE_FB), so feeding
    # DNODE_FB back into DNODE is consistent (DNODE_FB == DNODE), not
    # an oscillator -- MBAR is the free complementary output, exactly
    # as Tm2 gave it "for free" in Trick3.
    t += _tg('phi1', 'phi1bar', 'DNODE_COMB', 'DNODE')  # TG_write_master
    t += _inv('DNODE', 'MBAR')                          # INV1_master
    t += _inv('MBAR', 'DNODE_FB')                       # INV2_master
    t += _tg('phi2', 'phi2bar', 'DNODE_FB', 'DNODE')    # TG_hold_master
    # slave: samples DNODE during phi2, holds through phi1
    t += _tg('phi2', 'phi2bar', 'DNODE', 'S')           # TG_write_slave
    t += _inv('S', 'Sbar')                              # INV1_slave
    t += _inv('Sbar', 'S_FB')                           # INV2_slave
    t += _tg('phi1', 'phi1bar', 'S_FB', 'S')            # TG_hold_slave
    return t

FEEDBACK = ['DNODE', 'MBAR', 'S', 'Sbar']

COMPONENTS = dict(transistors=28, resistors=0, capacitors=0, diodes=0)

def phase1(o, r, seed, transistors=None):
    fixed = {'o': o, 'obar': 1 - o, 'r': r,
             'phi1': 1, 'phi1bar': 0, 'phi2': 0, 'phi2bar': 1}
    return evaluate_cmos_static(transistors or build_transistors(), fixed,
                                 FEEDBACK, seed)

def phase2(o, r, seed, transistors=None):
    fixed = {'o': o, 'obar': 1 - o, 'r': r,
             'phi1': 0, 'phi1bar': 1, 'phi2': 1, 'phi2bar': 0}
    return evaluate_cmos_static(transistors or build_transistors(), fixed,
                                 FEEDBACK, seed)

def tick(state, o, r, transistors=None):
    n1 = phase1(o, r, state, transistors)
    g = state['S']
    toggle = g
    move_plus = 1 - n1['MOVE_P_N']
    move_minus = 1 - n1['MOVE_M_N']
    n2 = phase2(o, r, n1, transistors)
    next_state = {k: n2[k] for k in FEEDBACK}
    return toggle, move_plus, move_minus, next_state

def truth_table(transistors=None):
    rows = []
    for o in (0, 1):
        for r in (0, 1):
            for flag in (0, 1):
                g = 1 - flag
                state = {'S': g, 'Sbar': 1 - g, 'DNODE': g, 'MBAR': 1 - g}
                toggle, mp, mm, nstate = tick(state, o, r, transistors)
                g_next = nstate['S']
                flag_next = 1 - g_next
                if flag:
                    exp = (0, 0, 0, 0)
                else:
                    exp = (1, o, 1 - o, r)
                got = (toggle, mp, mm, flag_next)
                rows.append((o, r, flag, got, exp, got == exp))
    return rows

if __name__ == '__main__':
    print("cmos-fully-complementary machine components:", COMPONENTS,
          "total=", sum(COMPONENTS.values()))
    rows = truth_table()
    bad = [r for r in rows if not r[-1]]
    print("Truth table: %d/%d correct" % (len(rows) - len(bad), len(rows)))
    for r in bad:
        print("MISMATCH", r)
