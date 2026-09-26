"""
Independent verification of the orchestrator's GAPCNOT(K): flip T iff A==1
(a "CNOT" whose target is K+1 cells away from the control, with everything
in between untouched -- so other data/blocks can live there), built as the
Toffoli template (sec 3b) with control B replaced by a constant-1 cell.

Layout relative to the pointer at a (offset 0):
  0: a
  1: constant 1
  2..K-1: untouched ("mid" cells -- other blocks may live here)
  K: scratch g0
  K+1: t
  K+2: scratch g1
  K+3: t-bar (t's dual-rail partner)
  K+4, K+5, K+6: constant markers 0, 1, 1

GAPCNOT(K) = CC N^K FNF N^3 DD P^(K+4)  C N^K FNF N^3 DD P^(K+4)
"""
import itertools
import random
from gadget_search import step_raw


def gapcnot_word(K):
    m = {'F': 'F', 'N': 'N', 'P': 'P', 'C': 'CN', 'D': 'CP'}
    s = ("CC" + "N" * K + "FNF" + "N" * 3 + "DD" + "P" * (K + 4)
         + "C" + "N" * K + "FNF" + "N" * 3 + "DD" + "P" * (K + 4))
    return [m[ch] for ch in s]


def window_size(K):
    return K + 7


def build_window(K, a, mids, t, g1val=None):
    n = window_size(K)
    w = [0] * n
    w[0] = a
    w[1] = 1
    for i, v in enumerate(mids):
        w[2 + i] = v
    w[K] = 0  # g0, will be set by caller if desired
    w[K + 1] = t
    w[K + 2] = 0  # g1
    w[K + 3] = 1 - t
    w[K + 4] = 0
    w[K + 5] = 1
    w[K + 6] = 1
    return w


def verify_exhaustive(K, n_mid_random_trials=200, rng=None):
    """Exhaustive over (a, t, g0, g1); mid cells and any remaining freedom
    covered by random trials (mid can be large, so don't enumerate it)."""
    rng = rng or random.Random(0)
    word = gapcnot_word(K)
    n = window_size(K)
    n_mid = K - 2  # number of "untouched" cells (2..K-1)
    total = fails = 0
    for a, t, g0, g1 in itertools.product([0, 1], repeat=4):
        for _ in range(n_mid_random_trials if n_mid > 0 else 1):
            mids = [rng.randint(0, 1) for _ in range(n_mid)]
            w = [0] * n
            w[0] = a
            w[1] = 1
            for i, v in enumerate(mids):
                w[2 + i] = v
            w[K] = g0
            w[K + 1] = t
            w[K + 2] = g1
            w[K + 3] = 1 - t
            w[K + 4] = 0
            w[K + 5] = 1
            w[K + 6] = 1
            total += 1
            cur = list(w)
            p = 0
            ok = True
            for letter in word:
                r = step_raw(letter, cur, p, n)
                if r is None:
                    ok = False
                    break
                p = r
            want_t = t ^ a
            want = list(w)
            want[K + 1] = want_t
            want[K + 3] = 1 - want_t
            if not ok or cur != want or p != 0:
                fails += 1
                if fails <= 3:
                    print(f"  FAIL K={K} a={a} t={t} g0={g0} g1={g1} mids={mids}: "
                          f"got={cur if ok else 'OOB'} ptr={p if ok else '-'} want={want}")
            if n_mid == 0:
                break
    return total, fails


if __name__ == "__main__":
    rng = random.Random(42)
    for K in range(2, 13):
        total, fails = verify_exhaustive(K, n_mid_random_trials=50, rng=rng)
        word = gapcnot_word(K)
        print(f"K={K:2d}: {total-fails}/{total} passed  (len={len(word)}, window={window_size(K)})")
