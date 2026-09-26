"""S1: R3(k): s[i+k] = NOT(s[i] & s[i+1] & s[i+k]).
k=2..5, N=16..64 (step 4), 200 random seeds each.
Report per-seed: transient length, period, final density (fraction of 1s in
the state at the end of the transient, i.e. at the start of the detected
cycle). CSV: results/nand/r3_s1.csv columns k,N,seed,transient,period,final_density.
Plus summary table (median/max transient & period per (k,N)), and whether
periods grow with N.
"""
import csv
import random
import statistics
import sys
sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
from nandring import r3_pass, find_period_brent

KS = [2, 3, 4, 5]
NS = list(range(16, 65, 4))
SEEDS = 200
CAP = 10 ** 6
OUT_CSV = "/home/user/toffoli-ring/results/nand/r3_s1.csv"


def final_density(s0, k, transient):
    """State density at the moment the orbit enters its cycle (after `transient` passes)."""
    s = list(s0)
    for _ in range(transient):
        s = r3_pass(s, k)
    return sum(s) / len(s)


def main():
    rows = []
    summary = {}
    for k in KS:
        for n in NS:
            rng = random.Random(1000003 * k + n)
            transients = []
            periods = []
            n_capped = 0
            n_leq2 = 0
            for seed_idx in range(SEEDS):
                s0 = [rng.randint(0, 1) for _ in range(n)]
                mu, lam = find_period_brent(s0, lambda s: r3_pass(s, k), cap=CAP)
                if mu is None:
                    rows.append([k, n, seed_idx, ">cap", ">cap", ""])
                    n_capped += 1
                    continue
                dens = final_density(s0, k, mu)
                rows.append([k, n, seed_idx, mu, lam, f"{dens:.4f}"])
                transients.append(mu)
                periods.append(lam)
                if lam <= 2:
                    n_leq2 += 1
            summary[(k, n)] = dict(
                med_t=statistics.median(transients) if transients else None,
                max_t=max(transients) if transients else None,
                med_p=statistics.median(periods) if periods else None,
                max_p=max(periods) if periods else None,
                frac_leq2=n_leq2 / SEEDS,
                n_capped=n_capped,
            )

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["k", "N", "seed", "transient", "period", "final_density"])
        w.writerows(rows)
    print(f"wrote {OUT_CSV} ({len(rows)} rows)")

    print("\n=== summary: median/max transient & period per (k,N) ===")
    print(f"{'k':>3} {'N':>4} {'med_T':>7} {'max_T':>7} {'med_P':>7} {'max_P':>7} "
          f"{'frac_period<=2':>15} {'#capped':>8}")
    for k in KS:
        for n in NS:
            s = summary[(k, n)]
            print(f"{k:>3} {n:>4} {s['med_t']:>7} {s['max_t']:>7} {s['med_p']:>7} "
                  f"{s['max_p']:>7} {s['frac_leq2']:>15.3f} {s['n_capped']:>8}")

    print("\n=== does period/transient grow with N? (max over seeds, per k) ===")
    for k in KS:
        max_ps = [summary[(k, n)]['max_p'] for n in NS]
        max_ts = [summary[(k, n)]['max_t'] for n in NS]
        print(f" k={k}: N={NS}")
        print(f"       max_period={max_ps}")
        print(f"       max_transient={max_ts}")


if __name__ == "__main__":
    main()
