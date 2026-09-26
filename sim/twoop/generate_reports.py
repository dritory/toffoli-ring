"""
Consolidate the full-menu search, the no-(-1) confirmatory run, and (if it
has been run) the +/-2 window rerun into results/twoop/skip_summary.md.

If skip_full.csv contains any winner (FLIP+NEXT+SKIPZ all found for some
(pair,encoding,rest)), also run the independent brute-force re-verification
(verify_bruteforce.py) over a cyclic tape of 12 groups, 1000 random tapes,
both flags, and include that in the summary.
"""
import ast
import csv

from pairs import BUNDLES, canonical_pairs
from enc import ENCODING_REST_LIST
from search import search_pair

CSV_PATH = "/home/user/toffoli-ring/results/twoop/skip_full.csv"
SUMMARY_PATH = "/home/user/toffoli-ring/results/twoop/skip_summary.md"
NO_MINUS_PATH = "/home/user/toffoli-ring/results/twoop/no_minus_report.txt"
WIDE_RERUN_PATH = "/home/user/toffoli-ring/results/twoop/wide_rerun_report.txt"

PRIMS = ("FLIP", "NEXT", "SKIPZ", "PREV")


def parse_cell(s):
    if s.startswith("none<="):
        return None
    word, rest_s = s.split("(")
    length = int(rest_s.rstrip(")"))
    return (word, length)


def main():
    rows = []
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    pair_idxs = sorted(set(int(r["pair_idx"]) for r in rows))
    n_pairs = len(pair_idxs)
    n_rows = len(rows)

    winners = []
    for r in rows:
        flip = parse_cell(r["FLIP"])
        next_ = parse_cell(r["NEXT"])
        skipz = parse_cell(r["SKIPZ"])
        prev = parse_cell(r["PREV"])
        if flip and next_ and skipz:
            total = flip[1] + next_[1] + skipz[1]
            winners.append({
                "pair_idx": int(r["pair_idx"]), "bundleA": r["bundleA"], "bundleB": r["bundleB"],
                "encoding": r["encoding"], "rest": int(r["rest"]), "search_L": int(r["search_L"]),
                "FLIP": flip, "NEXT": next_, "SKIPZ": skipz, "PREV": prev, "total": total,
            })
    winners.sort(key=lambda w: w["total"])

    n_at_least_2 = 0
    for r in rows:
        hits = sum(1 for p in ("FLIP", "NEXT", "SKIPZ") if parse_cell(r[p]) is not None)
        if hits >= 2:
            n_at_least_2 += 1

    lines = []
    lines.append("# Skip-flag full menu search: summary\n")
    lines.append("Scope: HANDOVER-B.md sections 2-4 (skip-flag pairs). Sections 6-7 "
                  "(stateless pairs) are out of scope for this report.\n")
    lines.append("## Counts\n")
    lines.append(f"- Canonical pairs searched (mod mirror + complement symmetry, "
                  f"each with a +1 mover and a -1 mover): **{n_pairs}**\n")
    lines.append(f"- Encoding x rest combinations per pair: **{len(ENCODING_REST_LIST)}**\n")
    lines.append(f"- Total (pair, encoding, rest) rows: **{n_rows}**\n")
    lines.append(f"- Rows extended to length 12 (had >= 2 of FLIP/NEXT/SKIPZ at length 10): "
                  f"**{n_at_least_2}**\n")
    lines.append(f"- Winners (FLIP, NEXT and SKIPZ all found for the same pair/encoding/rest): "
                  f"**{len(winners)}**\n")

    if winners:
        lines.append("\n## Winners, ranked by total macro length (FLIP+NEXT+SKIPZ)\n")
        lines.append("| rank | A | B | encoding | rest | FLIP | NEXT | SKIPZ | PREV | total |\n")
        lines.append("|---|---|---|---|---|---|---|---|---|---|\n")
        for i, w in enumerate(winners, 1):
            prev_s = f"{w['PREV'][0]}({w['PREV'][1]})" if w["PREV"] else "none"
            lines.append(f"| {i} | `{w['bundleA']}` | `{w['bundleB']}` | {w['encoding']} | "
                         f"{w['rest']} | {w['FLIP'][0]}({w['FLIP'][1]}) | "
                         f"{w['NEXT'][0]}({w['NEXT'][1]}) | {w['SKIPZ'][0]}({w['SKIPZ'][1]}) | "
                         f"{prev_s} | {w['total']} |\n")

        lines.append("\n## Identity words for each winner\n")
        cp = canonical_pairs()
        enc_lookup = {(name, rest): (g, template) for (name, g, template, rest) in ENCODING_REST_LIST}
        verify_target = None
        for w in winners:
            ai, bi = cp[w["pair_idx"]]
            bundleA, bundleB = BUNDLES[ai], BUNDLES[bi]
            g, template = enc_lookup[(w["encoding"], w["rest"])]
            _, idents = search_pair(bundleA, bundleB, g, template, w["rest"], w["search_L"],
                                     want=PRIMS, collect_identities=True, max_identities=6)
            lines.append(f"- `{w['bundleA']}` / `{w['bundleB']}` @ {w['encoding']} rest={w['rest']}: "
                         f"identity words found: {idents if idents else '(none found up to L)'}\n")
            if verify_target is None:
                verify_target = (bundleA, bundleB, g, template, w["rest"], w)

        # Independent brute-force re-verification of the top winner.
        if verify_target is not None:
            import verify_bruteforce as vb
            bundleA, bundleB, g, template, rest, w = verify_target

            def to_ops(bundle):
                out = []
                for o in bundle.ops:
                    if o.kind == "flip":
                        out.append(("flip",))
                    elif o.kind == "move":
                        cond = {"always": "always", "eq0": "eq0", "eq1": "eq1"}[o.cond]
                        out.append(("move", o.dir, cond))
                    elif o.kind == "skip":
                        out.append(("skip", o.v))
                return out

            opsA = to_ops(bundleA)
            opsB = to_ops(bundleB)
            macros = {"FLIP": w["FLIP"][0], "NEXT": w["NEXT"][0], "SKIPZ": w["SKIPZ"][0]}
            results = vb.verify("top_winner", opsA, opsB, g, template, rest, macros,
                                 n_groups=12, n_random=1000, seed=12345)
            lines.append("\n## Independent brute-force re-verification (top winner)\n")
            lines.append(f"Pair: A=`{w['bundleA']}`, B=`{w['bundleB']}`, encoding={w['encoding']}, "
                         f"rest={w['rest']}. Cyclic tape of 12 groups, 1000 random tapes, both "
                         f"flag_in values (2000 checks per macro), verified with a second, "
                         f"separately written simulator (verify_bruteforce.py, no shared code "
                         f"with machine.py/search.py).\n\n")
            for prim, (ok, total, fails) in results.items():
                lines.append(f"- {prim} = `{macros[prim]}`: {ok}/{total} checks passed"
                             + ("" if ok == total else f" -- FAILURES: {fails}") + "\n")
    else:
        lines.append("\n## No winner\n")
        lines.append(f"Exhaustive search over **{n_pairs}** canonical pairs x "
                     f"**{len(ENCODING_REST_LIST)}** encoding/rest combinations "
                     f"(**{n_rows}** rows total), words to length 10 (extended to 12 for the "
                     f"**{n_at_least_2}** rows that already had >= 2 of FLIP/NEXT/SKIPZ at "
                     f"length 10), found **no pair** achieving FLIP, NEXT and SKIPZ together "
                     f"under any single encoding and rest position.\n")

    # no -1 subspace confirmation
    lines.append("\n## No -1 subspace confirmation\n")
    try:
        with open(NO_MINUS_PATH) as f:
            lines.append("```\n" + f.read() + "```\n")
    except FileNotFoundError:
        lines.append("(no_minus_search.py has not been run yet)\n")

    # wide (+/-2) rerun section, if available
    lines.append("\n## Window +/-2 rerun\n")
    try:
        with open(WIDE_RERUN_PATH) as f:
            lines.append("Requested by the orchestrator: rerun step 1 (all of it) and every "
                         "step-2 row that had >= 2 of FLIP/NEXT/SKIPZ at length 10, with the "
                         "window widened to the current group +/- 2 groups (prune only when a "
                         "branch leaves that wider window). Raw report:\n\n")
            lines.append("```\n" + f.read() + "```\n")
    except FileNotFoundError:
        lines.append("(wide_rerun.py has not been run yet)\n")

    with open(SUMMARY_PATH, "w") as f:
        f.writelines(lines)
    print("Wrote", SUMMARY_PATH)
    print(f"pairs={n_pairs} rows={n_rows} winners={len(winners)}")


if __name__ == "__main__":
    main()
