"""
Confirmatory run: the "no -1 subspace" (HANDOVER-B.md lemma "A -1 move is
necessary"). Pairs drawn only from bundles that never contain a -1 move
(i.e. every bundle used is either a non-mover or a +1-only mover). The
lemma predicts no winner (a word achieving FLIP, NEXT and SKIPZ together)
can exist here; this is a single confirmatory pass at length 8.
"""
import time

from enc import ENCODING_REST_LIST
from pairs import BUNDLES, no_minus_pairs, bundle_desc
from search import search_pair

L = 8
PRIMS = ("FLIP", "NEXT", "SKIPZ", "PREV")


def main():
    pairs = no_minus_pairs()
    print(f"no -1 subspace pairs: {len(pairs)}", flush=True)
    t0 = time.time()
    n_checked = 0
    n_winners = 0
    any_flip = 0
    any_next = 0
    any_skipz = 0
    winners = []

    for pidx, (ai, bi) in enumerate(pairs):
        A, B = BUNDLES[ai], BUNDLES[bi]
        for name, g, template, rest in ENCODING_REST_LIST:
            found, _ = search_pair(A, B, g, template, rest, L, want=PRIMS)
            n_checked += 1
            if found["FLIP"] is not None:
                any_flip += 1
            if found["NEXT"] is not None:
                any_next += 1
            if found["SKIPZ"] is not None:
                any_skipz += 1
            if found["FLIP"] and found["NEXT"] and found["SKIPZ"]:
                n_winners += 1
                winners.append((bundle_desc(ai), bundle_desc(bi), name, rest, found))
        if pidx % 200 == 0:
            print(f"  pair {pidx}/{len(pairs)}  elapsed={time.time()-t0:.1f}s", flush=True)

    elapsed = time.time() - t0
    print(f"DONE. pairs={len(pairs)} rows_checked={n_checked} elapsed={elapsed:.1f}s")
    print(f"any FLIP found in {any_flip} rows, any NEXT in {any_next} rows, "
          f"any SKIPZ in {any_skipz} rows")
    print(f"winners (all three): {n_winners}")

    with open("/home/user/toffoli-ring/results/twoop/no_minus_report.txt", "w") as f:
        f.write(f"no -1 subspace confirmatory run, L={L}\n")
        f.write(f"pairs tested: {len(pairs)}\n")
        f.write(f"(pair x encoding x rest) rows checked: {n_checked}\n")
        f.write(f"rows where FLIP was found: {any_flip}\n")
        f.write(f"rows where NEXT was found: {any_next}\n")
        f.write(f"rows where SKIPZ was found: {any_skipz}\n")
        f.write(f"winners (FLIP+NEXT+SKIPZ together): {n_winners}\n")
        for w in winners:
            f.write(repr(w) + "\n")
        if n_winners == 0:
            f.write("\nConfirms the handover's 'A -1 move is necessary' lemma: "
                    "exhaustive at L=8 across all bundles with no -1 move, "
                    "no encoding/rest achieves FLIP+NEXT+SKIPZ together.\n")


if __name__ == "__main__":
    main()
