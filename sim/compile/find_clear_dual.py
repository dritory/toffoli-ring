"""
CLEAR(c) search, take 2: c represented in dual rail (c, c-bar), by analogy
with how CNOT needed dual rail on both sides to succeed where single-rail
failed. Window = dual-rail c plus 0-4 constant cells (both sides).
"""
import itertools
import time
from gadget_search import search, verify


def clear_target(assign):
    return {'c': 0}


def run(max_left=2, max_right=4, maxlen=22, time_budget=260, max_visited=2_000_000):
    best = None
    configs_tried = 0
    t0 = time.time()
    for orient in ('T', 'F'):
        for n_const in range(0, max_right + 1):
            for n_left in range(0, min(max_left, n_const) + 1):
                n_right = n_const - n_left
                for left_vals in itertools.product([0, 1], repeat=n_left):
                    for right_vals in itertools.product([0, 1], repeat=n_right):
                        if time.time() - t0 > time_budget:
                            print(f"time budget hit after {configs_tried} configs", flush=True)
                            return best
                        layout = ([('const', v) for v in left_vals] + [('dual', 'c', orient)]
                                  + [('const', v) for v in right_vals])
                        start_idx = n_left
                        configs_tried += 1
                        res, nv = search(layout, start_idx, clear_target, maxlen, max_visited=max_visited)
                        if configs_tried % 10 == 0:
                            print(f"  ...tried {configs_tried} (orient={orient} n_left={n_left} "
                                  f"left={left_vals} right={right_vals} visited={nv})", flush=True)
                        if res is not None:
                            ok = verify(layout, start_idx, clear_target, res)
                            print(f"FOUND orient={orient} n_left={n_left} left={left_vals} "
                                  f"right={right_vals}: len={len(res)} word={''.join(res)} "
                                  f"verify={ok} visited={nv}", flush=True)
                            if best is None or len(res) < len(best[-1]):
                                best = (orient, n_left, left_vals, right_vals, res)
    print(f"configs tried: {configs_tried}, elapsed {time.time()-t0:.1f}s", flush=True)
    if best is None:
        print(f"CLEAR (dual-rail c): none found, n_const 0..{max_right} "
              f"(up to {max_left} left), len<={maxlen}", flush=True)
    return best


if __name__ == "__main__":
    import sys
    tb = int(sys.argv[1]) if len(sys.argv) > 1 else 260
    run(time_budget=tb)
