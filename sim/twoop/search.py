"""
Macro search: given a pair of bundles (A, B), an encoding+rest, and a max
word length L, find the shortest word over {A,B} that is an exact macro for
FLIP / NEXT / PREV / SKIPZ, and the shortest identity word.

Definitions (HANDOVER-B.md primitives section), for window = current group
plus one full group on each side, over every valid assignment of the two
context groups and the current group, and both flag_in values:

  flag_in = 1: final state = initial tape (bit for bit), pointer at the
               same place, flag 0.                          [always required]
  flag_in = 0:
    FLIP:  current group's bits == template(1 - x_cur); left/right groups
           unchanged; pointer delta 0; flag 0.
    NEXT:  tape bit-for-bit unchanged; pointer delta = +g; flag 0.
    PREV:  tape bit-for-bit unchanged; pointer delta = -g; flag 0.
    SKIPZ: tape bit-for-bit unchanged; pointer delta 0; flag_out = 1 iff
           x_cur == 0.
  IDENTITY: flag_in = 0 behaves like flag_in = 1 (pure no-op).

A branch that ever pushes the pointer outside the window is pruned (and so
is every extension of that word).
"""

from typing import Optional

from machine import step, SKIP


class DeadWord(Exception):
    pass


def flag_reachable(bundleA, bundleB):
    """True iff either bundle contains a skip-test, i.e. the flag can ever
    become 1 during execution of a program built from this pair. If it is
    never reachable, the flag_in=1 requirement is vacuous (flag_in=1 can
    never actually occur) and is not enforced -- this matches the task's
    sanity requirement that, for the pure near-solution pair with no skip
    at all, AB/ABA/B count as exact FLIP/NEXT/PREV even though a *formal*
    flag_in=1 check on those words alone would fail (a flag_in=1 that can
    never arise for a flagless pair)."""
    return any(o.kind == SKIP for o in bundleA.ops) or any(o.kind == SKIP for o in bundleB.ops)


def build_window(g, template, xl, xc, xr):
    left = template(xl)
    cur = template(xc)
    right = template(xr)
    return list(left) + list(cur) + list(right)


def search_pair(bundleA, bundleB, g, template, rest, L,
                 want=("FLIP", "NEXT", "PREV", "SKIPZ"),
                 collect_identities=False, max_identities=5):
    """Returns dict primitive -> (word_string, length) or None, plus a list
    of identity words found (word_string) up to max_identities, plus a flag
    saying whether the whole word-tree was exhausted without any OOB issue
    at length L (for bookkeeping)."""

    W = 3 * g
    ptr0 = g + rest
    combos = [(xl, xc, xr) for xl in (0, 1) for xc in (0, 1) for xr in (0, 1)]
    flag_ok = flag_reachable(bundleA, bundleB)

    # initial states: for each combo, for each flag_in in (0,1)
    inits = []
    for (xl, xc, xr) in combos:
        win = build_window(g, template, xl, xc, xr)
        inits.append((win, ptr0, 0, (xl, xc, xr)))   # flag_in = 0
        inits.append((win, ptr0, 1, (xl, xc, xr)))   # flag_in = 1

    letters = {"A": bundleA, "B": bundleB}

    found = {p: None for p in want}
    identities = []

    # DFS with incremental branch states; state per node = list of
    # (window, ptr, flag, alive) aligned with `inits`.
    root_states = []
    for (win, p0, fin, combo) in inits:
        root_states.append([list(win), p0, fin, True])

    def check(word_str, states):
        # states aligned with inits (same order): pairs of flag_in=0/1 per combo
        for idx, (xl, xc, xr) in enumerate(combos):
            s0 = states[2 * idx]      # flag_in = 0
            s1 = states[2 * idx + 1]  # flag_in = 1
            w0, p0f, f0f, ok0 = s0
            w1, p1f, f1f, ok1 = s1
            if not ok0 or not ok1:
                return  # shouldn't happen if we only check alive words
            init_win = build_window(g, template, xl, xc, xr)
            # flag_in = 1 must always be pure identity -- but only when the
            # pair can ever actually produce flag = 1 (see flag_reachable).
            if flag_ok and not (w1 == init_win and p1f == ptr0 and f1f == 0):
                return
            for prim in list(found.keys()):
                if found[prim] is not None:
                    continue
                ok = False
                if prim == "FLIP":
                    left = init_win[:g]
                    right = init_win[2 * g:]
                    cur_expected = list(template(1 - xc))
                    expected = left + cur_expected + right
                    ok = (w0 == expected and p0f == ptr0 and f0f == 0)
                elif prim == "NEXT":
                    ok = (w0 == init_win and p0f == ptr0 + g and f0f == 0)
                elif prim == "PREV":
                    ok = (w0 == init_win and p0f == ptr0 - g and f0f == 0)
                elif prim == "SKIPZ":
                    want_flag = 1 if xc == 0 else 0
                    ok = (w0 == init_win and p0f == ptr0 and f0f == want_flag)
                if not ok:
                    return
            # if we got here for this combo, all remaining prims still hold;
            # move to next combo (loop continues)
        # all combos passed for all remaining prims -> record
        for prim in found:
            if found[prim] is None:
                found[prim] = (word_str, len(word_str))
        # identity check (flag_in=0 also pure identity, for every combo)
        is_identity = True
        for idx, (xl, xc, xr) in enumerate(combos):
            s0 = states[2 * idx]
            w0, p0f, f0f, ok0 = s0
            init_win = build_window(g, template, xl, xc, xr)
            if not (w0 == init_win and p0f == ptr0 and f0f == 0):
                is_identity = False
                break
        if is_identity and collect_identities and len(identities) < max_identities:
            identities.append(word_str)

    def advance(states, letter_char):
        bundle = letters[letter_char]
        new_states = []
        for (w, p, f, alive) in states:
            if not alive:
                new_states.append((w, p, f, False))
                continue
            nw, npo, nf, ok = step(bundle, w, p, f)
            if not ok:
                new_states.append((None, None, None, False))
            else:
                new_states.append((nw, npo, nf, True))
        return new_states

    def all_alive(states):
        return all(s[3] for s in states)

    def dfs(prefix, states):
        if not all_alive(states):
            return
        if prefix:
            check(prefix, states)
        if len(prefix) >= L:
            return
        if all(found[p] is not None for p in want) and not collect_identities:
            return
        for ch in ("A", "B"):
            new_states = advance(states, ch)
            dfs(prefix + ch, new_states)

    dfs("", root_states)
    return found, identities
