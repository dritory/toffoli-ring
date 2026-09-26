"""
Enumerate the bundle universe and the qualifying (A,B) pairs for the full
menu search (HANDOVER-B.md sections 3-4), with mirror/complement symmetry
reduction.
"""

from machine import all_bundles, dedupe_bundles, bundle_signature, MOVE, SKIP


def has_dir(b, d):
    return any(o.kind == MOVE and o.dir == d for o in b.ops)


def has_skip(b):
    return any(o.kind == SKIP for o in b.ops)


BUNDLES = dedupe_bundles(all_bundles())
N = len(BUNDLES)

_sig_to_idx = {bundle_signature(b): i for i, b in enumerate(BUNDLES)}

MIRROR_IDX = []
COMPLEMENT_IDX = []
for b in BUNDLES:
    m = b.mirror()
    c = b.complement()
    MIRROR_IDX.append(_sig_to_idx[bundle_signature(m)])
    COMPLEMENT_IDX.append(_sig_to_idx[bundle_signature(c)])

HAS_PLUS = [has_dir(b, 1) for b in BUNDLES]
HAS_MINUS = [has_dir(b, -1) for b in BUNDLES]


def qualifying_pairs():
    """Ordered pairs (i,j), i != j, where {A,B} has both a +1 mover and a
    -1 mover (one of A/B is the +1 mover, the other the -1 mover)."""
    out = []
    for i in range(N):
        for j in range(N):
            if i == j:
                continue
            if (HAS_PLUS[i] and HAS_MINUS[j]) or (HAS_MINUS[i] and HAS_PLUS[j]):
                out.append((i, j))
    return out


def canonical_pairs():
    """Reduce qualifying_pairs() by the mirror/complement symmetry group
    (id, mirror, complement, mirror . complement), keeping one
    representative (the lexicographically smallest (i,j)) per orbit."""
    pairs = qualifying_pairs()
    canon = {}
    for (i, j) in pairs:
        orbit = {(i, j)}
        mi, mj = MIRROR_IDX[i], MIRROR_IDX[j]
        orbit.add((mi, mj))
        ci, cj = COMPLEMENT_IDX[i], COMPLEMENT_IDX[j]
        orbit.add((ci, cj))
        mci, mcj = MIRROR_IDX[ci], MIRROR_IDX[cj]
        orbit.add((mci, mcj))
        rep = min(orbit)
        canon.setdefault(rep, orbit)
    return sorted(canon.keys())


def no_minus_pairs():
    """Ordered pairs (i,j), i != j, drawn from bundles that never contain a
    -1 move (used for the confirmatory 'no -1 subspace' run)."""
    idxs = [i for i in range(N) if not HAS_MINUS[i]]
    out = []
    for i in idxs:
        for j in idxs:
            if i != j:
                out.append((i, j))
    return out


def bundle_desc(i):
    return repr(BUNDLES[i])


if __name__ == "__main__":
    print("bundles:", N)
    print("qualifying pairs:", len(qualifying_pairs()))
    cp = canonical_pairs()
    print("canonical pairs after mirror+complement:", len(cp))
    nm = no_minus_pairs()
    print("no -1 subspace pairs:", len(nm))
