"""
Search for a "long-jump" CNOT: flip T iff A==1, with A,T dual rail as
before but separated by a gap of untouched spare cells in between (so the
copy can jump over other live data, e.g. a per-state test block, without
disturbing it) -- needed to chain-broadcast the symbol bit across the
per-state dispatch blocks without CNOT's own mechanics touching what's in
the gap.
"""
import time
from gadget_search import search, verify


def cnot_target(assign):
    out = {'A': assign['A'], 'T': assign['T'] ^ assign['A']}
    for k in assign:
        if k.startswith('spare'):
            out[k] = assign[k]
    return out


for gap in (1, 2, 3, 4):
    layout = [('dual', 'A', 'T')] + [('free', f'spare{i}') for i in range(gap)] + [('dual', 'T', 'T')]
    t0 = time.time()
    res, nv = search(layout, 0, cnot_target, maxlen := 18, max_visited=800_000)
    dt = time.time() - t0
    if res is not None:
        ok = verify(layout, 0, cnot_target, res)
        print(f"gap={gap}: FOUND len={len(res)} word={''.join(res)} verify={ok} visited={nv} ({dt:.1f}s)")
    else:
        print(f"gap={gap}: none <= {maxlen} (visited={nv}) ({dt:.1f}s)")
