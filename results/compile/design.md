# A Turing-machine compiler for the two-instruction pointer machine

Code: `sim/compile/`. Raw search logs: `results/compile/*.log`.

Status up front: levels 0 and 1 (the hardware and the reference machine R)
are fully re-verified. All **three** named R-level gates the TM-step
construction needs are now found and independently re-verified from
scratch: **CNOT** (§3a, found by this session's own BFS), **TOFFOLI** (§3b,
supplied by the orchestrator after this session's own search did not
converge, re-verified here on all 512 valuations of its window), and
**CLEAR** (§3c, found by this session's own BFS after switching `c` to dual
rail, mirroring what made CNOT work). The group layout and per-cell
dispatch built from these three gates is fully specified (§4), but wiring
them into a complete per-machine program hit one further, genuinely open
engineering obstruction — **broadcasting the symbol bit to every state's
test window without a "long-jump" copy gate**, which this session's search
did not resolve (§4b) — so the R-level and level-0 programs for the three
test machines were **not** produced or run this session. All three test
machines *are* fully implemented and verified as direct Turing machines
(`sim/compile/tm.py`, `verify_tms.py`), independent of that outcome. See §7
("Where this stands") for the precise scope of what is and is not verified.

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

## 4. The TM-step construction

### 4a. Group layout

Each TM cell is a group of logical bits:

```
[ s, s̄,  block_0, block_1, ..., block_{|Q|-1} ]
```

- `s, s̄`: the cell's symbol, dual rail.
- `block_k` (13 logical bits): the *test window for state k*, laid out
  exactly as TOFFOLI's window (§3b) with `A := sc_k` (a local, reusable
  copy of the symbol, initialized fresh each pass), `B := q_k` (this
  state's one-hot bit), and `q̄_k` sitting in TOFF's own "untouched spare"
  slot 2 (proven safe by the 512/512 check in §3b) — free real estate,
  since `q_k` needs a `q̄_k` neighbor for CLEAR later but TOFF never reads
  slot 2. Slots 4–12 are TOFF's own `g0, t(=fire_k), g1, t̄(=f̄ire_k), spares,
  const(0,1,1)`.

One-hot invariant, maintained by construction: at any rest point between
passes, at most one cell (the head) has any `q_k = 1`, and there exactly
one; every other cell has all `q_k = 0`.

### 4b. Per-cell dispatch, as far as this session got

For each state `k`, both of its rules (`k,0` and `k,1`) share `block_k`:
run TOFF with `A=sc_k, B=q_k` for the `v=1` rule (`sc_k` set to a copy of
`s`); then `F` on `sc_k` alone (TOFF proved `A` unchanged, so flipping it
turns "copy of `s`" into "copy of `s̄`" in place); run TOFF again for the
`v=0` rule, reusing the same `fire`/`g0`/`g1` scratch (cleared with
CLEAR between the two). Gated on `fire_k_v`: `CNOT` the new symbol into
`s` iff `new_sym != v`; carry `new_state`'s bit to the neighbor cell
`dir` away; then unconditionally `CLEAR(q_k)` once (safe regardless of
whether either rule fired — clearing an already-0 bit is a no-op) and
`CLEAR(fire)`.

**Open engineering step, not resolved this session: broadcasting `s` into
every block's `sc_k`.** `sc_k` must start each pass equal to `s`, but `s`
lives once, at the group's start, while there are `|Q|` `block_k`'s at
increasing distance from it — a fan-out CNOT can only be found for a
*fixed* small window, and the verified CNOT (§3a) is exactly 4 bits wide
with nothing in between. Two ways to try to bridge this were explored:

1. **Chain-copy** `s -> sc_0 -> sc_1 -> ... -> sc_{|Q|-1}` using CNOT
   `|Q|` times in a row (each verified CNOT invocation ends with the
   pointer sitting on its own `t`, ready to serve as the next `a` —
   confirmed by re-tracing the gate, so the *chaining itself* needs no new
   search). This conflicts with `block_k`'s own layout: CNOT's window
   requires offset+1 from `sc_k` to be `sc_k`'s own dual-rail partner
   `s̄c_k` (read and flipped by the gate's own mechanism), but `block_k`
   needs offset+1 from `sc_k` to be `q_k` (TOFF's `B`) — the two
   requirements collide on the same physical slot, and using `q_k` in
   place of `s̄c_k` is not sound (CNOT's own word reads and flips that
   slot as part of its mechanism, so it would corrupt `q_k`, and CNOT was
   only verified assuming that slot truly holds `1 - a`).
2. **A "gap" CNOT** — flip `T` iff `A=1`, with 1–4 untouched spare cells
   between `(A,Ā)` and `(T,T̄)` so the copy can jump over a `block_k` — was
   searched for (`find_cnot_gap.py`) at gaps 1–4, word length ≤ 18, capped
   at 800,000 visited states per gap: **all four hit the cap without a
   hit** — inconclusive (not exhausted), same shape of result as the
   original Toffoli search in §3b before the orchestrator's construction
   resolved it, i.e. plausibly just a larger/longer search than this
   session's remaining budget could run.

Either a longer/wider "gap CNOT" search, or a layout that avoids fan-out
entirely (e.g. carrying the comparison through pointer *movement* itself,
the way CNOT/TOFF/CLEAR all encode their conditionals as movement rather
than data-copying, instead of literally copying `s`), is the natural next
step. This is reported honestly as **not completed**, rather than papered
over with an untested construction.

### 4c. Program length, symbolically

Modulo the broadcast step above, one full TM step is, for every `(k, v)`
pair (`2|Q|` of them): one TOFF (51 letters) + a constant number of CNOTs
(12 letters each, `O(1)` per rule for the symbol write, `O(W)` for the
state-bit carry to the neighbor cell, `W` the group width) + two CLEARs (5
letters each) + the (not yet resolved) broadcast cost `b(|Q|)` per state.
Since `W = O(|Q|)` (`13|Q| + 2` logical bits per cell from §4a):

```
L(|Q|) = 2|Q| · (51 + O(|Q|) + 10) + |Q| · b(|Q|)  =  O(|Q|²) + |Q|·b(|Q|)
```

independent of `N` (the number of TM cells) either way — program length is
a function of the TM alone, the required property — with the exact
constant pending `b(|Q|)`, the resolved broadcast cost.

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

Not measured end-to-end (the wiring in §4b was not finished, so no R
program was actually run for any of the three test machines). What *is*
established: every level-0 macro used anywhere in this design costs 2–12
ticks (§1 table); every R-level gate used costs 5–51 letters (§3a-c); and
by §4c's count, `O(|Q|)` gate invocations are needed per TM step. So
**ticks per TM step is O(|Q|²) (times the unresolved broadcast cost) and
independent of tape length `N`** — the qualitative claim the task asks
for — but no concrete tick count is reported for the three test machines
because the compiler was not run on them.

## 7. Where this stands (honest summary)

Fully done and verified:
- Level 0 (hardware) re-verified from the task's own description (§1).
- Level 1 (R) simulator + exact level-0 correspondence, letter by letter,
  not just at word boundaries (§2).
- A general BFS gadget-search framework (§3), applicable to any small
  window/valuation gate.
- **All three named gates the construction needs, found and independently
  re-verified**: CNOT (12 letters, 4-bit window), TOFFOLI (51 letters,
  13-bit window, construction supplied by the orchestrator after this
  session's own search stalled, re-verified from scratch here), CLEAR
  (5 letters, 2-bit window) (§3a-c).
- The full group layout and per-cell dispatch structure built from these
  three gates (§4a-b), and the resulting program-length bound (§4c).
- All three required test machines, fully defined and verified as direct
  Turing machines, including the counter's ripple-carry correctness against
  an independent reference and the busy beaver's halting-by-state-slots
  behavior (§5).

Not done: broadcasting the symbol bit `s` out to every state's local test
copy `sc_k` without either corrupting that state's own one-hot bit or
requiring a "long-jump" CNOT this session could not find within its search
budget (§4b) — so no R-level or level-0 program was assembled or run for
any of the three test machines, and no concrete tick count was measured.
This is reported as the (now much narrower) obstruction, per the task's own
fallback allowance, rather than papered over: three sessions of gate search
(this one's CNOT and CLEAR, the orchestrator's TOFFOLI) all needed either
dual rail or a wide, carefully-marked window to succeed where a naive
attempt failed, and the broadcast step looks like it needs the same kind of
treatment, just not yet found.
