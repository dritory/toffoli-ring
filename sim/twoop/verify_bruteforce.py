"""
Independent, separately-written brute-force verifier for a winning pair.

This does NOT import machine.py or search.py: it is a fresh implementation
of the same machine semantics, used only to cross-check a claimed winner's
three macros (FLIP, NEXT, SKIPZ) against many random full cyclic tapes.

Usage: edit the CONFIG block below (bundle op-lists, encoding template,
rest, macro words) and run `python3 verify_bruteforce.py`.
"""
import random

# ---- fresh, independent bundle representation -----------------------------
# Each op is a tuple:
#   ('flip',)
#   ('move', dir, cond)   cond in {'always','eq0','eq1'}
#   ('skip', v)


def exec_bundle(ops, tape, pos, n):
    """Execute one bundle's sub-ops in order on a cyclic tape of length n.
    Returns (new_pos, flag_out)."""
    p = pos
    flag_out = 0
    for op in ops:
        if op[0] == 'flip':
            tape[p] ^= 1
        elif op[0] == 'move':
            _, d, cond = op
            cur = tape[p]
            move = (cond == 'always') or (cond == 'eq0' and cur == 0) or (cond == 'eq1' and cur == 1)
            if move:
                p = (p + d) % n
        elif op[0] == 'skip':
            _, v = op
            flag_out = 1 if tape[p] == v else 0
    return p, flag_out


def run_macro(word, opsA, opsB, tape, pos, flag, n):
    """word: string over 'A'/'B'. Runs the macro on a CYCLIC tape (mod n),
    tick by tick, exactly per machine semantics (flag-gated fetch)."""
    for ch in word:
        ops = opsA if ch == 'A' else opsB
        if flag == 1:
            flag = 0
            continue
        pos, flag = exec_bundle(ops, tape, pos, n)
    return tape, pos, flag


def decode_group(cells, templates):
    """templates: [template(0), template(1)] as tuples. Returns 0/1 or None
    if cells match neither (shouldn't happen for a valid tape)."""
    if tuple(cells) == tuple(templates[0]):
        return 0
    if tuple(cells) == tuple(templates[1]):
        return 1
    return None


def verify(name, opsA, opsB, g, template, rest, macros, n_groups=12, n_random=1000, seed=12345):
    """macros: dict primitive -> word string. Builds a cyclic tape of
    n_groups groups (width g each, total n = n_groups*g cells), assigns
    random logical bits to every group, and checks each macro's exactness
    (bit-for-bit, both flag_in values) at a random group boundary."""
    rng = random.Random(seed)
    n = n_groups * g
    templates = [tuple(template(0)), tuple(template(1))]

    results = {}
    for prim, word in macros.items():
        ok_count = 0
        fail_examples = []
        for trial in range(n_random):
            xs = [rng.randint(0, 1) for _ in range(n_groups)]
            group0 = rng.randrange(n_groups)  # which group is "current"
            tape = []
            for x in xs:
                tape.extend(template(x))
            pos0 = group0 * g + rest

            for flag_in in (0, 1):
                tape_copy = list(tape)
                tape_out, pos_out, flag_out = run_macro(word, opsA, opsB, tape_copy, pos0, flag_in, n)

                if flag_in == 1:
                    good = (tape_out == tape and pos_out == pos0 and flag_out == 0)
                else:
                    if prim == "FLIP":
                        expected = list(tape)
                        expected[group0 * g:group0 * g + g] = list(template(1 - xs[group0]))
                        good = (tape_out == expected and pos_out == pos0 and flag_out == 0)
                    elif prim == "NEXT":
                        good = (tape_out == tape and pos_out == (pos0 + g) % n and flag_out == 0)
                    elif prim == "PREV":
                        good = (tape_out == tape and pos_out == (pos0 - g) % n and flag_out == 0)
                    elif prim == "SKIPZ":
                        want_flag = 1 if xs[group0] == 0 else 0
                        good = (tape_out == tape and pos_out == pos0 and flag_out == want_flag)
                    else:
                        raise ValueError(prim)

                if good:
                    ok_count += 1
                else:
                    if len(fail_examples) < 3:
                        fail_examples.append((xs, group0, flag_in, tape_out, pos_out, flag_out))
        total = n_random * 2
        results[prim] = (ok_count, total, fail_examples)
    return results


if __name__ == "__main__":
    print("This module is meant to be imported/parameterized once a winner "
          "is found by the exhaustive search. See generate_reports.py for "
          "the actual invocation (if any winner exists).")
