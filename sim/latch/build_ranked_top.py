"""Select the task-2 subset from results/latch/ranked.csv: every pair with
cost_total <= 2, plus a systematic (evenly spaced) sample of the cost_total==3
pairs, so the heavy per-pair dynamics work (cycle stats + vacuum + full
pairwise interaction grid) finishes in bounded time. Running it on all 122173
ranked.csv pairs would take on the order of a day; this keeps the same
cost-ordered coverage without the blowup, and is exactly the set task 2's
CSV/summary/seeds outputs are built from.
"""
import csv
import sys

RANKED = "/home/user/toffoli-ring/results/latch/ranked.csv"
OUT = "/home/user/toffoli-ring/results/latch/ranked_top.csv"
PAIRS_TOP = "/home/user/toffoli-ring/sim/latch/pairs_top.txt"

CAP_COST3_SAMPLE = 3000


def main():
    with open(RANKED) as f:
        rows = list(csv.DictReader(f))

    cheap = [r for r in rows if int(r["cost_total"]) <= 2]
    cost3 = [r for r in rows if int(r["cost_total"]) == 3]
    stride = max(1, len(cost3) // CAP_COST3_SAMPLE)
    sampled3 = cost3[::stride]

    out_rows = cheap + sampled3
    out_rows.sort(key=lambda r: (int(r["cost_total"]), r["f_hex"], r["g_hex"]))

    with open(OUT, "w", newline="") as f, open(PAIRS_TOP, "w") as pf:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
            pf.write(f"{r['f_hex']} {r['g_hex']} {r['class']}\n")

    print(f"cost<=2: {len(cheap)}, cost==3 sampled: {len(sampled3)} (stride {stride} of {len(cost3)}), "
          f"total ranked_top: {len(out_rows)}", file=sys.stderr)


if __name__ == "__main__":
    main()
