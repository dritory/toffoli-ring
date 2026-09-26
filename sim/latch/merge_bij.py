"""Fill in the 'bijective' column of ranked.csv from bij.c's output."""
import csv
import sys

RANKED = "/home/user/toffoli-ring/results/latch/ranked.csv"
BIJOUT = "/home/user/toffoli-ring/sim/latch/bij_out.txt"


def main():
    bij = {}
    with open(BIJOUT) as f:
        for line in f:
            parts = line.split()
            if len(parts) < 3:
                continue
            fh, gh, ans = parts[0], parts[1], parts[2]
            bij[(fh, gh)] = ans

    with open(RANKED) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["bijective"] = bij.get((r["f_hex"], r["g_hex"]), "unknown")

    with open(RANKED, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"filled bijective for {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
