"""V1: NAND-ahead s[i+k] = NOT(s[i] & s[i+1]).

(i) 200 random seed pairs agreeing on cells 0..k-1, random elsewhere:
    confirm identical *entire ring* after pass 1.
(ii) For each (N,k), 100 random seeds: transient & period of the full ring
     state trajectory (under repeated whole passes); confirm both <= 2^k.
(iii) Cycle structure of the k-bit register e_t = NAND(e_{t-k}, e_{t-k+1})
      for k=2..8 (all 2^k initial windows): cycle lengths & transient lengths.
"""
import random
import sys
sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
from nandring import nand_ahead_pass, to_str

KS = [2, 3, 4, 5]
NS = list(range(16, 65, 4))


def v1i(k, n, trials=200, rng=None):
    rng = rng or random.Random(12345 + k * 1000 + n)
    ok = True
    fail_example = None
    for _ in range(trials):
        prefix = [rng.randint(0, 1) for _ in range(k)]
        s0 = prefix + [rng.randint(0, 1) for _ in range(n - k)]
        s1 = prefix + [rng.randint(0, 1) for _ in range(n - k)]
        r0 = nand_ahead_pass(s0, k)
        r1 = nand_ahead_pass(s1, k)
        if r0 != r1:
            ok = False
            fail_example = (s0, s1, r0, r1)
            break
    return ok, fail_example


def v1ii(k, n, trials=100, rng=None):
    rng = rng or random.Random(54321 + k * 1000 + n)
    cap = 4 * (2 ** k) + 20  # generous vs. the 2^k bound we're testing
    max_transient = 0
    max_period = 0
    violations = []
    for _ in range(trials):
        s0 = [rng.randint(0, 1) for _ in range(n)]
        # Brent-style cycle detection on full ring state (cheap since bounded)
        seen = {}
        cur = tuple(s0)
        t = 0
        seen[cur] = 0
        while True:
            cur = tuple(nand_ahead_pass(list(cur), k))
            t += 1
            if cur in seen:
                transient = seen[cur]
                period = t - transient
                break
            seen[cur] = t
            if t > cap:
                transient, period = None, None
                break
        if transient is None:
            violations.append(("cap_exceeded", s0))
            continue
        max_transient = max(max_transient, transient)
        max_period = max(max_period, period)
        if transient > 2 ** k or period > 2 ** k:
            violations.append((transient, period, s0))
    return max_transient, max_period, violations


def v1iii(k):
    """Enumerate the 2^k-state functional graph of
    b=(b0..b_{k-1}) -> (b1..b_{k-1}, NAND(b0,b1))."""
    nstates = 2 ** k
    def succ(w):
        bits = [(w >> j) & 1 for j in range(k)]  # bits[0]=b0 .. bits[k-1]=b_{k-1}
        c = 1 - (bits[0] & bits[1])
        newbits = bits[1:] + [c]
        v = 0
        for j, b in enumerate(newbits):
            v |= (b << j)
        return v

    succ_map = [succ(w) for w in range(nstates)]
    # find transient+cycle for every state (rho shape)
    transient = [None] * nstates
    cyclen = [None] * nstates
    # standard approach: iterate, mark visit order, detect repeats
    color = [0] * nstates  # 0 unvisited,1 in-progress,2 done
    order = [0] * nstates
    for start in range(nstates):
        if color[start] == 2:
            continue
        path = []
        w = start
        while color[w] == 0:
            color[w] = 1
            order[w] = len(path)
            path.append(w)
            w = succ_map[w]
        if color[w] == 1:
            idx = order[w]
            cl = len(path) - idx
            for j, node in enumerate(path):
                if j < idx:
                    transient[node] = idx - j
                    cyclen[node] = cl
                else:
                    transient[node] = 0
                    cyclen[node] = cl
        else:  # color[w]==2, merges into an already-finished path
            tr_w = transient[w]
            cl = cyclen[w]
            for j, node in enumerate(path):
                transient[node] = (len(path) - j) + tr_w
                cyclen[node] = cl
        for node in path:
            color[node] = 2

    # collect distinct cycles
    cycles = {}
    for w in range(nstates):
        if transient[w] == 0:
            # w is on a cycle; find canonical rep = min over the cycle
            cyc = [w]
            cur = succ_map[w]
            while cur != w:
                cyc.append(cur)
                cur = succ_map[cur]
            key = tuple(sorted(cyc))
            cycles[key] = len(cyc)
    return transient, cyclen, succ_map, cycles


def main():
    print("=== V1(i): pass-1 identity for seeds agreeing on cells 0..k-1 ===")
    all_i_ok = True
    for k in KS:
        for n in NS:
            ok, fail = v1i(k, n)
            if not ok:
                all_i_ok = False
                print(f"  FAIL k={k} N={n}: {fail}")
    print(f"  all (k,N) pairs passed: {all_i_ok}  ({len(KS)*len(NS)} combos x 200 pairs)")

    print("\n=== V1(ii): ring-state transient/period <= 2^k ===")
    summary = []
    all_ii_ok = True
    for k in KS:
        row_max_t = 0
        row_max_p = 0
        any_violation = False
        for n in NS:
            mt, mp, viol = v1ii(k, n)
            row_max_t = max(row_max_t, mt)
            row_max_p = max(row_max_p, mp)
            if viol:
                any_violation = True
                all_ii_ok = False
                print(f"  VIOLATION k={k} N={n}: {viol[:3]}")
        summary.append((k, row_max_t, row_max_p, 2 ** k))
    print("  k | max transient (over N,seeds) | max period | 2^k bound")
    for k, mt, mp, bound in summary:
        flag = "OK" if (mt <= bound and mp <= bound) else "VIOLATION"
        print(f"  {k} | {mt} | {mp} | {bound}  [{flag}]")
    print(f"  all within bound: {all_ii_ok}")

    print("\n=== V1(iii): cycle structure of k-bit NAND register ===")
    for k in range(2, 9):
        transient, cyclen, succ_map, cycles = v1iii(k)
        max_t = max(transient)
        cyc_lens = sorted(cycles.values())
        print(f"  k={k}: {2**k} states, cycles (lengths)={cyc_lens}, "
              f"n_cycles={len(cycles)}, max_transient={max_t}")


if __name__ == "__main__":
    main()
