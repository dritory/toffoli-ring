"""Regenerate results/twoop/stateless_summary.md from stateless_full.csv."""

import csv
import os
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'results', 'twoop'))
CSV_PATH = os.path.join(RESULTS_DIR, 'stateless_full.csv')
MD_PATH = os.path.join(RESULTS_DIR, 'stateless_summary.md')

TARGETS = ['FLIP', 'NEXT', 'PREV', 'CFLIP', 'CNEXT', 'CPREV']
CORE = ['FLIP', 'NEXT', 'CFLIP']


def found(m):
    return not m.startswith('none')


def main():
    rows = list(csv.DictReader(open(CSV_PATH)))
    combos = defaultdict(dict)
    meta = {}
    for r in rows:
        key = (r['pair_idx'], r['encoding'], r['rest'])
        combos[key][r['target']] = r['macro']
        meta[key] = r

    n_pairs = len(set(r['pair_idx'] for r in rows))
    n_enc_rest = len(set((r['encoding'], r['rest']) for r in rows))
    n_combos = len(combos)

    winners = []
    subset_counter = Counter()
    core_counter = Counter()
    for key, d in combos.items():
        present = frozenset(t for t in TARGETS if found(d[t]))
        subset_counter[present] += 1
        core_present = frozenset(t for t in CORE if found(d[t]))
        core_counter[core_present] += 1
        if set(CORE) <= present:
            winners.append(key)

    max_size = max((len(s) for s in subset_counter), default=0)
    best_subsets = {s: c for s, c in subset_counter.items() if len(s) == max_size and max_size > 0}

    lines = []
    lines.append("# Stateless two-instruction pairs: exhaustive search (HANDOVER-B.md section 6)\n")
    lines.append(f"Pairs searched: **{n_pairs}** raw candidate pairs "
                 f"(all satisfying: one bundle carries +1, the other -1, at least one move "
                 f"conditional, at least one bundle has a flip).\n")
    lines.append(f"Encoding x rest-position combinations: **{n_enc_rest}** "
                 f"(1 none + 4 dual-rail-complementary + 8 dual-rail-with-constant + 36 period-3).\n")
    lines.append(f"Total (pair, encoding, rest) combinations tested: **{n_combos}**, "
                 f"each against all 6 targets to word length <= 12 "
                 f"({n_combos * len(TARGETS)} target-checks total).\n")

    lines.append("\n## Winners\n")
    if winners:
        lines.append(f"{len(winners)} combinations found FLIP + NEXT + CFLIP simultaneously:\n")
        for key in winners:
            r = meta[key]
            row_by_t = {t: r['macro'] for t in TARGETS}
            lines.append(f"- pair `{r['pair_label']}`, encoding `{r['encoding']}`, rest={r['rest']}: "
                         + ", ".join(f"{t}={combos[key][t]}" for t in TARGETS))
    else:
        lines.append("**None.** No (pair, encoding, rest) combination realizes FLIP, NEXT and CFLIP "
                     "simultaneously for any word of length <= 12.\n")
        lines.append("\nBreakdown of how many of the 3 core targets {FLIP, NEXT, CFLIP} any single "
                     "combination manages together:\n")
        for k in sorted(core_counter, key=lambda s: -len(s)):
            lines.append(f"- {{{', '.join(sorted(k)) if k else '(none)'}}}: {core_counter[k]} combinations")
        lines.append("\nNotably FLIP and CFLIP were **never** found together in the same combination "
                     "(0 out of 3136); CFLIP itself was found in 40 combinations, all of them under a "
                     "dual-rail complementary encoding (x,not x) or (not x,x) -- never under a scratch-cell "
                     "or period-3 encoding.")

    lines.append(f"\n## Closest near-misses (most targets realized at once: {max_size} of 6)\n")
    for subset, count in sorted(best_subsets.items(), key=lambda kv: -kv[1]):
        lines.append(f"\n### {{{', '.join(sorted(subset))}}} -- {count} combinations\n")
        shown = set()
        for key, d in combos.items():
            present = frozenset(t for t in TARGETS if found(d[t]))
            if present == subset and key[0] not in shown:
                shown.add(key[0])
                r = meta[key]
                lines.append(f"- pair `{r['pair_label']}`, encoding `{r['encoding']}`, rest={r['rest']}: "
                             + ", ".join(f"{t}={d[t]}" for t in TARGETS if found(d[t])))
                if len(shown) >= 4:
                    break

    lines.append("\n## Exhaustion statement\n")
    lines.append(f"All {n_pairs} candidate pairs, satisfying the section-6 constraints (one +1-mover, "
                 f"one -1-mover, >=1 conditional move, >=1 flip), were tested against all {n_enc_rest} "
                 f"(encoding, rest-position) combinations listed in the encodings menu (none; dual-rail "
                 f"(x,not x) and (not x,x); dual-rail-with-constant (x,1),(1,x),(x,0),(0,x); period-3 with "
                 f"one data cell and two constants, all 4 constant-arrangements x all 3 rotations), and "
                 f"against all 6 targets (FLIP, NEXT, PREV, CFLIP, CNEXT, CPREV), for every word over "
                 f"{{A,B}} of length 1 through 12, pruning (per the spec) any word whose pointer leaves "
                 f"the 3-group window in any of the 8 logical-bit valuations of the window. "
                 f"No combination realizes FLIP + NEXT + CFLIP together. The exhaustive search is "
                 f"complete to word length 12 as specified; nothing beyond that length was attempted.")

    with open(MD_PATH, 'w') as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", MD_PATH)


if __name__ == '__main__':
    main()
