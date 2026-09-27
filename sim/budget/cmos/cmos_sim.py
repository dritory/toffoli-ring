"""Strength-aware extension of switchsim's static (cross-coupled feedback)
evaluator, for PURE-MOSFET circuits: no resistors, no capacitors, no
diodes. Every pull-up is a real PMOS (or occasionally a second NMOS),
so a written-vs-held-value conflict on an internal net is a genuine
ratioed transistor fight, not "transistor beats resistor" as in
switchsim.evaluate_static -- this module makes that fight explicit and
enforces the safety rule the design brief requires.

Transistor tuple: (gate, a, b, kind, strength)
  kind:      'n' (NMOS, closed iff gate==1) or 'p' (PMOS, closed iff gate==0)
  strength:  'strong' (a write/pull-down device, or any device sized to
             win a ratioed fight) or 'weak' (a keeper -- a latch's
             continuously-on feedback/pull-up device, meant to be
             overpowered when something strong writes the node).
  (both fields default to 'n'/'strong' for brevity when omitted.)

No resistors anywhere -- every "pull to a rail" is one of these
transistors. VDD (=1) and GND (=0) are just two more fixed/source nets;
any OTHER externally driven net (e.g. a bit line held during a write)
is handled identically, at whatever strength its own driving devices
have -- there is nothing rail-specific in the resolution rule.

Resolution rule per net, each Gauss-Seidel pass (`known` from the
previous pass/seed decides which transistors are closed this pass,
exactly as switchsim._fixed_point does):

  1. Compute, separately for value 1 and value 0, the best (lowest-
     weakness) path from ANY net fixed to that value, over the graph of
     currently-closed transistors (0-1 relaxation: a 'strong' edge costs
     0, a 'weak' edge costs 1 -- the total path cost is the count of weak
     edges crossed; 0 = a fully strong path exists, >=1 = only weak
     path(s) exist).
  2. A net that is itself one of the given `fixed` nets (primary input,
     VDD, GND, or any other externally-driven net) is authoritative: if
     the OPPOSITE value is reachable to it at all (any strength), that
     is an unconditional short/contention error -- a driven net's value
     is not up for a ratioed vote.
  3. Any other net, reachable to only one value -> resolves to it
     (strength doesn't matter, nothing opposes).
  4. Reachable to both values:
       - one strong, one weak  -> the strong value wins (the allowed
         ratioed write; caller/report must state the required on-
         resistance ratio, this module only enforces the topology rule)
       - both strong            -> contention error (two low-impedance
         drivers to different rails -- a real short)
       - both weak               -> contention error (indeterminate --
         neither keeper dominates the other)
  5. A net reachable to neither value this pass is left unresolved
     (must be produced by a later pass, or be a feedback net seeded from
     the previous phase, or be declared `holdable`) -- checked by
     `_check_floating` once the pass loop reaches a fixed point.

`evaluate_cmos_static(transistors, fixed, feedback_nets, seed, holdable,
max_iters)` mirrors switchsim.evaluate_static's outer contract exactly
(same seed-then-corner-search method, same race/oscillation
diagnostics), just built on this strength-aware core instead of
switchsim's resistor-aware one.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from switchsim import UF  # reuse the tested union-find only

def _norm(t):
    gate, a, b = t[0], t[1], t[2]
    kind = t[3] if len(t) > 3 else 'n'
    strength = t[4] if len(t) > 4 else 'strong'
    assert kind in ('n', 'p'), t
    assert strength in ('strong', 'weak'), t
    return gate, a, b, kind, strength

def _collect_nets(transistors, fixed):
    all_nets = set(['VDD', 'GND'])
    for t in transistors:
        gate, a, b, kind, strength = _norm(t)
        all_nets.update([gate, a, b])
    all_nets.update(fixed.keys())
    return all_nets

def _closed_edges(transistors, known):
    edges = []
    for t in transistors:
        gate, a, b, kind, strength = _norm(t)
        gv = known.get(gate)
        closed = (gv == 1) if kind == 'n' else (gv == 0)
        if closed:
            edges.append((a, b, strength))
    return edges

def _relax(edges, sources, exclude=None):
    """Multi-source 0-1 shortest path (edge weight 0 for 'strong', 1 for
    'weak'). `sources`: iterable of nets at distance 0. Small graphs
    (a few dozen nets) -- plain Bellman-Ford-style relaxation to a fixed
    point is simplest and plenty fast.

    `exclude` (used to pass the OPPOSITE rail): that net is never given a
    distance and never expanded through, at any cost. Without this, a
    weak keeper elsewhere in the circuit that happens to be strongly
    pulled to the opposite rail (e.g. a latch's own MBAR node, correctly
    resolved strong-vs-weak in ITS OWN fight) would make the powered rail
    itself look like it has some tiny leakage path to the other rail,
    and that phantom "weak reach" would then contaminate every other
    net's resolution through the rail -- physically wrong: VDD and GND
    are ideal, zero-impedance supplies, never influenced back by
    anything drawing on them, no matter how many weak devices lean on
    them elsewhere."""
    adj = {}
    for a, b, s in edges:
        w = 0 if s == 'strong' else 1
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))
    dist = {n: 0 for n in sources if n != exclude}
    for _ in range(len(adj) + 2):
        changed = False
        for u in list(dist.keys()):
            if u == exclude:
                continue
            for v, w in adj.get(u, []):
                if v == exclude:
                    continue
                nd = dist[u] + w
                if v not in dist or nd < dist[v]:
                    dist[v] = nd
                    changed = True
        if not changed:
            break
    return dist

def _fixed_point_cmos(transistors, base_fixed, all_nets, init_known, max_iters):
    known = dict(init_known)
    converged = False
    fights = []
    for _ in range(max_iters):
        edges = _closed_edges(transistors, known)

        # Whether two DIFFERENT fixed nets are directly shorted together
        # is checked only once the network has settled (`_tie_check_fixed`,
        # called from evaluate_cmos_static after convergence) -- not here,
        # per pass: a fixed net's own value never changes, but the PATH
        # connecting it to another fixed net can transiently exist only
        # because some in-between net is itself mid-resolution (the same
        # lagging-gate artifact the per-net fight logic below defers), and
        # checking it here would reject perfectly good, settling circuits
        # (e.g. a differential SRAM write, see sram6t.py) for a fight that
        # is not there once everything has caught up.
        srcs1 = [n for n, v in base_fixed.items() if v == 1]
        srcs0 = [n for n, v in base_fixed.items() if v == 0]
        cost1 = _relax(edges, srcs1, exclude='GND')
        cost0 = _relax(edges, srcs0, exclude='VDD')
        new_known = {}
        fights_this_pass = []
        for net in all_nets:
            c1 = cost1.get(net)
            c0 = cost0.get(net)
            if net in base_fixed:
                new_known[net] = base_fixed[net]
                continue
            if c1 is None and c0 is None:
                continue  # unresolved this pass
            if c0 is None:
                new_known[net] = 1
                continue
            if c1 is None:
                new_known[net] = 0
                continue
            s1 = 'strong' if c1 == 0 else 'weak'
            s0 = 'strong' if c0 == 0 else 'weak'
            if s1 == s0:
                # A same-strength fight to opposite rails. This may be a
                # genuine, permanent short (raised for real below, once
                # settled) or -- in a cross-coupled differential write --
                # only a same-pass Gauss-Seidel artifact from a gate that
                # lags one pass behind (the write side of the fight has
                # already tipped, but the other side's transistor gate
                # hasn't caught up yet): deferring it, instead of raising
                # immediately, lets the next pass re-derive it once the
                # lagging gate updates, exactly the way real (continuous-
                # time, regenerative) hardware settles. `_tie_check_pass`
                # re-examines the net once the whole network has reached
                # a fixed point and raises then if the tie is still real.
                continue
            if s1 == 'strong':
                new_known[net] = 1
            else:
                new_known[net] = 0
            fights_this_pass.append((net, 'value=%d wins' % new_known[net],
                                      's1=%s s0=%s' % (s1, s0)))
        if new_known == known:
            converged = True
            known = new_known
            fights = fights_this_pass
            break
        known = new_known
    return known, converged, fights

def _tie_check(transistors, base_fixed, all_nets, known):
    """Re-derive cost1/cost0 once more from a SETTLED `known` (a Gauss-
    Seidel fixed point, or a corner-search candidate) and return the list
    of non-fixed nets still genuinely tied (strong-vs-strong or weak-vs-
    weak) at that settled point. Unlike the per-pass loop, this is not
    deferred further -- a tie that survives to the fixed point itself
    (as opposed to only appearing in an intermediate, not-yet-settled
    pass) cannot resolve by iterating more, and is a real design fault."""
    edges = _closed_edges(transistors, known)
    srcs1 = [n for n, v in base_fixed.items() if v == 1]
    srcs0 = [n for n, v in base_fixed.items() if v == 0]
    cost1 = _relax(edges, srcs1, exclude='GND')
    cost0 = _relax(edges, srcs0, exclude='VDD')
    ties = []
    for net in all_nets:
        if net in base_fixed:
            continue
        c1 = cost1.get(net)
        c0 = cost0.get(net)
        if c1 is None or c0 is None:
            continue
        s1 = 'strong' if c1 == 0 else 'weak'
        s0 = 'strong' if c0 == 0 else 'weak'
        if s1 == s0:
            ties.append((net, s1))
    return ties

def _fixed_short(transistors, base_fixed, all_nets, known):
    """At a settled `known`, are two DIFFERENT fixed nets connected by an
    ALL-STRONG path of closed transistors? That is a direct, low-
    impedance wiring short between two authoritative/ideal drivers --
    there is no ratio that decides it. A path that includes a weak edge
    is NOT this: it is the ordinary per-net strong-vs-weak/weak-vs-weak
    fight `_tie_check` already reports more specifically (e.g. two weak
    keepers in series between VDD and GND is a "weak-vs-weak, node can't
    decide" fault on the node between them, not a hard short of the
    rails themselves). Returns None, or (net_a, net_b) naming one pair."""
    edges = [(a, b) for a, b, s in _closed_edges(transistors, known)
             if s == 'strong']
    uf = UF(all_nets)
    for a, b in edges:
        uf.union(a, b)
    groupnet = {}
    for net, val in sorted(base_fixed.items()):
        root = uf.find(net)
        if root in groupnet and base_fixed[groupnet[root]] != val:
            return (groupnet[root], net)
        groupnet[root] = net
    return None

def _raise_ties(ties):
    strong = [n for n, s in ties if s == 'strong']
    weak = [n for n, s in ties if s == 'weak']
    parts = []
    if strong:
        parts.append("strong-vs-strong contention on %r (two low-"
                      "impedance drivers to different rails -- a real "
                      "short)" % strong)
    if weak:
        parts.append("weak-vs-weak contention on %r (both sides only "
                      "weakly held -- indeterminate, no ratio decides "
                      "it)" % weak)
    raise ValueError("; ".join(parts))

def _check_floating(known, transistors, fixed, holdable):
    required = set(fixed.keys())
    for t in transistors:
        gate, a, b, kind, strength = _norm(t)
        required.add(gate)
    missing = sorted(n for n in required
                      if n not in known and n not in holdable)
    if missing:
        raise ValueError("floating net(s), not driven/pulled/fixed in "
                          "this phase, and not declared holdable: %r"
                          % missing)

def evaluate_cmos_static(transistors, fixed, feedback_nets, seed,
                          holdable=frozenset(), max_iters=8):
    """Strength-aware counterpart of switchsim.evaluate_static. See module
    docstring for the resolution rule. Returns `known` (dict net->0/1) on
    success. Raises ValueError with a descriptive message on contention,
    oscillation, or race/metastability -- same three-way diagnosis as
    evaluate_static."""
    transistors = [_norm(t) for t in transistors]
    all_nets = _collect_nets(transistors, fixed)
    base_fixed = dict(fixed)
    base_fixed['VDD'] = 1
    base_fixed['GND'] = 0

    init_known = dict(base_fixed)
    for n in feedback_nets:
        if n in seed:
            init_known[n] = seed[n]

    try:
        known, converged, fights = _fixed_point_cmos(
            transistors, base_fixed, all_nets, init_known, max_iters)
    except ValueError:
        converged = False
        known = None
        fights = []
    if converged:
        short = _fixed_short(transistors, base_fixed, all_nets, known)
        if short:
            raise ValueError(
                "contention: strong-vs-strong -- fixed nets %r (=%d) and "
                "%r (=%d) are directly shorted together through closed "
                "transistors (a hard, unconditional short between two "
                "externally-driven nets)"
                % (short[0], base_fixed[short[0]], short[1], base_fixed[short[1]]))
        ties = _tie_check(transistors, base_fixed, all_nets, known)
        if ties:
            _raise_ties(ties)
        _check_floating(known, transistors, fixed, holdable)
        known['_fights'] = fights
        return known

    stable_points = {}
    for corner in range(2 ** len(feedback_nets)):
        corner_known = dict(base_fixed)
        for i, n in enumerate(feedback_nets):
            corner_known[n] = (corner >> i) & 1
        try:
            c_known, c_converged, _ = _fixed_point_cmos(
                transistors, base_fixed, all_nets, corner_known, max_iters)
        except ValueError:
            continue
        if not c_converged:
            continue
        if _fixed_short(transistors, base_fixed, all_nets, c_known) is not None:
            continue  # not a real stable point -- a direct short
        if _tie_check(transistors, base_fixed, all_nets, c_known):
            continue  # not a real stable point -- still a genuine fight
        key = tuple(c_known.get(n) for n in feedback_nets)
        if None in key:
            continue
        stable_points[key] = c_known

    if not stable_points:
        raise ValueError("no stable fixed point exists for these inputs "
                          "from the given previous state %r, nor from ANY "
                          "starting corner of %r -- oscillation"
                          % (seed, feedback_nets))

    seed_key = tuple(seed.get(n) for n in feedback_nets)
    raise ValueError(
        "race/metastable: %d distinct stable point(s) exist for these "
        "inputs (%r), but the previous state %r does not itself settle "
        "onto any of them" % (len(stable_points), sorted(stable_points.keys()),
                               seed_key))
