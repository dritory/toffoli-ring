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
