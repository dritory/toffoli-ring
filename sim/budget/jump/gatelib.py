"""Reusable static-CMOS gate/latch builders, shared by both jump-machine
variants. Same conventions as machine_cmos_full.py: transistor tuple
(gate, a, b, kind, strength), all 'strong' (no ratioed fights anywhere).

Only three families are needed:
  _inv   -- plain inverter (2T)
  _tg    -- transmission gate (2T)
  _aoi   -- general AND-OR-INVERT: out = NOT(OR_i AND(terms[i])).
            A single one-literal-per-term-of-1 case is a NOR; a single
            term is a NAND. This one function builds all of NOR2/3/4,
            NAND2/3/4/5 and every genuine AOIxx this design needs, with
            the standard series-parallel / parallel-series CMOS dual
            (2 transistors per literal, no more).
  _regbit -- one bit of static master-slave storage, literally
            machine_cmos_full.py's DNODE/MBAR/S/Sbar structure (8T
            master + 8T slave = 16T), replicated under a name prefix so
            several independent state bits can share the same phi1/phi2
            clock nets.
"""

def _inv(gate, out):
    return [
        (gate, 'VDD', out, 'p', 'strong'),
        (gate, out, 'GND', 'n', 'strong'),
    ]

def _tg(ctrl, ctrl_bar, a, b):
    return [
        (ctrl, a, b, 'n', 'strong'),
        (ctrl_bar, a, b, 'p', 'strong'),
    ]

def _aoi(terms, out):
    """out = NOT(OR_i AND(terms[i])), terms: list of lists of net names
    (literals, already the correct true/complement choice). NMOS network:
    one series chain per term, all chains in parallel between `out` and
    GND (conducts -> pulls out low -- exactly when some term is fully
    true). PMOS network: the series-parallel dual (one parallel group of
    PMOS per term, the groups themselves in series between VDD and
    `out`) -- conducts, pulling out high, exactly when NO term is fully
    true. 2 transistors per literal, matching a hand-built AOI/NAND/NOR
    cell exactly (verified against machine_cmos_full.py's own NAND2 and
    INV shapes for the 1-term / 1-literal corner cases)."""
    ts = []
    tag = out
    for ti, term in enumerate(terms):
        nodes = [out] + ['%s_n%d_%d' % (tag, ti, i) for i in range(1, len(term))] + ['GND']
        for i, lit in enumerate(term):
            ts.append((lit, nodes[i], nodes[i + 1], 'n', 'strong'))
    node_before = 'VDD'
    for ti, term in enumerate(terms):
        node_after = out if ti == len(terms) - 1 else '%s_p%d' % (tag, ti)
        for lit in term:
            ts.append((lit, node_before, node_after, 'p', 'strong'))
        node_before = node_after
    return ts

def _and_true(literals, out):
    """out = AND(literals), true polarity (NAND-N + inverter)."""
    bar = out + '_bar'
    return _aoi([literals], bar) + _inv(bar, out)

def _sop_true(terms, out):
    """out = OR_i AND(terms[i]), true polarity (AOI + inverter)."""
    bar = out + '_bar'
    return _aoi(terms, bar) + _inv(bar, out)

def _regbit(comb_net, prefix):
    """One bit of static master-slave storage (16T), the exact structure
    machine_cmos_full.py uses for its single flag bit, replicated under
    `prefix` so several bits can coexist. `comb_net` is the always-live
    combinational net that is sampled into the master during phi1.
    Returns (transistors, feedback_nets); feedback_nets are the 4 nets
    that need cross-phase seeding (the two 2-inversion loops)."""
    M, MB, MFB = prefix + '_M', prefix + '_MB', prefix + '_MFB'
    S, SB, SFB = prefix + '_S', prefix + '_SB', prefix + '_SFB'
    ts = []
    ts += _tg('phi1', 'phi1bar', comb_net, M)   # TG_write_master
    ts += _inv(M, MB)                            # INV1_master
    ts += _inv(MB, MFB)                           # INV2_master
    ts += _tg('phi2', 'phi2bar', MFB, M)         # TG_hold_master
    ts += _tg('phi2', 'phi2bar', M, S)           # TG_write_slave
    ts += _inv(S, SB)                             # INV1_slave
    ts += _inv(SB, SFB)                            # INV2_slave
    ts += _tg('phi1', 'phi1bar', SFB, S)          # TG_hold_slave
    return ts, [M, MB, S, SB]
