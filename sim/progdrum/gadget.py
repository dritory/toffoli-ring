"""Gadget search machinery for HANDOVER-C sec 3, tasks 2 and 2b/2c (static
frame).

Row update (same rule as machine.py, inlined/tiled for speed): row length
M = m*P (m=12 fixed), program tiled to prog_full = p*m so no modulo is
needed in the inner loop. `s` generalises the copy-site offset N = M-s
(task 1 / task 2 use s=1; task 2b sweeps s=1..P-1). See machine.py's
static_frame_rows docstring for the derivation; this is the same rule,
just inlined for speed.
"""
from __future__ import annotations

M_BLOCKS = 12  # m


def step_row(prev, prog_full, k, M, s=1):
    """One static-frame row step. prog_full has length M (p tiled m times).
    s generalises the copy-site offset (N = M-s); s=1 is tasks 1/2."""
    cur = [0] * M
    km1 = k - 1
    Ncopy = M - s
    for x in range(M):
        if prog_full[x]:
            xk = x - k
            a = cur[xk] if xk >= 0 else prev[xk + M]
            xk1 = x - km1
            b = cur[xk1] if xk1 >= 0 else prev[xk1 + M]
            cur[x] = 1 - (a & b)
        else:
            idx = x - Ncopy
            if idx >= 0:
                cur[x] = cur[idx]
            else:
                cur[x] = prev[idx + M]
    return cur


def run_to_fixed(prog_full, k, M, start_row, max_rows, s=1):
    """Run up to max_rows rows from start_row; return (fixed_row, rows_taken)
    if it settles to cur==prev, else (None, max_rows)."""
    prev = start_row
    for r in range(max_rows):
        cur = step_row(prev, prog_full, k, M, s)
        if cur == prev:
            return cur, r + 1
        prev = cur
    return None, max_rows


def popcount_pattern(pattern, P):
    return bin(pattern).count("1")


def pattern_to_bits(pattern, P):
    return [(pattern >> i) & 1 for i in range(P)]


def bits_to_str(bits):
    return "".join(str(b) for b in bits)


def circular_extent(support, M):
    """support: sorted list of distinct indices in [0,M) with the bit set.
    Returns (width, center, count) for the tightest enclosing circular arc,
    or (0, None, 0) if support is empty."""
    n = len(support)
    if n == 0:
        return 0, None, 0
    if n == M:
        return M, (M - 1) / 2.0, n
    gaps = []
    for i in range(n):
        a = support[i]
        b = support[i + 1] if i + 1 < n else support[0] + M
        gaps.append(b - a)
    max_gap_idx = max(range(n), key=lambda i: gaps[i])
    start_idx = (max_gap_idx + 1) % n
    start = support[start_idx]
    end = support[start_idx - 1] if start_idx > 0 else support[-1]
    if end < start:
        end += M
    width = end - start + 1
    center = (start + end) / 2.0
    return width, center, n


def classify_disturbance(background, prog_full, k, M, P, flip_pos, n_rows, s=1):
    """Evolve a single-bit disturbance at flip_pos for n_rows rows against
    the fixed background; classify the difference pattern.

    Returns a dict with keys: cls, detail (free text), rows_run.
    """
    start = list(background)
    start[flip_pos] ^= 1

    widths = []
    centers = []  # unwrapped centers
    counts = []
    tail = []  # full history of diff rows (as tuples), for period detection

    prev_row = start
    died_at = None
    raw_center_prev = None
    unwrapped = 0.0

    def diff_of(row):
        return [row[x] ^ background[x] for x in range(M)]

    for r in range(n_rows + 1):
        if r == 0:
            row = start
        else:
            row = step_row(prev_row, prog_full, k, M, s)
            prev_row = row
        d = diff_of(row)
        support = [x for x in range(M) if d[x]]
        width, center, count = circular_extent(support, M)
        counts.append(count)
        widths.append(width)
        if count == 0:
            died_at = r
            centers.append(unwrapped)
            tail.append(tuple(d))
            break
        if raw_center_prev is None:
            unwrapped = center
        else:
            delta = center - raw_center_prev
            if delta > M / 2:
                delta -= M
            elif delta < -M / 2:
                delta += M
            unwrapped += delta
        raw_center_prev = center
        centers.append(unwrapped)
        tail.append(tuple(d))

    rows_run = len(counts) - 1  # number of steps actually taken (r=0..rows_run)

    if died_at is not None:
        return {
            "cls": "dies",
            "detail": f"transient={died_at} rows",
            "rows_run": rows_run,
            "velocity": 0.0,
        }

    # never died: classify motion / growth / memory
    n_pts = len(centers)
    head_end = max(1, n_pts // 4)
    tail_start = max(head_end, n_pts - max(1, n_pts // 4))
    width_head = sum(widths[:head_end]) / head_end
    width_tail = sum(widths[tail_start:]) / (n_pts - tail_start)

    # Robust velocity: mean of per-row deltas over the tail half of the run,
    # plus a same-sign-fraction consistency check. A genuine translating
    # structure has a fairly constant per-row shift; a chaotic/oscillating
    # blob (common once its width approaches M/2-M/3) instead makes the
    # circular-arc center jump back and forth by large amounts, which a
    # naive two-point (endpoint) velocity estimate can badly misread as a
    # large, spurious "speed". Requiring per-row consistency catches this.
    deltas = [centers[i] - centers[i - 1] for i in range(1, n_pts)]
    late_lo = max(0, len(deltas) - max(2, len(deltas) // 2))
    late_deltas = deltas[late_lo:]
    velocity = sum(late_deltas) / len(late_deltas) if late_deltas else 0.0
    if late_deltas:
        same_sign = sum(1 for d in late_deltas
                         if (d > 0) == (velocity > 0) or abs(d) < 1e-9)
        consistency = same_sign / len(late_deltas)
    else:
        consistency = 1.0
    coherent_motion = consistency >= 0.7

    GROW_THRESH = max(4 * P, 3 * width_head + 1)
    GROW_ABS = M / 3.0
    if (width_tail > GROW_ABS) or (width_tail > GROW_THRESH and width_tail > 1.4 * max(width_head, 1)):
        return {
            "cls": "grows",
            "detail": f"width_head={width_head:.1f} width_tail={width_tail:.1f}",
            "rows_run": rows_run,
            "velocity": velocity,
        }
    if not coherent_motion:
        return {
            "cls": "grows",
            "detail": (f"fallback (incoherent motion): width_head={width_head:.1f} "
                       f"width_tail={width_tail:.1f} v_mean={velocity:.4f} "
                       f"consistency={consistency:.2f}"),
            "rows_run": rows_run,
            "velocity": velocity,
        }

    if abs(velocity) < 0.02 and width_tail <= 1.5 * P:
        # memory candidate: search for a period in the tail window
        period = None
        L = len(tail)
        for T in range(1, L):
            if tail[-1] == tail[-1 - T]:
                if L - 1 - 2 * T >= 0 and tail[-1 - 2 * T] != tail[-1]:
                    continue
                period = T
                break
        detail = f"period={period}" if period else f"period>{L - 1} (window)"
        return {
            "cls": "memory",
            "detail": detail + f" width_tail={width_tail:.1f}",
            "rows_run": rows_run,
            "velocity": velocity,
        }

    if velocity <= -0.02:
        return {
            "cls": "moves_left",
            "detail": f"speed={abs(velocity) / P:.4f} blocks/row (={velocity:.4f} sites/row)",
            "rows_run": rows_run,
            "velocity": velocity,
        }
    if velocity >= 0.02:
        return {
            "cls": "moves_right",
            "detail": f"speed={velocity / P:.4f} blocks/row (={velocity:.4f} sites/row)",
            "rows_run": rows_run,
            "velocity": velocity,
        }

    return {
        "cls": "grows",
        "detail": f"fallback: width_head={width_head:.1f} width_tail={width_tail:.1f} v={velocity:.4f}",
        "rows_run": rows_run,
        "velocity": velocity,
    }


def run_rows_full(background, prog_full, k, M, flip_positions, n_rows, s=1):
    """Evolve a disturbance with an arbitrary set of flipped positions (any
    number of positions) for n_rows rows; return the list of full rows
    (row0..row n_rows), each a list of length M. Used for interaction tests
    and for regenerating spacetime diagrams of the chosen cheapest
    examples."""
    start = list(background)
    for fp in flip_positions:
        start[fp] ^= 1
    rows = [start]
    prev = start
    for _ in range(n_rows):
        cur = step_row(prev, prog_full, k, M, s)
        rows.append(cur)
        prev = cur
    return rows


def classify_localized(background, prog_full, k, M, P, flip_positions, n_rows,
                        s=1, window=None, period_cap=None):
    """For task 2c: evolve a multi-bit disturbance (2-4 flipped sites) and
    check whether the difference from background stays inside a bounded,
    non-drifting window for the whole run, and if so find its period.

    Returns a dict: {'localized': bool, 'dies': bool, 'period': int|None,
    'max_width': float, 'drift': float (unwrapped center displacement over
    the run), 'rows_run': int}.
    """
    if window is None:
        window = 2 * P
    if period_cap is None:
        period_cap = 8 * P

    start = list(background)
    for fp in flip_positions:
        start[fp] ^= 1

    prev_row = start
    tail = []
    widths = []
    centers = []
    raw_center_prev = None
    unwrapped = 0.0
    start_center = None
    died_at = None

    overflowed = False
    for r in range(n_rows + 1):
        row = start if r == 0 else step_row(prev_row, prog_full, k, M, s)
        if r > 0:
            prev_row = row
        d = [row[x] ^ background[x] for x in range(M)]
        support = [x for x in range(M) if d[x]]
        width, center, count = circular_extent(support, M)
        widths.append(width)
        if count == 0:
            died_at = r
            tail.append(tuple(d))
            break
        if raw_center_prev is None:
            unwrapped = center
            start_center = center
        else:
            delta = center - raw_center_prev
            if delta > M / 2:
                delta -= M
            elif delta < -M / 2:
                delta += M
            unwrapped += delta
        raw_center_prev = center
        centers.append(unwrapped)
        tail.append(tuple(d))
        # early exit: once it has spread past the window or drifted away
        # from where it started, it cannot become "localized" by the
        # definition below -- no need to burn the remaining rows (this is
        # what makes an exhaustive 2-4 bit injection sweep over a 2P
        # window affordable). Drift is measured from the START position,
        # not from zero.
        if width > window or abs(unwrapped - start_center) > 2 * window:
            overflowed = True
            break

    rows_run = len(tail) - 1
    if died_at is not None:
        return {"localized": False, "dies": True, "period": None,
                "max_width": max(widths) if widths else 0, "drift": 0.0,
                "rows_run": rows_run}
    if overflowed:
        return {"localized": False, "dies": False, "period": None,
                "max_width": max(widths), "drift": centers[-1] if centers else 0.0,
                "rows_run": rows_run}

    max_width = max(widths)
    drift = centers[-1] - centers[0] if centers else 0.0
    # "does not drift": total displacement over the run stays small
    # relative to the window (a couple of sites of slack for measurement
    # noise around the exact flip positions).
    localized = (max_width <= window) and (abs(drift) <= 2)

    period = None
    if localized:
        L = len(tail)
        for T in range(1, min(period_cap, L - 1) + 1):
            if tail[-1] == tail[-1 - T]:
                if L - 1 - 2 * T >= 0 and tail[-1 - 2 * T] != tail[-1]:
                    continue
                period = T
                break
        if period is None:
            localized = False  # never settled into a repeating pattern

    return {"localized": localized, "dies": False, "period": period,
            "max_width": max_width, "drift": drift, "rows_run": rows_run}
