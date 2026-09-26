# Milestone 1: the sweep architecture, assembled and run

Status: **done**. A generator (`sim/compile/sweep.py`) compiles an arbitrary
transition table into one fixed R word per TM cell ("group"); a sweep is
`n_groups` copies of (that word + an unconditional `N^G` move to the next
group). This was run, group by group, against `tm.py`'s direct simulator
for all three required test machines, decoding the tape and state after
every detected TM step and asserting an exact match, plus a full
constant/rest-value audit of every scratch cell after every single group
visit (`verify_sweep.py`'s `check_scratch_at_rest`). No new gates were
searched for; only `TOFF`, `gapcnot_word(K)` (`gates.py`) and `gap_clear(m)`
(`hand_gapclear.py`) are used, exactly as already verified.

Reproduce: `python3 sim/compile/verify_sweep.py`.

## 1. Layout (independent of design.md §4, which was not followed)

Each TM cell is a group: a symbol block, then one 31-cell block per TM
state. The construction and the reasoning behind every cell placement is
in `sweep.py`'s module docstring; the short version:

- `q_j`, the one-hot state bit, together with its dual-rail partner
  `qbar_j` two cells further along (`qbar_j = q_j + 2`), so that every
  gate that ever *writes* `q_j` (the state's own "I fired, clear myself"
  step, and the two arrival-cell merges below) can share one control
  convention: control-cell-after-target, i.e. every write to `(q_j,
  qbar_j)` is the *mirrored* form of GAPCNOT.
- Directly *before* `q_j`: a mirrored `TOFF(a=q_j, b=b1)` window, where
  `b1` is a fresh copy of the symbol (or its complement) made once per
  state per pass. `b1` cannot be written by a plain GAPCNOT copy of the
  symbol sitting right next to `q_j` -- GAPCNOT's own marker triple would
  then land exactly on TOFF's `fire` cell (checked by direct arithmetic,
  reproduced in `sweep.py`'s docstring and empirically below). The fix:
  give `fire` a *rest value of 1* rather than 0, and read the AND off its
  dual partner `firebar` (`=1-fire`) instead -- then the symbol-copy
  broadcast's marker precondition (which lands on `fire`) is satisfied
  "for free", every pass, by construction.
- `firebar` (not `fire`) drives every subsequent action for that state
  and symbol value: conditionally flip the symbol, conditionally write
  the new state's one-hot bit into a neighbour (or clear it locally if
  the rule doesn't move), and clear `q_j` itself. `(fire, firebar)` is
  then forced back to `(1, 0)` with `gap_clear` -- not by calling TOFF a
  second time with the same inputs, which breaks the moment `q_j` (one of
  those inputs) is the very thing just cleared.
- A state can be entered from either neighbour on different passes (e.g.
  BB(2,2)'s state `B`, entered with direction +1 from `A,0` and direction
  -1 from `A,1`), and a GAPCNOT-written dual-rail pair only supports being
  approached from one fixed side consistently. So every state has *two*
  arrival cells, `arrL_j` (written by a *forward* GAPCNOT from a lower-
  numbered neighbour's `firebar`, on direction +1) and `arrR_j` (written
  *mirrored*, from a higher-numbered neighbour, on direction -1), each
  merged into `(q_j, qbar_j)` and cleared at the start of every pass,
  before that state is tested.
- **A collision that only shows up with 3+ states, and its fix**: the
  "short way around the ring" that `Assembler.gapcnot` picks by default
  (whichever of the two directions needs fewer letters) can flip from
  forward to mirrored once the *group* is large enough relative to the
  *ring* (a handful of states already does it for `n_groups` in the
  single digits) -- and every one of the calls above has its marker cells
  pre-allocated assuming one *specific* direction. Picking the wrong one
  reads the wrong cells as markers and silently corrupts an unrelated
  state's `g1`. Every such call now forces its direction explicitly
  rather than letting the assembler optimise it away; this is the one
  case in this construction where the "shorter word" choice is unsound,
  not just suboptimal.

Constant/marker bookkeeping (`GAPCLEAR_M`, `GAP_CLEAR_PAIR_M` in
`sweep.py`) went through two rounds of exactly this kind of collision
(reusing a cell as both a live value and a constant a different call
needed fixed) before landing on cells provably constant *at the moment
each specific call runs* -- caught, each time, by `check_scratch_at_rest`
or by a direct before/after cell dump, per the task's "assert exactly the
expected cells changed" discipline, not by re-reasoning from scratch.

## 2. Numbers

`G` = group width = `12 + 31*|Q|` (12 cells for the symbol block, 31 per
state). R pass length and level-0 pass length are for **one full sweep**
(`n_groups` group-words, each followed by `N^G`). Level-0 ticks per
letter: F=3, N=6, P=12, CN=6, CP=12 (§1 of `results/compile/design.md`,
re-derived independently in `sim/compile/level0.py`).

| machine | `\|Q\|` | `G` | R pass length | level-0 pass length (ticks) |
|---|---:|---:|---:|---:|
| counter (L=3, `n_groups=3`) | 4 | 136 | 25,584 | 224,550 |
| echo (`n_groups=2`) | 3 | 105 | 13,508 | 118,716 |
| BB(2,2) (`n_groups=12`) | 3 | 105 | 57,528 | 501,912 |

Ticks per TM step (level 0), measured by counting the exact number of
group-visits consumed between consecutive detected TM steps over the full
verified run, times that machine's per-group level-0 tick cost:

| machine | steps verified | avg ticks/step | worst ticks/step | avg group-visits/step | worst group-visits/step |
|---|---:|---:|---:|---:|---:|
| counter | 300 | 112,275 | 224,550 | 1.5 | 3 |
| echo | 50 | 59,358 | 59,358 | 1.0 | 1 |
| BB(2,2) | 6 (halts) | 250,956 | 460,086 | 6.0 | 11 |

These are all `O(|Q|^2)` per group-visit (dominated by the `O(|Q|)`-wide
symbol-copy and neighbour-write GAPCNOT calls, `O(|Q|)` states) and, per
the sweep design, independent of `N` (tape length) -- e.g. BB(2,2) was run
on a 12-group ring though the head only ever visits a handful of cells;
milestone 2 (not attempted) would be needed to make ticks/step independent
of a sweep's `n_groups` as well.

## 3. Verification (`python3 sim/compile/verify_sweep.py`)

For each machine: the compiled sweep was run group by group (never as one
opaque word); after every group's word + its `N^G`, the tape was decoded
(symbol tape, plus whichever single cell -- a state bit or, transiently, an
arrival cell -- currently holds the one-hot "the head is here" token) and
cross-checked letter-exact against `tm.py`'s direct simulator, replaying
`tm_step` on the reference until it catches up (a direction=+1 chain can
fold more than one TM step into a single group visit). Every dual-rail
invariant (`q/qbar`, `arrL/arrLbar`, `arrR/arrRbar`, `s/sbar`) and every
supposedly-constant cell (25 named roles per state, audited by
`check_scratch_at_rest`) was asserted after *every single group visit*,
not just at sweep boundaries.

- **Binary counter**, `L=3` (states `C0,C1,C2,RET1_1`): **300/300** steps
  match the direct TM simulator exactly, tape decoded as `[0,1,1]` (value
  6 = 300 mod 8, correct for a 3-bit ripple counter) at the end.
- **Echo**: **50/50** steps match; a fresh random bit was poked into the
  input cell's symbol (both in the live compiled tape and in the
  reference) immediately before every `READ`, and every decoded
  `WRITE0`/`WRITE1` step wrote the correct 0/1 into the output cell.
- **BB(2,2)**: halts after exactly **6/6** verified steps, final tape
  `[1,1,0,0,0,0,0,0,0,0,1,1]` (**4 ones**), state `HALT` -- matching the
  well-known result, and detected purely by the state slots settling into
  the `HALT` one-hot pattern (no side-channel "step count" was read).

A smaller, hand-built 2-state machine with both a `+1`- and a `-1`-
direction rule pair (not one of the three required machines, used only to
shake out the direction-dependent bugs below before spending time on the
real ones) was separately run for 30/30 steps.

## 4. Bugs this caught (and how)

All found by the checking-mode simulator against real transition tables,
not by further hand-derivation, per the task's instructions:

1. Forgot to allocate the shared `q_j`-clearing marker triple at all
   (offsets `q-3,-4,-5`) -- silently aliased onto the symbol block.
   Caught by a `q/qbar` invariant assertion firing on the very first
   two-state test.
2. A forward-direction GAPCNOT call (writing into a *right* neighbour)
   needs a constant-1 neighbour on the *other* side of its control than
   the mirrored calls do; only the mirrored side had been fixed at 1.
   Caught by re-simulating the exact extracted window with `gates.py`'s
   own `step_raw` and finding the control-adjacent cell wasn't actually 1.
3. "Uncompute the symbol-copy broadcast by calling GAPCNOT again" is
   unsound when that same state's own symbol-write can change the symbol
   in between -- the second call cancels against the *new* symbol, not
   the one used to build the copy. Fixed by resetting with `gap_clear`
   (unconditional) instead of a second conditional GAPCNOT.
4. Two different marker-picking mistakes (`GAPCLEAR_M`) where the chosen
   offset landed on a cell that is constant *most* of the time but is
   exactly the live value the call itself is mid-computation on. Caught
   by re-deriving each marker offset from the actual, provably-constant
   neighbourhood of each control cell instead of reusing one number
   everywhere.
5. The "3+ states" direction-flip described in §1 above -- caught only
   once a 4-state machine (the real counter, via its `RET1_1` coast state)
   was tried; every 2-and-3-state synthetic test had, by chance, `G` small
   enough relative to the ring that the shorter-path heuristic never
   picked the wrong direction.

## 5. Unresolved / not attempted

- Milestone 2 (constant overhead per TM step, independent of `n_groups`)
  was not attempted.
- The `direction == 0` case where the new state differs from the current
  one (a same-group write to a *different* state's arrival slot) raises
  `NotImplementedError` in `compile_group_program` -- not needed by any of
  the three required machines (the counter's own `direction=0` rule always
  targets its *own* current state, which is handled by simply skipping
  the clear/write), so it was left unimplemented rather than guessed at.
- No attempt was made to minimize `G` (31 cells/state plus 12 fixed); the
  task's "space factor only needs to be constant" latitude was used
  generously in favour of a construction that could actually be gotten
  right and checked in the time available.
