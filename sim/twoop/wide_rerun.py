"""
Orchestrator-requested addition: rerun with the window widened to the
current group +/- 2 groups (half_width=2) instead of +/- 1, pruning only
when a branch leaves that wider window.

Scope:
  (a) ALL of step 1 (160 configurations), at L=10.
  (b) Every (pair, encoding, rest) row from the main step-2 sweep that had
      at least two of {FLIP, NEXT, SKIPZ} found at length 10 (i.e. every
      row the main sweep already extended to L=12), rerun at L=12.

Reports new hits compared to the +/-1 window, and whether any row becomes
a full winner (FLIP + NEXT + SKIPZ all found) under the wider window.
"""
import csv
import time

from machine import Bundle, Op, FLIP, MOVE, SKIP, ALWAYS
from enc import ENCODINGS, ENCODING_REST_LIST
from pairs import BUNDLES, canonical_pairs
from search import search_pair

PRIMS = ("FLIP", "NEXT", "SKIPZ", "PREV")


# ---------------------------------------------------------------------------
# (a) Step 1 rerun, half_width=2, L=10
# ---------------------------------------------------------------------------

BASE_PAIRS = [
    ("A=(flip,+1), B=(-1)",
     (Op(FLIP), Op(MOVE, dir=+1, cond=ALWAYS)),
     (Op(MOVE, dir=-1, cond=ALWAYS),)),
    ("A=(+1,flip), B=(-1)",
     (Op(MOVE, dir=+1, cond=ALWAYS), Op(FLIP)),
     (Op(MOVE, dir=-1, cond=ALWAYS),)),
]
SCRATCH_ENCODINGS = ["(x,1)", "(1,x)", "(x,0)", "(0,x)"]
STEP1_L = 10


def rerun_step1():
    rows = []
    for pair_name, a_ops, b_ops in BASE_PAIRS:
        for target in ("A", "B"):
            base_ops = a_ops if target == "A" else b_ops
            for insert_pos in range(len(base_ops) + 1):
                for v in (0, 1):
                    new_ops = base_ops[:insert_pos] + (Op(SKIP, v=v),) + base_ops[insert_pos:]
                    if target == "A":
                        bundleA = Bundle(new_ops)
                        bundleB = Bundle(b_ops)
                    else:
                        bundleA = Bundle(a_ops)
                        bundleB = Bundle(new_ops)
                    for enc_name in SCRATCH_ENCODINGS:
                        g, template = ENCODINGS[enc_name]
                        for rest in range(g):
                            found_narrow, _ = search_pair(
                                bundleA, bundleB, g, template, rest, STEP1_L,
                                want=PRIMS, half_width=1)
                            found_wide, _ = search_pair(
                                bundleA, bundleB, g, template, rest, STEP1_L,
                                want=PRIMS, half_width=2)
                            rows.append({
                                "desc": f"{pair_name} + skip(v={v}) into {target}@{insert_pos}",
                                "bundleA": repr(bundleA), "bundleB": repr(bundleB),
                                "encoding": enc_name, "rest": rest,
                                "narrow": found_narrow, "wide": found_wide,
                            })
    return rows


# ---------------------------------------------------------------------------
# (b) Step 2 promising-row rerun, half_width=2
# ---------------------------------------------------------------------------

def rerun_step2_promising(csv_path):
    cp = canonical_pairs()
    enc_lookup = {(name, rest): (g, template)
                  for (name, g, template, rest) in ENCODING_REST_LIST}

    promising = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["search_L"]) == 12:
                promising.append(row)

    def parse_cell(s):
        if s.startswith("none<="):
            return None
        word, rest_s = s.split("(")
        length = int(rest_s.rstrip(")"))
        return (word, length)

    out_rows = []
    for row in promising:
        pidx = int(row["pair_idx"])
        ai, bi = cp[pidx]
        bundleA, bundleB = BUNDLES[ai], BUNDLES[bi]
        name = row["encoding"]
        rest = int(row["rest"])
        g, template = enc_lookup[(name, rest)]
        found_wide, _ = search_pair(bundleA, bundleB, g, template, rest, 12,
                                     want=PRIMS, half_width=2)
        out_rows.append({
            "pair_idx": pidx, "bundleA": repr(bundleA), "bundleB": repr(bundleB),
            "encoding": name, "rest": rest,
            "narrow": {p: parse_cell(row[p]) for p in PRIMS},
            "wide": found_wide,
        })
    return promising, out_rows


def fmt_entry(v):
    if v is None:
        return "none"
    if isinstance(v, tuple):
        return f"{v[0]}({v[1]})"
    return str(v)


def main():
    t0 = time.time()
    print("Rerunning step 1 with half_width=2 ...", flush=True)
    step1_rows = rerun_step1()
    print(f"  step1 rerun done in {time.time()-t0:.1f}s", flush=True)

    csv_path = "/home/user/toffoli-ring/results/twoop/skip_full.csv"
    print("Rerunning step2 promising rows with half_width=2 ...", flush=True)
    t1 = time.time()
    promising, step2_rows = rerun_step2_promising(csv_path)
    print(f"  step2 rerun done in {time.time()-t1:.1f}s ({len(promising)} promising rows)",
          flush=True)

    # Analyze step1 new hits
    step1_new_hits = []
    for r in step1_rows:
        for p in PRIMS:
            had_narrow = r["narrow"][p] is not None
            had_wide = r["wide"][p] is not None
            if had_wide and not had_narrow:
                step1_new_hits.append((r["desc"], r["encoding"], r["rest"], p, r["wide"][p]))

    step1_new_winners = []
    for r in step1_rows:
        wide_all3 = all(r["wide"][p] is not None for p in ("FLIP", "NEXT", "SKIPZ"))
        narrow_all3 = all(r["narrow"][p] is not None for p in ("FLIP", "NEXT", "SKIPZ"))
        if wide_all3 and not narrow_all3:
            step1_new_winners.append(r)

    # Analyze step2 new hits
    step2_new_hits = []
    for r in step2_rows:
        for p in PRIMS:
            had_narrow = r["narrow"][p] is not None
            had_wide = r["wide"][p] is not None
            if had_wide and not had_narrow:
                step2_new_hits.append((r["pair_idx"], r["bundleA"], r["bundleB"],
                                        r["encoding"], r["rest"], p, r["wide"][p]))

    step2_new_winners = []
    for r in step2_rows:
        wide_all3 = all(r["wide"][p] is not None for p in ("FLIP", "NEXT", "SKIPZ"))
        narrow_all3 = all(r["narrow"][p] is not None for p in ("FLIP", "NEXT", "SKIPZ"))
        if wide_all3 and not narrow_all3:
            step2_new_winners.append(r)

    with open("/home/user/toffoli-ring/results/twoop/wide_rerun_report.txt", "w") as f:
        f.write(f"Step 1 rerun (half_width=2, L={STEP1_L}): {len(step1_rows)} configurations\n")
        f.write(f"Step 1 new hits (found wide, not found narrow): {len(step1_new_hits)}\n")
        for h in step1_new_hits:
            f.write(f"  {h}\n")
        f.write(f"Step 1 new full winners under wide window: {len(step1_new_winners)}\n")
        for r in step1_new_winners:
            f.write(f"  {r}\n")
        f.write("\n")
        f.write(f"Step 2 promising rows rechecked (had search_L=12, i.e. >=2/3 at L=10): "
                f"{len(promising)}\n")
        f.write(f"Step 2 new hits (found wide, not found narrow): {len(step2_new_hits)}\n")
        for h in step2_new_hits:
            f.write(f"  {h}\n")
        f.write(f"Step 2 new full winners under wide window: {len(step2_new_winners)}\n")
        for r in step2_new_winners:
            f.write(f"  {r}\n")

    print(f"DONE. step1_new_hits={len(step1_new_hits)} step1_new_winners={len(step1_new_winners)} "
          f"step2_promising={len(promising)} step2_new_hits={len(step2_new_hits)} "
          f"step2_new_winners={len(step2_new_winners)}", flush=True)
    print(f"total elapsed {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
