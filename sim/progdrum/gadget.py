"""Gadget search machinery for HANDOVER-C sec 3, task 2 (static frame).

Row update (same rule as machine.py, inlined/tiled for speed): row length
M = m*P (m=12 fixed for task 2), program tiled to prog_full = p*m so no
modulo is needed in the inner loop.
"""
from __future__ import annotations

M_BLOCKS = 12  # m


def step_row(prev, prog_full, k, M):
    """One static-frame row step. prog_full has length M (p tiled m times)."""
    cur = [0] * M
    km1 = k - 1
    Nm1 = M - 1
    for x in range(M):
        if prog_full[x]:
            xk = x - k
            a = cur[xk] if xk >= 0 else prev[xk + M]
            xk1 = x - km1
            b = cur[xk1] if xk1 >= 0 else prev[xk1 + M]
            cur[x] = 1 - (a & b)
        else:
            idx = x - Nm1
            if idx >= 0:
                cur[x] = cur[idx]
            else:
                cur[x] = prev[idx + M]
    return cur


def run_to_fixed(prog_full, k, M, start_row, max_rows):
    """Run up to max_rows rows from start_row; return (fixed_row, rows_taken)
    if it settles to cur==prev, else (None, max_rows)."""
    prev = start_row
    for r in range(max_rows):
        cur = step_row(prev, prog_full, k, M)
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


def classify_disturbance(background, prog_full, k, M, P, flip_pos, n_rows):
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
            row = step_row(prev_row, prog_full, k, M)
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
        }

    # never died: classify motion / growth / memory
    n_pts = len(centers)
    head_end = max(1, n_pts // 4)
    tail_start = max(head_end, n_pts - max(1, n_pts // 4))
    width_head = sum(widths[:head_end]) / head_end
    width_tail = sum(widths[tail_start:]) / (n_pts - tail_start)

    late_lo = max(0, n_pts - max(2, n_pts // 2))
    disp = centers[-1] - centers[late_lo]
    span = (n_pts - 1) - late_lo
    velocity = disp / span if span > 0 else 0.0

    GROW_THRESH = max(4 * P, 3 * width_head + 1)
    if width_tail > GROW_THRESH and width_tail > 1.4 * max(width_head, 1):
        return {
            "cls": "grows",
            "detail": f"width_head={width_head:.1f} width_tail={width_tail:.1f}",
            "rows_run": rows_run,
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
        }

    if velocity <= -0.02:
        return {
            "cls": "moves_left",
            "detail": f"speed={abs(velocity) / P:.4f} blocks/row (={velocity:.4f} sites/row)",
            "rows_run": rows_run,
        }
    if velocity >= 0.02:
        return {
            "cls": "moves_right",
            "detail": f"speed={velocity / P:.4f} blocks/row (={velocity:.4f} sites/row)",
            "rows_run": rows_run,
        }

    return {
        "cls": "grows",
        "detail": f"fallback: width_head={width_head:.1f} width_tail={width_tail:.1f} v={velocity:.4f}",
        "rows_run": rows_run,
    }


def run_rows_full(background, prog_full, k, M, flip_positions, n_rows):
    """Evolve a disturbance with an arbitrary set of flipped positions (0, 1,
    or 2 positions) for n_rows rows; return the list of full rows (row0..
    row n_rows), each a list of length M. Used for interaction tests and for
    regenerating spacetime diagrams of the chosen cheapest examples."""
    start = list(background)
    for fp in flip_positions:
        start[fp] ^= 1
    rows = [start]
    prev = start
    for _ in range(n_rows):
        cur = step_row(prev, prog_full, k, M)
        rows.append(cur)
        prev = cur
    return rows
