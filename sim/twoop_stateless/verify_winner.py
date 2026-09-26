"""
Independent re-verification of a candidate macro on a FULL cyclic tape of
12 groups (not the abstracted 3-group window used by the search), with
random group contents. This exercises a completely separate code path
(real wraparound indexing) as a cross-check against the window-based
exhaustive search in model.py / run_search.py.

Used both for genuine winners (none were found -- see stateless_summary.md)
and, as a bonus confidence check, for the best near-miss macros.
"""

import random

from model import materialize, decode_group


def apply_letter_cyclic(bundle, tape, ptr):
    """Same semantics as model.apply_letter but with cyclic (mod-N)
    pointer arithmetic instead of window-bounds failure."""
    flip, d, cond, order = bundle
    n = len(tape)
    if flip and order == 'FM':
        tape[ptr] ^= 1
        cell = tape[ptr]
        if cond is None or cell == cond:
            ptr = (ptr + d) % n
        return ptr
    elif flip and order == 'MF':
        cell = tape[ptr]
        if cond is None or cell == cond:
            ptr = (ptr + d) % n
        tape[ptr] ^= 1
        return ptr
    else:
        cell = tape[ptr]
        if cond is None or cell == cond:
            ptr = (ptr + d) % n
        return ptr


def verify_on_full_tape(pair, pattern, g, rest, word, target, ngroups=12, trials=1000, seed=0):
    """
    Returns (all_pass: bool, failures: list of counterexamples (up to 5)).
    Checks the macro `word` against `target` on a cyclic tape of `ngroups`
    groups, `trials` random group-content assignments and random start
    group, each checked exactly (not sampled per-branch: this uses concrete
    random data, so it's a Monte-Carlo cross-check, not a proof by itself --
    the proof is the exhaustive window search; this guards against bugs in
    that search's implementation).
    """
    A, B = pair
    N = ngroups * g
    rng = random.Random(seed)
    failures = []
    passes = 0
    for trial in range(trials):
        bits = [rng.randint(0, 1) for _ in range(ngroups)]
        tape = []
        for b in bits:
            tape.extend(materialize(b, pattern))
        start_group = rng.randrange(ngroups)
        ptr = start_group * g + rest
        start_ptr = ptr
        xm0 = bits[start_group]

        ok = True
        for letter in word:
            bundle = A if letter == 'A' else B
            ptr = apply_letter_cyclic(bundle, tape, ptr)

        # decode all groups
        decoded = []
        valid = True
        for gi in range(ngroups):
            seg = tape[gi * g:(gi + 1) * g]
            d = decode_group(seg, pattern)
            if d is None:
                valid = False
                break
            decoded.append(d)
        if not valid:
            failures.append((trial, bits, start_group, 'invalid encoding after run'))
            continue

        # expected effect
        expected = list(bits)
        if target == 'FLIP':
            expected[start_group] = 1 - bits[start_group]
            want_ptr = start_ptr
        elif target == 'NEXT':
            want_ptr = (start_ptr + g) % N
        elif target == 'PREV':
            want_ptr = (start_ptr - g) % N
        elif target == 'CFLIP':
            expected[start_group] = 0
            want_ptr = start_ptr
        elif target == 'CNEXT':
            want_ptr = (start_ptr + g) % N if xm0 == 1 else start_ptr
        elif target == 'CPREV':
            want_ptr = (start_ptr - g) % N if xm0 == 1 else start_ptr
        else:
            raise ValueError(target)

        ok = (decoded == expected and ptr == want_ptr)
        if ok:
            passes += 1
        else:
            failures.append((trial, bits, start_group, decoded, ptr, want_ptr))
        if len(failures) > 5:
            break

    return (passes == trials), failures[:5], passes, trials


if __name__ == '__main__':
    # Bonus check: best near-miss pair (idx 52 in gen_pairs()), which finds
    # FLIP, CNEXT, CPREV (but not NEXT/PREV/CFLIP) under (x,1), rest=0.
    from model import gen_pairs
    pairs = gen_pairs()
    pair = pairs[52]
    pattern = ('x', '1')
    g = 2
    rest = 0
    checks = [('AB', 'FLIP'), ('ABAABA', 'CNEXT'), ('BB', 'CPREV')]
    for word, target in checks:
        ok, fails, passes, trials = verify_on_full_tape(pair, pattern, g, rest, word, target)
        print(f"{target:6s} word={word:10s} -> {'PASS' if ok else 'FAIL'} ({passes}/{trials})")
        for f in fails:
            print("   counterexample:", f)
