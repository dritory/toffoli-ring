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

from machine import parse_bundle
from enc import ENCODING_REST_LIST
from search import search_pair

CSV_PATH = "/home/user/toffoli-ring/results/twoop/skip_full.csv"
SUMMARY_PATH = "/home/user/toffoli-ring/results/twoop/skip_summary.md"
NO_MINUS_PATH = "/home/user/toffoli-ring/results/twoop/no_minus_report.txt"
WIDE_RERUN_PATH = "/home/user/toffoli-ring/results/twoop/wide_rerun_report.txt"
GUARDED_CSV_PATH = "/home/user/toffoli-ring/results/twoop/guarded_full.csv"

PRIMS = ("FLIP", "NEXT", "SKIPZ", "PREV")
GUARDED_PRIMS = ("FLIP", "NEXT", "PREV", "CFLIP", "CNEXT", "CPREV")


def to_ops(bundle):
    out = []
    for o in bundle.ops:
        if o.kind == "flip":
            out.append(("flip",))
        elif o.kind == "move":
            out.append(("move", o.dir, o.cond))
        elif o.kind == "skip":
            out.append(("skip", o.v))
    return out


def guarded_section():
    lines = ["\n## Guarded-macro criterion\n"]
    lines.append("Per orchestrator instruction: SKIPZ X compiled jointly as one macro CX, flag "
                 "internal to the macro (flag_in=0 only; the word must end with flag_out=0 in "
                 "every branch). Targets: FLIP, NEXT, PREV (unconditional, as before) plus CFLIP "
                 "(flip iff bit==1, i.e. clear-if-1), CNEXT (+g iff bit==1 else 0), CPREV (-g "
                 "iff bit==1 else 0). Window: R = ceil(floor(L/2)/g)+1 groups each side (exact "
                 "for pruning at that L).\n\n")
    lines.append("**Criterion correction (from the orchestrator):** a guarded FLIP acts on the "
                 "same cell it tests, so CFLIP is just CLEAR and carries no data interaction -- "
                 "the reference machine's actual data dependence comes only from SKIPZ.NEXT and "
                 "SKIPZ.PREV, i.e. from CNEXT and CPREV. Accordingly:\n"
                 "- **Primary winner table**: rows with FLIP, NEXT, PREV, CNEXT **and** CPREV "
                 "all present, ranked by the total length of those five macros.\n"
                 "- **Secondary table**: rows with FLIP, NEXT and at least one of "
                 "CNEXT/CPREV (with or without PREV), that do not already qualify for the "
                 "primary table.\n"
                 "- The old FLIP+NEXT+CFLIP criterion is reported as a footnote count only.\n\n")

    try:
        with open(GUARDED_CSV_PATH, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        lines.append("(guarded_full_search.py has not been run yet)\n")
        return lines

    pair_idxs = sorted(set(int(r["pair_idx"]) for r in rows))
    n_pairs = len(pair_idxs)
    n_rows = len(rows)
    n_l12 = sum(1 for r in rows if int(r["search_L"]) == 12)

    def pc(s):
        return None if s.startswith("none<=") else (s.split("(")[0], int(s.split("(")[1].rstrip(")")))

    all_entries = []
    for r in rows:
        flip, next_, prev, cflip, cnext, cprev = (pc(r[p]) for p in GUARDED_PRIMS)
        e = {
            "pair_idx": int(r["pair_idx"]), "bundleA": r["bundleA"], "bundleB": r["bundleB"],
            "encoding": r["encoding"], "g": int(r["g"]), "rest": int(r["rest"]),
            "search_L": int(r["search_L"]),
            "FLIP": flip, "NEXT": next_, "PREV": prev, "CFLIP": cflip,
            "CNEXT": cnext, "CPREV": cprev,
        }
        all_entries.append(e)

    primary = []
    secondary = []
    old_cflip_winners = 0
    for e in all_entries:
        if e["FLIP"] and e["NEXT"] and e["CFLIP"]:
            old_cflip_winners += 1
        if e["FLIP"] and e["NEXT"] and e["PREV"] and e["CNEXT"] and e["CPREV"]:
            e["total5"] = (e["FLIP"][1] + e["NEXT"][1] + e["PREV"][1] +
                           e["CNEXT"][1] + e["CPREV"][1])
            primary.append(e)
        elif e["FLIP"] and e["NEXT"] and (e["CNEXT"] or e["CPREV"]):
            secondary.append(e)
    primary.sort(key=lambda w: w["total5"])

    n_standalone = {p: sum(1 for r in rows if pc(r[p]) is not None) for p in GUARDED_PRIMS}

    lines.append("### Counts\n")
    lines.append(f"- Canonical pairs searched: **{n_pairs}**\n")
    lines.append(f"- Total (pair, encoding, rest) rows: **{n_rows}**\n")
    lines.append(f"- Rows extended to length 12 (>= 3 of the 6 targets at length 10): **{n_l12}**\n")
    lines.append(f"- Standalone target counts: " +
                 ", ".join(f"{p} {n_standalone[p]}" for p in GUARDED_PRIMS) + "\n")
    lines.append(f"- **Primary winners (FLIP, NEXT, PREV, CNEXT, CPREV all found): "
                 f"{len(primary)}**\n")
    lines.append(f"- **Secondary winners (FLIP, NEXT, and at least one of CNEXT/CPREV, "
                 f"not already primary): {len(secondary)}**\n")
    lines.append(f"- Footnote -- old criterion (FLIP, NEXT, CFLIP all found; CFLIP carries no "
                 f"data interaction, superseded by the correction above): {old_cflip_winners}\n")

    def ref_check(w):
        """Orchestrator's independently-verified reference row: A=(flip,skip(v=0),move+1),
        B=(flip,skip(v=0),move-1), (x,xbar) rest 0, total = 3+6+12+6+12 = 39."""
        return (w["bundleA"] == "(flip,skip(v=0),move+1)" and
                w["bundleB"] == "(flip,skip(v=0),move-1)" and
                w["encoding"] == "(x,xbar)" and w["rest"] == 0)

    REF_TOTAL = 3 + 6 + 12 + 6 + 12  # ABB + ABBAAA + BAABBBABBABB + ABBAAB + ABBABABAABBB

    if primary:
        best = primary[0]
        beats_ref = best["total5"] < REF_TOTAL
        matches_ref = any(ref_check(w) for w in primary)
        lines.append(f"\nBest total-length in the complete CSV for the primary (five-macro) "
                     f"criterion: **{best['total5']}**. Orchestrator's independently-verified "
                     f"reference row totals **{REF_TOTAL}** (ABB=3 + ABBAAA=6 + "
                     f"BAABBBABBABB=12 + ABBAAB=6 + ABBABABAABBB=12). "
                     + ("The reference row itself is the best in the complete CSV (nothing beats it).\n"
                        if (matches_ref and best["total5"] == REF_TOTAL) else
                        (f"**{sum(1 for w in primary if w['total5'] < REF_TOTAL)} row(s) in the "
                         f"complete CSV beat the reference on total length.**\n" if beats_ref else
                         "No row in the complete CSV beats the reference on total length.\n")))

        lines.append("\n### (1) Primary winners, ranked by total length of FLIP+NEXT+PREV+CNEXT+CPREV\n")
        lines.append("| rank | A | B | encoding | rest | FLIP | NEXT | PREV | CNEXT | CPREV | total5 |\n")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for i, w in enumerate(primary, 1):
            lines.append(f"| {i} | `{w['bundleA']}` | `{w['bundleB']}` | {w['encoding']} | "
                         f"{w['rest']} | {w['FLIP'][0]}({w['FLIP'][1]}) | "
                         f"{w['NEXT'][0]}({w['NEXT'][1]}) | {w['PREV'][0]}({w['PREV'][1]}) | "
                         f"{w['CNEXT'][0]}({w['CNEXT'][1]}) | {w['CPREV'][0]}({w['CPREV'][1]}) | "
                         f"{w['total5']} |\n")

        enc_lookup = {(name, rest): (g, template) for (name, g, template, rest) in ENCODING_REST_LIST}
        import verify_bruteforce as vb
        lines.append("\n### Independent brute-force re-verification (top 3 of table 1)\n")
        for rank, w in enumerate(primary[:3], 1):
            bundleA, bundleB = parse_bundle(w["bundleA"]), parse_bundle(w["bundleB"])
            g, template = enc_lookup[(w["encoding"], w["rest"])]
            opsA, opsB = to_ops(bundleA), to_ops(bundleB)
            macros = {"FLIP": w["FLIP"][0], "NEXT": w["NEXT"][0], "PREV": w["PREV"][0],
                      "CNEXT": w["CNEXT"][0], "CPREV": w["CPREV"][0]}
            results = vb.verify_guarded(opsA, opsB, g, template, w["rest"], macros,
                                         n_groups=12, n_random=1000, seed=12345)
            lines.append(f"\nRank {rank}: A=`{w['bundleA']}`, B=`{w['bundleB']}`, "
                         f"encoding={w['encoding']}, rest={w['rest']}. Cyclic tape of 12 groups, "
                         f"1000 random tapes, flag_in=0 only, verified with `verify_guarded()` "
                         f"in verify_bruteforce.py (shares no code with guarded_search.py).\n\n")
            for prim, (ok, total, fails) in results.items():
                lines.append(f"- {prim} = `{macros[prim]}`: {ok}/{total} checks passed"
                             + ("" if ok == total else f" -- FAILURES: {fails}") + "\n")
    else:
        lines.append("\n### (1) No primary winner\n")
        lines.append(f"Exhaustive search over **{n_pairs}** canonical pairs x 49 encoding/rest "
                     f"combinations found no row with FLIP, NEXT, PREV, CNEXT and CPREV all "
                     f"present.\n")

    if secondary:
        secondary_sorted = sorted(
            secondary,
            key=lambda w: w["FLIP"][1] + w["NEXT"][1] +
            (w["CNEXT"][1] if w["CNEXT"] else 0) + (w["CPREV"][1] if w["CPREV"] else 0))
        lines.append(f"\n### (2) Secondary rows (FLIP, NEXT, and >=1 of CNEXT/CPREV; not "
                     f"already primary): {len(secondary)} total, top 20 shown\n")
        lines.append("| A | B | encoding | rest | FLIP | NEXT | PREV | CNEXT | CPREV |\n")
        lines.append("|---|---|---|---|---|---|---|---|---|\n")
        for w in secondary_sorted[:20]:
            prev_s = f"{w['PREV'][0]}({w['PREV'][1]})" if w["PREV"] else "no"
            cnext_s = f"{w['CNEXT'][0]}({w['CNEXT'][1]})" if w["CNEXT"] else "no"
            cprev_s = f"{w['CPREV'][0]}({w['CPREV'][1]})" if w["CPREV"] else "no"
            lines.append(f"| `{w['bundleA']}` | `{w['bundleB']}` | {w['encoding']} | {w['rest']} | "
                         f"{w['FLIP'][0]}({w['FLIP'][1]}) | {w['NEXT'][0]}({w['NEXT'][1]}) | "
                         f"{prev_s} | {cnext_s} | {cprev_s} |\n")
    else:
        lines.append("\n### (2) No secondary rows beyond the primary table.\n")

    return lines


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
    n_flip = n_next = n_prev = n_skipz = 0
    for r in rows:
        hits = sum(1 for p in ("FLIP", "NEXT", "SKIPZ") if parse_cell(r[p]) is not None)
        if hits >= 2:
            n_at_least_2 += 1
        if parse_cell(r["FLIP"]) is not None:
            n_flip += 1
        if parse_cell(r["NEXT"]) is not None:
            n_next += 1
        if parse_cell(r["PREV"]) is not None:
            n_prev += 1
        if parse_cell(r["SKIPZ"]) is not None:
            n_skipz += 1

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
    lines.append(f"- Standalone primitive counts (rows where that primitive alone was found, "
                  f"regardless of the others): FLIP {n_flip}, NEXT {n_next}, PREV {n_prev}, "
                  f"SKIPZ {n_skipz} (out of {n_rows} rows)\n")

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
        enc_lookup = {(name, rest): (g, template) for (name, g, template, rest) in ENCODING_REST_LIST}
        verify_target = None
        for w in winners:
            bundleA, bundleB = parse_bundle(w["bundleA"]), parse_bundle(w["bundleB"])
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

    lines.extend(guarded_section())

    with open(SUMMARY_PATH, "w") as f:
        f.writelines(lines)
    print("Wrote", SUMMARY_PATH)
    print(f"pairs={n_pairs} rows={n_rows} winners={len(winners)}")


if __name__ == "__main__":
    main()
