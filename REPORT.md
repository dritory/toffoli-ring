# Universality of the sequential Toffoli ring

Rule: cyclic string `s` of `N` bits, offset `k >= 2`, one pass applies for `i = 0..N-1` in order

    s[i+k] ^= s[i] & s[i+1]        (indices mod N)

with each write visible to later steps of the same pass. Pass map `T_{N,k}`.

## 0. Verdict

| k | verdict | what is settled |
|---|---------|-----------------|
| 2 | **open**; conjecture: not universal | Closed form of the pass (Thm 3). Every vacuum pattern with an adjacent pair eventually floods (Thm 10). No local structures on the ring: at N=26 all 6.7e7 non-fixed states lie on 11 cycles. Behaves like a near-maximal-period NLFSR. |
| 3, 4, 5 | **open** | Sparse (vacuum) structures exist but are all odometers: period a power of two or flood (Thm 5). Robust traveling backgrounds exist (Sec. 3.5). No universality construction found; the obstacles are structural, not a proof. |
| gcd(N,k) | irrelevant | The read pair `(i, i+1)` couples every residue class, and no `(N,k)` shows a block decomposition (Sec. 3.1). |

What is proved (Sec. 1–2) closes both routes suggested in the problem statement, for every k:

* **Route 1 (particles in a zero background) is impossible.** In vacuum the pass map is a triangular map over GF(2). The leftmost 1 of any pattern never moves, every bounded pattern has period a power of two, and nothing translates. There are no gliders, so there are no glider collisions (Thm 5).
* **Route 2 as stated (sparse BCT encoding with zeros as insulation) is impossible.** Zeros do not insulate a signal, they kill it: the sweep's only memory is its own last `k` outputs, so any window other than `1^k` dies within `(k-1)(k-2)+k` zeros (Thm 6), and `1^k` is the flood, which overwrites every zero it crosses. Any signal that crosses `k` unchanged cells is erased (Thm 7). So no information can be routed through insulation without writing on it.

What is *not* proved is non-universality. The system has giant irregular cycles (Sec. 3.1), unbounded rightward information speed, and dense periodic backgrounds with defects, so a construction on a non-zero background using the ring wrap is not excluded. Section 4 states exactly what such a construction has to do and why my attempts fail. Section 6 addresses the "smallest change" deliverable honestly: since there is no proven obstruction there is no *necessary* change, but the two constraints that are proved (no vacuum gliders, no silent signals) hold for **every** sequential write-ahead rule regardless of gate, so changing the gate alone (three controls, other AND positions) does not remove them.

## 1. Exact reformulations

**Theorem 1 (NLFSR).** Let `e_τ` be the value written at global step `τ = tN + i` (pass `t`, step `i`), i.e. the new value of cell `(i+k) mod N`. Then

    e_τ = e_{τ-N} XOR (e_{τ-k} AND e_{τ-k+1}).

*Proof.* At step `τ` the target `s[τ+k]` was last written at step `τ-N`; the controls `s[τ]`, `s[τ+1]` were last written at steps `τ-k`, `τ-k+1`. ∎

So `T_{N,k}` is `N` clockings of the Fibonacci nonlinear feedback shift register of length `N` with feedback `x_0 ⊕ x_{N-k} x_{N-k+1}`. The initial register is `s_0` with cell `j` at delay `N-(j-k)`. Verified against the literal rule on 2000 random rings (`sim/ring.py`).

**Theorem 2 (inverse is a one-way synchronous CA).** Write pass `t` as row `x` and pass `t+1` as row `y`, indexed so that `y[j] = e_{tN+j}`. Then

    x[j] = y[j] XOR y[j-k] y[j-k+1]                (helical: y[negative] := x[N + negative])

which is the synchronous one-way cellular automaton `G_k(y)[j] = y[j] ⊕ y[j-k] y[j-k+1]`, except at the `k` seam cells. For `k = 2`, `G_2` is elementary rule 106 (`c ⊕ ab`). `G_k` is right-permutive (bijective in `y[j]`), surjective, and not injective on the line (`G_k(1^Z) = G_k(0^Z) = 0`); the sequential pass is the bijective helical inverse. Consequently: **a forward orbit of the Toffoli ring is a backward orbit of the rule-106 family, read helically.** Information moves rightward at unbounded speed under `T` and leftward at speed ≤ k under `G`; under `T` nothing moves left except through the pass boundary.

**Theorem 3 (sweeping head).** Equivalently, the pass is a finite-state transducer sweeping the ring once: state = the last `k` bits written, `w = (w_1..w_k)`; on reading `x` it writes `y = x ⊕ w_1 w_2` and shifts `y` in. The state at the start of a pass is the tail of the previous pass (helix). Its power is fixed: `t` passes are computed by a `2^{kt}`-state one-way automaton, so anything the ring does in `O(log N)` passes is LOGSPACE-computable, and a universality construction must use `ω(log N)` passes.

For `k = 2` the transducer has three reachable states and a closed form (verified on 20000 random rings):

> copy input to output; as soon as the output ends in `11`, complement the input until the next input `1`, which is written as `0`; then resume copying.

So one k=2 pass rewrites every phrase `11 0^m 1` into `11 1^m 0` and copies everything else; a run `1^a` entered in copy mode becomes `(110)^{⌊a/3⌋} 1^{a mod 3}`.

## 2. Structure theorems

**Theorem 4 (fixed points).** `s` is fixed iff no two cyclically adjacent cells are both 1. Number of fixed points = Lucas number `L_N` (checked for all `N ≤ 26`, all `k`). Every gate is inert iff there is no adjacent pair; conversely the first adjacent pair (in pass order) fires and, since the pass is a bijection, the result differs from `s`. ∎

**Theorem 5 (vacuum theorem).** Consider a finite pattern on a ring long enough that the last `k` cells stay 0 (no wrap). Then the pass map restricted to any prefix `[0, j)` is a bijection of `{0,1}^j` of the form `x_j ← x_j ⊕ f_j(x_{<j})` (triangular). Hence:

1. the leftmost 1 never changes (pinned left edge);
2. the prefix `[0, j)` is a closed subsystem whose orbit has period dividing `2^j` (triangular maps form a 2-group, the Sylow 2-subgroup of `S_{2^j}`);
3. a bounded pattern has period a power of two; an unbounded one is an odometer whose right edge grows or a flood;
4. no pattern translates: there are no gliders in vacuum, for any `k`, and no glider collisions.

The same proof applies to every rule of the form `s[i+k] ^= g(s[i], s[i+1], ...)` with reads behind the write and `g(0,...,0) = 0`: the vacuum theorem is a property of the sweep architecture, not of the Toffoli gate. Checked numerically: all 512 (k=3), 512 (k=4), 512 (k=5) words of length ≤ 10 are periodic with period a power of two (up to 32 for length ≤ 7; 128 appears for longer gadgets, Sec. 3.3) or flood; no word grows at a finite speed (`results/words_long.txt`).

**Theorem 6 (window lemma).** On zero input the window evolves by `y_n = y_{n-k} y_{n-k+1}`. A single zero at position `m` forces zeros at `m + a(k-1) + bk` for all `a, b ≥ 0`, hence at every position `≥ m + (k-1)(k-2)`; so every window containing a 0 becomes `0^k` within `(k-1)(k-2)+k` cells (tight: 2, 5, 10, 17, 26 for k = 2..6, `results`), and `1^k` is the unique window that survives. `1^k` converts every zero it meets into a 1 (the **flood**). Meeting a 1 it writes 0, becomes `1^{k-1}0`, and the tail `1 0^{k-2} 0...` is XORed into the following cells: a flood deletes the first 1 it meets and complements the cell after it (for k=3: `...0001000` → `...1110100`).

**Theorem 7 (trail lemma; no silent signals).** If the sweep crosses `m ≥ k` consecutive cells without changing them (`y = x` there), its window on exit is the last `k` bits of `x`, independent of its window on entry. So information can cross a stretch of `k` cells only by modifying it. Every long-range signal leaves a trail, and the flood's trail is a solid run of ones ("ash"). Again architectural: the head's only memory is what it just wrote.

**Theorem 8 (ash is alive).** For k=3 a solid run `1^L` becomes `(11100)^{L/5}` plus a remainder in one pass; the remainder's window is `1^3` when `L ≡ 3 (mod 5)`, so the ash re-floods. Solid runs are periodic with period 8, 32, 128 or flood to infinity depending on `L` (`results`, Sec. 3.4). The block `1^k` isolated in vacuum is a periodic **flood emitter**.

**Theorem 9 (no decomposition, gcd irrelevant).** The control pair `(i, i+1)` couples cells of every residue class mod any `d`, so `T_{N,k}` is never a product over residue classes. The cycle data show single cycles covering 46–83 % of all non-fixed states for k=2 (N=18..26) and up to 46 % for k=3 (N=23), which excludes any product structure on disjoint cell subsets.

**Theorem 10 (k=2 flammability; verified, not proved).** For k=2 every vacuum word of length ≤ 14 that contains an adjacent pair floods to infinity, the slowest after 97 passes (`##..........##`; 7815 words, `results/k2_flammability.txt`). Mechanism (from Thm 3): the pair floods the gap to the next 1, deletes that 1, and the ash cycles back to a pair; each cycle consumes one stopper, and when none remains the flood is unbounded. So for k=2 no sparse encoding is stable in vacuum at all.

## 3. Empirical results

Code: `sim/` (Python reference simulator, C enumerators). Raw data: `results/`.

### 3.1 Exact cycle structure, N = 6..26, k = 2..5 (`results/cycles_exhaustive.txt`)

Selected rows (nontrivial cycles = cycles of length > 1; fraction = longest cycle / non-fixed states):

| N | k | nontrivial cycles | longest cycle | fraction |
|---|---|---|---|---|
| 20 | 2 | 63 | 190179 | 0.18 |
| 20 | 3 | 80781 | 156773 | 0.15 |
| 24 | 2 | 64 | 3196283 | 0.19 |
| 24 | 3 | 997356 | 5626499 | 0.34 |
| 25 | 2 | 53 | 27819033 | 0.83 |
| 25 | 3 | 1866697 | 11561239 | 0.35 |
| 26 | 2 | 11 | 30587623 | 0.46 |
| 26 | 3 | 3496893 | 6963770 | 0.10 |
| 26 | 4 | 4920391 | 5958715 | 0.09 |
| 26 | 5 | 4945341 | 15780797 | 0.24 |

Reading:

* **k=2 looks like a random permutation on the non-fixed states.** A random permutation of `M = 6.7e7` points has about `ln M ≈ 18` cycles and a longest cycle of about `0.62 M`; k=2 has 11 cycles and `0.46 M`. Its shortest nontrivial periods (21, 227, 3177 at N=26; 199 at N=18) are each realised by one or two cycles. There are no small oscillators.
* **k ≥ 3 has millions of short cycles**, almost all with period 2, 4, 8, 16, 32, 64: these are the vacuum odometers of Thm 5 placed on the ring. Odd periods are rare (k=3, N=26: one cycle of period 7, 52 of period 12).
* Longest cycles grow roughly like `2^N` with large fluctuations; nothing suggests a polynomial bound.

Sampled periods for larger N (`results/periods_sampled.txt`, Brent on random states): k=2 gives periods `1.1e8` (N=28) and `4.8e8` (N=32), a constant fraction of `2^N`; k=3..5 give typical periods around `2^{10}`–`2^{16}` (geometric mean over six random states) with maxima `2.6e7`–`4.2e8`.

### 3.2 Isolated words, all k (`sim/words.py`, `sim/growth.py`)

All words of length ≤ 10: periodic with 2-power period, or flood (some after transients of up to 38 passes: `####..####`, k=3). No finite-speed growth. For k=2 with length ≤ 7 the only non-flooding words are the fixed points; with stoppers (Thm 10) the pair survives a few dozen passes and then floods.

### 3.3 Floods, stoppers, counters (`results/seeds.md` §3–5)

`1^k 0^m 1` in vacuum, k=3: period 8 for m ≤ 3, 32 for 5 ≤ m ≤ 13 (m ≠ 9), 128 at m = 15; m = 4, 9, 14 destroy the stopper and flood to infinity. Inside a period the stopper drifts right one cell per emitter cycle and the emitter's period doubles as the gap grows. These are odometers, the only "computation" found in vacuum.

### 3.4 Solid runs, k=3

`1^L`: period 8 (L = 4, 6), 32 (L = 7, 9, 11, 12, 16), 128 (L = 17, 19, 21, 22), > 3000 (L = 23); L = 3, 5, 8, 10, 13, 14, 15, 18, 20, 24 flood to infinity, some only after 8–64 passes.

### 3.5 Traveling backgrounds (`sim/explore.py travel`, `sim/robust_bg.py`)

Bi-infinite p-periodic configurations `x` with `T(x) = shift_v(x)` exist for every k (k=2: p=4 v=1, p=9 v=5; k=3: p=4 v=3, p=7 v=2, p=9 v=3; k=4: p=8 v=1, p=9 v=3, p=10 v=3; k=5: p=7 v=5, p=8 v=7). Most are fragile: the window map over one period has several attractors, and the seam or any defect knocks the row into a different one (`.###` for k=3 becomes the period-8 `#..#.###`). Robust ones (single attractor, reached from the zero window in one period):

| k | p | v | pattern |
|---|---|---|---|
| 2 | 9 | 5 | `..####.##` |
| 3 | 10 | 5 | `...##.#.##` |
| 3 | 12 | 6 | `....##.#..##` |
| 4 | 12 | 6 | `....##..#.##` |

The three with `v = p/2` are temporal period-2 oscillations, not conveyors with a direction. The k=2 one has temporal period 9.

### 3.6 Dense random rings

No visible local structure for k=2 or k=3 (`results/seeds.md` §7).

## 4. What a universality proof must do, and why mine do not close

Reduce to the sweeping head (Thm 3). Group the ring into blocks. The head enters block `j` in a window that is a function of block `j-1`'s **new** content, transforms block `j` bijectively (for a fixed entering window `u`, `x ↦ y` is a bijection of `{0,1}^w`), and leaves. So on blocks the ring is exactly a **sequential one-way CA**

    q'_j = f(q'_{j-1}, q_j),      f(a, ·) a bijection of Q for every a,

with helical wrap. Any universality proof is a proof that some such factor of the ring is universal. Three facts constrain it:

1. **Right-permutivity is forced.** If the emulated alphabet is a partition of block contents into classes, and the emulated rule forgets information (`f(a,·)` not injective), then the emulated orbit has a transient while the real orbit is a pure cycle, so the emulated initial configuration must already lie on a cycle. A Turing-machine simulation that makes progress is not on a cycle. Hence the emulated rule must be injective on the configurations used, i.e. effectively right-permutive: a **reversible** one-way sequential CA.
2. **Carry equals content.** The "head state" handed to block `j` is the whole new content of block `j-1`. There is no separate head. Combined with reversibility this makes every relay a Feistel-type accumulation: a block cannot pass a bit on and return to its old content in the same pass (Thm 7), and the bit it stores is XORed with whatever it held before. Cleaning it is uncomputation, which needs the same inputs again one pass later, by which time the head is on the other side of the ring.
3. **Leftward motion is a full circuit.** A simulated head that wants to move left must send its state around the ring through every other block, each of which must relay it (and be modified, by 2) without destroying it (Thm 6 says only `1^k` survives vacuum; `1^k` destroys vacuum).

What this leaves: dense encodings where every block is active every pass (no vacuum), signals carried by phase defects in a periodic background rather than by window states, and a garbage discipline in which each block's Feistel accumulation is periodic (each block sees the same sequence of carries twice and cancels). I did not find such an encoding. The block-closure search implied by (1)–(2) (find `w`, a class partition of `{0,1}^w` closed under all block maps whose induced rule is a known universal reversible one-way CA) was not run: no known universal reversible *sequential one-way* CA with a small alphabet exists in the literature that I can target, and universality of the induced rule would need its own proof.

For k=2 the verdict tilts towards non-universal: the vacuum supports nothing but fixed points and floods (Thm 10), the ring has no small oscillators (Sec. 3.1), the cycle statistics are those of a random permutation, and the inverse dynamics is rule 106 (class 3). Every known universality proof for a 1D system uses a background with localized periodic structures; k=2 shows none at N ≤ 26.

For k ≥ 3 the situation is genuinely open. Odometers (Sec. 3.3) show that the vacuum computes counters. A Minsky machine needs two counters and a control that reads them; here the control would have to sit downstream (right) of the counters to read them and upstream to drive them, and the only way round is the ring wrap through the flood mechanism, whose ash is not a vacuum afterwards. I could not close this loop.

## 5. Overhead statement (conditional)

If a block emulation of a reversible one-way sequential CA with alphabet `Q` and block width `w` exists, then a Turing machine `M` running in time `T` and space `S` on input `x` is simulated with

* ring size `N = O(w · S)` blocks-worth of cells (conveyor simulation of a two-way head on a one-way ring, one full circuit per left move),
* slowdown `O(N)` passes per simulated step in the worst case (one circuit), i.e. `O(T · S)` passes total,
* encoding `x ↦ s_0` by a fixed block code (finite-state transduction),
* decoding by locating a fixed halting block pattern (finite-state), where "halting" must be a periodic configuration of the reversible simulation (a halted reversible machine idling), since orbits are cycles.

No such emulation is established here.

## 6. The "smallest change" deliverable

There is no proven obstruction, so no change can be shown *necessary*. Two constraints are proved, and both are properties of the architecture (sequential sweep, write ahead of the reads, no head state), independent of the gate:

* **No vacuum gliders** (Thm 5) holds for any gate `g` with `g(0..0) = 0` and reads behind the write. Adding a third control, moving the AND inputs, or adding a second write tap ahead of the reads keeps the pass triangular in vacuum.
* **No silent signals** (Thm 7) holds for any rule whose only inter-cell memory is the cells themselves: a head that carries nothing but its last `k` outputs cannot cross `k` unchanged cells with information.

The smallest changes that remove these constraints (without a universality proof for the result):

1. **One bit of head state** (a latch on the read head that survives across cells). This is what the problem statement excludes ("no head state"). With it, a silent signal exists trivially, and the Turing-machine-in-a-sweep constructions of the iterated-transducer literature apply. This is the change I would make for a plaque that must say "computer" with a proof behind it, at the cost of the "nothing else exists" purity.
2. **A write tap behind the reads** in addition to the one ahead (e.g. also `s[i-1] ^= s[i] & s[i+1]`): information then flows both ways within a pass and the vacuum is no longer triangular. No proof of universality; but the vacuum theorem no longer applies.
3. Note that reading old values (double-buffering the drum) turns the rule into the synchronous rule-106 family `G_k` (Thm 2), which is not a bijection on a ring and whose universality is equally unknown.

Changing the gate alone, as the problem statement suggests (three controls, a constant tap), does not touch either constraint; I recommend against it as a fix.

## 7. What the build is, with certainty

Whatever the universality answer, the drum is exactly the NLFSR of Theorem 1. For k=2 it is a near-maximal-period generator: at N=25 one cycle holds 83 % of the state space. For k ≥ 3 it has a rich set of short cycles (any configuration with a sparse arrangement of `11` pairs and stoppers is an odometer with period a power of two) and long cycles for dense states.

## 8. Reproduction

    cd sim && python3 ring.py                    # self-test: sequential rule == NLFSR/transducer, inverse
    gcc -O3 -o cycles cycles.c && ./cycles 20 3  # exact cycle structure
    gcc -O3 -o sample sample.c -lm && ./sample 32 2 6 1   # sampled periods
    python3 words.py 3 8                         # isolated word catalog
    python3 growth.py 3 10 3000 400              # long-run classification
    python3 explore.py travel 3 12               # traveling backgrounds (bi-infinite)
    python3 robust_bg.py 3 12                    # robust ones
    python3 explore.py word 3 "###.....#" 33 30  # spacetime of a seed
    python3 seeds.py > ../results/seeds.md       # the seed catalog
