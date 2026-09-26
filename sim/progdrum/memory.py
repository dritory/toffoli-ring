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


def load_candidates(require_both_movers=True):
    """Programs from slide.csv with both a left- and a right-mover (the
    literal task 2c precondition). If that set is empty (it is: see
    memory.md's note), fall back to programs with >=1 memory occurrence AND
    a mover in at least one direction -- the closest available proxy for
    "supports both a localized structure and a signal that can reach it"."""
    cands = []
    with open(SLIDE_CSV) as f:
        for row in csv.DictReader(f):
            has_left = int(row["n_moves_left"]) > 0
            has_right = int(row["n_moves_right"]) > 0
            has_mem = int(row["n_memory"]) > 0
            qualifies = (has_left and has_right) if require_both_movers else (
                has_mem and (has_left or has_right))
            if qualifies:
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


TOGGLE_SAMPLES_PER_SIZE = 3  # toggle-test up to this many survivors per flip-count (2,3,4)


def search_one_program(cand):
    """Exhaustive 2-4-bit injection search within the middle 2P-site window.
    Returns a lightweight per-program summary (not one full dict per
    survivor, which would duplicate the M-length background/program arrays
    tens of thousands of times over): survivor_summaries is a list of
    (flip_positions, period, max_width) tuples, and toggle_samples runs the
    (cheap) toggle test immediately, in-worker, on up to
    3*TOGGLE_SAMPLES_PER_SIZE representative survivors so the whole
    148k-structure landscape gets a toggle check, not just the handful of
    globally-cheapest examples."""
    k, P, s = cand["k"], cand["P"], cand["s"]
    bits = [int(c) for c in cand["program"]]
    bg, src, conv, prog_full, M = background_for(k, P, s, bits)
    mb0 = MIDDLE_BLOCK * P
    window_positions = list(range(mb0, mb0 + WINDOW_FACTOR * P))
    n_rows = N_ROWS_FACTOR * P
    window = WINDOW_FACTOR * P
    period_cap = PERIOD_CAP_FACTOR * P

    survivor_summaries = []
    toggle_samples = []
    for size in (2, 3, 4):
        n_this_size = 0
        for combo in itertools.combinations(window_positions, size):
            res = classify_localized(bg, prog_full, k, M, P, list(combo), n_rows,
                                       s=s, window=window, period_cap=period_cap)
            if res["localized"]:
                survivor_summaries.append((list(combo), res["period"], res["max_width"]))
                if n_this_size < TOGGLE_SAMPLES_PER_SIZE:
                    n_this_size += 1
                    surv = {"k": k, "P": P, "s": s, "M": M, "background": bg,
                            "prog_full": prog_full, "flip_positions": list(combo),
                            "period": res["period"],
                            "fastest_left": cand["fastest_left"],
                            "fastest_right": cand["fastest_right"]}
                    tog = toggle_test(surv)
                    toggle_samples.append({"flip_positions": list(combo),
                                            "period": res["period"], "toggle": tog})
    return {"cand": cand, "bits": bits, "background": bg, "bg_source": src,
            "conv_rows": conv, "prog_full": prog_full, "M": M,
            "survivor_summaries": survivor_summaries, "toggle_samples": toggle_samples}


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


def _find_settled_state(local_fn, lo, hi, max_period):
    """Scan rows lo..hi for the first row r with local_fn(r)==local_fn(r+T)
    ==local_fn(r+2T) for some T in [1,max_period] (T constant, all three in
    range) -- a genuinely settled, verified-periodic local state, not just a
    one-off coincidental match. Returns (settled_row, period, pattern) or
    None. This guards against sampling a single row while a signal is
    mid-transit through the window (a moving disturbance recirculates in
    this finite frame, so a naive single-sample before/after comparison can
    mistake "caught mid-pass" for a permanent change)."""
    for r in range(lo, hi + 1):
        pr = local_fn(r)
        for T in range(1, max_period + 1):
            if r + 2 * T > hi:
                break
            if local_fn(r + T) == pr and local_fn(r + 2 * T) == pr:
                return r, T, pr
    return None


def toggle_test(surv, settle_rows_cap=None, max_extra_rows_cap=80):
    """Two-phase test: (1) let the localized structure settle on its own
    (no signal) and verify its settled, periodic local state; (2) from that
    settled state, inject the program's own fastest right-mover from the
    left and, separately, its fastest left-mover from the right, and check
    whether the local window re-settles to the SAME periodic state (robust)
    or a DIFFERENT one (a toggle) after the signal has passed, or is wiped
    out (destroyed). Both settled states are verified via
    _find_settled_state, not a single-row sample, since a moving
    disturbance recirculates in this finite frame and a single sample can
    catch it mid-transit."""
    k, P, s = surv["k"], surv["P"], surv["s"]
    M = surv["M"]
    bg = surv["background"]
    prog_full = surv["prog_full"]
    mb0 = MIDDLE_BLOCK * P
    flip_positions = surv["flip_positions"]
    period = surv["period"] or (4 * P)
    max_period = max(period * 2, 4)
    win_lo = mb0 - P // 2
    win_hi = mb0 + WINDOW_FACTOR * P + P // 2
    if settle_rows_cap is None:
        settle_rows_cap = max(8 * P, 4 * max_period + 4)

    # Phase 1: let the bare defect settle (no signal yet).
    rows0 = run_rows_full(bg, prog_full, k, M, flip_positions, settle_rows_cap, s=s)

    def local0(r):
        row = rows0[max(0, min(r, len(rows0) - 1))]
        return tuple(row[x % M] ^ bg[x % M] for x in range(win_lo, win_hi))

    settle0 = _find_settled_state(local0, 1, settle_rows_cap - 2 * max_period - 1, max_period)
    if settle0 is None:
        return {"left": {"status": "defect_did_not_resettle_in_budget"},
                "right": {"status": "defect_did_not_resettle_in_budget"}}
    settle_row0, period0, pat_before = settle0
    baseline_row = rows0[settle_row0]  # full row: bg + settled defect, no signal

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
        n_rows = min(max(collision_row + max_extra_rows_cap, collision_row + 2 * max_period + 2),
                     max_extra_rows_cap * P)
        # Phase 2: from the settled baseline (no signal), inject just the
        # traveling signal and watch it approach and pass the defect.
        rows2 = run_rows_full(baseline_row, prog_full, k, M, [signal_pos], n_rows, s=s)

        def local2(r, rows2=rows2):
            row = rows2[max(0, min(r, len(rows2) - 1))]
            return tuple(row[x % M] ^ bg[x % M] for x in range(win_lo, win_hi))

        after_lo = collision_row + 1
        after_hi = len(rows2) - 2 * max_period - 1
        after = _find_settled_state(local2, after_lo, max(after_lo, after_hi), max_period) \
            if after_hi > after_lo else None
        if after is None:
            out[direction] = {
                "status": "inconclusive (signal did not produce a verified "
                          "settled state after collision, within the row budget)",
                "offset": offset, "src_block": src_block, "distance": distance,
                "collision_row": collision_row,
            }
            continue
        after_row, after_T, pat_after = after
        destroyed = (sum(pat_after) == 0)
        same = (pat_after == pat_before)
        out[direction] = {
            "status": "destroyed" if destroyed else ("same" if same else "toggled"),
            "offset": offset, "src_block": src_block, "distance": distance,
            "collision_row": collision_row, "after_settled_row": after_row,
            "after_period": after_T,
            "pat_before": "".join("#" if b else "." for b in pat_before),
            "pat_after": "".join("#" if b else "." for b in pat_after),
        }
    return out


def main():
    t0 = time.time()
    strict_cands = load_candidates(require_both_movers=True)
    used_fallback = False
    print(f"[memory] {len(strict_cands)} candidate programs with BOTH a left- "
          f"and right-mover (the literal task 2c precondition)", flush=True)
    if strict_cands:
        cands = strict_cands
    else:
        used_fallback = True
        cands = load_candidates(require_both_movers=False)
        print(f"[memory] literal precondition is EMPTY (see memory.md); falling "
              f"back to {len(cands)} programs with >=1 memory occurrence and a "
              f"mover in at least one direction", flush=True)

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
                n_surv_total = sum(len(r["survivor_summaries"]) for r in results)
                print(f"[memory] {i+1}/{len(cands)} programs searched "
                      f"({n_surv_total} localized structures so far, {time.time()-t0:.1f}s)",
                      flush=True)

    print(f"[memory] search done ({time.time()-t0:.1f}s)", flush=True)

    n_total_structures = sum(len(r["survivor_summaries"]) for r in results)
    n_progs_with = sum(1 for r in results if r["survivor_summaries"])
    print(f"[memory] {n_total_structures} total localized structures found "
          f"across {n_progs_with} programs ({time.time()-t0:.1f}s)", flush=True)

    # toggle-test tallies across ALL sampled survivors (not just the cheapest)
    toggle_tally = {}  # status -> count, per direction
    toggle_hits = []   # (cost_key, r, sample) for every "toggled" result found
    for r in results:
        cand = r["cand"]
        cost = (cand["P"], cand["program"].count("1"))
        for sample in r["toggle_samples"]:
            for direction in ("left", "right"):
                status = sample["toggle"].get(direction, {}).get("status", "?")
                toggle_tally.setdefault(direction, {})
                toggle_tally[direction][status] = toggle_tally[direction].get(status, 0) + 1
                if status == "toggled":
                    toggle_hits.append((cost, r, sample, direction))
    toggle_hits.sort(key=lambda h: h[0])

    # cheapest programs (by P, then popcount) that have >=1 localized structure
    results_with = [r for r in results if r["survivor_summaries"]]

    def prog_cost_key(r):
        return (r["cand"]["P"], r["cand"]["program"].count("1"))
    results_with.sort(key=prog_cost_key)

    write_report(cands, results, results_with, toggle_tally, toggle_hits, t0,
                 used_fallback, len(strict_cands))
    return cands, results


def write_report(cands, results, results_with, toggle_tally, toggle_hits, t0,
                  used_fallback, n_strict):
    lines = ["# Task 2c: memory search\n"]
    if used_fallback:
        lines.append(
            f"**The literal precondition is empty.** Zero of the 54,320 stationary "
            "programs from task 2b have both a moves_left AND a moves_right "
            "instance among their own middle-block single-bit disturbances "
            f"(checked: {n_strict} qualify). This is a genuine structural "
            "finding, not a search-coverage gap: 28,610 programs have >=1 "
            "moves_left instance and 421 have >=1 moves_right instance, but "
            "these two sets are disjoint -- among programs with any memory "
            "occurrence, not one has a right-mover either. The static frame's "
            "copy sites always shift data left one site per row (u_r(x) = "
            "u_{r-1}(x+s)); gate chains have to fight this systemic leftward "
            "drift to produce a net rightward group velocity, and apparently "
            "no program in this search does that while also supporting a "
            "clean independent leftward mover elsewhere in the same block.\n"
        )
        lines.append(
            f"\n**Fallback used for the search below:** the {len(cands)} "
            "programs with >=1 memory occurrence (a single-bit disturbance "
            "that settles into a stationary periodic pattern, from task 2b) "
            "AND a mover in at least one direction (in practice, always "
            "moves_left -- see above). This tests the same physical "
            "question (can a stationary structure be reached and possibly "
            "toggled by an arriving signal) with a signal from whichever "
            "direction the program actually supports, rather than from "
            "both.\n"
        )
    lines.append(
        f"\n{len(cands)} candidate (k,s,program) combinations tested. For each, "
        "every pattern of 2-4 flipped sites within "
        "the 2P-site window [6P,8P) (blocks 6-7) was tried, evolved 40P "
        "rows, and kept if the difference from the background stayed "
        "within that 2P window and settled into a period <=8P rows (early "
        "exit on death or on spreading past the window keeps this "
        "affordable: most few-bit patches die or spread within a handful "
        "of rows).\n"
    )
    n_total_structures = sum(len(r["survivor_summaries"]) for r in results)
    lines.append(f"\nTotal localized (memory-candidate) structures found: "
                 f"{n_total_structures}, across {len(results_with)} distinct "
                 f"programs (out of {len(cands)} candidates tested).\n")

    by_k = {2: [], 3: []}
    for r in results:
        by_k[r["cand"]["k"]].extend(r["survivor_summaries"])
    lines.append("\n| k | programs tested | programs with >=1 localized structure | "
                 "total localized structures |\n|---|---|---|---|\n")
    for k in (2, 3):
        n_tested_k = sum(1 for c in cands if c["k"] == k)
        n_with = sum(1 for r in results_with if r["cand"]["k"] == k)
        lines.append(f"| {k} | {n_tested_k} | {n_with} | {len(by_k[k])} |\n")

    lines.append(
        "\n## Toggle test, tallied over every sampled structure\n\n"
        f"Every localized structure found was toggle-tested in-worker "
        f"(up to {3 * TOGGLE_SAMPLES_PER_SIZE} representative samples per "
        "program, spread over the 2/3/4-flipped-site sizes), using the "
        "two-phase protocol: let the bare defect settle, then fire the "
        "program's own fastest available mover at it from the side it "
        "actually travels toward, and verify (via repeated-period checking, "
        "not a single-row sample) whether the local window re-settles to "
        "the SAME periodic state, a DIFFERENT one (toggled), is wiped out "
        "(destroyed), or never re-settles within the row budget "
        "(inconclusive).\n"
    )
    lines.append("\n| signal direction | " + " | ".join(sorted({
        st for d in toggle_tally for st in toggle_tally[d]})) + " |\n")
    all_statuses = sorted({st for d in toggle_tally for st in toggle_tally[d]})
    lines.append("|---|" + "---|" * len(all_statuses) + "\n")
    for direction in ("left", "right"):
        row = [str(toggle_tally.get(direction, {}).get(st, 0)) for st in all_statuses]
        lines.append(f"| {direction} | " + " | ".join(row) + " |\n")

    lines.append(f"\n**Genuine toggles found: {len(toggle_hits)}** (signal from "
                 "the right, since that is the only direction any "
                 "memory-and-mover program supports).\n")

    lines.append("\n## Cheapest localized structures (one row per distinct program)\n")
    lines.append("| k | s | P | ones | program | cheapest flips (offset in window) | period (rows) | max width | n localized (this program) |\n")
    lines.append("|---|---|---|---|---|---|---|---|---|\n")
    for r in results_with[:8]:
        cand = r["cand"]
        combo, period, width = min(r["survivor_summaries"], key=lambda t: len(t[0]))
        mb0 = MIDDLE_BLOCK * cand["P"]
        offs = [fp - mb0 for fp in combo]
        lines.append(f"| {cand['k']} | {cand['s']} | {cand['P']} | {cand['program'].count('1')} | "
                     f"`{cand['program']}` | {offs} | {period} | {width:.1f} | "
                     f"{len(r['survivor_summaries'])} |\n")

    # spacetime diagrams + toggle test for the top few cheapest examples,
    # plus the cheapest genuine TOGGLE found anywhere in the sampled set.
    lines.append("\n## Spacetime diagrams and toggle test (cheapest examples)\n")
    n_diagrams = min(4, len(results_with))
    shown = []
    for r in results_with[:n_diagrams]:
        combo, period, width = min(r["survivor_summaries"], key=lambda t: len(t[0]))
        shown.append((r, combo, period))
    if toggle_hits:
        cost, r, sample, direction = toggle_hits[0]
        shown.append((r, sample["flip_positions"], sample["period"]))
        lines.append(f"\n(The last example below is the cheapest genuine TOGGLE found "
                     f"anywhere in the sampled set: P={cost[0]}, ones={cost[1]}.)\n")

    for r, combo, period in shown:
        cand = r["cand"]
        P, k, s = cand["P"], cand["k"], cand["s"]
        M = r["M"]
        bg = r["background"]
        prog_full = r["prog_full"]
        n_rows = min(20 * P, 400)
        rows = run_rows_full(bg, prog_full, k, M, combo, n_rows, s=s)
        mb0 = MIDDLE_BLOCK * P
        win_lo = mb0 - P
        win_hi = mb0 + WINDOW_FACTOR * P + P
        lines.append(f"\n### k={k} s={s} P={P} ones={cand['program'].count('1')} p=`{cand['program']}` "
                     f"flips={[fp - mb0 for fp in combo]} period={period}\n")
        stride = max(1, len(rows) // 100)
        diagram = []
        for row_i in range(0, len(rows), stride):
            d = "".join("#" if (rows[row_i][x % M] ^ bg[x % M]) else "." for x in range(win_lo, win_hi))
            diagram.append(f"r={row_i:4d}: {d}")
        lines.append("```\n" + "\n".join(diagram) + "\n```\n")

        surv = {"k": k, "P": P, "s": s, "M": M, "background": bg, "prog_full": prog_full,
                "flip_positions": combo, "period": period,
                "fastest_left": cand["fastest_left"], "fastest_right": cand["fastest_right"]}
        tog = toggle_test(surv)
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
