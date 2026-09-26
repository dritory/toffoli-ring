"""Catalog of isolated words: behaviour of every bit string of length <= L
placed on a long zero ring. Reports period, support growth and flooding.

Left edges of words are pinned (proved in REPORT.md), so a word can only
grow to the right; growth is measured as (rightmost 1) - (leftmost 1).
"""
import sys
from ring import pass_, to_str, from_str


def evolve_word(word, k, passes, pad=None):
    """Place word at position 0 of a zero ring long enough that nothing wraps
    within `passes` passes unless it floods. Returns list of rows (as strings,
    trimmed to a window) plus flags."""
    n = len(word) + (pad if pad else 40 * (passes + 1) + 60)
    s = list(word) + [0] * (n - len(word))
    rows = [s]
    flooded = False
    for _ in range(passes):
        s = pass_(s, k)
        rows.append(s)
        if sum(s) > n // 2:
            flooded = True
            break
    return rows, flooded


def support(s):
    idx = [i for i, b in enumerate(s) if b]
    return (idx[0], idx[-1]) if idx else (None, None)


def classify(word, k, passes=60):
    rows, flooded = evolve_word(word, k, passes)
    if flooded:
        return dict(word=to_str(word), kind="flood", rows=rows)
    # period search
    seen = {}
    for t, r in enumerate(rows):
        key = tuple(r)
        if key in seen:
            return dict(word=to_str(word), kind="periodic", period=t - seen[key],
                        preperiod=seen[key], maxwidth=max(support(x)[1] - support(x)[0] + 1 for x in rows[:t]),
                        rows=rows)
        seen[key] = t
    widths = [support(x)[1] - support(x)[0] + 1 for x in rows]
    return dict(word=to_str(word), kind="growing", widths=widths, rows=rows)


def canonical_words(L):
    for n in range(1, L + 1):
        for v in range(1 << n):
            w = [(v >> i) & 1 for i in range(n)]
            if w[0] == 1 and w[-1] == 1:
                yield w


if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    L = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    from collections import Counter
    kinds = Counter()
    periods = Counter()
    for w in canonical_words(L):
        c = classify(w, k)
        kinds[c["kind"]] += 1
        if c["kind"] == "periodic":
            periods[c["period"]] += 1
        if c["kind"] != "periodic" or c["period"] > 2 or (c["kind"] == "periodic" and c["maxwidth"] > len(w) + k + 2):
            extra = ""
            if c["kind"] == "periodic":
                extra = "period=%d preperiod=%d maxwidth=%d" % (c["period"], c["preperiod"], c["maxwidth"])
            elif c["kind"] == "growing":
                extra = "widths=%s" % c["widths"][:12]
            print("%-10s %-9s %s" % (c["word"], c["kind"], extra))
    print("k=%d L=%d kinds=%s periods=%s" % (k, L, dict(kinds), sorted(periods.items())))
