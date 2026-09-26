"""V3: write-behind (c<a) and c=a geometries.
Examples: s[i-1] = NAND(s[i], s[i+1])  (a=0,b=1,c=-1, "write-behind")
          s[i]   = NAND(s[i], s[i+1])  (a=0,b=1,c=0,  "c=a")

Method: the pure all-ones "background" is not a fixed point (NAND(1,1)=0), it
period-2-flips to all-zeros and back; on top of that, the finite ring's own
wraparound injects a persistent local defect near the seam every pass (write-
behind reads are only *locally* synchronous with the previous pass -- exactly
b-c cells next to the seam see an already-updated, same-pass neighbor). We
isolate an injected defect's true signature by subtracting a separately-
simulated defect-free background trajectory from the same initial condition
(same seed for the seam artifact in both runs), then track the surviving
runs of the XOR-difference (`dev`) around the whole ring (no fixed window,
so genuine translation is never mistaken for "leaving the window").
"""
import sys
sys.path.insert(0, "/home/user/toffoli-ring/sim/nand")
from nandring import nand_pass, to_str


def run(s, a, b, c, passes):
    rows = [list(s)]
    for _ in range(passes):
        rows.append(nand_pass(rows[-1], a, b, c))
    return rows


def diff(rowsA, rowsB):
    return [[x ^ y for x, y in zip(ra, rb)] for ra, rb in zip(rowsA, rowsB)]


def all_runs(row):
    """List of (start, width) maximal runs of 1s in a cyclic bit row."""
    n = len(row)
    if all(row):
        return [(0, n)]
    if not any(row):
        return []
    start = next(i for i in range(n) if row[i] == 0)
    row2 = row[start:] + row[:start]
    runs = []
    i = 0
    while i < n:
        if row2[i]:
            j = i
            while j < n and row2[j]:
                j += 1
            runs.append(((start + i) % n, j - i))
            i = j
        else:
            i += 1
    return runs


def demo_background(a, b, c, n=20, passes=6, label=""):
    print(f"\n--- background probe: geometry a={a} b={b} c={c} ({label}), N={n} ---")
    rows = run([1] * n, a, b, c, passes)
    for t, r in enumerate(rows):
        print(f"  t={t}: {to_str(r)}")
    return rows


def defect_track(a, b, c, n, start, width, passes):
    bg = run([1] * n, a, b, c, passes)
    s = [1] * n
    for j in range(start, start + width):
        s[j % n] = 0
    rows = run(s, a, b, c, passes)
    dev = diff(rows, bg)
    return rows, bg, dev, [all_runs(d) for d in dev]


def main():
    GEOMS = [
        (0, 1, -1, "write-behind: s[i-1]=NAND(s[i],s[i+1])"),
        (0, 1, 0, "c=a: s[i]=NAND(s[i],s[i+1])"),
    ]

    for (a, b, c, label) in GEOMS:
        demo_background(a, b, c, n=20, passes=6, label=label)

    print("\n" + "=" * 78)
    print("Isolated single defect, width 1..4, tracked via background-subtracted runs")
    print("(no fixed window -- the whole ring is searched every pass)")
    print("=" * 78)
    for (a, b, c, label) in GEOMS:
        n, passes = 60, 120  # more than one full circuit of the ring
        print(f"\n[{label}]  N={n}, passes={passes}")
        for width in (1, 2, 3, 4):
            _, _, dev, runs_per_t = defect_track(a, b, c, n, 30, width, passes)
            died = any(len(r) == 0 for r in runs_per_t[3:])  # allow tiny startup transient
            widths_seen = sorted({w for r in runs_per_t for (_, w) in r})
            death_t = next((t for t, r in enumerate(runs_per_t) if t > 2 and len(r) == 0), None)
            print(f"  width {width}: ever dies (empty ring)? {died} (t={death_t}); "
                  f"footprint widths ever seen: {widths_seen}; "
                  f"positions t=0..14: {[r[0][0] if r else None for r in runs_per_t[:15]]}")

    print("\n--- short spacetime sample: width-1 (singleton) defect, both geometries ---")
    for (a, b, c, label) in GEOMS:
        n, passes = 40, 24
        rows, bg, dev, runs_per_t = defect_track(a, b, c, n, 20, 1, passes)
        print(f"\n[{label}] raw ring (background flips each pass; defect is the local flaw):")
        for t, r in enumerate(rows):
            print(f"  t={t:3d}: {to_str(r)}")
        print(f"[{label}] deviation from pure background (isolates the defect):")
        for t, d in enumerate(dev):
            print(f"  t={t:3d}: {to_str(d)}   runs={all_runs(d)}")

    print("\n" + "=" * 78)
    print("Non-interaction: two well-separated defects, isolated vs. together")
    print("=" * 78)
    for (a, b, c, label) in GEOMS:
        n = 100
        passes = 16
        bg_rows = run([1] * n, a, b, c, passes)

        def single(start, width):
            s = [1] * n
            for j in range(start, start + width):
                s[j % n] = 0
            return run(s, a, b, c, passes)

        rows_d1 = single(30, 2)
        rows_d2 = single(60, 3)
        s_both = [1] * n
        for j in range(30, 32):
            s_both[j] = 0
        for j in range(60, 63):
            s_both[j] = 0
        rows_both = run(s_both, a, b, c, passes)

        dev1 = diff(rows_d1, bg_rows)
        dev2 = diff(rows_d2, bg_rows)
        dev_both = diff(rows_both, bg_rows)

        match = True
        first_mismatch = None
        for t in range(passes + 1):
            for j in range(15, 90):
                expected = dev1[t][j] | dev2[t][j]
                actual = dev_both[t][j]
                if expected != actual:
                    match = False
                    first_mismatch = (t, j, expected, actual)
                    break
            if not match:
                break
        print(f"  [{label}] together == union(isolated) for t in [0,{passes}], "
              f"j in [15,90): {match}"
              + (f"  first mismatch at {first_mismatch}" if first_mismatch else ""))


if __name__ == "__main__":
    main()
