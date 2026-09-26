#!/bin/bash
# Full task-1/task-2 pipeline. Run from sim/latch/. Usage: ./run_pipeline.sh [bound] [n_parallel]
#
# bound: task-1 pair-cost bound for ranked.csv (default 3; the task spec's
#   procedure -- start at 4, lower to 3 if >~200k survive, raise to 5 if
#   <1000 -- gives 3 for this gate set: bound 4 gives 694059 pairs, bound 3
#   gives 122173, which is <=200k so it stands).
# n_parallel: how many chunks to split pairs_top.txt into for the (heavy)
#   interact step. Default 4 (this machine has 4 cores). The interact grid
#   over ALL 122173 ranked.csv pairs would take on the order of a day, so
#   task 2 (cycles/vacuum/interact/gliders) runs on results/latch/ranked_top.csv
#   instead: every pair with cost_total<=2, plus a systematic sample of the
#   cost_total==3 pairs (see build_ranked_top.py).
set -e
cd "$(dirname "$0")"
BOUND="${1:-3}"
NPAR="${2:-4}"

echo "== building C tools ==" >&2
gcc -O3 -o cost cost.c
gcc -O2 -o dynamics dynamics.c
gcc -O3 -o bij bij.c

echo "== gate-cost table for all 65536 4-input functions (cost.c) ==" >&2
./cost 5 cost_table.txt 2>cost_run.log   # exact for levels 0-3, time-budgeted best-effort for 4-5

echo "== task 1: ranked.csv (bound<=$BOUND), all surviving (f,g) pairs ==" >&2
python3 build_ranked.py "$BOUND"

echo "== bijectivity of the full ranked.csv (C, exhaustive N=8..12, k=2,3) ==" >&2
./bij pairs.txt > bij_out.txt
python3 merge_bij.py

echo "== task-2 subset: ranked_top.csv ==" >&2
python3 build_ranked_top.py

echo "== task 2: cycle statistics (N=16,20,24; 20 seeds; cap 1e6 passes) ==" >&2
./dynamics cycles pairs_top.txt > cycles.csv

echo "== task 2: vacuum classification ==" >&2
./dynamics vacuum pairs_top.txt > vacuum.csv

echo "== task 2: interaction + gliders (parallel x$NPAR) ==" >&2
split -n l/$NPAR --numeric-suffixes=1 pairs_top.txt pairs_top_part_
pids=()
for part in pairs_top_part_*; do
  ./dynamics interact "$part" vacuum.csv > "interact_${part#pairs_top_part_}.csv" 2>"interact_${part#pairs_top_part_}.log" &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
{ head -1 "$(ls interact_*.csv | head -1)"; for f in interact_*.csv; do tail -n +2 "$f"; done; } > interact.csv

echo "== combining into dynamics.csv, summary.md, seeds.md ==" >&2
python3 make_outputs.py

echo "== done ==" >&2
