# Plan: sequential NAND ring (and Toffoli sibling)

## Results (after the sweep)

* **V1 confirmed.** Seeds agreeing on cells 0..k−1 are identical after one pass; ring transient ≤ 3 and period ≤ 9 for k = 2..5, N = 16..64. Lemma A holds.
* **V2 corrected.** Write-between rules collapse within 2 passes to a helical rotation e_τ = e_{τ−M} with M = L + p (L = N − (b−c), p = c − a), exact at the median in all 130 (geometry, N) cells. The "L + 1" in Lemma C below is correct only for p = 1. Some seeds fall into even smaller cycles. In ring coordinates this appears as a kink walking around the ring, not a uniform shift.
* **V3 qualitatively confirmed.** Runs translate and never interact. "Isolated ones die" holds only in one of the two phases of the period-2 background; a single cell in the other phase is a width-2 run and translates.
* **R3 is dead.** 5197 of 5200 seeds reach e_τ = e_{τ−M} within 7 passes, with either M = N + k − 1 (helical rotation) or M a small constant independent of N (the Lemma A register cycle, which is an exact solution of R3 because the target read becomes redundant). The remaining 3 have period 115 passes. "Periods grow with N" in S1 was a bad liveness test: a rotation passes it. Use the helix-period test (`sim/nand/helix.py`) as the liveness criterion from now on.
* **Consequence.** Every tested one-NAND drum with a fixed rule dies, with or without the target diode. Common mechanism: the only old value the gate sees enters once per step through a NAND with recent outputs, and the output sequence locks onto a shift of itself. S4 (a read strictly ahead of the write) is the same shape and is expected to die the same way; not run.

## Next candidate: NAND drum with a program track

Add a program track p (free memory) read at each step and gate the write: s[i+k] ← NAND(s[i], s[i+1]) if p[τ mod P] else unchanged. One NAND transistor; the program bit gates the write strobe (diode AND, or one transistor). In grid form, with row t = pass and column c = cell:

    v(t, c) = en(t, c) ? NAND(v(t, c−k), v(t, c−k+1)) : v(t−1, c),    en(t, c) = p((tN + c) mod P).

If P divides N the enable pattern is the same every pass, unwritten cells are frozen constants, and Lemma A applies again: dead. If N ≡ d (mod P) with d ≠ 0 the pattern slides d cells per pass, so a cell written in one pass can hold its value in later passes. The grid is then a circuit with a space-time periodic layout, in which signals move down (copy) and right (NAND chains). A frame drifting right at the slide speed gives both directions, which is what a cellular automaton step needs. Expected universal by construction (simulate a Turing machine encoded as a CA with a blank, stationary background so the helical seam is harmless). Not yet built. Handover to be written.

Status of the Toffoli ring: see REPORT.md (open for all k; k=2 conjectured not universal). Everything below reuses one piece of machinery from it: **write the sweep as a recurrence on the helix** (global step τ = tN + i, e_τ = value written at step τ). The only thing that matters about a rule is the *age* of each value it reads, i.e. how many steps ago the read cell was last written.

## 1. The NAND ring as specified is not universal, for every k and every N

Rule: s[i+k] ← NAND(s[i], s[i+1]), k ≥ 2, overwrite, sequential.

**Lemma A (the ring is never read).** At step τ the cell s[τ] was last written at step τ−k and s[τ+1] at step τ−k+1 (both in the current pass, or the tail of the previous one; the next write to either cell is N steps later). So

    e_τ = NAND(e_{τ−k}, e_{τ−k+1})     for all τ ≥ 0.

This is a recurrence of order k. The initial condition is e_{−k..−1} = s₀[0..k−1]. Nothing else about s₀ is ever read: cell j ≥ k is overwritten at step j−k before its first read at step j−1. N does not appear.

**Consequences.**
1. The orbit is that of a k-bit register with feedback "NAND of the two oldest bits". State space 2^k. Transient and period ≤ 2^k regardless of N. gcd(N,k) and N mod k are irrelevant; N is a display length.
2. Not universal under any encoding: the system cannot even count to 2^k + 1.
3. The same holds for **every** overwrite rule s[i+k] ← f(s[i], s[i+1]) with k ≥ 2 and any f: the gate is irrelevant, the tap geometry kills it. The "already settled" list in the problem statement analyses gates; the obstruction is the taps.
4. The Toffoli ring survives only because XOR-into-target *reads the target* (age N), which puts the N-delay term into the recurrence.

**Lemma B (complete taxonomy of one-NAND rings).** Reads at i+a, i+b (a < b), overwrite at i+c, any c. Let d = b − a. The two ages are (c−a, c−b) reduced mod N. Cases:

| geometry | recurrence (row form) | fate |
|---|---|---|
| c > b (write ahead of both reads; the spec) | e_τ = NAND(e_{τ−(c−a)}, e_{τ−(c−b)}) | (c−a)-bit register, period ≤ 2^{c−a}, N irrelevant |
| c < a (write behind both), or c = a | y[j] = NAND(x[j−d], x[j]) on rows of length N−(b−c) (synchronous) | its square is x''[j] = x[j−d] ∧ (x[j−2d] ∨ x[j]): monotone; runs of ≥2 (within a residue class mod d) translate right by d every two passes, isolated ones die, runs never interact. Class 2. |
| a < c ≤ b (write between the reads, or at the far read) | y[j] = NAND(y[j−p], x[j]), p = c−a, rows of length L = N−(b−c) | collapses to a rigid rotation within 2 passes (Lemma C) |

**Lemma C (write-between collapses).** Take p = 1 (p > 1 is p interleaved copies braided at the seam; same argument per chain). y[j] = 1 if x[j] = 0, y[j] = ¬y[j−1] if x[j] = 1. So (i) after one pass the row has no two adjacent zeros; (ii) on such a row, each maximal run 1^r followed by a 0 becomes alt(r)·1 with alt(r) = 0101…, hence after two passes every run of ones has length 1 or 2 and zeros are isolated; (iii) on such a row, `1 0 → 0 1` and `1 1 0 → 0 1 1`: the row shifts right by one cell per pass. On the helix: e_τ = e_{τ−L−1} for τ ≥ 2L. Period ≤ L+1 ≈ N, transient ≤ 2 passes, no interaction ever.

NOR is conjugate to NAND by complementing all cells, so the taxonomy covers NOR. One-input rules and AND/OR/XOR overwrite are dead by the problem's own list. **Verdict: no one-transistor two-read overwrite ring is universal, in any tap geometry, for any k or N.**

## 2. What the cheap models should do (verification, not exploration)

Each is a few lines against `sim/ring.py`-style code. Expected result stated; a deviation would mean a lemma is wrong.

* **V1** NAND-ahead, k = 2..5, N = 16..64: two seeds agreeing on cells 0..k−1 give identical rings after pass 1. Ring-state period and transient ≤ 2^k for every N. Enumerate the 2^k-state register for k = 2..8 and report its cycle structure (this is the entire dynamics).
* **V2** Write-between rule s[i+1] ← NAND(s[i], s[i+2]) and the general (a,b,c) with a < c ≤ b, N = 16..64: every orbit is a rotation by one cell per pass (in the row frame of length N−(b−c)) from pass 2 on.
* **V3** Write-behind rule s[i−1] ← NAND(s[i], s[i+1]) and s[i] ← NAND(s[i], s[i+1]): runs preserved and translating, singletons dead, no run ever changes length.
* Do **not** run the transient/attractor/particle sweep of the original route 1 for the NAND-ahead rule; Lemma A makes it a sweep of a k-bit register.

## 3. Smallest modification, and what to sweep for it

Necessary condition for the ring to be memory at all: some read must return a value of age ≈ N, i.e. a read tap at or ahead of the write tap. With two reads and overwrite, Lemma B says every such geometry collapses. So the fix needs either the XOR (Toffoli: reads the target, but is not one transistor) or a **third input to the NAND**, and the natural third input is the target itself:

    R3(k):  s[i+k] ← NAND(s[i], s[i+1], s[i+k])         one transistor, three diodes

Row form: y[j] = ¬x[j] where the new pair (y[j−k], y[j−k+1]) is 11, and y[j] = 1 elsewhere. It reads the target (age N), is non-monotone, and erases garbage where the pair is not 11. Not dead by any lemma above (all-ones is not a fixed point: k=2 gives (011)*, k=3 gives (00111)*). Its universality is open and it is the candidate for the build. Cost of the fix: one diode, zero transistors.

Sweep for the cheap models (this is the empirical work that is actually warranted):

* **S1** R3(k), k = 2..5, N = 16..64, 200 random seeds per (N,k): transient length, cycle length, fraction of seeds ending in a cycle of length ≤ 2. Fatal signs: cycle lengths that do not grow with N, or all orbits dying in O(N) passes.
* **S2** Backgrounds ("ether"): spatially periodic rows with period ≤ 12 that are temporally periodic under R3(k), with the window-map attractor analysis from `sim/robust_bg.py` (single attractor = robust). Report shift per pass.
* **S3** Defects on each robust background: insert every perturbation of width ≤ 4, evolve 200 passes in the co-moving frame, keep anything that stays localized. These are the particle candidates. Pairwise collisions of survivors.
* **S4** Same three items for the variants s[i+k] ← NAND(s[i], s[i+1], s[i+m]) with m > k (a read strictly ahead of the write, age N−(m−k)), k = 2,3, m = k+1..k+3. Only if S1–S3 for R3 look dead.
* **S5** Toffoli, low priority: nothing new needed for the verdict. If spare capacity: the block-closure search described in REPORT.md §4 (block width 2k..4k, classes closed under all block maps).

Output format for all sweeps: one CSV per rule with columns (k, N, seed, transient, period, final_density), plus spacetime text diagrams for anything localized.

## 4. Theory queue (mine, after S1–S3 come back)

* Helix recurrence and window lemma for R3: e_τ = ¬(e_{τ−k} ∧ e_{τ−k+1} ∧ e_{τ−N}); which window states survive a run of ones, of zeros, of the background; the analogue of the trail lemma (a sweep that crosses k cells writing 1s has forgotten its entry state).
* Whether R3 has a vacuum theorem. Overwrite means no triangular structure, so gliders are not excluded a priori.
* If S3 finds particles: gadget requirements for a BCT relay, with the garbage advantage made explicit (a region set to 1 by a non-firing pair is clean).

## 5. Plaque

As specified (two reads at i, i+1, one NAND, write at i+k ≥ 2): the plaque may claim "a k-bit nonlinear feedback shift register with an N-cell display". Not a computer, and the ring is not memory: its contents are never read. With the third diode (R3): "one-transistor ring computer, memory excluded, universality open". With the XOR sibling (Toffoli): "reversible one-gate ring, 2^N states, universality open; for k=2 evidence says no". None of the three can currently carry "universal".
