"""
Memory-lean version of the gadget BFS: packs the joint state (window+ptr for
every valuation) into a single Python int key, and stores only a (parent_int,
letter_code) pair per visited state, to keep per-state overhead small enough
for 8-valuation (3-free-bit) searches with windows up to ~8 physical bits.
"""
from collections import deque
import itertools

LETTERS = ['F', 'N', 'P', 'CN', 'CP']
LETTER_CODE = {l: i for i, l in enumerate(LETTERS)}


def expand_layout(layout):
    phys = []
    name_slots = {}
    for spec in layout:
        if spec[0] == 'free':
            name_slots.setdefault(spec[1], []).append(len(phys))
            phys.append(('free', spec[1]))
        elif spec[0] == 'const':
            phys.append(('const', spec[1]))
        elif spec[0] == 'dual':
            _, name, orient = spec
            name_slots.setdefault(name, []).append(len(phys))
            if orient == 'T':
                phys.append(('dual_true', name))
                phys.append(('dual_false', name))
            else:
                phys.append(('dual_false', name))
                phys.append(('dual_true', name))
        else:
            raise ValueError(spec)
    return phys, name_slots


def build_valuations(layout):
    phys, name_slots = expand_layout(layout)
    free_names = sorted(name_slots.keys())
    combos = list(itertools.product([0, 1], repeat=len(free_names)))
    out = []
    for combo in combos:
        assign = dict(zip(free_names, combo))
        w = []
        for p in phys:
            if p[0] == 'free':
                w.append(assign[p[1]])
            elif p[0] == 'const':
                w.append(p[1])
            elif p[0] == 'dual_true':
                w.append(assign[p[1]])
            elif p[0] == 'dual_false':
                w.append(1 - assign[p[1]])
        out.append((assign, tuple(w)))
    return phys, free_names, out


def make_goal_window(phys, assign_out):
    w = []
    for p in phys:
        if p[0] == 'free':
            w.append(assign_out[p[1]])
        elif p[0] == 'const':
            w.append(p[1])
        elif p[0] == 'dual_true':
            w.append(assign_out[p[1]])
        elif p[0] == 'dual_false':
            w.append(1 - assign_out[p[1]])
    return tuple(w)


def step_raw(letter, window_list, ptr, n):
    if letter == 'F':
        window_list[ptr] ^= 1
        return ptr
    if letter == 'N':
        ptr += 1
    elif letter == 'P':
        ptr -= 1
    elif letter == 'CN':
        if window_list[ptr] == 1:
            ptr += 1
    elif letter == 'CP':
        if window_list[ptr] == 1:
            ptr -= 1
    if ptr < 0 or ptr >= n:
        return None
    return ptr


def search(layout, start_idx, target_fn, max_len, max_visited=3_000_000, verbose=False):
    phys, free_names, valuations = build_valuations(layout)
    n_phys = len(phys)
    n_val = len(valuations)
    ptr_bits = max(1, (n_phys - 1).bit_length())
    slot_bits = n_phys + ptr_bits  # per-valuation packed size

    def pack(windows, ptrs):
        acc = 0
        for i in range(n_val):
            wbits = 0
            for b in windows[i]:
                wbits = (wbits << 1) | b
            acc = (acc << slot_bits) | (wbits << ptr_bits) | ptrs[i]
        return acc

    def unpack(state):
        windows = [None] * n_val
        ptrs = [None] * n_val
        s = state
        for i in range(n_val - 1, -1, -1):
            chunk = s & ((1 << slot_bits) - 1)
            s >>= slot_bits
            ptrs[i] = chunk & ((1 << ptr_bits) - 1)
            wbits = chunk >> ptr_bits
            w = [0] * n_phys
            for b in range(n_phys - 1, -1, -1):
                w[b] = wbits & 1
                wbits >>= 1
            windows[i] = w
        return windows, ptrs

    start_windows = [list(w) for (_, w) in valuations]
    start_ptrs = [start_idx] * n_val
    start_state = pack(start_windows, start_ptrs)

    goal_windows = [list(make_goal_window(phys, target_fn(assign))) for assign, _ in valuations]

    def is_goal(windows, ptrs):
        p0 = ptrs[0]
        for i in range(n_val):
            if ptrs[i] != p0 or windows[i] != goal_windows[i]:
                return False
        return True

    if is_goal(start_windows, start_ptrs):
        return [], 1

    visited = {start_state: (None, -1)}
    q = deque([(start_state, 0)])
    while q:
        cur_state, d = q.popleft()
        if d >= max_len:
            continue
        cur_windows, cur_ptrs = unpack(cur_state)
        for letter in LETTERS:
            new_windows = [list(w) for w in cur_windows]
            new_ptrs = list(cur_ptrs)
            ok = True
            for i in range(n_val):
                p = step_raw(letter, new_windows[i], cur_ptrs[i], n_phys)
                if p is None:
                    ok = False
                    break
                new_ptrs[i] = p
            if not ok:
                continue
            nxt_state = pack(new_windows, new_ptrs)
            if nxt_state in visited:
                continue
            visited[nxt_state] = (cur_state, LETTER_CODE[letter])
            if is_goal(new_windows, new_ptrs):
                word = []
                s = nxt_state
                while True:
                    prev, lc = visited[s]
                    if prev is None:
                        break
                    word.append(LETTERS[lc])
                    s = prev
                word.reverse()
                return word, len(visited)
            if len(visited) > max_visited:
                return None, len(visited)
            q.append((nxt_state, d + 1))
        if verbose and len(visited) % 100000 < 6:
            print(f"    ...depth={d} visited={len(visited)}", flush=True)
    return None, len(visited)


def verify(layout, start_idx, target_fn, word):
    phys, free_names, valuations = build_valuations(layout)
    all_ok = True
    n_phys = len(phys)
    for assign, w in valuations:
        cur_w = list(w)
        cur_p = start_idx
        ok = True
        for letter in word:
            p = step_raw(letter, cur_w, cur_p, n_phys)
            if p is None:
                ok = False
                break
            cur_p = p
        gw = list(make_goal_window(phys, target_fn(assign)))
        if not ok or cur_w != gw:
            all_ok = False
            print(f"  FAIL assign={assign}: got={cur_w if ok else 'OOB'} ptr={cur_p if ok else '-'} want={gw}")
    return all_ok
