"""
Encodings: groups of width g holding one logical bit x, with a fixed pointer
rest position inside the group. See HANDOVER-B.md section on primitives.

Each encoding is given as a name and a template function x -> tuple of g
bits (the group's physical contents for logical value x). Rest position r
(0 <= r < g) is enumerated separately.
"""

from itertools import permutations

# name -> (g, template(x) -> tuple of length g)
ENCODINGS = {}

ENCODINGS["none"] = (1, lambda x: (x,))
ENCODINGS["(x,xbar)"] = (2, lambda x: (x, 1 - x))
ENCODINGS["(xbar,x)"] = (2, lambda x: (1 - x, x))
ENCODINGS["(x,1)"] = (2, lambda x: (x, 1))
ENCODINGS["(1,x)"] = (2, lambda x: (1, x))
ENCODINGS["(x,0)"] = (2, lambda x: (x, 0))
ENCODINGS["(0,x)"] = (2, lambda x: (0, x))

# period-3 patterns: one data cell, two constants; base patterns and their
# rotations (rotate right: seq -> [seq[-1]] + seq[:-1]).
_P3_BASES = [
    ("x", 0, 1),
    ("x", 1, 0),
    ("x", 0, 0),
    ("x", 1, 1),
]


def _rotate_right(seq):
    return (seq[-1],) + tuple(seq[:-1])


def _make_p3_template(pattern):
    # pattern is a 3-tuple where exactly one entry is "x" and the others are
    # 0/1 constants.
    def template(x, pattern=pattern):
        out = []
        for c in pattern:
            out.append(x if c == "x" else c)
        return tuple(out)
    return template


_seen_p3 = set()
for base in _P3_BASES:
    seq = base
    for _ in range(3):
        if seq not in _seen_p3:
            _seen_p3.add(seq)
            name = "p3" + str(seq)
            ENCODINGS[name] = (3, _make_p3_template(seq))
        seq = _rotate_right(seq)

# sanity: should be 1 (none) + 6 (width-2) + 12 (period-3) = 19 encodings
assert len(ENCODINGS) == 1 + 6 + 12, len(ENCODINGS)


def encoding_rest_list():
    """List of (encoding_name, g, template, rest) covering every rest
    position within the group, for every encoding."""
    out = []
    for name, (g, template) in ENCODINGS.items():
        for r in range(g):
            out.append((name, g, template, r))
    return out


ENCODING_REST_LIST = encoding_rest_list()
# sanity: 1*1 + 6*2 + 12*3 = 49
assert len(ENCODING_REST_LIST) == 1 + 12 + 36, len(ENCODING_REST_LIST)
