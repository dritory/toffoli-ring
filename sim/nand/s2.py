"""S2: spatially periodic backgrounds for R3(k) = s[i+k] <- NOT(s[i] & s[i+1] & s[i+k]).

Row/transducer derivation (row index j <-> ring cell j+k, x=old row, y=new row):
  read s[i]   = s[j]     -> row index j-k  -> already-updated this pass -> y[j-k]
  read s[i+1] = s[j+1]   -> row index j-k+1-> already-updated this pass -> y[j-k+1]
  read s[i+k] = s[j+k]   -> row index j    -> the OLD value about to be overwritten -> x[j]
  y[j] = NOT( y[j-k] & y[j-k+1] & x[j] )
       = NOT(x[j])  if (y[j-k], y[j-k+1]) == (1,1)
       = 1          otherwise

First: verify this transducer against the literal sequential r3_pass on random
rings. Then: for period p<=12 spatially-periodic backgrounds x, run the
window map (as in sim/robust_bg.py) from the all-zero window until it cycles;
check whether the resulting output is a rotation of x repeated (temporally
periodic up to a shift v). Then check whether ALL 2^k starting windows lead
to the same output cycle (robust = single attractor).
"""
import itertools
import random
import sys
sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
from nandring import r3_pass, to_str


def step_period_r3(k, x, w):
    """One period's worth of the window map. w: k-tuple = (y[j-k],...,y[j-1])."""
    w = list(w)
    out = []
    for b in x:
        y = (1 - b) if (w[0] == 1 and w[1] == 1) else 1
        out.append(y)
        w = w[1:] + [y]
    return tuple(w), out


def verify_transducer(trials=2000):
    rng = random.Random(7)
    for _ in range(trials):
        n = rng.randint(5, 40)
        k = rng.randint(2, min(6, n - 1))
        s = [rng.randint(0, 1) for _ in range(n)]
        ref = r3_pass(s, k)
        # row view: x[j] = s[(j+k)%n]; seed window from tail of old row
        x = [s[(j + k) % n] for j in range(n)]
        y = [0] * n
        for j in range(n):
            a = y[j - k] if j - k >= 0 else x[j - k + n]
            b = y[j - k + 1] if j - k + 1 >= 0 else x[j - k + 1 + n]
            y[j] = (1 - x[j]) if (a == 1 and b == 1) else 1
        out = [0] * n
        for j in range(n):
            out[(j + k) % n] = y[j]
        assert out == ref, (s, k, out, ref)
    print(f"verify_transducer: OK against literal r3_pass on {trials} random (N,k,s)")


def analyze(k, x):
    """Iterate window map from zero window until it repeats a window; check if
    the resulting output cycle is a rotation of x repeated."""
    p = len(x)
    w = tuple([0] * k)
    seen = {}
    outs = []
    t = 0
    while w not in seen:
        seen[w] = t
        w2, out = step_period_r3(k, x, w)
        outs.append(out)
        w = w2
        t += 1
    start = seen[w]
    cyc = outs[start:]
    y = sum(cyc, [])
    c = len(cyc)
    for v in range(p):
        if all(y[j] == x[(j - v) % p] for j in range(c * p)):
            return dict(shift=v, transient=start, cyclelen=c)
    return None


def all_windows_attract(k, x):
    p = len(x)
    cycles = set()
    for w0 in itertools.product((0, 1), repeat=k):
        w = w0
        seen = {}
        t = 0
        outs = []
        while w not in seen:
            seen[w] = t
            w, out = step_period_r3(k, x, w)
            outs.append(out)
            t += 1
        cyc = tuple(map(tuple, outs[seen[w]:]))
        rots = [cyc[i:] + cyc[:i] for i in range(len(cyc))]
        cycles.add(min(rots))
    return len(cycles), cycles


def is_primitive(x):
    p = len(x)
    return not any(p % d == 0 and d < p and all(x[i] == x[(i + d) % p] for i in range(p))
                   for d in range(1, p))


def min_rotation(x):
    p = len(x)
    return min(tuple(x[i:] + x[:i]) for i in range(p))


def main():
    verify_transducer()

    KS = [2, 3, 4, 5]
    PMAX = 12
    robust_found = []  # (k, p, x, shift, transient, ncycles)
    print("\n=== S2 search: period-p backgrounds robust under R3(k) ===")
    for k in KS:
        seen_reps = set()
        found_this_k = []
        for p in range(1, PMAX + 1):
            for bits in itertools.product((0, 1), repeat=p):
                x = list(bits)
                if not is_primitive(x):
                    continue
                rep = min_rotation(x)
                if (p, rep) in seen_reps:
                    continue
                seen_reps.add((p, rep))
                r = analyze(k, x)
                if r is None:
                    continue
                if r["shift"] % p == 0 and r["cyclelen"] == 1:
                    kind = "static (shift 0)"
                else:
                    kind = f"shift {r['shift']}"
                nc, _ = all_windows_attract(k, x)
                if nc == 1:
                    found_this_k.append((p, x, r, kind))
                    robust_found.append((k, p, x, r, kind, nc))
        print(f"\n k={k}: {len(found_this_k)} robust (single-attractor) period<=|{PMAX} backgrounds found")
        for (p, x, r, kind) in found_this_k:
            print(f"   p={p:2d} x={to_str(x):14s} transient={r['transient']} "
                  f"cyclelen={r['cyclelen']} {kind}")

    print(f"\nTotal robust backgrounds across k=2..5, p<=12: {len(robust_found)}")
    return robust_found


if __name__ == "__main__":
    main()
