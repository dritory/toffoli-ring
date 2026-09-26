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


def find_mover_offset(bg, prog_full, k, M, P, s, target_cls, target_speed):
    """Among this program's own middle-block offsets, find the one whose
    single-bit disturbance is class target_cls ('moves_left'/'moves_right')
    with speed closest to target_speed (sites/row). Returns (offset, res)."""
    mb0 = MIDDLE_BLOCK * P
    n_rows = 20 * P
    best = None
    for o in range(P):
        res = classify_disturbance(bg, prog_full, k, M, P, mb0 + o, n_rows, s=s)
        if res["cls"] == target_cls:
            d = abs(abs(res["velocity"]) - target_speed)
            if best is None or d < best[2]:
                best = (o, res, d)
    if best is None:
        return None, None
    return best[0], best[1]


def toggle_test(surv, max_extra_rows_cap=60):
    """Fire the program's own fastest right-mover from the left, and its
    fastest left-mover from the right, at the localized structure `surv`
    lives in; report whether the post-collision local pattern differs from
    the pre-collision one (a toggle) or matches it (robust/no toggle), or
    the structure is destroyed."""
    k, P, s = surv["k"], surv["P"], surv["s"]
    M = surv["M"]
    bg = surv["background"]
    prog_full = surv["prog_full"]
    mb0 = MIDDLE_BLOCK * P
    flip_positions = surv["flip_positions"]
    period = surv["period"] or (4 * P)
    win_lo = mb0 - P // 2
    win_hi = mb0 + WINDOW_FACTOR * P + P // 2
    sample_width = win_hi - win_lo

    def local_pattern(row):
        return tuple(row[x % M] ^ bg[x % M] for x in range(win_lo, win_hi))

    out = {}
    for direction, target_cls, src_block in (("left", "moves_right", MIDDLE_BLOCK - 3),
                                              ("right", "moves_left", MIDDLE_BLOCK + 4)):
        target_speed = surv["fastest_right"] if direction == "left" else surv["fastest_left"]
        if target_speed <= 0:
            out[direction] = {"status": "no_mover_available"}
            continue
        offset, mover_res = find_mover_offset(bg, prog_full, k, M, P, s, target_cls, target_speed)
        if offset is None:
            out[direction] = {"status": "no_mover_offset_found"}
            continue
        signal_pos = src_block * P + offset
        distance = abs(signal_pos - mb0)
        collision_row = int(distance / max(target_speed, 1e-6)) + 1
        n_rows = min(collision_row + 8 * P, max_extra_rows_cap * P)
        if n_rows <= collision_row:
            out[direction] = {"status": "signal_too_slow_for_row_cap"}
            continue
        rows = run_rows_full(bg, prog_full, k, M, flip_positions + [signal_pos], n_rows, s=s)
        before_row = min(max(1, 3 * period), max(1, collision_row - 2 * P))
        after_row = min(len(rows) - 1, collision_row + 6 * P)
        pat_before = local_pattern(rows[before_row])
        pat_after = local_pattern(rows[after_row])
        destroyed = (sum(pat_after) == 0)
        same = (pat_after == pat_before)
        out[direction] = {
            "status": "destroyed" if destroyed else ("same" if same else "toggled"),
            "offset": offset, "src_block": src_block, "distance": distance,
            "collision_row": collision_row, "before_row": before_row, "after_row": after_row,
            "pat_before": "".join("#" if b else "." for b in pat_before),
            "pat_after": "".join("#" if b else "." for b in pat_after),
        }
    return out


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

    all_survivors = []
    for r in results:
        all_survivors.extend(r["survivors"])
    print(f"[memory] {len(all_survivors)} total localized structures found "
          f"across {sum(1 for r in results if r['survivors'])} programs "
          f"({time.time()-t0:.1f}s)", flush=True)

    # cheapest localized structures overall, and per k
    def gadget_cost_key(g):
        return (g["P"], sum(g["bits"]), len(g["flip_positions"]))
    all_survivors.sort(key=gadget_cost_key)

    write_report(cands, results, all_survivors, t0)
    return cands, results, all_survivors


def write_report(cands, results, all_survivors, t0):
    lines = ["# Task 2c: memory search\n"]
    lines.append(
        f"{len(cands)} (k,s,program) combinations from slide.csv have both a "
        "left-mover and a right-mover among their own single-bit "
        "disturbances. For each, every pattern of 2-4 flipped sites within "
        "the 2P-site window [6P,8P) (blocks 6-7) was tried, evolved 40P "
        "rows, and kept if the difference from the background stayed "
        "within that 2P window and settled into a period <=8P rows (early "
        "exit on death or on spreading past the window keeps this "
        "affordable: most few-bit patches die or spread within a handful "
        "of rows).\n"
    )
    lines.append(f"\nTotal localized (memory-candidate) structures found: "
                 f"{len(all_survivors)}, across "
                 f"{len(set((g['k'], g['s'], g['program']) for g in all_survivors))} "
                 f"distinct programs (out of {len(cands)} candidates tested).\n")

    by_k = {2: [], 3: []}
    for g in all_survivors:
        by_k[g["k"]].append(g)
    lines.append("\n| k | programs tested (both movers) | programs with >=1 localized structure | "
                 "total localized structures |\n|---|---|---|---|\n")
    for k in (2, 3):
        n_tested_k = sum(1 for c in cands if c["k"] == k)
        n_with = len(set((g["s"], g["program"]) for g in by_k[k]))
        lines.append(f"| {k} | {n_tested_k} | {n_with} | {len(by_k[k])} |\n")

    lines.append("\n## Cheapest localized structures\n")
    seen_progs = set()
    cheapest_examples = []
    for g in all_survivors:
        key = (g["k"], g["s"], g["program"])
        if key in seen_progs:
            continue
        seen_progs.add(key)
        cheapest_examples.append(g)
        if len(cheapest_examples) >= 8:
            break

    lines.append("| k | s | P | ones | program | flip positions (offset in window) | period (rows) | max width |\n")
    lines.append("|---|---|---|---|---|---|---|---|\n")
    for g in cheapest_examples:
        mb0 = MIDDLE_BLOCK * g["P"]
        offs = [fp - mb0 for fp in g["flip_positions"]]
        n_ones = sum(g["bits"])
        lines.append(f"| {g['k']} | {g['s']} | {g['P']} | {n_ones} | `{g['program']}` | "
                     f"{offs} | {g['period']} | {g['max_width']:.1f} |\n")

    # spacetime diagrams + toggle test for the top few cheapest examples
    lines.append("\n## Spacetime diagrams and toggle test (cheapest examples)\n")
    n_diagrams = min(4, len(cheapest_examples))
    for g in cheapest_examples[:n_diagrams]:
        P, k, s = g["P"], g["k"], g["s"]
        M = g["M"]
        bg = g["background"]
        prog_full = g["prog_full"]
        n_rows = min(20 * P, 400)
        rows = run_rows_full(bg, prog_full, k, M, g["flip_positions"], n_rows, s=s)
        mb0 = MIDDLE_BLOCK * P
        win_lo = mb0 - P
        win_hi = mb0 + WINDOW_FACTOR * P + P
        lines.append(f"\n### k={k} s={s} P={P} ones={sum(g['bits'])} p=`{g['program']}` "
                     f"flips={[fp - mb0 for fp in g['flip_positions']]} period={g['period']}\n")
        stride = max(1, len(rows) // 100)
        diagram = []
        for r in range(0, len(rows), stride):
            d = "".join("#" if (rows[r][x % M] ^ bg[x % M]) else "." for x in range(win_lo, win_hi))
            diagram.append(f"r={r:4d}: {d}")
        lines.append("```\n" + "\n".join(diagram) + "\n```\n")

        tog = toggle_test(g)
        lines.append("Toggle test (fire this program's own fastest right-mover from the "
                     "left, and fastest left-mover from the right, at this structure):\n")
        for direction in ("left", "right"):
            info = tog.get(direction, {})
            status = info.get("status", "?")
            lines.append(f"- signal from the {direction}: **{status}**"
                         + (f" (offset={info.get('offset')}, distance={info.get('distance')} sites, "
                            f"collision~row {info.get('collision_row')})" if "offset" in info else "")
                         + "\n")
            if "pat_before" in info:
                lines.append(f"  before: `{info['pat_before']}`\n")
                lines.append(f"  after:  `{info['pat_after']}`\n")

    with open(MD_OUT, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {MD_OUT}")
    print(f"total time {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
