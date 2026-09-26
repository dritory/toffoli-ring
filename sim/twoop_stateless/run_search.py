"""
Exhaustive search driver for HANDOVER-B.md section 6 (stateless pairs).

Writes:
  results/twoop/stateless_full.csv
  results/twoop/stateless_summary.md
"""

import csv
import os
import time

from model import (gen_pairs, gen_encodings, bundle_str, pattern_str,
                    search_combo, TARGETS)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'results', 'twoop'))
os.makedirs(RESULTS_DIR, exist_ok=True)

MAX_LEN = 12


def main():
    pairs = gen_pairs()
    encs = gen_encodings()

    rows = []
    t0 = time.time()
    ncombos = 0
    for pair_idx, (A, B) in enumerate(pairs):
        a_str = bundle_str(A)
        b_str = bundle_str(B)
        pair_label = f"A=({a_str}) B=({b_str})"
        for (fam, g, patt) in encs:
            enc_str = pattern_str(patt)
            for rest in range(g):
                found = search_combo((A, B), patt, g, rest, max_len=MAX_LEN, early_stop=True)
                ncombos += 1
                for t in TARGETS:
                    macro = found[t] if found[t] is not None else f'none<={MAX_LEN}'
                    rows.append({
                        'pair_idx': pair_idx,
                        'A': a_str,
                        'B': b_str,
                        'pair_label': pair_label,
                        'family': fam,
                        'encoding': enc_str,
                        'g': g,
                        'rest': rest,
                        'target': t,
                        'macro': macro,
                        'length': len(found[t]) if found[t] is not None else '',
                    })
    t1 = time.time()

    csv_path = os.path.join(RESULTS_DIR, 'stateless_full.csv')
    fieldnames = ['pair_idx', 'A', 'B', 'pair_label', 'family', 'encoding',
                  'g', 'rest', 'target', 'macro', 'length']
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} rows ({ncombos} combos x {len(TARGETS)} targets) to {csv_path}")
    print(f"Search wall time: {t1 - t0:.2f} sec")

    return rows, pairs, encs, ncombos, (t1 - t0)


if __name__ == '__main__':
    main()
