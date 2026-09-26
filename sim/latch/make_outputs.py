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
RANKED = f"{BASE}/results/latch/ranked.csv"
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


def load_interact():
    d = {}
    with open(INTERACT) as f:
        for r in csv.DictReader(f):
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
                  "interact_pass"]

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
            })

    with open(DYNAMICS_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {DYNAMICS_OUT} ({len(out_rows)} rows)", file=sys.stderr)

    # ---- candidates passing all three filters ----
    good = [r for r in out_rows if r["vac_usable"] and r["n_gliders"] > 0 and r["interact_pass"]]
    good.sort(key=lambda r: (int(r["cost_total"]), r["f_hex"], r["g_hex"], r["k"]))

    with open(SUMMARY_OUT, "w") as f:
        f.write("# Latch-ring dynamics: cheapest pairs with vacuum + glider + interaction\n\n")
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

            # one collision: place the same pattern at 0 and at d=12 (or first tested d)
            d = 12
            f.write(f"### Collision: same pattern at positions 0 and {d}\n\n```\n")
            s = [0] * N
            for i in range(width):
                s[i] = (pat >> i) & 1
                s[(d + i) % N] = (pat >> i) & 1
            q = qstart
            for t in range(26):
                f.write("".join("#" if b else "." for b in s) + "\n")
                s, q = pass_latch(s, q, k, f_tt, g_tt)
            f.write("```\n\n")

    print(f"wrote {SEEDS_OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
