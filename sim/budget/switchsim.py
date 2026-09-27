"""Generic switch-level evaluator.

Model: nets carry 0/1. A Transistor(gate, a, b[, kind]) is an ideal
bidirectional switch: closed (a<->b shorted) iff value(gate) == 1 for an
NMOS (kind='n', the default) or iff value(gate) == 0 for a PMOS
(kind='p') -- both are ordinary MOSFETs, one discrete component each; a
PMOS gate directly implements "conducts when this net is LOW" without a
separate inverter. A Resistor(net, rail)
is a weak pull of `net` toward `rail` (0 or 1), active only if nothing
stronger drives that net's connected group. `fixed` gives strongly-driven
nets (primary inputs, VDD=1, GND=0). Evaluation unions nets joined by
closed transistors (union-find), then assigns each group the fixed value
found in it (contention is an error), or else the resistor rail if the
group holds a resistor and no fixed driver. Iterated to a fixed point
(newly-resolved nets can close further transistors) -- our nets are
resistor/transistor gated, dependency depth is small (<=3), so this
converges in a couple of passes; we cap iterations defensively.
"""

class UF:
    def __init__(self, items):
        self.p = {x: x for x in items}
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.p[rx] = ry

def _fixed_point(transistors, resistors, base_fixed, all_nets, init_known,
                  max_iters):
    """Shared Gauss-Seidel core: iterate union-find + rail resolution from
    `init_known` (the values used for pass-1 gate lookups) until it
    reaches a fixed point or exhausts max_iters. Returns (known,
    converged). Raises on contention (same as evaluate())."""
    known = dict(init_known)
    converged = False
    for _ in range(max_iters):
        uf = UF(all_nets)
        for t in transistors:
            gate, a, b = t[0], t[1], t[2]
            kind = t[3] if len(t) > 3 else 'n'
            gv = known.get(gate)
            closed = (gv == 1) if kind == 'n' else (gv == 0)
            if closed:
                uf.union(a, b)
        groupval = {}
        for net, val in base_fixed.items():
            root = uf.find(net)
            if root in groupval and groupval[root] != val:
                raise ValueError("contention on net group containing %r" % net)
            groupval[root] = val
        for net, rail in resistors:
            root = uf.find(net)
            if root not in groupval:
                groupval[root] = rail
        new_known = dict(base_fixed)
        for net in all_nets:
            root = uf.find(net)
            if root in groupval:
                new_known[net] = groupval[root]
        if new_known == known:
            converged = True
            known = new_known
            break
        known = new_known
    return known, converged

def _collect_nets(transistors, resistors, fixed):
    all_nets = set(['VDD', 'GND'])
    for t in transistors:
        all_nets.update([t[0], t[1], t[2]])
    for net, rail in resistors:
        all_nets.add(net)
    all_nets.update(fixed.keys())
    return all_nets

def _check_floating(known, transistors, resistors, fixed, holdable):
    required = set(fixed.keys())
    for t in transistors:
        required.add(t[0])
    for net, _ in resistors:
        required.add(net)
    missing = sorted(n for n in required
                      if n not in known and n not in holdable)
    if missing:
        raise ValueError("floating net(s), not driven/pulled/fixed in "
                          "this phase, and not declared holdable: %r"
                          % missing)

def evaluate(transistors, resistors, fixed, holdable=frozenset(), max_iters=8,
             require_all_gates=True):
    """holdable: nets allowed to stay undefined after evaluation (used for
    capacitor nodes this particular phase's network deliberately does not
    drive/read here). Every OTHER net that is used as a transistor's gate,
    or that carries a resistor, or that is a primary input, must resolve
    to a value or this raises -- "no implicit storage": nothing may
    silently retain a level unless it is an explicit capacitor and the
    caller has said so via `holdable`. A pure a/b pass-through junction
    between series switches (never anyone's gate, never resistor-loaded)
    is exempt: it carries no logical meaning of its own and is freshly
    resolved (as connected-or-not) every phase, so it is not in
    `required` at all.
    """
    all_nets = set(['VDD', 'GND'])
    for t in transistors:
        all_nets.update([t[0], t[1], t[2]])  # gate, a, b (kind, if present, is not a net)
    for net, rail in resistors:
        all_nets.add(net)
    all_nets.update(fixed.keys())

    base_fixed = dict(fixed)
    base_fixed['VDD'] = 1
    base_fixed['GND'] = 0
    known = dict(base_fixed)  # only used for this pass's gate lookups

    converged = False
    for _ in range(max_iters):
        uf = UF(all_nets)
        for t in transistors:
            gate, a, b = t[0], t[1], t[2]
            kind = t[3] if len(t) > 3 else 'n'
            gv = known.get(gate)
            closed = (gv == 1) if kind == 'n' else (gv == 0)
            if closed:
                uf.union(a, b)
        # Fresh groupval each pass: only the *permanently* fixed nets
        # (primary inputs, VDD, GND) can genuinely contend; a resistor
        # default from an earlier pass must never be carried forward as
        # if it were a real driver (that stale-value bug caused a false
        # "contention" the first time this was written).
        groupval = {}
        for net, val in base_fixed.items():
            root = uf.find(net)
            if root in groupval and groupval[root] != val:
                raise ValueError("contention on net group containing %r" % net)
            groupval[root] = val
        for net, rail in resistors:
            root = uf.find(net)
            if root not in groupval:
                groupval[root] = rail
        new_known = dict(base_fixed)
        for net in all_nets:
            root = uf.find(net)
            if root in groupval:
                new_known[net] = groupval[root]
        if new_known == known:
            converged = True
            known = new_known
            break
        known = new_known
    if not converged:
        raise ValueError("did not converge in %d iterations -- likely a "
                          "combinational feedback loop" % max_iters)

    if require_all_gates:
        required = set(fixed.keys())
        for t in transistors:
            required.add(t[0])
        for net, _ in resistors:
            required.add(net)
        missing = sorted(n for n in required
                          if n not in known and n not in holdable)
        if missing:
            raise ValueError("floating net(s), not driven/pulled/fixed in "
                              "this phase, and not declared holdable: %r"
                              % missing)
    return known

def evaluate_static(transistors, resistors, fixed, feedback_nets, seed,
                     holdable=frozenset(), max_iters=8):
    """Cross-coupled / static-feedback variant of evaluate(), for circuits
    that hold state through transistor+resistor feedback loops (e.g. an
    SR latch) rather than through a capacitor's held charge.

    `feedback_nets`: the loop's own state nets (e.g. a latch's Q, Qbar),
    which are not externally fixed but whose resolved value can depend on
    which way the loop was already leaning. `seed`: their values carried
    over from the previous phase -- used ONLY to seed pass-1's gate
    lookups (so Gauss-Seidel starts in the physically correct basin);
    they are still resolved from the live circuit like any other net, not
    held fixed.

    Method: run the ordinary Gauss-Seidel fixed point starting from
    `seed` (this is a deterministic function of the *actual* previous
    state, same union-find resolution `evaluate()` uses -- there is no
    processing-order ambiguity to inject a race by itself). If it
    converges with no contention, that is the answer: it is exactly what
    the real previous state settles to, including the ordinary
    master/slave case where some seeded nets (already recomputed ahead of
    the rest, e.g. a master latch that updates within the same phase a
    slave is still holding its old value) legitimately disagree with each
    other without that being a race.

    If instead it does NOT converge (or hits contention) from the given
    seed, that is only reported as a plain oscillation if NO starting
    corner of `feedback_nets` leads anywhere stable either -- a true
    astable circuit. But if some OTHER starting corner(s) of
    `feedback_nets` do settle (the fixed inputs admit one or more real
    stable points), while the literal given `seed` fails to reach any of
    them, that is precisely "more than one stable point is consistent and
    the previous state does not decide it": the classic released-
    simultaneous-set/reset metastability. This is reported as a distinct
    race/metastability error, not silently resolved by whichever stable
    point Gauss-Seidel happens to wander into.
    """
    all_nets = _collect_nets(transistors, resistors, fixed)
    base_fixed = dict(fixed)
    base_fixed['VDD'] = 1
    base_fixed['GND'] = 0

    init_known = dict(base_fixed)
    for n in feedback_nets:
        if n in seed:
            init_known[n] = seed[n]

    try:
        known, converged = _fixed_point(transistors, resistors, base_fixed,
                                         all_nets, init_known, max_iters)
    except ValueError:
        converged = False
        known = None
    if converged:
        _check_floating(known, transistors, resistors, fixed, holdable)
        return known

    # The literal seed did not settle -- find out whether ANY starting
    # corner of feedback_nets does, to give an accurate diagnosis.
    stable_points = {}
    for corner in range(2 ** len(feedback_nets)):
        corner_known = dict(base_fixed)
        for i, n in enumerate(feedback_nets):
            corner_known[n] = (corner >> i) & 1
        try:
            c_known, c_converged = _fixed_point(
                transistors, resistors, base_fixed, all_nets, corner_known,
                max_iters)
        except ValueError:
            continue  # contention from this corner: not a real stable point
        if not c_converged:
            continue  # oscillates from this corner: not a stable point
        key = tuple(c_known.get(n) for n in feedback_nets)
        if None in key:
            continue  # this corner doesn't even pin down its own feedback nets
        stable_points[key] = c_known

    if not stable_points:
        raise ValueError("no stable fixed point exists for these inputs "
                          "from the given previous state %r, nor from ANY "
                          "starting corner of %r -- oscillation (a true "
                          "astable circuit for these inputs)"
                          % (seed, feedback_nets))

    seed_key = tuple(seed.get(n) for n in feedback_nets)
    raise ValueError(
        "race/metastable: %d distinct stable point(s) exist for these "
        "inputs (%r), but the previous state %r does not itself settle "
        "onto any of them (it oscillates instead) -- there is no "
        "principled way to pick a winner, this is exactly the released-"
        "simultaneous-set/reset kind of metastability" %
        (len(stable_points), sorted(stable_points.keys()), seed_key))
