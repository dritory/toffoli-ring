"""Exploration helpers: spacetime diagrams, ash dynamics, traveling backgrounds."""
import sys, itertools, random
from ring import pass_, to_str, from_str, run


def spacetime(s, k, passes, lo=0, hi=None):
    rows = run(s, k, passes)
    hi = hi if hi is not None else len(s)
    return "\n".join("%4d %s" % (t, to_str(r[lo:hi])) for t, r in enumerate(rows))


def traveling_backgrounds(k, pmax=14, vmax=None):
    """Bi-infinite p-periodic x with P(x) = shift of x by v cells (rightward),
    i.e. x[j] ^ x[j-v] == x[j-k-v] & x[j-k+1-v] for all j (mod p)."""
    found = []
    for p in range(1, pmax + 1):
        vmax_ = p if vmax is None else vmax
        for v in range(0, vmax_):
            for bits in itertools.product((0, 1), repeat=p):
                if all((bits[j] ^ bits[(j - v) % p]) == (bits[(j - k - v) % p] & bits[(j - k + 1 - v) % p]) for j in range(p)):
                    # skip fixed points (v=0 trivial: no adjacent ones)
                    if v == 0:
                        continue
                    # primitive period only
                    if any(p % d == 0 and d < p and all(bits[i] == bits[(i + d) % p] for i in range(p)) for d in range(1, p)):
                        continue
                    found.append((p, v, "".join("#" if b else "." for b in bits)))
    return found


def periodic_orbit_backgrounds(k, pmax=10, qmax=8, vmax=None):
    """Bi-infinite p-periodic x such that P^q(x) = shift by v of x, computed by
    iterating the transducer on a ring of length m*p for m large enough that the
    window is in its steady state; we check consistency via a long ring.
    Returns list of (p, q, v, pattern)."""
    out = []
    for p in range(1, pmax + 1):
        for bits in itertools.product((0, 1), repeat=p):
            if not any(bits[i] & bits[(i + 1) % p] for i in range(p)):
                continue  # fixed point
            if any(p % d == 0 and d < p and all(bits[i] == bits[(i + d) % p] for i in range(p)) for d in range(1, p)):
                continue
            m = 40
            n = m * p
            s = list(bits) * m
            # helical seed consistent with periodic x requires ring length multiple of p; use it directly
            cur = s
            for q in range(1, qmax + 1):
                cur = pass_(cur, k)
                # is cur a shift of s? (check on the ring)
                for v in range(p):
                    if all(cur[(j + v) % n] == s[j] for j in range(n)):
                        out.append((p, q, v, "".join("#" if b else "." for b in bits)))
                        break
                else:
                    continue
                break
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    k = int(sys.argv[2])
    if cmd == "ash":
        L = int(sys.argv[3]); passes = int(sys.argv[4])
        s = [1] * L + [0] * 12
        print(spacetime(s, k, passes))
    elif cmd == "word":
        w = from_str(sys.argv[3]); passes = int(sys.argv[4])
        s = w + [0] * (int(sys.argv[5]) if len(sys.argv) > 5 else 40)
        print(spacetime(s, k, passes))
    elif cmd == "random":
        n = int(sys.argv[3]); passes = int(sys.argv[4]); seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        random.seed(seed)
        dens = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5
        s = [1 if random.random() < dens else 0 for _ in range(n)]
        print(spacetime(s, k, passes))
    elif cmd == "travel":
        pmax = int(sys.argv[3]) if len(sys.argv) > 3 else 12
        for f in traveling_backgrounds(k, pmax):
            print("p=%d v=%d %s" % f)
    elif cmd == "porbits":
        pmax = int(sys.argv[3]) if len(sys.argv) > 3 else 8
        qmax = int(sys.argv[4]) if len(sys.argv) > 4 else 8
        for f in periodic_orbit_backgrounds(k, pmax, qmax):
            print("p=%d q=%d v=%d %s" % f)
