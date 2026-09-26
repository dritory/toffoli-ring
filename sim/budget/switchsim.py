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

def evaluate(transistors, resistors, fixed, max_iters=8):
    all_nets = set(['VDD', 'GND'])
    for t in transistors:
        all_nets.update([t[0], t[1], t[2]])  # gate, a, b (kind, if present, is not a net)
    for net, rail in resistors:
        all_nets.add(net)
    all_nets.update(fixed.keys())

    known = dict(fixed)
    known['VDD'] = 1
    known['GND'] = 0

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
        for net, val in known.items():
            root = uf.find(net)
            if root in groupval and groupval[root] != val:
                raise ValueError("contention on net group containing %r" % net)
            groupval[root] = val
        for net, rail in resistors:
            root = uf.find(net)
            if root not in groupval:
                groupval[root] = rail
        changed = False
        for net in all_nets:
            root = uf.find(net)
            if root in groupval and known.get(net) != groupval[root]:
                known[net] = groupval[root]
                changed = True
        if not changed:
            break
    return known
