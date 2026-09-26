"""
Full menu search (HANDOVER-B.md sections 3-4): every canonical pair (mod
mirror + complement symmetry) with a +1 mover and a -1 mover, against every
encoding x rest position, words up to length 10 (extended to 12 for rows
that already have >= 2 of {FLIP, NEXT, SKIPZ} at length 10).

Writes results/twoop/skip_full.csv incrementally (one row per pair x
encoding x rest) and prints progress to stdout.
"""
import csv
import sys
import time

from enc import ENCODING_REST_LIST
from pairs import BUNDLES, canonical_pairs, bundle_desc
from search import search_pair

L1 = 10
L2 = 12
OUT_CSV = "/home/user/toffoli-ring/results/twoop/skip_full.csv"

PRIMS = ("FLIP", "NEXT", "SKIPZ", "PREV")


def fmt(found_entry, L):
    if found_entry is None:
        return f"none<={L}"
    word, length = found_entry
    return f"{word}({length})"


def main():
    cp = canonical_pairs()
    print(f"canonical pairs: {len(cp)}", flush=True)
    print(f"encoding x rest combos: {len(ENCODING_REST_LIST)}", flush=True)

    t0 = time.time()
    n_rows = 0
    n_winners = 0
    winners = []

    with open(OUT_CSV, "w", newline="") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(["pair_idx", "bundleA", "bundleB", "encoding", "g", "rest",
                          "search_L", "FLIP", "NEXT", "SKIPZ", "PREV"])

        for pidx, (ai, bi) in enumerate(cp):
            bundleA = BUNDLES[ai]
            bundleB = BUNDLES[bi]
            descA = bundle_desc(ai)
            descB = bundle_desc(bi)

            for name, g, template, rest in ENCODING_REST_LIST:
                found, _ = search_pair(bundleA, bundleB, g, template, rest, L1,
                                        want=PRIMS)
                used_L = L1
                n_hits = sum(1 for p in ("FLIP", "NEXT", "SKIPZ") if found[p] is not None)
                if n_hits >= 2:
                    found2, _ = search_pair(bundleA, bundleB, g, template, rest, L2,
                                             want=PRIMS)
                    found = found2
                    used_L = L2

                row = [pidx, descA, descB, name, g, rest, used_L,
                       fmt(found["FLIP"], used_L), fmt(found["NEXT"], used_L),
                       fmt(found["SKIPZ"], used_L), fmt(found["PREV"], used_L)]
                writer.writerow(row)
                n_rows += 1

                if found["FLIP"] is not None and found["NEXT"] is not None and found["SKIPZ"] is not None:
                    n_winners += 1
                    winners.append((pidx, ai, bi, descA, descB, name, g, rest, used_L, dict(found)))

            if pidx % 25 == 0:
                elapsed = time.time() - t0
                print(f"  pair {pidx}/{len(cp)}  rows={n_rows}  winners={n_winners}  "
                      f"elapsed={elapsed:.1f}s", flush=True)
                fcsv.flush()

    elapsed = time.time() - t0
    print(f"DONE. pairs={len(cp)} rows={n_rows} winners={n_winners} elapsed={elapsed:.1f}s", flush=True)

    with open("/home/user/toffoli-ring/results/twoop/full_search_winners.txt", "w") as fw:
        fw.write(f"pairs_searched={len(cp)}\n")
        fw.write(f"rows={n_rows}\n")
        fw.write(f"winners={n_winners}\n")
        for w in winners:
            fw.write(repr(w) + "\n")

    return winners


if __name__ == "__main__":
    main()
