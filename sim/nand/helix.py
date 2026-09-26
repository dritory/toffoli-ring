"""Decisive helix test requested by the coordinator.

1. For R3(k), k=2..5, N=16..64 (step 4), 100 seeds: find the smallest M such
   that e_tau = e_{tau-M} for a verification window of 5N steps, searching
   M in [1, 3N]. Histogram of M-N per (k,N).
2. Seeds with no such M <= 3N: list with their (full ring-state) period, show
   a spacetime diagram of one.
3. S3 survivors: velocity minus background's per-pass shift, to 3 decimals,
   measured over passes 100-200. If ~0 -> frozen/co-moving defects.
4. Same M-search for the write-between geometries; compare to M = L+p,
   L=N-(b-c), p=c-a.
"""
import random
import sys
sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
from nandring import (r3_pass, nand_pass, to_str, find_period_brent,
                       helix_trace_general, helix_trace_r3)

OUT_MD = "/home/user/toffoli-ring/results/nand/r3_helix.md"

KS = [2, 3, 4, 5]
NS = list(range(16, 65, 4))
SEEDS = 100
WARMUP_PASSES = 20   # generous vs. S1's observed transient (<=7 passes)
SEARCH_MULT = 3      # search M up to 3N
VERIFY_MULT = 5      # verify over a window of 5N


def find_M(e, search_max, verify_window):
    """Smallest M in [1, search_max] with e[M:M+verify_window] == e[0:verify_window]."""
    pattern = e[:verify_window]
    idx = e.find(pattern, 1)
    if idx == -1 or idx > search_max:
        return None
    return idx


def analyze_r3_seed(k, n, rng):
    s0 = [rng.randint(0, 1) for _ in range(n)]
    warmup = WARMUP_PASSES * n
    total = warmup + SEARCH_MULT * n + VERIFY_MULT * n + 1
    trace = helix_trace_r3(s0, k, total)
    e = trace[warmup:]
    M = find_M(e, SEARCH_MULT * n, VERIFY_MULT * n)
    return s0, M


def full_state_period(s0, k, cap=2000):
    mu, lam = find_period_brent(s0, lambda s: r3_pass(s, k), cap=cap)
    return mu, lam


def item1_and_2():
    lines = ["## 1-2. R3(k) helix period M (search M<=3N, verify over 5N)\n"]
    histo = {}          # (k,n) -> list of M-n (only found)
    not_found = []      # (k,n,seed_idx,s0)
    for k in KS:
        for n in NS:
            rng = random.Random(2024_0000 + k * 100003 + n)
            diffs = []
            for seed_idx in range(SEEDS):
                s0, M = analyze_r3_seed(k, n, rng)
                if M is None:
                    not_found.append((k, n, seed_idx, s0))
                else:
                    diffs.append(M - n)
            histo[(k, n)] = diffs
            print(f"k={k} N={n}: found {len(diffs)}/{SEEDS}, "
                  f"M-N range=[{min(diffs) if diffs else None},"
                  f"{max(diffs) if diffs else None}]")

    lines.append("Histogram of (M - N) per (k,N), counts over 100 seeds "
                  "(blank = value not observed; 'miss' = no M<=3N found):\n")
    for k in KS:
        lines.append(f"\n### k={k}\n")
        lines.append("| N | found/100 | miss | min(M-N) | median(M-N) | max(M-N) | "
                      "value:count histogram |")
        lines.append("|---|---|---|---|---|---|---|")
        for n in NS:
            diffs = histo[(k, n)]
            miss = SEEDS - len(diffs)
            if diffs:
                import statistics
                mn, med, mx = min(diffs), statistics.median(diffs), max(diffs)
                from collections import Counter
                c = Counter(diffs)
                hist_str = ", ".join(f"{v}:{ct}" for v, ct in sorted(c.items()))
            else:
                mn = med = mx = "-"
                hist_str = "(all missed)"
            lines.append(f"| {n} | {len(diffs)} | {miss} | {mn} | {med} | {mx} | {hist_str} |")

    lines.append(f"\nTotal seeds with NO M<=3N found: {len(not_found)} "
                 f"(out of {len(KS)*len(NS)*SEEDS})\n")

    if not_found:
        lines.append("\n### Seeds with no M<=3N (listed with full ring-state period)\n")
        lines.append("| k | N | seed_idx | full-state transient (passes) | "
                      "full-state period (passes) |")
        lines.append("|---|---|---|---|---|")
        example = None
        for (k, n, seed_idx, s0) in not_found:
            mu, lam = full_state_period(s0, k, cap=2000)
            lines.append(f"| {k} | {n} | {seed_idx} | {mu} | {lam} |")
            if example is None:
                example = (k, n, s0)
        if example:
            k, n, s0 = example
            lines.append(f"\nSpacetime diagram of one such seed (k={k}, N={n}), "
                          f"20 passes:\n")
            lines.append("```")
            rows = [s0]
            for _ in range(20):
                rows.append(r3_pass(rows[-1], k))
            for t, r in enumerate(rows):
                lines.append(f"t={t:3d}: {to_str(r)}")
            lines.append("```")
    else:
        lines.append("\n(none -- every seed in the sweep had M<=3N)\n")

    return lines, histo, not_found


def item3():
    """Re-derive S3 survivors and report velocity - background_shift over
    passes 100-200, to 3 decimals."""
    lines = ["\n## 3. S3 survivors: velocity minus background shift (passes 100-200)\n"]
    sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
    import importlib
    import s3
    importlib.reload(s3)
    from s3 import (run, diff, measure_background_velocity, measure_velocity,
                     BACKGROUNDS)

    for k, pat in BACKGROUNDS.items():
        p = len(pat)
        copies = 600
        n = copies * p
        passes = 200
        v, _ = measure_background_velocity(k, pat)
        bg = run(pat * copies, k, passes)
        center = n // 2
        lines.append(f"\n### k={k}, background `{to_str(pat)}` (p={p}), "
                      f"background shift v={v} cells/pass\n")
        lines.append("| patch (width) | pattern | velocity (steps 100-200) | "
                      "velocity - v | frozen (|.|<0.05)? |")
        lines.append("|---|---|---|---|---|")
        import itertools
        count = 0
        for w in range(1, 5):
            for bits in itertools.product((0, 1), repeat=w):
                patch = list(bits)
                s = pat * copies
                for idx, b in enumerate(patch):
                    s[(center + idx) % n] = b
                if s == bg[0]:
                    continue
                rows = run(s, k, passes)
                dev = diff(rows, bg)
                vel_full = measure_velocity(dev, n, center)
                vel_late = measure_velocity(dev[100:], n, center)
                if vel_late is None:
                    continue
                rel = vel_late - v
                frozen = "yes" if abs(rel) < 0.05 else "no"
                lines.append(f"| {w} | `{to_str(patch)}` | {vel_late:.3f} | "
                              f"{rel:.3f} | {frozen} |")
                count += 1
        print(f"item3 k={k}: reported {count} patches")
    return lines


def item4():
    lines = ["\n## 4. Write-between geometries: helix period M vs. predicted L+p\n"]
    lines.append("Prediction: M = L + p, L = N-(b-c), p = c-a.\n")
    GEOMS = []
    for b in range(1, 5):
        for c in range(1, b + 1):
            GEOMS.append((0, c, b))
    lines.append("| geom(a,c,b) | N | L | p | predicted M=L+p | found/100 | "
                  "min(M) | median(M) | max(M) | matches predicted (all)? |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for (a, c, b) in GEOMS:
        for n in NS:
            L = n - (b - c)
            p = c - a
            predicted = L + p
            rng = random.Random(555_0000 + a * 13 + c * 101 + b * 1009 + n)
            Ms = []
            search_max = max(3 * n, predicted + 2 * n)
            verify = 5 * n
            for _ in range(SEEDS):
                s0 = [rng.randint(0, 1) for _ in range(n)]
                warmup = WARMUP_PASSES * n
                total = warmup + search_max + verify + 1
                trace = helix_trace_general(s0, a, b, c, total)
                e = trace[warmup:]
                M = find_M(e, search_max, verify)
                if M is not None:
                    Ms.append(M)
            if Ms:
                import statistics
                mn, med, mx = min(Ms), statistics.median(Ms), max(Ms)
                all_match = all(m == predicted for m in Ms)
            else:
                mn = med = mx = "-"
                all_match = False
            lines.append(f"| {(a,c,b)} | {n} | {L} | {p} | {predicted} | "
                          f"{len(Ms)} | {mn} | {med} | {mx} | {all_match} |")
        print(f"item4 geom {(a,c,b)} done")
    return lines


def main():
    lines = ["# R3 / write-between helix decisive test\n",
             "Requested by the coordinator to test whether R3(k) merely collapses "
             "to a helical rigid rotation (dead) despite S1's period/transient "
             "numbers.\n"]
    l1, histo, not_found = item1_and_2()
    lines += l1
    lines += item3()
    lines += item4()
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines))
    print(f"\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()
