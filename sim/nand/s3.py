"""S3: defects on robust R3(k) backgrounds found in S2.

For each chosen robust background (one representative per k, the smallest
period found in S2): tile it many times around a large ring, evolve a clean
reference trajectory (no defect) -- this reference already contains one
*forced* topological kink (the ring's finite closure is generally incompatible
with the background's own per-pass shift unless the shift and ring length
happen to be commensurate; see s3_notes below), which travels at a roughly
constant rate. We then inject every possible width<=4 replacement patch at a
fixed position far from that kink, evolve 200 passes, and subtract the clean
reference (XOR) to isolate the injected perturbation's own signature. A
perturbation is a *survivor* (particle candidate) if that signature stays
bounded in width for all 200 passes and does not vanish. Spacetime diagrams
(in the co-moving frame of the background) for every survivor, and for
pairwise collisions of survivors, are written to results/nand/r3_particles.md.
"""
import itertools
import sys
sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
from nandring import r3_pass, to_str

OUT_MD = "/home/user/toffoli-ring/results/nand/r3_particles.md"

# (k, background pattern, period p) -- smallest robust background per k from S2
BACKGROUNDS = {
    2: [0, 1, 1, 1],          # p=4
    3: [0, 1, 1, 1],          # p=4
    4: [0, 0, 1, 1, 1, 1],    # p=6
    5: [0, 0, 1, 1, 1, 1, 1],  # p=7
}


def run(s, k, passes):
    rows = [list(s)]
    for _ in range(passes):
        rows.append(r3_pass(rows[-1], k))
    return rows


def diff(rowsA, rowsB):
    return [[x ^ y for x, y in zip(ra, rb)] for ra, rb in zip(rowsA, rowsB)]


def all_runs(row):
    n = len(row)
    if all(row):
        return [(0, n)]
    if not any(row):
        return []
    start = next(i for i in range(n) if row[i] == 0)
    row2 = row[start:] + row[:start]
    runs = []
    i = 0
    while i < n:
        if row2[i]:
            j = i
            while j < n and row2[j]:
                j += 1
            runs.append(((start + i) % n, j - i))
            i = j
        else:
            i += 1
    return runs


def local_shift(rowA, rowB, center, halfwin=6, search=15):
    """Best integer shift r (|r|<=search) s.t. rowB[center-halfwin:center+halfwin]
    matches rowA[center-halfwin-r : center+halfwin-r] (local, avoids the kink)."""
    n = len(rowA)
    target = [rowB[(center + d) % n] for d in range(-halfwin, halfwin)]
    best_r, best_err = 0, None
    for r in range(-search, search + 1):
        cand = [rowA[(center + d - r) % n] for d in range(-halfwin, halfwin)]
        err = sum(1 for x, y in zip(cand, target) if x != y)
        if best_err is None or err < best_err:
            best_err, best_r = err, r
    return best_r, best_err


def measure_background_velocity(k, pat, copies=60, passes=30):
    p = len(pat)
    n = copies * p
    bg = run(pat * copies, k, passes)
    center = n // 2
    shifts = []
    for t in range(5, passes):
        r, err = local_shift(bg[t], bg[t + 1], center)
        if err == 0:
            shifts.append(r)
    v = max(set(shifts), key=shifts.count) if shifts else 0
    return v, bg


def comoving(rows, v, n):
    out = []
    for t, r in enumerate(rows):
        sh = (v * t) % n
        out.append(r[sh:] + r[:sh])
    return out


def classify_and_track(dev, n, center, bound_total=25):
    """Track the *total* footprint (sum of 1s in dev) and number of separate
    runs over time. A perturbation is localized if the total footprint stays
    bounded (doesn't grow without limit -- it may split into a few separate
    traveling pieces, each itself a particle) and does not vanish entirely."""
    totals = []
    nruns = []
    max_pos_list = []
    for d in dev:
        runs = all_runs(d)
        totals.append(sum(w for (_, w) in runs))
        nruns.append(len(runs))
        max_pos_list.append([pos for (pos, w) in runs])
    max_total = max(totals) if totals else 0
    alive_end = totals[-1] > 0 if totals else False
    bounded = max_total <= bound_total
    return dict(max_total=max_total, bounded=bounded, alive_end=alive_end,
                totals=totals, nruns=nruns, final_nruns=nruns[-1] if nruns else 0)


def main():
    lines = []
    lines.append("# R3(k) particle search (S3)\n")
    lines.append("Backgrounds are the smallest robust (single-attractor) period-p "
                  "patterns found in S2. Perturbations are every width<=4 replacement "
                  "patch (2+4+8+16=30 per background) at a fixed position, evolved 200 "
                  "passes, viewed as deviation-from-clean-background (XOR), which "
                  "removes the ring's own forced boundary kink from the comparison.\n")

    survivors_by_k = {}

    for k, pat in BACKGROUNDS.items():
        p = len(pat)
        copies = 80
        n = copies * p
        passes = 200
        v, bg = measure_background_velocity(k, pat)
        lines.append(f"\n## k={k}, background pattern `{to_str(pat)}` (p={p}), "
                      f"N={n}, measured per-pass shift v={v}\n")
        print(f"k={k} pat={to_str(pat)} p={p} N={n} v={v}")

        center = n // 2
        survivors = []
        for w in range(1, 5):
            for bits in itertools.product((0, 1), repeat=w):
                patch = list(bits)
                s = pat * copies
                for idx, b in enumerate(patch):
                    s[(center + idx) % n] = b
                if s == bg[0]:
                    continue  # not actually a perturbation
                rows = run(s, k, passes)
                dev = diff(rows, bg)
                max_w, alive_end, positions = classify_and_track(dev, n, center)
                localized = (max_w <= 40) and alive_end
                if localized:
                    survivors.append(dict(width=w, patch=tuple(patch), max_w=max_w,
                                           positions=positions, rows=rows, bg=bg,
                                           dev=dev))
        print(f"  survivors: {len(survivors)} / 30 perturbations")
        survivors_by_k[k] = dict(v=v, n=n, p=p, pat=pat, survivors=survivors, bg=bg,
                                  copies=copies, center=center, passes=passes)

        lines.append(f"Survivors (localized, non-dying) out of 30 perturbations: "
                      f"{len(survivors)}\n")
        for surv in survivors:
            w, patch = surv["width"], surv["patch"]
            lines.append(f"\n### k={k} bg=`{to_str(pat)}` patch width={w} "
                          f"pattern=`{to_str(patch)}` (max footprint width over "
                          f"200 passes = {surv['max_w']})\n")
            lines.append("```")
            cm = comoving(surv["rows"], v, n)
            lo, hi = max(0, center - 30), min(n, center + 30)
            for t in range(0, min(60, passes + 1), 2):
                row = cm[t]
                window = row[(lo - v * 0) % n: hi] if hi <= n else row  # simple slice ok since lo,hi in range
                lines.append(f"t={t:3d}: {to_str(row[lo:hi])}")
            lines.append("```")

    # ---- pairwise collisions of survivors (within each k) ----
    lines.append("\n## Pairwise collisions of survivors\n")
    for k, info in survivors_by_k.items():
        survs = info["survivors"]
        pat, p, v = info["pat"], info["p"], info["v"]
        if len(survs) < 1:
            continue
        lines.append(f"\n### k={k}\n")
        # pair each survivor with itself and with a different survivor (if any),
        # placed far apart on a big ring, evolve until (if) they meet.
        copies = 160
        n = copies * p
        passes = 300
        pairs = []
        if len(survs) >= 2:
            pairs.append((survs[0], survs[1]))
        pairs.append((survs[0], survs[0]))  # same-particle collision (both directions)

        for (s1, s2) in pairs:
            bg = run(pat * copies, k, passes)
            posA, posB = n // 3, 2 * n // 3
            s = pat * copies
            for idx, b in enumerate(s1["patch"]):
                s[(posA + idx) % n] = b
            for idx, b in enumerate(s2["patch"]):
                s[(posB + idx) % n] = b
            rows = run(s, k, passes)
            dev = diff(rows, bg)
            n_runs_over_time = [len(all_runs(d)) for d in dev]
            merged_at = next((t for t, c in enumerate(n_runs_over_time) if t > 2 and c == 1), None)
            vanished_at = next((t for t, c in enumerate(n_runs_over_time) if t > 2 and c == 0), None)
            lines.append(f"\nwidths {s1['width']}(`{to_str(s1['patch'])}`) and "
                         f"{s2['width']}(`{to_str(s2['patch'])}`), start separation "
                         f"{(posB - posA) % n}: merged_to_1_run_at={merged_at}, "
                         f"vanished_at={vanished_at}\n")
            lines.append("```")
            lo, hi = max(0, min(posA, posB) - 15), min(n, max(posA, posB) + 15)
            for t in range(0, passes + 1, max(1, passes // 40)):
                lines.append(f"t={t:3d}: {to_str(dev[t][lo:hi])}")
            lines.append("```")

    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines))
    print(f"\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()
