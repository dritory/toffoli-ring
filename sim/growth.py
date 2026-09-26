"""Long-run classification of isolated words: periodic (2-power), flood, or growing."""
import sys
from ring import pass_, to_str
from words import canonical_words

def classify_long(word, k, passes, n):
    s = list(word) + [0] * (n - len(word))
    seen = {tuple(s): 0}
    widths = []
    for t in range(1, passes + 1):
        s = pass_(s, k)
        idx = [i for i, b in enumerate(s) if b]
        w = idx[-1] - idx[0] + 1
        widths.append(w)
        if idx[-1] > n - 3 * k - 3:
            return ("flood_or_wrap", t, widths)
        key = tuple(s)
        if key in seen:
            return ("periodic", t - seen[key], widths)
        seen[key] = t
    return ("growing?", None, widths)

if __name__ == "__main__":
    k = int(sys.argv[1]); L = int(sys.argv[2]); passes = int(sys.argv[3]); n = int(sys.argv[4])
    from collections import Counter
    c = Counter()
    for w in canonical_words(L):
        kind, per, widths = classify_long(w, k, passes, n)
        c[kind] += 1
        if kind == "growing?" or (kind == "periodic" and per > 64):
            print(to_str(w), kind, per, "maxwidth", max(widths), "width@end", widths[-1])
        if kind == "flood_or_wrap" and per > 3:
            print(to_str(w), "late-flood at pass", per, "widths", widths[:per])
    print("k=%d L<=%d passes=%d:" % (k, L, passes), dict(c))
