# toffoli-ring

Is the sequential Toffoli ring `s[i+k] ^= s[i] & s[i+1]` (i = 0..N-1, sequential, cyclic) computationally universal?

* `STATUS.md` — one-page verdicts and the working two-instruction machine.
* `REPORT.md` — verdicts per k, theorems, empirical results, what a proof would need, and the "smallest change" discussion.
* `PLAN.md` — NAND ring: dead in every one-NAND tap geometry; the three-input fix and its sweep tasks.
* `HANDOVER-A.md` — drum with one bit of head state.
* `HANDOVER-B.md` — two-instruction pointer machines.
* `HANDOVER-D.md` — the 4-, 8-, 16- and 32-transistor computers.
* `sim/` — simulator (`ring.py`), exact cycle enumerator (`cycles.c`), sampled periods (`sample.c`), word catalogs, background search, seed patterns.
* `results/` — raw sweep output, word classifications, `seeds.md` (spacetime diagrams of every structure mentioned).

Short version: the pass map is exactly the nonlinear feedback shift register `e_t = e_{t-N} ^ e_{t-k} e_{t-k+1}`, and its inverse is the one-way cellular automaton `x[j] = y[j] ^ y[j-k] y[j-k+1]` (rule 106 for k=2). In a zero background the dynamics is a triangular map: no pattern moves, every bounded pattern has period a power of two, and the only long-range signal is a flood that overwrites what it crosses. Universality is open for every k; for k=2 the evidence points to "no".
