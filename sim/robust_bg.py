"""Traveling backgrounds with attractor analysis.

For a p-periodic input x, the transducer window after each period is a map
W: {0,1}^k -> {0,1}^k. Each cycle of W gives a periodic output. We report,
for each x, whether the output reached from the ZERO window (and from every
window) is a shift of x (then the background is a robust conveyor), and the
transient length."""
import sys, itertools
from ring import to_str

def step_period(k, x, w):
    w = list(w); out = []
    for b in x:
        y = b ^ (w[0] & w[1])
        out.append(y)
        w = w[1:] + [y]
    return tuple(w), out

def analyze(k, x):
    p = len(x)
    # iterate window map from zero window until cycle
    w = tuple([0] * k); seen = {}
    outs = []
    t = 0
    while w not in seen:
        seen[w] = t
        w2, out = step_period(k, x, w)
        outs.append(out); w = w2; t += 1
    start = seen[w]
    cyc = outs[start:]
    y = sum(cyc, [])  # one period of output, length c*p
    # is y a rotation of x repeated?
    c = len(cyc)
    for v in range(p):
        if all(y[j] == x[(j - v) % p] for j in range(c * p)):
            return dict(shift=v, transient=start, cyclelen=c)
    return None

def all_windows_attract(k, x):
    """Do all 2^k windows lead to the same output cycle?"""
    p = len(x)
    cycles = set()
    for w0 in itertools.product((0, 1), repeat=k):
        w = w0; seen = {}; t = 0; outs = []
        while w not in seen:
            seen[w] = t; w, out = step_period(k, x, w); outs.append(out); t += 1
        cyc = tuple(map(tuple, outs[seen[w]:]))
        # canonicalize rotation of the cycle
        rots = [cyc[i:] + cyc[:i] for i in range(len(cyc))]
        cycles.add(min(rots))
    return len(cycles)

if __name__ == "__main__":
    k = int(sys.argv[1]); pmax = int(sys.argv[2])
    for p in range(1, pmax + 1):
        for bits in itertools.product((0, 1), repeat=p):
            x = list(bits)
            if any(p % d == 0 and d < p and all(x[i] == x[(i + d) % p] for i in range(p)) for d in range(1, p)):
                continue
            if not any(x[i] & x[(i + 1) % p] for i in range(p)):
                continue
            r = analyze(k, x)
            if r and r["shift"] % p != 0:
                na = all_windows_attract(k, x)
                # print only one rotation representative
                if x == min(x[i:] + x[:i] for i in range(p)):
                    print("p=%2d v=%2d transient=%d ncycles_of_windowmap=%d  %s" % (p, r["shift"], r["transient"], na, to_str(x)))
