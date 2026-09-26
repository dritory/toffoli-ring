"""V2: write-between geometry (a,c,b), a < c <= b: s[i+c] = NOT(s[i+a] & s[i+b]).

Lemma B/C predicts collapse to a periodic orbit of period <= L+1 (L=N-(b-c))
within a short transient, described in a "row frame" as a rigid shift of one
cell per pass. We check, directly on the raw ring array:
  1. transient T and exact period P of the ring-state trajectory (T small, P<=L+1)
  2. whether the periodic part is *also* a per-pass rigid rotation in raw ring
     coordinates (same integer shift r every single pass) -- report r if so,
     and explicitly flag when it is periodic (bound satisfied) but NOT expressible
     as a single per-pass raw rotation (the domain wall / phase pattern still
     returns after P passes, just not via one constant shift each step).
"""
import random
import sys
sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
from nandring import nand_pass, to_str

GEOMS = []
for b in range(1, 5):
    for c in range(1, b + 1):
        GEOMS.append((0, c, b))

NS = list(range(16, 65, 4))
SEEDS_PER = 100


def rotate(s, r):
    n = len(s)
    r %= n
    return s[-r:] + s[:-r] if r else list(s)


def analyze_seed(a, c, b, n, s0, cap):
    rows = [list(s0)]
    seen = {tuple(s0): 0}
    t = 0
    period = transient = None
    while True:
        rows.append(nand_pass(rows[-1], a, b, c))
        t += 1
        key = tuple(rows[-1])
        if key in seen:
            transient = seen[key]
            period = t - transient
            break
        seen[key] = t
        if t > cap:
            return None  # exceeded cap, shouldn't happen given L bound
    # check per-pass rigid rotation across the periodic part
    r_const = None
    clean_rotation = True
    for tt in range(transient, transient + period):
        r = None
        for cand in range(n):
            if rotate(rows[tt], cand) == rows[tt + 1]:
                r = cand
                break
        if r is None:
            clean_rotation = False
            break
        if r_const is None:
            r_const = r
        elif r != r_const:
            clean_rotation = False
            break
    return dict(transient=transient, period=period, clean_rotation=clean_rotation,
                r=r_const if clean_rotation else None, rows_sample=rows[:min(6, len(rows))])


def test_geom(a, c, b, n, trials=SEEDS_PER, rng=None):
    rng = rng or random.Random(999 + a * 7 + c * 13 + b * 17 + n)
    L = n - (b - c)
    cap = 4 * (L + 1) + 20
    transients = []
    periods = []
    clean_shifts = set()
    n_clean = 0
    n_dirty = 0
    dirty_example = None
    period_violations = []
    for _ in range(trials):
        s0 = [rng.randint(0, 1) for _ in range(n)]
        res = analyze_seed(a, c, b, n, s0, cap)
        if res is None:
            period_violations.append(("cap_exceeded", s0))
            continue
        transients.append(res["transient"])
        periods.append(res["period"])
        if res["period"] > L + 1:
            period_violations.append(("period_exceeds_L+1", res["period"], L + 1, s0))
        if res["clean_rotation"]:
            n_clean += 1
            clean_shifts.add(res["r"])
        else:
            n_dirty += 1
            if dirty_example is None:
                dirty_example = res
    return dict(L=L, transients=transients, periods=periods, clean_shifts=clean_shifts,
                n_clean=n_clean, n_dirty=n_dirty, dirty_example=dirty_example,
                period_violations=period_violations)


def main():
    print("=== V2: write-between geometry, collapse to period <= L+1 ===\n")
    header = f"{'geom(a,c,b)':>12} {'N':>4} {'L':>4} {'max T':>6} {'max P':>6} {'L+1':>5} {'#clean-rot(shift)':>22} {'#periodic-not-rot':>18}"
    print(header)
    any_violation = False
    dirty_examples = {}
    for (a, c, b) in GEOMS:
        for n in NS:
            res = test_geom(a, c, b, n)
            L = res["L"]
            max_t = max(res["transients"]) if res["transients"] else -1
            max_p = max(res["periods"]) if res["periods"] else -1
            viol = res["period_violations"]
            if viol:
                any_violation = True
            shift_str = ",".join(str(s) for s in sorted(res["clean_shifts"])) if res["clean_shifts"] else "-"
            clean_col = "%d(%s)" % (res["n_clean"], shift_str)
            viol_tag = "  <-- BOUND VIOLATION" if viol else ""
            print(f"{str((a,c,b)):>12} {n:>4} {L:>4} {max_t:>6} {max_p:>6} {L+1:>5} "
                  f"{clean_col:>22} {res['n_dirty']:>18}{viol_tag}")
            if res["n_dirty"] > 0 and (a, c, b) not in dirty_examples:
                dirty_examples[(a, c, b)] = (n, res["dirty_example"])
    print(f"\nany period-bound violation across all geometries/N: {any_violation}")
    print("\n--- sample 'periodic but not per-pass rotation' cases (first 6 rows shown) ---")
    for geom, (n, ex) in dirty_examples.items():
        print(f"\ngeometry {geom}, N={n}: transient={ex['transient']} period={ex['period']}")
        for t, r in enumerate(ex["rows_sample"]):
            print(f"  t={t}: {to_str(r)}")


if __name__ == "__main__":
    main()
