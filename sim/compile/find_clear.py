"""
Search for CLEAR(c): set c to 0 regardless of its incoming value, pointer
returned to c's position, everything else (constant marker/scratch cells in
the window) unchanged -- per the orchestrator's task, BFS over R words with
window = c plus 2-6 constant cells (all placements/values), only c varying.
"""
import itertools
import time
from gadget_search import search, verify


def clear_target(assign):
    return {'c': 0}


def run(max_left=3, max_right=6, maxlen=20, time_budget=260):
    best = None
    configs_tried = 0
    t0 = time.time()
    for n_const in range(2, max_right + 1):
        for n_left in range(0, min(max_left, n_const) + 1):
            n_right = n_const - n_left
            for left_vals in itertools.product([0, 1], repeat=n_left):
                for right_vals in itertools.product([0, 1], repeat=n_right):
                    if time.time() - t0 > time_budget:
                        print(f"time budget hit after {configs_tried} configs")
                        return best
                    layout = ([('const', v) for v in left_vals] + [('free', 'c')]
                              + [('const', v) for v in right_vals])
                    start_idx = n_left
                    configs_tried += 1
                    res, nv = search(layout, start_idx, clear_target, maxlen, max_visited=2_000_000)
                    if configs_tried % 20 == 0:
                        print(f"  ...tried {configs_tried} configs so far "
                              f"(n_left={n_left} left={left_vals} right={right_vals} "
                              f"visited={nv})", flush=True)
                    if res is not None:
                        ok = verify(layout, start_idx, clear_target, res)
                        print(f"FOUND n_left={n_left} left={left_vals} right={right_vals}: "
                              f"len={len(res)} word={''.join(res)} verify={ok} visited={nv}")
                        if best is None or len(res) < len(best[2]):
                            best = (n_left, left_vals, right_vals, res)
        if best is not None:
            break
    print(f"configs tried: {configs_tried}, elapsed {time.time()-t0:.1f}s")
    if best is None:
        print(f"CLEAR: none found for n_const in 2..{max_right} (up to {max_left} left), len<={maxlen}")
    return best


if __name__ == "__main__":
    import sys
    tb = int(sys.argv[1]) if len(sys.argv) > 1 else 260
    run(max_left=3, max_right=6, maxlen=24, time_budget=tb)
