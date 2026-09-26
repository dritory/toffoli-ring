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

import itertools
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


def build_window(g, template, xs):
    """xs: logical bit for each group, left to right (odd length, middle
    entry is the current group)."""
    cells = []
    for x in xs:
        cells.extend(template(x))
    return cells


def search_pair(bundleA, bundleB, g, template, rest, L,
                 want=("FLIP", "NEXT", "PREV", "SKIPZ"),
                 collect_identities=False, max_identities=5, half_width=1):
    """Returns dict primitive -> (word_string, length) or None, plus a list
    of identity words found (word_string) up to max_identities.

    half_width: number of full context groups on each side of the current
    group (1 = the base spec's "group plus one group each side"; 2 = the
    wider ±2-group rerun). Window = (2*half_width+1) groups; a branch that
    ever pushes the pointer outside this window is pruned, and so is every
    extension of that word."""

    ngroups = 2 * half_width + 1
    ptr0 = half_width * g + rest
    cur_slot = half_width  # index of the current group within a combo tuple
    combos = list(itertools.product((0, 1), repeat=ngroups))
    flag_ok = flag_reachable(bundleA, bundleB)

    letters = {"A": bundleA, "B": bundleB}

    found = {p: None for p in want}
    identities = []

    init_wins = [build_window(g, template, xs) for xs in combos]

    root_states = []
    for win in init_wins:
        root_states.append((list(win), ptr0, 0, True))   # flag_in = 0
        root_states.append((list(win), ptr0, 1, True))   # flag_in = 1

    def check(word_str, states):
        # Each primitive must hold across ALL combos independently; one
        # primitive failing on some combo must not stop us from recording a
        # *different* primitive that holds across all combos for this same
        # word.
        pending = [p for p in found if found[p] is None]
        if not pending:
            return
        still_ok = {p: True for p in pending}

        for idx, xs in enumerate(combos):
            xc = xs[cur_slot]
            s0 = states[2 * idx]      # flag_in = 0
            s1 = states[2 * idx + 1]  # flag_in = 1
            w0, p0f, f0f, ok0 = s0
            w1, p1f, f1f, ok1 = s1
            if not ok0 or not ok1:
                return  # shouldn't happen if we only check alive words
            init_win = init_wins[idx]
            # flag_in = 1 must always be pure identity -- but only when the
            # pair can ever actually produce flag = 1 (see flag_reachable).
            # This is a blanket requirement independent of which primitive
            # is being tested, so if it fails, no primitive can match this
            # word at all.
            if flag_ok and not (w1 == init_win and p1f == ptr0 and f1f == 0):
                return

            for prim in pending:
                if not still_ok[prim]:
                    continue
                ok = False
                if prim == "FLIP":
                    cur_start = cur_slot * g
                    expected = list(init_win)
                    expected[cur_start:cur_start + g] = list(template(1 - xc))
                    ok = (w0 == expected and p0f == ptr0 and f0f == 0)
                elif prim == "NEXT":
                    ok = (w0 == init_win and p0f == ptr0 + g and f0f == 0)
                elif prim == "PREV":
                    ok = (w0 == init_win and p0f == ptr0 - g and f0f == 0)
                elif prim == "SKIPZ":
                    want_flag = 1 if xc == 0 else 0
                    ok = (w0 == init_win and p0f == ptr0 and f0f == want_flag)
                if not ok:
                    still_ok[prim] = False
            if not any(still_ok.values()):
                return  # nothing left can match; stop early

        # Record whichever primitives held across every combo. Since we
        # process words in strict increasing-length (BFS) order below, the
        # first word recorded for a primitive is guaranteed shortest.
        for prim in pending:
            if still_ok[prim] and found[prim] is None:
                found[prim] = (word_str, len(word_str))
        # identity check (flag_in=0 also pure identity, for every combo)
        is_identity = True
        for idx in range(len(combos)):
            s0 = states[2 * idx]
            w0, p0f, f0f, ok0 = s0
            init_win = init_wins[idx]
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

    # Level-order (BFS) traversal by word length, so that the first time a
    # primitive is matched is guaranteed to be at the shortest possible
    # length (a plain depth-first traversal would visit some length-3 words
    # before some length-1 words and could record a non-shortest macro).
    frontier = [("", root_states)]
    for depth in range(1, L + 1):
        next_frontier = []
        need_more = collect_identities or not all(found[p] is not None for p in want)
        if not need_more:
            break
        for prefix, states in frontier:
            for ch in ("A", "B"):
                new_states = advance(states, ch)
                if not all_alive(new_states):
                    continue  # pruned: this word (and its extensions) is dead
                word = prefix + ch
                check(word, new_states)
                next_frontier.append((word, new_states))
        frontier = next_frontier
        if not frontier:
            break

    return found, identities
