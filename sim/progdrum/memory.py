"""HANDOVER-C sec 3, task 2c: memory search.

For the (k,s,program) combinations found in task 2b that have BOTH a
left-mover and a right-mover (n_moves_left>0 and n_moves_right>0 in
slide.csv), search for localized non-moving periodic structures: inject
every pattern of 2-4 flipped sites within a window of 2P sites (the middle
two blocks, columns [6P,8P)), run 40P rows, and keep patterns whose
difference from the background stays within a bounded window that does not
drift (period <= 8P rows).

Then, for the cheapest surviving localized structures, test whether a
signal (a moving disturbance, reusing the fastest left/right mover found
for that same program) arriving from the left or right can toggle it
between two distinct stable states (a 1-bit memory cell).

Writes results/progdrum/memory.md. At most 2 worker processes.
"""
import csv
import itertools
import multiprocessing as mp
import sys
import time

sys.path.insert(0, "/home/user/toffoli-ring/sim/progdrum")
from gadget import (
    step_row, run_to_fixed, pattern_to_bits, popcount_pattern, bits_to_str,
    classify_localized, classify_disturbance, run_rows_full, M_BLOCKS,
)

SLIDE_CSV = "/home/user/toffoli-ring/results/progdrum/slide.csv"
MD_OUT = "/home/user/toffoli-ring/results/progdrum/memory.md"
MIDDLE_BLOCK = M_BLOCKS // 2

N_ROWS_FACTOR = 40   # 40P rows
WINDOW_FACTOR = 2    # 2P-site injection window
PERIOD_CAP_FACTOR = 8  # period <= 8P rows


def load_candidates():
    """Programs from slide.csv with both a left- and a right-mover."""
    cands = []
    with open(SLIDE_CSV) as f:
        for row in csv.DictReader(f):
            if int(row["n_moves_left"]) > 0 and int(row["n_moves_right"]) > 0:
                cands.append({
                    "program": row["program"],
                    "k": int(row["k"]),
                    "P": int(row["P"]),
                    "s": int(row["s"]),
                    "fastest_left": float(row["fastest_left_speed_sites_per_row"]),
                    "fastest_right": float(row["fastest_right_speed_sites_per_row"]),
                })
    return cands


def background_for(k, P, s, bits):
    M = M_BLOCKS * P
    prog_full = bits * M_BLOCKS
    bg0, r0 = run_to_fixed(prog_full, k, M, [0] * M, 4 * P, s=s)
    bg1, r1 = run_to_fixed(prog_full, k, M, [1] * M, 4 * P, s=s)
    if bg0 is not None:
        return bg0, "zero", r0, prog_full, M
    return bg1, "one", r1, prog_full, M


def search_one_program(cand):
    """Exhaustive 2-4-bit injection search within the middle 2P-site window.
    Returns list of surviving localized structures (dicts)."""
    k, P, s = cand["k"], cand["P"], cand["s"]
    bits = [int(c) for c in cand["program"]]
    bg, src, conv, prog_full, M = background_for(k, P, s, bits)
    mb0 = MIDDLE_BLOCK * P
    window_positions = list(range(mb0, mb0 + WINDOW_FACTOR * P))
    n_rows = N_ROWS_FACTOR * P
    window = WINDOW_FACTOR * P
    period_cap = PERIOD_CAP_FACTOR * P

    survivors = []
    for size in (2, 3, 4):
        for combo in itertools.combinations(window_positions, size):
            res = classify_localized(bg, prog_full, k, M, P, list(combo), n_rows,
                                       s=s, window=window, period_cap=period_cap)
            if res["localized"]:
                survivors.append({
                    "k": k, "P": P, "s": s, "program": cand["program"],
                    "bits": bits, "background": bg, "bg_source": src,
                    "conv_rows": conv, "prog_full": prog_full, "M": M,
                    "flip_positions": list(combo),
                    "period": res["period"], "max_width": res["max_width"],
                    "fastest_left": cand["fastest_left"],
                    "fastest_right": cand["fastest_right"],
                })
    return {"cand": cand, "n_tested": (
                len(window_positions) * (len(window_positions) - 1) // 2 +
                len(window_positions) * (len(window_positions) - 1) * (len(window_positions) - 2) // 6 +
                len(window_positions) * (len(window_positions) - 1) * (len(window_positions) - 2) * (len(window_positions) - 3) // 24),
            "survivors": survivors}


def main():
    t0 = time.time()
    cands = load_candidates()
    print(f"[memory] {len(cands)} candidate programs (both movers) loaded from slide.csv", flush=True)

    # cheapest first: smallest P, then fewest ones, so a time-limited run
    # still gets a representative/complete picture at the cheap end.
    def cost_key(c):
        return (c["P"], c["program"].count("1"))
    cands.sort(key=cost_key)

    with mp.Pool(processes=2) as pool:
        results = []
        for i, res in enumerate(pool.imap(search_one_program, cands, chunksize=1)):
            results.append(res)
            if (i + 1) % 20 == 0 or (i + 1) == len(cands):
                n_surv_total = sum(len(r["survivors"]) for r in results)
                print(f"[memory] {i+1}/{len(cands)} programs searched "
                      f"({n_surv_total} localized structures so far, {time.time()-t0:.1f}s)",
                      flush=True)

    print(f"[memory] search done ({time.time()-t0:.1f}s)", flush=True)
    return cands, results


if __name__ == "__main__":
    main()
