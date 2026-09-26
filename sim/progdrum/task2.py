"""HANDOVER-C sec 3, task 2: gadget search in the static frame.

For k=2,3 and every block program p of length P=4..14 (all 2^P patterns,
skipping all-zero/all-one), m=12 blocks (M=12P):

1. Stationary background: run 4P rows from all-zero and from all-one rows;
   keep programs that settle to a row-invariant fixed row within 4P rows;
   record the background(s).
2. On each such background, inject a single flipped site at each of the P
   positions of the middle block (block index m//2 = 6), run 20P rows,
   classify the resulting difference-from-background pattern as dies /
   memory (stays in its block) / moves_left / moves_right / grows.
3. Interaction test: inject two adjacent bits (offsets 0 and 1 of the middle
   block) together and compare to XOR of the two single-bit runs.

Writes gadgets.csv (program,k,P,class,detail) and, via a second pass that
regenerates full spacetime traces only for the handful of cheapest examples,
gadgets.md with diagrams. Uses at most 2 worker processes.
"""
import csv
import json
import multiprocessing as mp
import sys
import time

sys.path.insert(0, "/home/user/toffoli-ring/sim/progdrum")
from gadget import (
    step_row, run_to_fixed, pattern_to_bits, popcount_pattern, bits_to_str,
    classify_disturbance, run_rows_full, circular_extent, M_BLOCKS,
)

CSV_OUT = "/home/user/toffoli-ring/results/progdrum/gadgets.csv"
MD_OUT = "/home/user/toffoli-ring/results/progdrum/gadgets.md"
MIDDLE_BLOCK = M_BLOCKS // 2  # block index 6 of 0..11

KS = (2, 3)
P_RANGE = range(4, 15)


# ------------------------------------------------------------- phase 1 ----
def phase1_scan(k, P):
    M = M_BLOCKS * P
    out = []
    for pattern in range(1, 2 ** P - 1):
        bits = pattern_to_bits(pattern, P)
        prog_full = bits * M_BLOCKS
        bg0, r0 = run_to_fixed(prog_full, k, M, [0] * M, 4 * P)
        bg1, r1 = run_to_fixed(prog_full, k, M, [1] * M, 4 * P)
        if bg0 is None and bg1 is None:
            continue
        if bg0 is not None:
            bg, src, conv = bg0, "zero", r0
        else:
            bg, src, conv = bg1, "one", r1
        both = (bg0 is not None and bg1 is not None)
        same = both and (bg0 == bg1)
        out.append({
            "k": k, "P": P, "pattern": pattern, "bits": bits,
            "background": bg, "source": src, "conv_rows": conv,
            "both_settle": both, "both_same": same,
        })
    return out


# ------------------------------------------------------------- phase 2 ----
def phase2_worker(surv):
    k, P, pattern, bits = surv["k"], surv["P"], surv["pattern"], surv["bits"]
    M = M_BLOCKS * P
    prog_full = bits * M_BLOCKS
    bg = surv["background"]
    n_rows = 20 * P
    mb0 = MIDDLE_BLOCK * P
    results = []
    for o in range(P):
        res = classify_disturbance(bg, prog_full, k, M, P, mb0 + o, n_rows)
        res.update({"offset": o})
        results.append(res)

    # interaction test: offsets 0 and 1 together vs XOR of the two singles
    rows_a = run_rows_full(bg, prog_full, k, M, [mb0 + 0], n_rows)
    rows_b = run_rows_full(bg, prog_full, k, M, [mb0 + 1], n_rows)
    rows_ab = run_rows_full(bg, prog_full, k, M, [mb0 + 0, mb0 + 1], n_rows)
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
    interaction = {"interacts": interacts, "first_row_diff": first_row_diff}

    return {"k": k, "P": P, "pattern": pattern, "bits": bits,
            "conv_rows": surv["conv_rows"], "source": surv["source"],
            "background": bg,
            "positions": results, "interaction": interaction}


def main():
    t0 = time.time()
    all_survivors = []
    for k in KS:
        for P in P_RANGE:
            s = phase1_scan(k, P)
            all_survivors.extend(s)
            print(f"[phase1] k={k} P={P}: {len(s)}/{2**P-2} survive "
                  f"({time.time()-t0:.1f}s)", flush=True)
    print(f"[phase1] total survivors: {len(all_survivors)} "
          f"({time.time()-t0:.1f}s)", flush=True)

    with mp.Pool(processes=2) as pool:
        processed = []
        for i, res in enumerate(pool.imap_unordered(phase2_worker, all_survivors, chunksize=4)):
            processed.append(res)
            if (i + 1) % 200 == 0:
                print(f"[phase2] {i+1}/{len(all_survivors)} "
                      f"({time.time()-t0:.1f}s)", flush=True)
    print(f"[phase2] done: {len(processed)} programs "
          f"({time.time()-t0:.1f}s)", flush=True)

    # ---------------------------------------------------------- CSV -----
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["program", "k", "P", "class", "details"])
        for rec in processed:
            prog_str = bits_to_str(rec["bits"])
            for pos in rec["positions"]:
                detail = (f"offset={pos['offset']} bg_source={rec['source']} "
                           f"conv_rows={rec['conv_rows']} rows_run={pos['rows_run']} "
                           f"{pos['detail']}")
                w.writerow([prog_str, rec["k"], rec["P"], pos["cls"], detail])
            it = rec["interaction"]
            cls = "interacts" if it["interacts"] else "no_interaction"
            detail = (f"pair_offsets=(0,1) bg_source={rec['source']} "
                       f"first_row_diff={it['first_row_diff']}")
            w.writerow([prog_str, rec["k"], rec["P"], cls, detail])
    print(f"wrote {CSV_OUT}")

    # ------------------------------------------------------ aggregate ---
    CLASSES = ["dies", "memory", "moves_left", "moves_right", "grows"]
    # per k: class -> list of (P, popcount, pattern, prog_str, offset, detail, rec)
    per_k_class = {k: {c: [] for c in CLASSES} for k in KS}
    per_k_class_progset = {k: {c: set() for c in CLASSES} for k in KS}
    interaction_hits = {k: [] for k in KS}

    for rec in processed:
        k, P, pattern, bits = rec["k"], rec["P"], rec["pattern"], rec["bits"]
        prog_str = bits_to_str(bits)
        pc = popcount_pattern(pattern, P)
        seen_classes_this_prog = set()
        for pos in rec["positions"]:
            c = pos["cls"]
            if c in CLASSES:
                per_k_class[k][c].append((P, pc, pattern, prog_str, pos["offset"], pos["detail"], rec))
                seen_classes_this_prog.add(c)
        for c in seen_classes_this_prog:
            per_k_class_progset[k][c].add(pattern)
        if rec["interaction"]["interacts"]:
            interaction_hits[k].append((P, pc, pattern, prog_str, rec))

    def cheapest(entries):
        if not entries:
            return None
        return min(entries, key=lambda e: (e[0], e[1], e[2]))

    cheapest_per_k_class = {}
    for k in KS:
        cheapest_per_k_class[k] = {}
        for c in CLASSES:
            cheapest_per_k_class[k][c] = cheapest(per_k_class[k][c])

    cheapest_interaction = {}
    for k in KS:
        cheapest_interaction[k] = cheapest(interaction_hits[k])

    # ------------------------------------------------------- gadgets.md -
    lines = ["# Gadget search (static frame), k=2,3, P=4..14, m=12\n"]
    lines.append(
        "Middle block = block index 6 of 0..11 (0-indexed), i.e. columns "
        "[6P,7P) of the M=12P row. Single-site injections at each of the P "
        "offsets of that block; 20P rows evolved; classified against the "
        "unperturbed (fixed) background. Diagrams below show the "
        "difference pattern (disturbed XOR background): `#` = differs from "
        "background, `.` = matches background.\n"
    )
    lines.append(f"\nTotal stationary programs found: {len(processed)} "
                  f"(k=2: {sum(1 for r in processed if r['k']==2)}, "
                  f"k=3: {sum(1 for r in processed if r['k']==3)})\n")

    for k in KS:
        lines.append(f"\n## k={k}\n")
        lines.append("| class | programs (>=1 occurrence) | position-instances | "
                      "cheapest program (P, popcount) | detail |\n")
        lines.append("|---|---|---|---|---|\n")
        for c in CLASSES:
            n_prog = len(per_k_class_progset[k][c])
            n_inst = len(per_k_class[k][c])
            ch = cheapest_per_k_class[k][c]
            if ch is None:
                lines.append(f"| {c} | 0 | 0 | - | (none found) |\n")
            else:
                P, pc, pattern, prog_str, offset, detail, rec = ch
                lines.append(
                    f"| {c} | {n_prog} | {n_inst} | P={P}, ones={pc}, p=`{prog_str}` "
                    f"(pattern={pattern}) | offset={offset}: {detail} |\n"
                )
        n_int_prog = len(set(pattern for (_, _, pattern, _, _) in interaction_hits[k]))
        lines.append(f"\ninteracting-pair programs (offsets 0,1 of middle block): "
                     f"{n_int_prog} distinct programs out of {sum(1 for r in processed if r['k']==k)} "
                     f"stationary programs tested.\n")
        ci = cheapest_interaction[k]
        if ci is not None:
            P, pc, pattern, prog_str, rec = ci
            it = rec["interaction"]
            lines.append(f"cheapest interacting program: P={P}, ones={pc}, p=`{prog_str}` "
                         f"(pattern={pattern}), first differing row vs XOR(single,single) = "
                         f"{it['first_row_diff']}\n")
        else:
            lines.append("cheapest interacting program: (none found)\n")

    # -------------------------------------------------- diagrams --------
    lines.append("\n## Spacetime diagrams (cheapest example of each class)\n")
    for k in KS:
        lines.append(f"\n### k={k}\n")
        for c in CLASSES:
            ch = cheapest_per_k_class[k][c]
            if ch is None:
                continue
            P, pc, pattern, prog_str, offset, detail, rec = ch
            M = M_BLOCKS * P
            bits = rec["bits"]
            prog_full = bits * M_BLOCKS
            bg = rec["background"]
            mb0 = MIDDLE_BLOCK * P
            n_rows = 20 * P
            rows = run_rows_full(bg, prog_full, k, M, [mb0 + offset], n_rows)
            lines.append(f"\n#### k={k} class={c} P={P} ones={pc} p=`{prog_str}` "
                         f"offset={offset} ({detail})\n")
            lines.append(f"Background (row-invariant, from {rec['source']}-seed, "
                         f"settled in {rec['conv_rows']} rows):\n")
            lines.append("```\n" + "".join("#" if b else "." for b in bg) + "\n```\n")
            if c == "dies":
                death_r = None
                for r in range(len(rows)):
                    if all(rows[r][x] == bg[x] for x in range(M)):
                        death_r = r
                        break
                show_rows = list(range(0, min(len(rows), (death_r or 0) + 4)))
                lines.append(f"Difference pattern (disturbed XOR background), all rows up "
                             f"to the death row (+3 to confirm it stays dead):\n")
            else:
                stride = max(1, (len(rows)) // 120)
                show_rows = list(range(0, len(rows), stride))
                lines.append("Difference pattern (disturbed XOR background), one row per "
                             f"line, stride chosen so <=120 lines are shown:\n")
            diagram = []
            for r in show_rows:
                d = [rows[r][x] ^ bg[x] for x in range(M)]
                diagram.append(f"r={r:4d}: " + "".join("#" if b else "." for b in d))
            lines.append("```\n" + "\n".join(diagram) + "\n```\n")

        # interaction diagram
        ci = cheapest_interaction[k]
        if ci is not None:
            P, pc, pattern, prog_str, rec = ci
            M = M_BLOCKS * P
            bits = rec["bits"]
            prog_full = bits * M_BLOCKS
            bg = rec["background"]
            mb0 = MIDDLE_BLOCK * P
            n_rows = 20 * P
            rows_a = run_rows_full(bg, prog_full, k, M, [mb0 + 0], n_rows)
            rows_b = run_rows_full(bg, prog_full, k, M, [mb0 + 1], n_rows)
            rows_ab = run_rows_full(bg, prog_full, k, M, [mb0 + 0, mb0 + 1], n_rows)
            lines.append(f"\n#### k={k} interaction example P={P} ones={pc} p=`{prog_str}`\n")
            lines.append("Rows: A = single flip at offset 0, B = single flip at offset 1, "
                         "AB = both flipped together, XOR = XOR(diff_A,diff_B) (the linear "
                         "prediction); AB != XOR wherever the two sites interact.\n")
            stride = max(1, (len(rows_ab)) // 60)
            diagram = []
            for r in range(0, len(rows_ab), stride):
                da = "".join("#" if (rows_a[r][x] ^ bg[x]) else "." for x in range(M))
                db = "".join("#" if (rows_b[r][x] ^ bg[x]) else "." for x in range(M))
                dab = "".join("#" if (rows_ab[r][x] ^ bg[x]) else "." for x in range(M))
                dxor = "".join("#" if ((rows_a[r][x] ^ bg[x]) ^ (rows_b[r][x] ^ bg[x])) else "." for x in range(M))
                diagram.append(f"r={r:4d} A : {da}")
                diagram.append(f"r={r:4d} B : {db}")
                diagram.append(f"r={r:4d} AB: {dab}")
                diagram.append(f"r={r:4d} XOR: {dxor}")
                diagram.append("")
            lines.append("```\n" + "\n".join(diagram) + "\n```\n")

    with open(MD_OUT, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {MD_OUT}")
    print(f"total time {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
