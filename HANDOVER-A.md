# Handover A: single-drum sweep with one bit of head state

Follows REPORT.md. Read §1 (reformulations), §4 (what a construction must do), §6 (the two architectural obstructions).

## 0. Model, pinned to the drum

Transducer form (REPORT Thm 3). The step writing ring cell j reads x = old s[j], the two control taps a = y[j−k], b = y[j−k+1] (already written this pass, or the tail of the last), and the latch q. It writes y = f(q, x, a, b) and sets q' = g(q, x, a, b). The latch crosses the pass boundary. The drum reads two of the last k written bits, not all k; more taps means more diodes, count them if proposed. So (f, g) : {0,1}^4 → {0,1}^2 is the finite object: 2^32 pairs before symmetry, for each k.

Helix form (REPORT Thm 1): with e_p the value written at global step p and q_p the latch,

    e_p = f(q_p, e_{p−N}, e_{p−k}, e_{p−k+1}),     q_{p+1} = g(q_p, e_{p−N}, e_{p−k}, e_{p−k+1}).

Toffoli is f = x ⊕ ab, q unused. NAND-ahead is f = ¬(ab), x and q unused, dead (PLAN.md §1).

## 1. Corrections to the statement

**Bijectivity does not prevent progress.** "If every step is bijective the orbit is a cycle and progress is impossible" is false. It traces to REPORT §4 item 1, now corrected. Reversible machines are universal (Bennett 1973; Morita's reversible CA), and on a finite ring every orbit of any map is eventually periodic, so "halting" is always "reaching a designated pattern". What a bijective (f, g) excludes is exact step-for-step emulation of an irreversible machine; the target must then be reversible and the overhead is Bennett's. Do not filter on bijectivity. Record it as a property of each candidate, because it decides the target.

**Confirming REPORT §6 is one line and proves nothing.** f = q, g = x is a one-cell delay: the pass is a rotation by one cell, every pattern is a glider and q carries a bit silently across any stretch. The latch removes both obstructions by construction. The meaningful precondition is interaction: two structures whose collision outcome depends on both, with f nonlinear. Ask for that before any construction.

**Rule 110 is the wrong target.**
* State count: Rule 110 needs two carried old bits, not three. Write F(x_{j−2}, x_{j−1}, x_j) into cell j (the configuration drifts one cell per pass); the head carries x_{j−2}, x_{j−1} and reads x_j. One latch carries one of them; the taps see written values, which are F-values, not old values.
* Seam: this drift gives e_p = F(e_{p−M−1}, e_{p−M}, e_{p−M+1}) with M = N + 1, i.e. Rule 110 spacetimes invariant under one generation combined with a shift by M. A pure-ether run needs that translation in the ether's lattice. Rule 110's ether repeats only after 7 generations up to translation (verify), so no lattice vector has time component 1 and the seam is a permanent defect every glider must cross. Cook's construction does not provide that.

## 2. Recommended route: direct Turing-machine simulation, one TM step per pass

A one-way transducer with a one-cell delay buffer performs one TM step per sweep. The background drifts by one cell per pass. A TM left move becomes "no drift" for the head mark, a right move "drift by two". The vacuum (all zeros, blank = 0) is seam-consistent, so the helical seam costs nothing. This gives universality with polynomial overhead (O(N) ticks per TM step, N = O(TM space)) and a large gate. The research question is how small (f, g) can be.

Structural fact the executor should use: if g = x (the latch is a delay) then q_p = e_{p−N−1} and

    e_p = f(e_{p−N−1}, e_{p−N}, e_{p−k}, e_{p−k+1}):

two old values (left neighbour and self, synchronous) and two new values (sequential, k back). In a region where f = q (pure drift), the new values are themselves drifted old values, so the taps read old values at offsets −k−1, −k. A drifting region is a synchronous window {−k−1, −k, −1, 0} on old values. The whole design space is how f departs from q on non-background inputs.

Cases that reduce to known results and can be dropped:
* f independent of q: back to REPORT (the Toffoli family) or to PLAN.md §1 (overwrite families).
* f independent of a and b, g = x: e_p = F(e_{p−N−1}, e_{p−N}), a binary radius-½ synchronous CA. None of the 16 is universal.
* g independent of x, a, b: q is a clock of period ≤ 2, i.e. a phase bit alternating two rules along the helix. Keep it as a separate class. It is legitimate here, unlike in Handover B, because it is real head state.

## 3. Tasks for the cheap models

1. Enumerate (f, g) over 4 inputs mod the symmetries (complement of the tape where the rule allows it, complement of q). Drop the reduced cases above. Rank survivors by DTL cost (count gates and transistors for f and g; the flip-flop is separate).
2. For the cheapest few thousand: cycle statistics at N = 16..24 for k = 2, 3, and the interaction test. Place two isolated non-background patterns on the drifting vacuum at varying separations and check whether the outcome after collision depends on both. Report which (f, g) pass.
3. For survivors: gliders on the vacuum (REPORT's no-glider theorem no longer holds), their speeds, pairwise collision tables.

## 4. Theory queue (after 3.1–3.2 come back)

* For the passing (f, g): which inputs occur in the background and which only at structures. Decide whether a block code can carry a TM mark plus a state of s bits. State lives in written cells near the mark, read through the taps, since the latch is spent on the drift when g = x.
* If the latch cannot serve both drift and state: minimal k and minimal extra state, stated as an obstruction.
* Reversible candidates: target a small reversible universal machine instead.

## 5. Deliverables

Minimal (f, g, k) with a construction and proof, or a precise obstruction. DTL gate count including the latch. A seed catalog on the drifting vacuum: a glider, a collision whose result depends on both inputs, and the TM mark moving left and right.

If only one handover runs, run B: a finite search with a usable answer either way. A has a finite core (§3) but no finite answer.
