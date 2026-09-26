"""
Guarded-macro criterion full menu search (orchestrator's task 2): every
canonical pair (same 1017 pairs, mod mirror+complement, as the strict-
criterion sweep) x every encoding/rest (49), words to length 10, extended
to 12 for rows with >= 3 of the 6 guarded targets found at length 10.

A row is a "winner" if it has FLIP, NEXT and CFLIP. CNEXT/PREV/CPREV are
reported too, for winners and non-winners alike.

Parallelized across worker processes (one pair per task) since the g=1
("none") encoding's window is large (up to N=2^15 valuations at L=12) and
the pure-Python/numpy inner loop, while vectorized over valuations, is
still costly per BFS node.
"""
import csv
import multiprocessing as mp
import time

from enc import ENCODING_REST_LIST
from pairs import BUNDLES, canonical_pairs, bundle_desc
from guarded_search import search_pair_guarded, GUARDED_TARGETS

L1 = 10
L2 = 12
OUT_CSV = "/home/user/toffoli-ring/results/twoop/guarded_full.csv"
NPROC = 4


def fmt(entry, L):
    if entry is None:
        return f"none<={L}"
    word, length = entry
    return f"{word}({length})"


def process_pair(pidx):
    cp = canonical_pairs()
    ai, bi = cp[pidx]
    bundleA, bundleB = BUNDLES[ai], BUNDLES[bi]
    descA, descB = bundle_desc(ai), bundle_desc(bi)
    rows = []
    for name, g, template, rest in ENCODING_REST_LIST:
        found = search_pair_guarded(bundleA, bundleB, g, template, rest, L1)
        used_L = L1
        n_hits = sum(1 for t in GUARDED_TARGETS if found[t] is not None)
        if n_hits >= 3:
            found = search_pair_guarded(bundleA, bundleB, g, template, rest, L2)
            used_L = L2
        row = [pidx, descA, descB, name, g, rest, used_L] + \
              [fmt(found[t], used_L) for t in GUARDED_TARGETS]
        rows.append(row)
    return pidx, rows


def main():
    cp = canonical_pairs()
    n_pairs = len(cp)
    print(f"canonical pairs: {n_pairs}", flush=True)
    print(f"encoding x rest combos: {len(ENCODING_REST_LIST)}", flush=True)

    t0 = time.time()
    n_done = 0
    n_rows = 0
    n_winners = 0

    with open(OUT_CSV, "w", newline="") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(["pair_idx", "bundleA", "bundleB", "encoding", "g", "rest",
                          "search_L"] + list(GUARDED_TARGETS))

        with mp.Pool(processes=NPROC) as pool:
            for pidx, rows in pool.imap_unordered(process_pair, range(n_pairs), chunksize=1):
                for row in rows:
                    writer.writerow(row)
                    n_rows += 1
                    flip, next_, cflip = row[7], row[8], row[10]
                    if not flip.startswith("none") and not next_.startswith("none") and not cflip.startswith("none"):
                        n_winners += 1
                n_done += 1
                if n_done % 25 == 0:
                    elapsed = time.time() - t0
                    print(f"  pairs done {n_done}/{n_pairs}  rows={n_rows}  winners={n_winners}  "
                          f"elapsed={elapsed:.1f}s", flush=True)
                    fcsv.flush()

    elapsed = time.time() - t0
    print(f"DONE. pairs={n_pairs} rows={n_rows} winners={n_winners} elapsed={elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
