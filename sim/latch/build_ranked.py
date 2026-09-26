"""Build results/latch/ranked.csv from the NAND-gate cost table.

Reads sim/latch/cost_table.txt (lines: "tt cost op c1 c2 c3"), applies the
drop rules and the q-complement symmetry from HANDOVER-A section 3 task 1,
and writes results/latch/ranked.csv with columns:
    f_hex,g_hex,cost_f,cost_g,cost_total,class,bijective,formula
"""
import csv
import itertools
import sys

COST_TABLE = "/home/user/toffoli-ring/sim/latch/cost_table.txt"
OUT_CSV = "/home/user/toffoli-ring/results/latch/ranked.csv"
PAIRS_TXT = "/home/user/toffoli-ring/sim/latch/pairs.txt"

NF = 65536


def load_cost_table(path):
    cost = [None] * NF
    op = [None] * NF
    c1 = [None] * NF
    c2 = [None] * NF
    c3 = [None] * NF
    with open(path) as f:
        for line in f:
            parts = line.split()
            v, c, o, x1, x2, x3 = (int(p) for p in parts)
            cost[v] = c if c >= 0 else None  # None => unresolved at this search depth ("> max level")
            op[v] = o
            c1[v] = x1
            c2[v] = x2
            c3[v] = x3
    return cost, op, c1, c2, c3


def bit(tt, idx):
    return (tt >> idx) & 1


def independent_of_q(tt):
    return all(bit(tt, idx) == bit(tt, idx ^ 8) for idx in range(16))


def independent_of_ab(tt):
    return all(bit(tt, idx) == bit(tt, idx ^ 1) == bit(tt, idx ^ 2) for idx in range(16))


def independent_of_xab(tt):
    return all(bit(tt, idx) == bit(tt, idx ^ 7) and bit(tt, idx) == bit(tt, idx ^ 1)
               and bit(tt, idx) == bit(tt, idx ^ 2) and bit(tt, idx) == bit(tt, idx ^ 4)
               for idx in range(16))


def permute_q(tt):
    """f(NOT q, x, a, b): swap the q=0 half (bits 0-7) and q=1 half (bits 8-15)."""
    return ((tt & 0xFF) << 8) | ((tt >> 8) & 0xFF)


def complement(tt):
    return (~tt) & 0xFFFF


# ---------------- formula reconstruction from the minimal-cost derivation ----------------

VAR_NAMES = {2: "q", 3: "x", 4: "a", 5: "b"}

_formula_memo = {}
_negformula_memo = {}


def formula(tt, op, c1, c2, c3):
    if tt in _formula_memo:
        return _formula_memo[tt]
    o = op[tt]
    if o == 0:
        s = "0"
    elif o == 1:
        s = "1"
    elif o in VAR_NAMES:
        s = VAR_NAMES[o]
    elif o == 6:
        s = negformula(c1[tt], op, c1, c2, c3)
    elif o == 7:
        u = negformula(c1[tt], op, c1, c2, c3)
        v = negformula(c2[tt], op, c1, c2, c3)
        s = f"({u}) OR ({v})"
    elif o == 8:
        u = negformula(c1[tt], op, c1, c2, c3)
        v = negformula(c2[tt], op, c1, c2, c3)
        w = negformula(c3[tt], op, c1, c2, c3)
        s = f"({u}) OR ({v}) OR ({w})"
    else:
        s = f"<tt={tt:04x}>"
    _formula_memo[tt] = s
    return s


def negformula(tt, op, c1, c2, c3):
    if tt in _negformula_memo:
        return _negformula_memo[tt]
    o = op[tt]
    if o == 0:
        s = "1"
    elif o == 1:
        s = "0"
    elif o in VAR_NAMES:
        s = "~" + VAR_NAMES[o]
    elif o == 6:
        s = formula(c1[tt], op, c1, c2, c3)
    elif o == 7:
        u = formula(c1[tt], op, c1, c2, c3)
        v = formula(c2[tt], op, c1, c2, c3)
        s = f"({u}) AND ({v})"
    elif o == 8:
        u = formula(c1[tt], op, c1, c2, c3)
        v = formula(c2[tt], op, c1, c2, c3)
        w = formula(c3[tt], op, c1, c2, c3)
        s = f"({u}) AND ({v}) AND ({w})"
    else:
        s = f"~<tt={tt:04x}>"
    _negformula_memo[tt] = s
    return s


def simplify_text(s):
    # a few cheap textual cleanups
    s = s.replace("~~", "")
    while "((" in s:
        # collapse doubled parens around single tokens like ((q)) -> (q)
        import re
        s2 = re.sub(r"\(\(([a-z0-9~]+)\)\)", r"(\1)", s)
        if s2 == s:
            break
        s = s2
    return s


# ---------------- template matching for readable names ----------------

def all_truth_tables_for_templates():
    """Map truth-table value -> short template name, for common 2/3-input
    functions of {q,x,a,b} (and their negated-input variants)."""
    templates = {}

    def tt_of(fn):
        v = 0
        for idx in range(16):
            q = (idx >> 3) & 1
            x = (idx >> 2) & 1
            a = (idx >> 1) & 1
            b = idx & 1
            if fn(q, x, a, b):
                v |= (1 << idx)
        return v

    names = {"q": lambda q, x, a, b: q, "x": lambda q, x, a, b: x,
             "a": lambda q, x, a, b: a, "b": lambda q, x, a, b: b}

    def lit(n, neg):
        f = names[n]
        return (lambda q, x, a, b, f=f: 1 - f(q, x, a, b)) if neg else f

    vars_ = ["q", "x", "a", "b"]
    for n1, n2 in itertools.combinations(vars_, 2):
        for neg1 in (False, True):
            for neg2 in (False, True):
                l1, l2 = lit(n1, neg1), lit(n2, neg2)
                s1 = ("~" if neg1 else "") + n1
                s2 = ("~" if neg2 else "") + n2
                templates.setdefault(tt_of(lambda q, x, a, b, l1=l1, l2=l2: l1(q, x, a, b) and l2(q, x, a, b)), f"{s1} AND {s2}")
                templates.setdefault(tt_of(lambda q, x, a, b, l1=l1, l2=l2: l1(q, x, a, b) or l2(q, x, a, b)), f"{s1} OR {s2}")
                templates.setdefault(tt_of(lambda q, x, a, b, l1=l1, l2=l2: l1(q, x, a, b) ^ l2(q, x, a, b)), f"{s1} XOR {s2}")
                templates.setdefault(tt_of(lambda q, x, a, b, l1=l1, l2=l2: not (l1(q, x, a, b) ^ l2(q, x, a, b))), f"{s1} XNOR {s2}")
                templates.setdefault(tt_of(lambda q, x, a, b, l1=l1, l2=l2: not (l1(q, x, a, b) and l2(q, x, a, b))), f"NAND({s1},{s2})")
    for n in vars_:
        for neg in (False, True):
            l = lit(n, neg)
            s = ("~" if neg else "") + n
            templates.setdefault(tt_of(lambda q, x, a, b, l=l: l(q, x, a, b)), s)
    templates.setdefault(0, "0")
    templates.setdefault(0xFFFF, "1")

    # mux: q ? A : B  and its variants over {x,a,b} pairs (this is the natural
    # "clock class" / latch-controlled select shape)
    for n1, n2 in itertools.permutations(["x", "a", "b"], 2):
        l1, l2 = names[n1], names[n2]
        templates.setdefault(
            tt_of(lambda q, x, a, b, l1=l1, l2=l2: l1(q, x, a, b) if q else l2(q, x, a, b)),
            f"q ? {n1} : {n2}")
    # x XOR (a AND b): the Toffoli update itself, and q-gated variants
    templates.setdefault(tt_of(lambda q, x, a, b: x ^ (a & b)), "x XOR (a AND b)")
    templates.setdefault(tt_of(lambda q, x, a, b: (x ^ (a & b)) if q else x), "q ? (x XOR (a AND b)) : x")
    templates.setdefault(tt_of(lambda q, x, a, b: x ^ (a & b) ^ q), "x XOR (a AND b) XOR q")
    templates.setdefault(tt_of(lambda q, x, a, b: (a & b) ^ q), "(a AND b) XOR q")
    templates.setdefault(tt_of(lambda q, x, a, b: x ^ q), "x XOR q")
    templates.setdefault(tt_of(lambda q, x, a, b: a ^ b ^ q), "a XOR b XOR q")
    templates.setdefault(tt_of(lambda q, x, a, b: (x & (a ^ b)) ^ q), "(x AND (a XOR b)) XOR q")
    return templates


def short_formula(tt, templates, op, c1, c2, c3):
    if tt in templates:
        return templates[tt]
    return simplify_text(formula(tt, op, c1, c2, c3))


# ---------------- bijectivity check ----------------

def tt_eval(tt, q, x, a, b):
    idx = (q << 3) | (x << 2) | (a << 1) | b
    return (tt >> idx) & 1


def pass_state(state, N, k, f_tt, g_tt):
    s, q = state
    s = list(s)
    for i in range(N):
        xi = (i + k) % N
        bi = (i + 1) % N
        x, a, b = s[xi], s[i], s[bi]
        y = tt_eval(f_tt, q, x, a, b)
        q = tt_eval(g_tt, q, x, a, b)
        s[xi] = y
    return (tuple(s), q)


def is_bijective(f_tt, g_tt, Ns=(8, 9, 10, 11, 12), ks=(2, 3)):
    for N in Ns:
        for k in ks:
            if k >= N:
                continue
            seen = set()
            for m in range(1 << N):
                s = tuple((m >> i) & 1 for i in range(N))
                for q in (0, 1):
                    out = pass_state((s, q), N, k, f_tt, g_tt)
                    if out in seen:
                        return False
                    seen.add(out)
    return True


def main():
    bound = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    cost, op, c1, c2, c3 = load_cost_table(COST_TABLE)

    n_known = sum(1 for c in cost if c is not None)
    print(f"functions with known cost (<=5 or whatever the search reached): {n_known}/{NF}", file=sys.stderr)
    from collections import Counter
    print("cost histogram:", Counter(c for c in cost if c is not None), file=sys.stderr)

    templates = all_truth_tables_for_templates()

    # candidate f's: cost known and cost <= bound, and NOT independent of q
    f_candidates = [tt for tt in range(NF) if cost[tt] is not None and cost[tt] <= bound
                     and not independent_of_q(tt)]
    g_candidates = [tt for tt in range(NF) if cost[tt] is not None and cost[tt] <= bound]

    print(f"f candidates (depend on q, cost<={bound}): {len(f_candidates)}", file=sys.stderr)
    print(f"g candidates (cost<={bound}): {len(g_candidates)}", file=sys.stderr)

    x_tt = 0
    for idx in range(16):
        if (idx >> 2) & 1:
            x_tt |= (1 << idx)

    g_by_cost = {}
    for g_tt in g_candidates:
        g_by_cost.setdefault(cost[g_tt], []).append(g_tt)

    seen_canon = set()
    rows = []
    for f_tt in f_candidates:
        cf = cost[f_tt]
        indep_ab = independent_of_ab(f_tt)
        for cg in range(0, bound - cf + 1):
            for g_tt in g_by_cost.get(cg, ()):
                # rule 2: f independent of a,b AND g == x  -> drop
                if indep_ab and g_tt == x_tt:
                    continue

                # q-complement symmetry: (f,g) ~ (f', g') where f'(q,..)=f(~q,..)
                # and g' = NOT(g(~q,..)). The two representations of the same
                # equivalence class can have different gate costs (permuting q
                # is not free in general), so the canonical representative is
                # whichever realization is cheaper -- never the more expensive
                # one, which would misreport a total above what this class
                # actually costs. Tie-break on the numeric tuple for determinism.
                f2 = permute_q(f_tt)
                g2 = complement(permute_q(g_tt))
                cost_a = cf + cg
                cost_b = cost[f2] + cost[g2]
                if cost_b < cost_a or (cost_b == cost_a and (f2, g2) < (f_tt, g_tt)):
                    canon = (f2, g2)
                else:
                    canon = (f_tt, g_tt)
                if canon in seen_canon:
                    continue
                seen_canon.add(canon)
                # also mark the other representation seen, so it isn't emitted
                # again later as its own (f_tt,g_tt) outer-loop iteration
                other = (f2, g2) if canon == (f_tt, g_tt) else (f_tt, g_tt)
                seen_canon.add(other)
                cf2, cg2 = cost[canon[0]], cost[canon[1]]
                is_clock = independent_of_xab(canon[1])
                rows.append({
                    "f_tt": canon[0], "g_tt": canon[1],
                    "cost_f": cf2, "cost_g": cg2, "cost_total": cf2 + cg2,
                    "class": "clock" if is_clock else "generic",
                })

    rows.sort(key=lambda r: (r["cost_total"], r["f_tt"], r["g_tt"]))

    print(f"surviving pairs (bound total<={bound}, after drop rules + q-symmetry dedup): {len(rows)}",
          file=sys.stderr)

    # bijectivity: computed by the compiled C helper (sim/latch/bij), exhaustive
    # over N=8..12, k=2,3 -- see run_pipeline.sh. Write pairs.txt now, and a
    # ranked.csv with a placeholder that run_pipeline fills in afterwards.
    with open(OUT_CSV, "w", newline="") as csvf, open(PAIRS_TXT, "w") as pf:
        w = csv.writer(csvf)
        w.writerow(["f_hex", "g_hex", "cost_f", "cost_g", "cost_total", "class", "bijective", "formula_f", "formula_g"])
        for r in rows:
            ff = short_formula(r["f_tt"], templates, op, c1, c2, c3)
            gf = short_formula(r["g_tt"], templates, op, c1, c2, c3)
            w.writerow([f"{r['f_tt']:04x}", f"{r['g_tt']:04x}", r["cost_f"], r["cost_g"], r["cost_total"],
                        r["class"], "PENDING", ff, gf])
            pf.write(f"{r['f_tt']:04x} {r['g_tt']:04x} {r['class']}\n")

    print(f"wrote {OUT_CSV} (bijective column pending) and {PAIRS_TXT}", file=sys.stderr)


if __name__ == "__main__":
    main()
