"""HANDOVER-C sec 3, task 2b: generalised slide N = mP-s, s=1..P-1.

Part 1: verify the generalised static frame (copy sites read u_{r-1}(x+s),
with the boundary rule -- the last s columns of a copy site read the SAME
row's columns [0,s-1] instead) against the literal machine, 500 random
instances per s.

Part 2: repeat task 2's gadget search (stationary background, single-bit
injection classification, two-bit interaction) for k=2,3, P=4..12, all
s=1..P-1, m=12. Report per (k,s): counts per class, fastest left/right
mover (speed in sites/row), cheapest program per class.

Writes results/progdrum/slide.md and slide.csv. At most 2 worker processes.
"""
import csv
import multiprocessing as mp
import random
import statistics
import sys
import time

sys.path.insert(0, "/home/user/toffoli-ring/sim/progdrum")
from machine import run_literal_ticks, static_frame_rows, random_bits, to_str
from gadget import (
    step_row, run_to_fixed, pattern_to_bits, popcount_pattern, bits_to_str,
    classify_disturbance, run_rows_full, M_BLOCKS,
)

MD_OUT = "/home/user/toffoli-ring/results/progdrum/slide.md"
CSV_OUT = "/home/user/toffoli-ring/results/progdrum/slide.csv"
MIDDLE_BLOCK = M_BLOCKS // 2

KS = (2, 3)
P_RANGE = range(4, 13)  # 4..12
CLASSES = ["dies", "memory", "moves_left", "moves_right", "grows"]


# ============================================================ Part 1 =====
def verify_generalised_slide(seed=20260927, n_per_s=500, s_values=range(1, 12),
                              rows_checked=5):
    lines = ["## 1. Verification: generalised static frame (N = mP-s)\n"]
    lines.append(
        f"{n_per_s} random instances per s (s = {s_values.start}..{s_values.stop-1}), "
        f"each with a random P > s (P in [s+1,14]), m in [2,10], k in [2,6] "
        f"(N=mP-s > k+1 enforced by resampling). Compares the literal machine "
        f"against `static_frame_rows(..., s=s)` for {rows_checked} rows "
        f"beyond row 0 (row 0 seeded from the literal trace).\n"
    )
    lines.append("\n| s | instances | matched | mismatches |\n|---|---|---|---|\n")
    rng = random.Random(seed)
    total_fail = 0
    fail_examples = []
    for s in s_values:
        ok = 0
        for _ in range(n_per_s):
            while True:
                P = rng.randint(s + 1, 14)
                m = rng.randint(2, 10)
                k = rng.randint(2, 6)
                N = m * P - s
                if N > k + 1:
                    break
            M = m * P
            p = random_bits(P, rng)
            s0 = random_bits(N, rng)
            ticks = (rows_checked + 1) * M
            _, e_a = run_literal_ticks(s0, p, k, ticks)
            row0 = e_a[0:M]
            rows = static_frame_rows(p, k, m, row0, rows_checked, s=s)
            good = all(rows[r] == e_a[r * M:(r + 1) * M] for r in range(1, rows_checked + 1))
            if good:
                ok += 1
            else:
                total_fail += 1
                if len(fail_examples) < 3:
                    fail_examples.append((s, P, m, k))
        lines.append(f"| {s} | {n_per_s} | {ok} | {n_per_s - ok} |\n")
        print(f"[verify] s={s}: {ok}/{n_per_s} matched", flush=True)
    if total_fail:
        lines.append(f"\n**{total_fail} total mismatches.** Examples (s,P,m,k): {fail_examples}\n")
    else:
        lines.append("\nNo mismatches: the generalised static frame (copy sites read "
                     "u_{r-1}(x+s), with the last s columns of a copy site reading "
                     "the same row's columns [0,s-1]) is confirmed identical to the "
                     "literal machine for every s tested.\n")
    return lines, total_fail == 0


# ============================================================ Part 2 =====
def phase1_scan(k, P, s):
    M = M_BLOCKS * P
    out = []
    for pattern in range(1, 2 ** P - 1):
        bits = pattern_to_bits(pattern, P)
        prog_full = bits * M_BLOCKS
        bg0, r0 = run_to_fixed(prog_full, k, M, [0] * M, 4 * P, s=s)
        bg1, r1 = run_to_fixed(prog_full, k, M, [1] * M, 4 * P, s=s)
        if bg0 is None and bg1 is None:
            continue
        if bg0 is not None:
            bg, src, conv = bg0, "zero", r0
        else:
            bg, src, conv = bg1, "one", r1
        out.append({"k": k, "P": P, "s": s, "pattern": pattern, "bits": bits,
                     "background": bg, "source": src, "conv_rows": conv})
    return out


def phase2_worker(surv):
    k, P, s, pattern, bits = surv["k"], surv["P"], surv["s"], surv["pattern"], surv["bits"]
    M = M_BLOCKS * P
    prog_full = bits * M_BLOCKS
    bg = surv["background"]
    n_rows = 20 * P
    mb0 = MIDDLE_BLOCK * P
    results = []
    for o in range(P):
        res = classify_disturbance(bg, prog_full, k, M, P, mb0 + o, n_rows, s=s)
        res["offset"] = o
        results.append(res)

    rows_a = run_rows_full(bg, prog_full, k, M, [mb0 + 0], n_rows, s=s)
    rows_b = run_rows_full(bg, prog_full, k, M, [mb0 + 1], n_rows, s=s)
    rows_ab = run_rows_full(bg, prog_full, k, M, [mb0 + 0, mb0 + 1], n_rows, s=s)
    interacts = False
    first_row_diff = None
    for r in range(len(rows_ab)):
        da = [rows_a[r][x] ^ bg[x] for x in range(M)]
        db = [rows_b[r][x] ^ bg[x] for x in range(M)]
        dab = [rows_ab[r][x] ^ bg[x] for x in range(M)]
        xor_pred = [da[x] ^ db[x] for x in range(M)]
        if dab != xor_pred:
            interacts = True
            first_row_diff = r
            break

    return {"k": k, "P": P, "s": s, "pattern": pattern, "bits": bits,
            "conv_rows": surv["conv_rows"], "source": surv["source"],
            "positions": results,
            "interaction": {"interacts": interacts, "first_row_diff": first_row_diff}}


def _phase1_task(args):
    k, P, s = args
    return phase1_scan(k, P, s)


def run_2b_search():
    t0 = time.time()
    tasks = [(k, P, s) for k in KS for P in P_RANGE for s in range(1, P)]
    all_survivors = []
    with mp.Pool(processes=2) as pool:
        for i, surv in enumerate(pool.imap(_phase1_task, tasks, chunksize=1)):
            all_survivors.extend(surv)
            if (i + 1) % 10 == 0 or (i + 1) == len(tasks):
                print(f"[phase1] {i+1}/{len(tasks)} (k,P,s) cells done "
                      f"(cumulative survivors {len(all_survivors)}, {time.time()-t0:.1f}s)", flush=True)
    print(f"[phase1] total survivors: {len(all_survivors)} ({time.time()-t0:.1f}s)", flush=True)

    with mp.Pool(processes=2) as pool:
        processed = []
        for i, res in enumerate(pool.imap_unordered(phase2_worker, all_survivors, chunksize=4)):
            processed.append(res)
            if (i + 1) % 500 == 0:
                print(f"[phase2] {i+1}/{len(all_survivors)} ({time.time()-t0:.1f}s)", flush=True)
    print(f"[phase2] done: {len(processed)} programs ({time.time()-t0:.1f}s)", flush=True)
    return processed


def write_csv(processed):
    """Task 2b spans ~20x more (k,P,s) cells than task 2, so a row per
    (program,position) would be tens of MB (measured: ~62MB) -- over the
    10MB budget. slide.csv is therefore one row per PROGRAM (not per
    position), with class counts and the fastest mover speeds; this is
    documented in slide.md. (gadgets.csv from task 2 remains one row per
    (program,position); that convention doesn't scale to 2b's program
    count.)
    """
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["program", "k", "P", "s", "n_dies", "n_memory",
                     "n_moves_left", "n_moves_right", "n_grows",
                     "fastest_left_speed_sites_per_row",
                     "fastest_right_speed_sites_per_row",
                     "interacts", "interact_first_row_diff"])
        for rec in processed:
            prog_str = bits_to_str(rec["bits"])
            counts = {c: 0 for c in CLASSES}
            fastest_left = 0.0
            fastest_right = 0.0
            for pos in rec["positions"]:
                c = pos["cls"]
                if c in counts:
                    counts[c] += 1
                if c == "moves_left":
                    fastest_left = max(fastest_left, abs(pos["velocity"]))
                elif c == "moves_right":
                    fastest_right = max(fastest_right, abs(pos["velocity"]))
            it = rec["interaction"]
            w.writerow([prog_str, rec["k"], rec["P"], rec["s"],
                         counts["dies"], counts["memory"], counts["moves_left"],
                         counts["moves_right"], counts["grows"],
                         f"{fastest_left:.4f}", f"{fastest_right:.4f}",
                         it["interacts"], it["first_row_diff"]])
    print(f"wrote {CSV_OUT}")


def aggregate_and_report(processed):
    lines = ["\n## 2. Gadget search across s (k=2,3, P=4..12, m=12)\n"]
    lines.append(f"Total stationary programs found (summed over all P,s): {len(processed)}\n")
    lines.append(
        "\nslide.csv is one row per PROGRAM (program,k,P,s,n_dies,n_memory,"
        "n_moves_left,n_moves_right,n_grows,fastest_left_speed_sites_per_row,"
        "fastest_right_speed_sites_per_row,interacts,interact_first_row_diff) "
        "rather than one row per (program,position) as in gadgets.csv: with "
        f"{len(processed)} programs (vs. task 2's 2893) a per-position CSV "
        "would be ~60MB, over the 10MB budget.\n"
    )

    by_ks = {}
    for rec in processed:
        by_ks.setdefault((rec["k"], rec["s"]), []).append(rec)

    def cheapest(entries):
        if not entries:
            return None
        return min(entries, key=lambda e: (e[0], e[1], e[2]))

    for k in KS:
        lines.append(f"\n### k={k}\n")
        lines.append("| s | programs tested (this s) | class counts (programs w/ occurrence) "
                     "| fastest left (sites/row) | fastest right (sites/row) | cheapest per class |\n")
        lines.append("|---|---|---|---|---|---|\n")
        s_max = max((s for (kk, s) in by_ks if kk == k), default=0)
        for s in range(1, s_max + 1):
            recs = by_ks.get((k, s), [])
            n_tested = sum(2 ** P - 2 for P in P_RANGE if P > s)
            class_progsets = {c: set() for c in CLASSES}
            class_entries = {c: [] for c in CLASSES}  # (P,pc,pattern,prog,offset,detail,rec)
            fastest_left = None   # (abs_speed, P, pc, pattern, prog, offset)
            fastest_right = None
            for rec in recs:
                P, pattern, bits = rec["P"], rec["pattern"], rec["bits"]
                pc = popcount_pattern(pattern, P)
                prog_str = bits_to_str(bits)
                for pos in rec["positions"]:
                    c = pos["cls"]
                    if c in CLASSES:
                        class_progsets[c].add((P, pattern))
                        class_entries[c].append((P, pc, pattern, prog_str, pos["offset"], pos["detail"]))
                    if c == "moves_left":
                        v = abs(pos["velocity"])
                        if fastest_left is None or v > fastest_left[0]:
                            fastest_left = (v, P, pc, pattern, prog_str, pos["offset"])
                    elif c == "moves_right":
                        v = abs(pos["velocity"])
                        if fastest_right is None or v > fastest_right[0]:
                            fastest_right = (v, P, pc, pattern, prog_str, pos["offset"])

            counts_str = ", ".join(f"{c}:{len(class_progsets[c])}" for c in CLASSES)
            fl = f"{fastest_left[0]:.3f} (P={fastest_left[1]},p=`{fastest_left[4]}`,off={fastest_left[5]})" if fastest_left else "-"
            fr = f"{fastest_right[0]:.3f} (P={fastest_right[1]},p=`{fastest_right[4]}`,off={fastest_right[5]})" if fastest_right else "-"
            cheap_strs = []
            for c in CLASSES:
                ch = cheapest(class_entries[c])
                if ch is None:
                    cheap_strs.append(f"{c}:-")
                else:
                    P, pc, pattern, prog_str, offset, detail = ch
                    cheap_strs.append(f"{c}:P={P},ones={pc},p=`{prog_str}`")
            lines.append(f"| {s} | {n_tested} | {counts_str} | {fl} | {fr} | "
                         f"{'; '.join(cheap_strs)} |\n")
        print(f"[report] k={k} done", flush=True)
    return lines, by_ks


def main():
    t0 = time.time()
    lines = ["# Task 2b: generalised slide N = mP-s\n"]
    l1, verify_ok = verify_generalised_slide()
    lines += l1
    processed = run_2b_search()
    write_csv(processed)
    l2, by_ks = aggregate_and_report(processed)
    lines += l2
    with open(MD_OUT, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {MD_OUT}")
    print(f"total time {time.time()-t0:.1f}s (verify_ok={verify_ok})")
    return processed, by_ks


if __name__ == "__main__":
    main()
