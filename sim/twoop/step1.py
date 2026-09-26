"""
Step 1 (HANDOVER-B.md section 2): base pairs + one skip-test added at every
position, tested under the four scratch encodings. Search words up to
length 10.
"""
import itertools

from machine import Bundle, Op, FLIP, MOVE, SKIP, ALWAYS
from enc import ENCODINGS
from search import search_pair, flag_reachable

L = 10

BASE_PAIRS = [
    ("A=(flip,+1), B=(-1)",
     (Op(FLIP), Op(MOVE, dir=+1, cond=ALWAYS)),
     (Op(MOVE, dir=-1, cond=ALWAYS),)),
    ("A=(+1,flip), B=(-1)",
     (Op(MOVE, dir=+1, cond=ALWAYS), Op(FLIP)),
     (Op(MOVE, dir=-1, cond=ALWAYS),)),
]

SCRATCH_ENCODINGS = ["(x,1)", "(1,x)", "(x,0)", "(0,x)"]

rows = []

for pair_name, a_ops, b_ops in BASE_PAIRS:
    for target in ("A", "B"):
        base_ops = a_ops if target == "A" else b_ops
        for insert_pos in range(len(base_ops) + 1):
            for v in (0, 1):
                new_ops = base_ops[:insert_pos] + (Op(SKIP, v=v),) + base_ops[insert_pos:]
                if target == "A":
                    bundleA = Bundle(new_ops)
                    bundleB = Bundle(b_ops)
                else:
                    bundleA = Bundle(a_ops)
                    bundleB = Bundle(new_ops)

                variant_desc = (f"{pair_name} + skip(v={v}) inserted into "
                                f"{target} at position {insert_pos} "
                                f"-> A={bundleA}, B={bundleB}")

                for enc_name in SCRATCH_ENCODINGS:
                    g, template = ENCODINGS[enc_name]
                    for rest in range(g):
                        found, idents = search_pair(
                            bundleA, bundleB, g, template, rest, L,
                            want=("FLIP", "NEXT", "SKIPZ", "PREV"),
                            collect_identities=True, max_identities=3)
                        rows.append({
                            "pair_name": pair_name,
                            "target": target,
                            "insert_pos": insert_pos,
                            "v": v,
                            "bundleA": repr(bundleA),
                            "bundleB": repr(bundleB),
                            "encoding": enc_name,
                            "rest": rest,
                            "FLIP": found["FLIP"],
                            "NEXT": found["NEXT"],
                            "SKIPZ": found["SKIPZ"],
                            "PREV": found["PREV"],
                            "identities": idents,
                        })

winners = [r for r in rows if r["FLIP"] and r["NEXT"] and r["SKIPZ"]]

print(f"Total configurations tested: {len(rows)}")
print(f"Winners (FLIP, NEXT, SKIPZ all found, L<= {L}): {len(winners)}")
for w in winners:
    total = w["FLIP"][1] + w["NEXT"][1] + w["SKIPZ"][1]
    print(f"  {w['bundleA']} / {w['bundleB']} enc={w['encoding']} rest={w['rest']} "
          f"FLIP={w['FLIP']} NEXT={w['NEXT']} SKIPZ={w['SKIPZ']} PREV={w['PREV']} total={total}")

# write markdown report
import json

with open("/home/user/toffoli-ring/results/twoop/skip_step1.md", "w") as f:
    f.write("# Step 1: near-solution + one skip-test (HANDOVER-B section 2)\n\n")
    f.write(f"Base pairs: A=(flip,+1),B=(-1) and A=(+1,flip),B=(-1). "
            f"One skip-test (v=0 or v=1) inserted at every position into A or "
            f"into B. Tested under scratch encodings (x,1),(1,x),(x,0),(0,x), "
            f"both rest positions, words up to length {L}.\n\n")
    f.write(f"Total configurations tested: **{len(rows)}**\n\n")
    f.write(f"Configurations with FLIP, NEXT and SKIPZ all found: **{len(winners)}**\n\n")

    f.write("## Interpretation notes\n\n")
    f.write("- \"Every possible position\" is read literally as every insertion slot in the "
            "2-op letter (3 slots: before both ops, between them, after both) and every slot "
            "in the 1-op letter (2 slots), a strict superset of the handover's own count of "
            "\"2 placements\" (departure/arrival), since two of those slots are equivalent up "
            "to relabelling v and we did not want to risk missing a case by assuming that "
            "equivalence.\n")
    f.write("- Search length: the handover's section 2 prose mentions length 8; the task "
            "instructions for step 1 explicitly say length 10, which is what was run here.\n")
    f.write("- Exactness and the flag: every configuration here has a skip-test in exactly one "
            "bundle, so the flag is reachable and the full flag_in=1 identity requirement is "
            "enforced for every word tested (see `search.flag_reachable`). This differs from "
            "the flagless base pair (tested only in the sanity suite), where flag_in=1 can "
            "never actually occur and is not enforced -- see the final report for this "
            "interpretation decision.\n\n")

    if winners:
        f.write("## Winners (shortest macros)\n\n")
        f.write("| A | B | encoding | rest | FLIP | NEXT | SKIPZ | PREV | total len |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        winners_sorted = sorted(winners, key=lambda w: w["FLIP"][1] + w["NEXT"][1] + w["SKIPZ"][1])
        for w in winners_sorted:
            total = w["FLIP"][1] + w["NEXT"][1] + w["SKIPZ"][1]
            flip_s = f"{w['FLIP'][0]} ({w['FLIP'][1]})"
            next_s = f"{w['NEXT'][0]} ({w['NEXT'][1]})"
            skipz_s = f"{w['SKIPZ'][0]} ({w['SKIPZ'][1]})"
            prev_s = f"{w['PREV'][0]} ({w['PREV'][1]})" if w["PREV"] else "none"
            f.write(f"| `{w['bundleA']}` | `{w['bundleB']}` | {w['encoding']} | {w['rest']} | "
                    f"{flip_s} | {next_s} | {skipz_s} | {prev_s} | {total} |\n")
        f.write("\n")
    else:
        f.write("No configuration in step 1 found all three of FLIP, NEXT, SKIPZ "
                f"within length {L}. Full results below.\n\n")

    f.write("## Full results table\n\n")
    f.write("| A | B | encoding | rest | FLIP | NEXT | SKIPZ | PREV |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        def fmt(x):
            return f"{x[0]} ({x[1]})" if x else f"none<={L}"
        f.write(f"| `{r['bundleA']}` | `{r['bundleB']}` | {r['encoding']} | {r['rest']} | "
                f"{fmt(r['FLIP'])} | {fmt(r['NEXT'])} | {fmt(r['SKIPZ'])} | {fmt(r['PREV'])} |\n")

print("Wrote results/twoop/skip_step1.md")
