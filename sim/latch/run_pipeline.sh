#!/bin/bash
# Full task-1/task-2 pipeline. Run from sim/latch/. Usage: ./run_pipeline.sh [bound]
set -e
cd "$(dirname "$0")"
BOUND="${1:-4}"

echo "== building C tools ==" >&2
gcc -O3 -o cost cost.c
gcc -O2 -o dynamics dynamics.c
gcc -O3 -o bij bij.c

echo "== task 1: ranked.csv (bound<=$BOUND) ==" >&2
python3 build_ranked.py "$BOUND"

echo "== bijectivity (C, exhaustive N=8..12 k=2,3) ==" >&2
./bij pairs.txt > bij_out.txt
python3 merge_bij.py

echo "== task 2: cycle statistics ==" >&2
./dynamics cycles pairs.txt > cycles.csv

echo "== task 2: vacuum classification ==" >&2
./dynamics vacuum pairs.txt > vacuum.csv

echo "== task 2: interaction + gliders ==" >&2
./dynamics interact pairs.txt vacuum.csv > interact.csv

echo "== combining into dynamics.csv, summary.md, seeds.md ==" >&2
python3 make_outputs.py

echo "== done ==" >&2
