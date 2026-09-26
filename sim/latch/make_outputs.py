"""Combine ranked.csv + the three dynamics.c CSV outputs (cycles, vacuum,
interact) into results/latch/dynamics.csv, and pick the best candidates for
results/latch/summary.md and results/latch/seeds.md (spacetime diagrams).
"""
import csv
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, "/home/user/toffoli-ring/sim/latch")
from model import pass_latch  # noqa: E402

BASE = "/home/user/toffoli-ring"
RANKED_FULL = f"{BASE}/results/latch/ranked.csv"     # task-1 deliverable, all surviving pairs
RANKED = f"{BASE}/results/latch/ranked_top.csv"       # task-2 subset actually simulated
CYCLES = f"{BASE}/sim/latch/cycles.csv"
VACUUM = f"{BASE}/sim/latch/vacuum.csv"
INTERACT = f"{BASE}/sim/latch/interact.csv"
DYNAMICS_OUT = f"{BASE}/results/latch/dynamics.csv"
SUMMARY_OUT = f"{BASE}/results/latch/summary.md"
SEEDS_OUT = f"{BASE}/results/latch/seeds.md"


def load_ranked():
    rows = {}
    with open(RANKED) as f:
        for r in csv.DictReader(f):
            rows[(r["f_hex"], r["g_hex"])] = r
    return rows


def load_cycles():
    """key (f,g,k) -> list of (transient,period,capped)"""
    d = defaultdict(list)
    with open(CYCLES) as f:
        for r in csv.DictReader(f):
            key = (r["f_hex"], r["g_hex"], r["k"])
            d[key].append((int(r["transient"]), int(r["period"]), int(r["capped"])))
    return d


def load_vacuum():
    """key (f,g,k) -> dict qstart -> (status,period); pick best (usable, min period)"""
    d = defaultdict(dict)
    with open(VACUUM) as f:
        for r in csv.DictReader(f):
            key = (r["f_hex"], r["g_hex"], r["k"])
            d[key][r["qstart"]] = (int(r["status"]), int(r["period"]))
    best = {}
    for key, qd in d.items():
        usable = [(qs, st) for qs, (st, per) in qd.items() if st >= 1]
        if usable:
            qs, st = min(usable, key=lambda t: t[1])
            best[key] = (True, qs, st)
        else:
            best[key] = (False, None, None)
    return best


import re

_EX_RE = re.compile(r",(\d+/\d+,\d+/\d+,d=\d+)$")


def _parse_interact_line(line):
    """dynamics.c's interact CSV has two fields (glider_examples,
    example_dependent) that contain un-escaped internal commas, so a plain
    csv split misaligns columns. Parse from both ends instead: the first 7
    fields (f_hex,g_hex,label,k,qstart,vac_period,n_gliders) are comma-free,
    and the trailing example_dependent field matches a known shape."""
    line = line.rstrip("\n")
    left, rest = line.split(",", 6)[:6], line.split(",", 6)[6]
    f_hex, g_hex, label, k, qstart, vac_period = left
    m = _EX_RE.search(rest)
    if m:
        example_dependent = m.group(1)
        rest = rest[: m.start()]
    else:
        example_dependent = ""
        if rest.endswith(","):
            rest = rest[:-1]
    # rest is now: n_gliders,glider_examples,n_interact_tested,n_interact_dependent
    n_gliders, rest2 = rest.split(",", 1)
    n_dependent_str, rest2 = rest2[::-1].split(",", 1)
    n_dependent = n_dependent_str[::-1]
    rest2 = rest2[::-1]
    n_tested_str, glider_examples = rest2[::-1].split(",", 1)
    n_tested = n_tested_str[::-1]
    glider_examples = glider_examples[::-1]
    return {
        "f_hex": f_hex, "g_hex": g_hex, "label": label, "k": k,
        "qstart": qstart, "vac_period": vac_period, "n_gliders": n_gliders,
        "glider_examples": glider_examples, "n_interact_tested": n_tested,
        "n_interact_dependent": n_dependent, "example_dependent": example_dependent,
    }


def load_interact():
    d = {}
    with open(INTERACT) as f:
        header = f.readline()
        assert header.startswith("f_hex"), header
        for line in f:
            if not line.strip():
                continue
            r = _parse_interact_line(line)
            key = (r["f_hex"], r["g_hex"], r["k"])
            d[key] = r
    return d


def main():
    ranked = load_ranked()
    cycles = load_cycles()
    vacuum = load_vacuum()
    interact = load_interact()

    fieldnames = ["f_hex", "g_hex", "cost_f", "cost_g", "cost_total", "class", "bijective",
                  "formula_f", "formula_g", "k",
                  "cyc_median_transient", "cyc_median_period", "cyc_max_period", "cyc_frac_capped",
                  "vac_usable", "vac_qstart", "vac_period",
                  "n_gliders", "glider_examples", "n_interact_tested", "n_interact_dependent",
                  "interact_pass", "example_dependent"]

    out_rows = []
    for (f_hex, g_hex), rr in ranked.items():
        for k in ("2", "3"):
            key = (f_hex, g_hex, k)
            cyc = cycles.get(key, [])
            if cyc:
                transients = [t for t, p, c in cyc]
                periods = [p for t, p, c in cyc]
                capped = [c for t, p, c in cyc]
                med_t = statistics.median(transients)
                med_p = statistics.median(periods)
                max_p = max(periods)
                frac_capped = sum(capped) / len(capped)
            else:
                med_t = med_p = max_p = frac_capped = ""

            vac = vacuum.get(key, (False, None, None))
            iac = interact.get(key, {})
            n_glide = int(iac.get("n_gliders", 0) or 0)
            n_tested = int(iac.get("n_interact_tested", 0) or 0)
            n_dep = int(iac.get("n_interact_dependent", 0) or 0)

            out_rows.append({
                "f_hex": f_hex, "g_hex": g_hex,
                "cost_f": rr["cost_f"], "cost_g": rr["cost_g"], "cost_total": rr["cost_total"],
                "class": rr["class"], "bijective": rr["bijective"],
                "formula_f": rr["formula_f"], "formula_g": rr["formula_g"],
                "k": k,
                "cyc_median_transient": med_t, "cyc_median_period": med_p,
                "cyc_max_period": max_p, "cyc_frac_capped": frac_capped,
                "vac_usable": vac[0], "vac_qstart": vac[1], "vac_period": vac[2],
                "n_gliders": n_glide, "glider_examples": iac.get("glider_examples", ""),
                "n_interact_tested": n_tested, "n_interact_dependent": n_dep,
                "interact_pass": n_dep > 0,
                "example_dependent": iac.get("example_dependent", ""),
            })

    with open(DYNAMICS_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {DYNAMICS_OUT} ({len(out_rows)} rows)", file=sys.stderr)

    # ---- candidates passing all three filters ----
    good = [r for r in out_rows if r["vac_usable"] and r["n_gliders"] > 0 and r["interact_pass"]]
    good.sort(key=lambda r: (int(r["cost_total"]), r["f_hex"], r["g_hex"], r["k"]))

    with open(RANKED_FULL) as ff:
        full_rows = list(csv.DictReader(ff))
    cost_counts = defaultdict(int)
    class_counts = defaultdict(int)
    for r in full_rows:
        cost_counts[int(r["cost_total"])] += 1
        class_counts[r["class"]] += 1
    n_bij = sum(1 for r in full_rows if r["bijective"] == "yes")

    with open(SUMMARY_OUT, "w") as f:
        f.write("# Latch-ring dynamics: cheapest pairs with vacuum + glider + interaction\n\n")
        f.write("## Task 1: full ranked.csv (all surviving pairs, cost bound <= 3)\n\n")
        f.write(f"Total surviving pairs: {len(full_rows)} "
                f"({class_counts.get('generic', 0)} generic, {class_counts.get('clock', 0)} clock class). "
                f"Bijective on N=8..12, k=2,3: {n_bij}.\n\n")
        f.write("| cost_total | pairs |\n|---|---|\n")
        for c in sorted(cost_counts):
            f.write(f"| {c} | {cost_counts[c]} |\n")
        f.write("\n## Task 2: the tested subset (results/latch/ranked_top.csv)\n\n")
        f.write(f"Task 2 (cycle stats, vacuum, gliders, pairwise interaction) was run on "
                f"{len(set((r['f_hex'], r['g_hex']) for r in out_rows))} pairs: every pair with "
                f"cost_total<=2 (all {sum(1 for r in full_rows if int(r['cost_total'])<=2)} of them), "
                f"plus a systematic sample of the cost_total==3 pairs (running the full pairwise "
                f"interaction grid on all {cost_counts.get(3,0)} cost-3 pairs would take on the order "
                f"of a day; see sim/latch/build_ranked_top.py).\n\n")
        f.write(f"Total (pair,k) rows evaluated: {len(out_rows)}. ")
        f.write(f"Rows with a usable vacuum: {sum(1 for r in out_rows if r['vac_usable'])}. ")
        f.write(f"...with >=1 glider: {sum(1 for r in out_rows if r['vac_usable'] and r['n_gliders']>0)}. ")
        f.write(f"...and passing the interaction test: {len(good)}.\n\n")
        f.write("| f | g | k | cost | class | bijective | vac period | gliders | glider examples | interact dependent/tested |\n")
        f.write("|---|---|---|------|-------|-----------|-----------|---------|------------------|---------------------------|\n")
        for r in good:
            f.write(f"| {r['f_hex']} | {r['g_hex']} | {r['k']} | {r['cost_total']} | {r['class']} | "
                    f"{r['bijective']} | {r['vac_period']} | {r['n_gliders']} | "
                    f"{r['glider_examples'][:80]} | {r['n_interact_dependent']}/{r['n_interact_tested']} |\n")
        f.write("\nFormulas for the top 10 (by total gate cost):\n\n")
        for r in good[:10]:
            f.write(f"* f={r['f_hex']} g={r['g_hex']} k={r['k']} cost={r['cost_total']}: "
                    f"f = {r['formula_f']}; g = {r['formula_g']}\n")

    print(f"wrote {SUMMARY_OUT} ({len(good)} passing candidates)", file=sys.stderr)

    # ---- seeds.md: spacetime diagrams for the top 5 ----
    with open(SEEDS_OUT, "w") as f:
        f.write("# Seed catalog: gliders and one collision for the top 5 candidates\n\n")
        f.write("`#` = 1, `.` = 0. Each block: seed pattern alone (glider), then one "
                "interacting collision at a chosen separation d.\n\n")
        for r in good[:5]:
            f_hex, g_hex, k = r["f_hex"], r["g_hex"], int(r["k"])
            f_tt, g_tt = int(f_hex, 16), int(g_hex, 16)
            qstart = int(r["vac_qstart"])
            f.write(f"## f={f_hex} g={g_hex} k={k} (cost {r['cost_total']}, class {r['class']})\n\n")
            f.write(f"formula: f = {r['formula_f']}; g = {r['formula_g']}\n\n")

            # parse one glider example "pat/width:t=..,sh=..;"
            ex = r["glider_examples"].split(";")[0]
            pat_w, rest = ex.split(":")
            pat, width = (int(v) for v in pat_w.split("/"))
            f.write(f"### Glider: pattern {pat:0{width}b} (width {width}), {rest}\n\n```\n")
            N = 60
            s = [0] * N
            for i in range(width):
                s[i] = (pat >> i) & 1
            q = qstart
            for t in range(26):
                f.write("".join("#" if b else "." for b in s) + "\n")
                s, q = pass_latch(s, q, k, f_tt, g_tt)
            f.write("```\n\n")

            # one collision: the actual (P,Q,d) triple the interact test flagged as
            # depending on both patterns (not a guess)
            ex = r["example_dependent"]
            if ex:
                pq, qq_, dpart = ex.split(",")
                p_pat, p_w = (int(v) for v in pq.split("/"))
                q_pat, q_w = (int(v) for v in qq_.split("/"))
                d = int(dpart.split("=")[1])
            else:
                p_pat, p_w, q_pat, q_w, d = pat, width, pat, width, 12
            f.write(f"### Collision: pattern {p_pat:0{p_w}b} at position 0, "
                    f"pattern {q_pat:0{q_w}b} at position {d} "
                    f"(flagged by the interact test as depending on both)\n\n```\n")
            s = [0] * N
            for i in range(p_w):
                s[i] = (p_pat >> i) & 1
            for i in range(q_w):
                s[(d + i) % N] |= (q_pat >> i) & 1
            q = qstart
            for t in range(26):
                f.write("".join("#" if b else "." for b in s) + "\n")
                s, q = pass_latch(s, q, k, f_tt, g_tt)
            f.write("```\n\n")

    print(f"wrote {SEEDS_OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
