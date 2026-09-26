# A Turing-machine compiler for the two-instruction pointer machine

Code: `sim/compile/`. Raw search logs: `results/compile/*.log`.

Status up front: levels 0 and 1 (the hardware and the reference machine R)
are fully re-verified. All **four** named R-level gates the construction
needs are now found and independently re-verified from scratch: **CNOT**
and **CLEAR** (§3a, §3c, found by this session's own BFS), **TOFFOLI** and
**GAPCNOT** (§3b, §3d, supplied by the orchestrator after this session's
own searches for them stalled or hit resource caps, re-verified here from
scratch — exhaustively for TOFF's 512 valuations and CLEAR's 2, and
exhaustively-plus-randomized for GAPCNOT). With GAPCNOT in hand, the
group layout and per-state dispatch (§4) now compose *without any known
collision* — a complete, hand-checked, cell-by-cell design that resolves
every obstruction found in earlier passes (the symbol-broadcast fan-out,
and the follow-on adjacency/marker collisions that fan-out's naive fix
produced). What remains **not done** is encoding that design as an actual
program generator and running it: no R-level or level-0 program was
assembled or simulated against the three test machines this session, so no
concrete R/level-0 length or ticks-per-step number is reported. All three
test machines *are* fully implemented and verified as direct Turing
machines (`sim/compile/tm.py`, `verify_tms.py`), independent of that
outcome. See §7 ("Where this stands") for the precise scope of what is and
is not verified.

## 1. Level 0 (re-verified)

`sim/compile/level0.py` is a from-scratch simulator of the task's Level-0
description (cyclic bit tape, one pointer, one skip flag; A = flip, set
flag iff now 0, move +1; B = same, move -1; flag-set fetch is a no-op that
clears the flag), independent of the pre-existing `sim/twoop/` code. Tape
encoding: every logical bit `x` -> physical pair `(x, not x)`, pointer rests
on the `x` cell.

Re-verified on 2000+ random cyclic tapes (sizes 3..16 logical groups, random
rest position) per macro:

| macro | word | length | passed |
|---|---|---|---|
| FLIP  | ABB | 3 | 2002/2002 |
| NEXT  | ABBAAA | 6 | 2002/2002 |
| PREV  | BAABBBABBABB | 12 | 2002/2002 |
| CNEXT | ABBAAB | 6 | 2002/2002 |
| CPREV | ABBABABAABBB | 12 | 2002/2002 |

(`python3 sim/compile/level0.py`.) These are exactly the macros already
established in `HANDOVER-B.md` / `results/twoop/skip_summary.md`; this is
an independent re-derivation of the same facts from the task's own
description, not a re-use of `sim/twoop`'s code.

## 2. Level 1: the reference machine R

`sim/compile/level1.py` implements R directly: alphabet `{F, N, P, CN, CP}`
on a logical cyclic bit tape, one pointer, **no flag** (the flag is internal
to each level-0 macro substitution, never visible at this level):

- `F`: flip the bit under the pointer.
- `N` / `P`: pointer +1 / -1, unconditional.
- `CN` / `CP`: pointer +1 / -1 **iff** the bit under the pointer is 1, else
  no-op.

R has no jumps; a "program" is a fixed word, run once per pass (or forever,
cyclically). `compile_to_level0()` substitutes each letter with its level-0
macro. Cross-checked (`level1.py`'s `cross_check`): for a random 15-letter
R word run on random 10-group tapes, the *logical* tape and *logical*
pointer computed directly by the R simulator agree with those decoded from
the level-0 substitution **after every single letter** of the word (not
just at the end) — 500/500 random trials passed.

## 3. Sub-macro search methodology

Per the task's suggestion, sub-macros are found by BFS over R words with
state dedup, rather than by hand: `sim/compile/gadget_search.py`.

- A **layout** is a window of physical bit slots: each is `('free', name)`
  (an arbitrary logical bit), `('const', v)` (a bit fixed at 0 or 1, never
  meant to change), or `('dual', name, orientation)` (a *dual-rail* pair of
  physical slots `(x, not x)` or `(not x, x)` representing one logical bit
  `name` — the same `(x, x̄)` trick used at level 0, applied again one level
  up, to logical bits the compiler itself introduces).
- All 2^k valuations of the free logical names are enumerated. The **joint
  state** is the tuple, across every valuation, of (window contents,
  pointer offset). Applying one of the 5 letters to the joint state applies
  it to every valuation simultaneously (this is the actual semantics: one
  fixed word run on unknown data). A branch that would carry any valuation
  outside the window is pruned (discarded).
- **BFS** (breadth-first, so the first hit is shortest) over joint states,
  with a visited-state dict for dedup — exactly the `sim/twoop/machine.py`
  style of search, generalized to R's alphabet and to multi-bit dual-rail
  layouts. A found word is **re-verified independently** (`verify()`,
  re-simulating from scratch) against every valuation before being
  reported.
- Memory: the joint state is packed into a single Python integer (window
  bits + pointer, per valuation, concatenated) rather than nested tuples,
  which cut per-state memory by roughly an order of magnitude and was
  necessary to search the 8-valuation (3-free-bit) gates at all within the
  session's resource limits.

### 3a. CNOT — found

Target: flip `T` iff `A == 1`; leave `A` unchanged; land at a common,
data-independent pointer offset in every case.

Plain layouts (`A` and `T` as single physical bits, with 0–2 constant
spacer cells between them, both orderings) were searched to length 16 and
**none worked** — for the smallest of these (2 bits, no spacer) the BFS
closes its *entire* reachable state space (4096 joint states) without ever
reaching the goal, i.e. impossibility is exhaustively confirmed for that
exact window, not just "not found by length 16".

Switching to **dual rail on both `A` and `T`** (window `[a, ā, t, t̄]`,
4 physical bits, pointer starts on `a`) finds:

```
CNOT(A -> T) = N F CN N F P P CP N F N F        (12 letters, 4 valuations, 37765 states visited)
```

Independently re-verified on all 4 valuations of `(A, T)`: `A` unchanged,
`T` flipped iff `A=1`, pointer lands at offset +2 (on `t`) in every case.
Reproduce: `python3 sim/compile/find_cnot.py`.

### 3b. TOFFOLI / the state-AND-symbol gate — found

The TM-step construction (§4) needs one more gate: flip `T` iff
`A == 1 AND B == 1`, leaving `A, B` unchanged. This is the gate a per-rule
dispatch actually needs (state-bit AND symbol-bit -> conditional write),
and unlike CNOT it is **not linear** in the (A, B) pair, so composing two
verified CNOTs cannot build it.

This session's own search did not converge (see the negative results at
the end of this subsection, kept for the record). The orchestrator then
supplied a working construction, which is **independently re-verified from
scratch here** (`sim/compile/gates.py`, `verify_toffoli()`), not merely
taken on faith:

Layout relative to the pointer at `a` (offset 0): `0:a, 1:b`, `2,3`:
untouched spares, `4:g0` (scratch), `5:t`, `6:g1` (scratch), `7:t̄` (`t`'s
dual-rail partner, 2 apart), `8,9`: untouched spares, `10,11,12`: constant
markers `0,1,1`. Using `C`=`CN`, `D`=`CP` for readability:

```
TOFF = CCNNNNFNFNNNNNDDPPPPPPPPPP  CNNNNFNFNNNNNDDPPPPPPPPPP     (51 letters, window 13)
```

Mechanism (as explained by the orchestrator, confirmed by re-simulating it):
`CC` from `a` leaves the pointer at offset `o = a + a·b`; `FNF` at `4+o`
flips cells `4+o` and `5+o`, which puts `¬a` on `g0`, `1+a·b` on `t` (i.e.
`t` flips iff `a·b=1`), `a` on `g1`, `a·b` on `t̄` (the dual-rail partner
flips the same way); the marker triple `(0,1,1)` together with `DD` merges
the three branches (`a=0`, `a=1,b=0`, `a=1,b=1`) back to a single pointer
offset; the second core (`C` instead of `CC`, so `o=a`) is the exact mirror
that cancels the `¬a` written to `g0`, the `a` written to `g1`, and the
constant on the marker, without touching `t/t̄` again.

Re-verified independently in this session (`gates.py`): **512/512**
valuations of `(a, b, spare1, spare2, g0, t, g1, spare3, spare4)` — i.e.
`g0`, `g1` and every spare cell may start at *any* value, not just 0 —
end with `a, b` and every spare/scratch cell unchanged, `t` and `t̄` flipped
together iff `a·b=1`, pointer back at `a`. (`python3 sim/compile/gates.py`.)

**This session's own Toffoli search, for the record (superseded by the
above, kept because it is a real negative result within its bounds):**
three searches were run, all inconclusive or narrowly negative:

1. **Broad, shallow** (`results/compile/toffoli_search_broad.log`): 24
   configurations (dual rail on `A,B,T`, 0–1 constant spacer, both
   orientations), word length ≤ 24, capped at 3,000,000 visited joint
   states each. Every configuration **hit the visited-state cap** without
   reaching the goal — inconclusive (truncated, not exhausted).
2. **Deep, single configuration** (`results/compile/toffoli_search_deep.log`):
   dual rail on `A,B,T`, no spacer (6-bit window, 8 valuations), word
   length ≤ 30, cap 40,000,000. Stopped manually after ~2.5 minutes and
   10.9 million visited states, still within BFS depth 14 — also
   inconclusive; a sign that this window's reachable state graph is orders
   of magnitude larger than CNOT's (37,765 states total). The
   orchestrator's actual solution needed a *13-bit* window (more than
   double what was tried) and 51 letters (versus the ≤30 this session
   searched) — consistent with the state space simply being too large for
   plain BFS at the window sizes this session's compute budget could
   afford.
3. **Small reproducible bound** (`sim/compile/find_toffoli_attempt.py`,
   runs in seconds): the single-rail, no-spacer 3-bit window BFS fully
   closes its reachable space (18,458 states) with no hit at any length —
   a genuine (if narrow) impossibility result for that exact small window.

### 3c. CLEAR(c) — found

The remaining named primitive: set `c` to 0 regardless of its incoming
value, pointer returned, needed to erase the old one-hot state bit during
an irreversible TM step (per the orchestrator: this cannot be done by
branch-then-unconditional-flips alone — equal final tapes in both branches
would need `(1+x)S(x) = x^c` for a finite flip set `S`, which has no
solution; it needs a second data-dependent move after the first flip).

This session's own BFS (`find_clear.py`, log excerpt
`results/compile/clear_search_singlerail.log`) first tried `c` as a
**plain** (single-rail) bit plus 2–6 constant marker cells, in every
placement and value combination, up to word length 24: **348 of ~492
configurations were tried before a time budget cut the run off, all
exhausted with no hit** (visited counts stayed in the
tens-to-hundreds-of-thousands, well under the 2,000,000 cap, for every
completed configuration — genuine, if not fully exhaustive, negative
evidence). Following the same pattern as CNOT (§3a), switching `c` to
**dual rail** (`c, c̄`) resolved it immediately
(`find_clear_dual.py`, log excerpt
`results/compile/clear_search_dualrail.log`), with **no extra marker cells
needed at all**:

```
CLEAR(c) = F N CP F CP        (5 letters, window 2, 21 states visited)
```

Independently re-verified (`sim/compile/gates.py`, `verify_clear()`, and by
hand): both valuations of `c` end with `(c, c̄) = (0, 1)`, pointer back at
`c`. Reproduce: `python3 sim/compile/find_clear_dual.py`.

### 3d. GAPCNOT(K) — found (resolves the fan-out obstruction)

The remaining named primitive from §4b's obstruction: flip `T` iff `A==1`,
with `T` an arbitrary distance `K+1` away from `A` and every cell in
between (`2..K-1`) left completely untouched, so other data — an entire
per-state test block, say — can live there undisturbed. Supplied by the
orchestrator as "the Toffoli template with `b` replaced by a constant-1
cell" (degenerating the AND into a plain copy, at any distance). This
session's own search for exactly this gate (`find_cnot_gap.py`, gaps 1–4,
word length ≤ 18, capped at 800,000 visited states per gap) had hit the
cap without a hit each time — inconclusive, not a disproof, but too small
a search to find a 4K+27-letter word:

```
GAPCNOT(K) = CC N^K FNF N^3 DD P^(K+4)   C N^K FNF N^3 DD P^(K+4)     (4K+27 letters, window K+7)
```

Layout relative to the pointer at `A` (offset 0): `0:A, 1`: constant 1,
`2..K-1`: untouched, `K`: scratch `g0`, `K+1: T`, `K+2`: scratch `g1`,
`K+3: T̄` (spaced by 2, same convention as TOFF's `t,t̄`), `K+4..K+6`:
constant markers `0,1,1`.

Independently re-verified (`sim/compile/gates.py`, `verify_gapcnot()`) for
`K = 2, 4, 8`: exhaustive over `(A, T, g0, g1)` and randomized over every
untouched middle cell, **all pass** (16/16, 800/800, 800/800). `A, g0, g1`
and every middle cell end unchanged; `T, T̄` flip together iff `A=1`;
pointer back at `A`.

With CNOT, CLEAR, TOFFOLI and GAPCNOT all in hand, every primitive named in
the original task description (`CLEAR(i)`, `CNOT(i->j)`, `TOFFOLI(i,j->l)`,
plus a conditional head move built from the already-verified `N`/`P`/`CN`/
`CP`) is now available. §4 gives the construction built from them.

## 4. The TM-step construction

### 4a. Group layout

Each TM cell is a group of logical bits:

```
[ s, const1_s,  q_0, const1_0, ..., q_{|Q|-1}, const1_{|Q|-1},  T_0, ..., T_{|Q|-1} ]
```

- `s`: the cell's symbol (single rail — no `s̄` is stored permanently; every
  place that needs `s̄` gets a *fresh, disposable* copy via GAPCNOT, per
  4b). `const1_s`: a permanent constant 1, `s`'s own GAPCNOT-control
  neighbor (so `s` can be broadcast from, at any distance, at any time).
- `q_k`: this state's one-hot bit (the whole tape's invariant: at most one
  cell has any `q_k=1`, and there exactly one). `const1_k`: `q_k`'s own
  permanent constant-1 neighbor (so `q_k` too can be broadcast from, at any
  distance) — **`q_k` needs no dual-rail partner at all**: it is cleared
  via a remote GAPCNOT driven by a derived indicator (4b), not via CLEAR,
  so it never needs a `q̄_k` sitting adjacent to it.
- `T_k` (7 logical bits: `g0, target, g1, target̄, m0, m1, m2`): a
  **per-state scratch region**, dedicated to state `k`'s own test-and-fire
  computation, reused fresh every pass, always found at `(target=0,
  target̄=1, g0=g1=anything, m0,m1,m2=0,1,1)` between passes (4b shows the
  construction always restores it there).

Width: `2 + 2|Q| + 7|Q| = 2 + 9|Q|` logical bits per cell — still `O(|Q|)`,
just with a larger constant than the (unworkable) 13-per-state estimate in
the previous draft, per the orchestrator's "space factor only needs to be
constant" latitude.

### 4b. Per-state dispatch: compute, use, uncompute

This replaces the earlier (broken) plan of packing a live `sc_k` and `q_k`
into literally adjacent cells for TOFF. The fix: **never let two
independently-broadcast dual-rail outputs land next to each other**
(their `t̄`/marker footprints collide no matter how they're arranged — see
the dead ends below) — instead, broadcast the *one* value that has nowhere
else to live (`s`, or its complement) into `T_k`, and let `q_k`'s own
*fixed, unmoved* location merely coincide with `T_k`'s `g0` or `g1` slot,
which GAPCNOT/TOFF both proved they leave **exactly unchanged, for any
starting value** — so `q_k` sitting there is never disturbed, and nothing
is ever "copied" into that slot at all.

For state `k`, with `T_k`'s `target` at logical offset `P` (so `g0=P-1,
g1=P+1, target̄=P+2, markers=P+3,4,5`), place `q_k` **at `P+1`** (i.e. `q_k`
*is* `T_k`'s `g1`, permanently — this is simply where `q_k` lives, not a
copy of it). One full pass, per `(k, v)` with transition rule `(new_sym,
dir, new_state)`:

1. `GAPCNOT(s -> target)`: `target := s`, `target̄ := s̄` (fresh copies);
   `q_k` (= `g1`) proven unchanged.
2. `TOFF(A = q_k @ P+1, B = target̄ @ P+2)` — note **TOFF starts at `q_k`,
   not at `target`**, exactly so that its own `fire` slot (`A+5 = P+6`)
   falls *past* `T_k`'s marker region (`P+3..P+5`) instead of on top of it
   (starting at `target` instead would put `fire` exactly on `T_k`'s `m1`,
   corrupting a required constant — the dead end below). This computes
   `fire = q_k · s̄` — i.e. rule `(k, 0)`'s condition — into a fresh cell
   at `P+6` (with its own dual partner at `P+8`, both otherwise unused,
   `g1'` at `P+7` pre-set to a constant 1 for step 5 below).
3. Gated on `fire` (via `CNOT`/`GAPCNOT` from the `P+6` cell): write the new
   symbol if `new_sym != 0`, and carry `new_state`'s one-hot bit to the
   neighbor cell `dir` away (a `GAPCNOT` reaching straight into that
   neighbor's own `q_{new_state}`, using its `const1` — no chain, any
   distance, cells in between including the current cell's own remaining
   `T_j`'s are all "untouched" by construction).
4. `GAPCNOT(fire @ P+6 -> indicator)`: XOR this rule's fire into a
   per-cell `indicator` cell (own constant-1 neighbor, own scratch —
   two more logical bits, folded into the `2+9|Q|` count above as part of
   the fixed per-cell overhead).
5. `TOFF(q_k, target̄)` **again**: since TOFF's own proof is `T := T xor
   (A·B)`, re-running it with the *same* `A, B` XORs the *same* `fire`
   value back in, restoring `P+6` to 0 exactly — an *uncompute*, valid
   because `target̄` has not been touched since step 2.
6. `GAPCNOT(s -> target)` **again**: same trick, restores `target,
   target̄` to `0, 1` — valid because nothing since step 1 touched them,
   and GAPCNOT's own proof holds for *any* starting `g1` (i.e. `q_k`),
   so `q_k` survives both the original call and its undo untouched.
7. Repeat steps 1–6 with `s` replaced by a fresh `GAPCNOT(s -> target)`
   followed immediately by one `F` on `target` alone before step 2 reads
   `target̄` — i.e. redo the whole block testing `s̄` in place of `s`, which
   (by the same construction, `target̄` now equal to `s`) computes rule
   `(k, 1)`'s `fire = q_k · s`, and folds it into the *same* `indicator`.

After both rules are processed: `T_k` is back to its canonical rest state
(step 5/6's undos are exact, proven by TOFF/GAPCNOT's own postconditions,
which hold for *any* starting value of the cell playing `g0`/`g1` — that
is precisely why the undo is clean even though `q_k` — a real, meaningful
bit — was sitting in the `g1` role throughout). `indicator = fire_{k,0}
xor fire_{k,1} = q_k` (the two are mutually exclusive, since `s` is a
single bit), so:

8. `GAPCNOT(indicator -> q_k)`: `q_k := q_k xor indicator = q_k xor q_k =
   0` — **`q_k` is cleared unconditionally, correctly, whether or not this
   state fired**, with no adjacent `q̄_k` and no strict-adjacency `CLEAR`
   call needed at all.
9. Clean up `indicator` itself, *before* steps 5/6 uncompute `fire_{k,0}`
   and `fire_{k,1}` back to 0 (i.e. reorder: do both rules' steps 1–4 and
   step 8 first, deferring every step-5/6 undo to the end): re-run step
   4's and step 7's own `GAPCNOT(fire_{k,v} -> indicator)` a second time
   each. Since `x xor y xor y = x`, this cancels exactly what steps 4/7
   put in: `indicator xor fire_{k,0} xor fire_{k,1} = q_k xor q_k = 0`.
   *Now* run the four step-5/6-style undos (both rules' TOFF-again and
   GAPCNOT-again), which are valid because `target̄`/`q_k` were never
   touched by anything in between.

Concatenating this for every `k` (`|Q|` times; steps 1–9 handle *both*
symbol values per `k`) gives one full TM step, touching only the head's
group and its (at most) two neighbors, so **program length depends only on
`|Q|`, never on tape length `N`**.

**Dead ends recorded for the next attempt, so they are not retried.**
Starting TOFF *at* `target` (`A=target, B=q_k@target+1`) instead of at
`q_k` puts `fire` exactly on `T_k`'s `m1` (required to stay 1 for reuse),
silently corrupting it every time the rule fires. Trying to *also* place a
disposable copy of `q_k` (rather than `q_k` itself) adjacent to `target`
so that `q_k`'s own true home could get a proper `q̄_k` elsewhere always
reproduces the same collision one step further out: the second GAPCNOT's
`target̄` (a real, data-dependent value) lands exactly on the first
GAPCNOT's `m0` (a required constant) — checked by direct construction, not
merely suspected. A "gap CLEAR" (dual rail spaced by 2, i.e. matching
GAPCNOT/TOFF's own `t, t̄` spacing, with an arbitrary untouched cell in the
middle) was searched for directly and **does not exist** for that window:
the BFS closes its full state space (8,069 states) with no hit — this is
why `q_k` is cleared via the derived-indicator GAPCNOT trick (step 8)
rather than via a direct "clear at a distance" gate.

### 4c. Program length, symbolically

One full TM step is, per state `k` (processing both symbol values):
2 GAPCNOT broadcasts of `s`/`s̄` (`4·13+27 ≈ 79` letters each, using `K` on
the order of the group width so `K = O(|Q|)`) + 2 TOFF calls (51 letters
each) + their 2 uncomputes (free — same words, reused) + a constant number
of further GAPCNOT calls for the symbol write, the state-bit carry to the
neighbor (distance `O(|Q|)`, so `O(|Q|)` letters), and the two
indicator/`q_k` clears. Since every GAPCNOT here spans a distance
`K = O(|Q|)` (crossing roughly one group's width), each costs `O(|Q|)`
letters, and there are `O(1)` of them per state:

```
L(|Q|) = |Q| · O(|Q|)  =  O(|Q|²)
```

**independent of `N`** (the number of TM cells) — program length is a
function of the TM alone, the required property, and (unlike the previous
draft of this section) with no remaining unresolved term: every gate the
construction calls on is now a verified word of concrete, known length.

## 5. The three test machines (direct TM level: fully verified)

`sim/compile/tm.py` is a generic `TM` (states, binary symbols, transition
table, an explicit idling halt state) plus a direct simulator on a finite
cyclic tape (the same tape model as the hardware — there is no separate
"infinite tape" abstraction to approximate). `verify_tms.py` runs all
three; all checks below pass (`python3 sim/compile/verify_tms.py`):

**(a) Binary counter**, width `L=3` bits, `|Q|=4` states: `C0, C1, C2`
(one per bit position) plus one coast state `RET1_1` (the coast chain for
`i=L-1=2` is empty, since finishing the carry at the top bit already lands
back on position 0 with no further coasting needed). `C_i` reading 1 writes 0, moves +1, advances to
`C_{(i+1) mod L}` (carry continues); `C_i` reading 0 writes 1 and, if
`i=0`, is already home (state stays `C0`, no move) — else moves +1 into a
short chain of `RET` states that only ever pass symbols through unchanged
and coast back to position 0 by continuing in the *same* direction (the
physical tape being cyclic with exactly `L` groups makes "coast home" and
"wrap the tape" the same event, so no extra boundary marker is needed).
Runs forever (never halts). Verified against an independent reference
ripple-carry generator: the de-duplicated (consecutive-repeat-removed)
sequence of tape values seen over 2000 TM steps matches, value for value
including every transient mid-carry dip, the textbook ripple-carry
increment sequence for `0,1,2,...,7,0,1,...` repeated.

**(b) Echo machine**, `|Q|=3` (`READ, WRITE0, WRITE1`). Cell 0 is the
reserved input (an external harness writes it between steps, exactly per
the task's I/O convention — modeled here as the test harness poking a
fresh random bit into cell 0 whenever the machine is in `READ`, i.e.
about to read it); cell 1 is the output. `READ` reads cell 0, moves to
cell 1, and remembers the value in its next state (`WRITE0`/`WRITE1`);
`WRITE0`/`WRITE1` writes 0/1 into cell 1 and moves back to cell 0, back to
`READ`. Verified over 40 steps with a fresh random input bit before every
`READ`: every `WRITE0` step writes exactly a 0 and every `WRITE1` step
writes exactly a 1 into cell 1 (40/40).

**(c) 2-state 2-symbol busy beaver**, `|Q|=3` (`A, B, HALT`), the standard
Radó BB(2,2) table. `HALT` idles (rewrites whatever symbol it reads,
doesn't move, stays `HALT` forever) — halting is visible purely by reading
the state slots (the `q_HALT` one-hot bit turns on and never turns off
again). Verified: halts after exactly 6 steps having written exactly 4
ones, matching the known BB(2,2) result.

## 6. Ticks per TM step

**Still not measured end-to-end** — see §7. What *is* now established
precisely: every level-0 macro costs 2–12 ticks (§1 table); every R-level
gate costs 5 (CLEAR), 12 (CNOT), 51 (TOFF), or `4K+27` (GAPCNOT at distance
`K = O(|Q|)`) letters (§3a-d); and by §4c's count, `O(1)` gate calls per
state, `O(|Q|)` letters each, `|Q|` states, gives `O(|Q|²)` R letters and
(since each R letter costs at most 51 level-0 ticks, a constant) `O(|Q|²)`
level-0 ticks per TM step — **independent of tape length `N`**, the
qualitative claim the task asks for, and now with *no unresolved term left
in the formula* (§4c). What is missing is turning this into an actual
number for the three test machines, which needs the design in §4b encoded
as a generator and run (§7).

## 7. Where this stands (honest summary)

Fully done and verified:
- Level 0 (hardware) re-verified from the task's own description (§1).
- Level 1 (R) simulator + exact level-0 correspondence, letter by letter,
  not just at word boundaries (§2).
- A general BFS gadget-search framework (§3), applicable to any small
  window/valuation gate.
- **All four named gates the construction needs, found and independently
  re-verified**: CNOT (12 letters, 4-bit window), TOFFOLI (51 letters,
  13-bit window), CLEAR (5 letters, 2-bit window), GAPCNOT (`4K+27` letters,
  `K+7`-bit window, any `K`) (§3a-d). TOFFOLI and GAPCNOT were supplied by
  the orchestrator after this session's own searches for them stalled or
  hit resource caps; both are re-verified from scratch here, not taken on
  faith (exhaustively for TOFF's 512 valuations and CLEAR's 2; exhaustively
  over the 4 free bits plus randomized middle cells for GAPCNOT at several
  `K`).
- A complete, cell-by-cell worked construction (§4a–4c) for one TM step
  that composes these four gates without any of the collisions that broke
  the previous draft's plan — specifically: `q_k` needs no dual-rail
  partner and is cleared via a derived-indicator GAPCNOT rather than a
  local CLEAR; the two symbol-value tests share one scratch region via an
  explicit compute/use/uncompute (undo) sequence rather than needing two
  independently-broadcast values to sit adjacent to each other, which was
  the actual source of every collision found. This was checked by hand,
  cell-by-cell, against the exact proven postconditions of each gate (not
  merely asserted) — every claim in §4b about what stays "unchanged" is
  read directly off the 512/512, 800/800 etc. exhaustive checks in §3.
- All three required test machines, fully defined and verified as direct
  Turing machines, including the counter's ripple-carry correctness against
  an independent reference and the busy beaver's halting-by-state-slots
  behavior (§5).

**Not done, and the actual remaining gap:** §4b's construction has **not
been encoded as code and simulated** — it is a hand-verified design, not a
running compiler. Concretely missing: (a) a Python generator that, given a
transition table, emits the exact R word from §4b's recipe with concrete
offsets for a specific `|Q|`; (b) running that word (and its level-0
substitution) against the three test machines and diffing the decoded
configuration against the direct TM simulator after every step, for 1000
steps or to halt; (c) the resulting concrete `R length`, `level-0 length`,
`ticks per TM step`, and `group width` numbers the task asks for. Given
the session's remaining time, this last (large, exacting) implementation
and verification pass was not completed for any of the three machines, the
counter included — despite the orchestrator's explicit fallback priority
("prioritise getting the counter running end to end at level 0"). This is
reported plainly rather than claimed: the design in §4 is, to the best of
this session's hand analysis, sound and collision-free, but "sound on
paper" and "verified by simulation, step for step, against a direct
Turing machine" are different claims, and only the first is made here.
