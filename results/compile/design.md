# A Turing-machine compiler for the two-instruction pointer machine

Code: `sim/compile/`. Raw search logs: `results/compile/*.log`.

Status up front, so the obstruction is not buried: levels 0 and 1 (the
hardware and the reference machine R) are fully re-verified, the R-level
sub-macro toolkit includes a **found and verified CNOT gadget** but **no
Toffoli-class (state-AND-symbol) gadget** was found within the search
budget available in this session. That gate is exactly the one piece the
generic TM-step construction needs, so the compiler is specified completely
but not executed end-to-end for the three test machines at the R/level-0
tiers. All three test machines *are* fully implemented and verified as
direct Turing machines (`sim/compile/tm.py`, `verify_tms.py`). See "Where
this stands" at the end for the precise scope of what is and is not
verified.

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

### 3b. TOFFOLI / the state-AND-symbol gate — not found (open obstruction)

The TM-step construction (§4) needs one more gate: flip `T` iff
`A == 1 AND B == 1`, leaving `A, B` unchanged. This is the gate a per-rule
dispatch actually needs (state-bit AND symbol-bit -> conditional write),
and unlike CNOT it is **not linear** in the (A, B) pair, so composing two
verified CNOTs cannot build it — the R primitives' own nonlinearity (the
conditional move) has to supply it directly, the same way it supplied
CNOT's.

Three searches were run, all negative within their bounds:

1. **Broad, shallow** (`results/compile/toffoli_search_broad.log`): 24
   configurations (dual rail on `A,B,T`, 0–1 constant spacer, both
   orientations), word length ≤ 24, capped at 3,000,000 visited joint
   states each. Every configuration **hit the visited-state cap** without
   reaching the goal — i.e. inconclusive (the search was truncated, not
   exhausted).
2. **Deep, single configuration** (`results/compile/toffoli_search_deep.log`):
   dual rail on `A,B,T`, no spacer (6-bit window, 8 valuations), word
   length ≤ 30, cap 40,000,000. Stopped manually after ~2.5 minutes and
   10.9 million visited states, still within BFS depth 14 — also
   inconclusive, and a strong sign that this window's *reachable* state
   graph is orders of magnitude larger than CNOT's (which needed only
   37,765 states total), making plain BFS impractical here within a
   two-CPU, few-GB budget.
3. **Small reproducible bound** (`sim/compile/find_toffoli_attempt.py`,
   runs in seconds): the **single-rail, no-spacer** 3-bit window (`A,B,T`
   as plain bits, no dual rail, no padding) BFS **fully closes** its
   reachable space (18,458 states) with no hit at *any* length — a genuine
   (if narrow) impossibility result, unlike the two inconclusive dual-rail
   runs above.

No conservation-law proof of impossibility was found either (the obvious
candidate — every letter-word has a fixed, data-independent count of `F`
operations, hence a fixed parity of total window popcount change across all
branches — is satisfied by the required output here, since Toffoli's
output popcount change is 0 or 2, always even, same as CNOT's; it does not
rule the gate out). The honest state is: **found for a linear (single
control) gate, not found for the genuinely nonlinear (two-control) gate,
within the compute budget available**; a larger window/length search, a
bidirectional (meet-in-the-middle) BFS, or a hand construction refined from
the partial analysis below are the natural next steps.

**Partial hand analysis, for whoever picks this up next.** Two plain `CN`
tests on adjacent bits `A, B` (no markers) send the joint state to one of
three *distinct* pointer offsets depending on `(A,B)`: offset 0 (on `A`,
reading its own true value 0) when `A=0`; offset 1 (on `B`, reading 0) when
`(A,B)=(1,0)`; offset 2 (on a fresh ancilla `M`, reading `M`'s own value)
when `(A,B)=(1,1)` — i.e. the *position* already encodes the AND correctly,
and all three landing cells read the same value (0, if `M` starts at 0).
The obstruction is committing this into a permanent bit: an unconditional
`F` at that point flips whichever cell the pointer is on, which is `M` in
the true case (correct) but is `A` or `B` in the two false cases
(corrupts the control that must survive unchanged for the rest of the
per-cell decode). Every cleanup attempted by hand (mirrored `CP`/`CN`
passes exploiting that the corrupted cell now reads 1) fixes the pointer's
*position* but not both corrupted values at once without re-introducing the
same asymmetry one bit further out — consistent with why CNOT needed dual
rail (an extra "shadow" bit to absorb exactly this kind of asymmetry) and
suggesting Toffoli needs at least one more scratch/marker bit than the
6-bit dual-rail window already tried, hence a wider search.

## 4. The TM-step construction (specified, not executed past this gate)

**Group layout.** Each TM cell is a group of `W = 2 + |Q|` logical bits:

```
[ s, s̄,  q_0, q_1, ..., q_{|Q|-1} ]
```

- `s, s̄`: the cell's symbol, dual rail (matches the level-0/level-1
  encoding pattern throughout, and is what made CNOT work in §3a).
- `q_0..q_{|Q|-1}`: one-hot current-state indicator. Invariant, maintained
  by construction and checkable on every configuration: **at most one cell
  on the whole tape has any `q_k = 1`** (the head cell), and there it is
  exactly one `q_k` (the current state); every other cell has all `q_k = 0`.

The physical (level-0) tape is the concatenation of `N` such groups (`N`
= number of TM cells in use) around the cyclic tape, each of physical width
`2W` after level-0's own `(x, x̄)` doubling — i.e. `2W` level-0 cells per TM
cell, `2WN` level-0 cells in total.

**Dispatch (verified independently of the missing gate).** Scanning the
one-hot state block with the letter sequence `(CN N)` repeated `|Q|` times
starting at `q_0` lands the pointer at a *constant*, data-independent final
offset (`|Q|+1` past `q_0`) regardless of which `q_k` is the active one —
because `CN` fires exactly once (at the true `k`) contributing an extra +1,
and every other iteration contributes exactly +1 whether or not it fires
(reading 0 either side of the true bit, by the one-hot invariant). This is
a simple, hand-checked fact (confirmed computationally for `|Q|` up to 8 in
the course of this work), independent of the missing gate, and is *most* of
what "find out which state we are in" needs. What is still missing is
hooking a **per-(state, symbol) action** onto the exact tick `CN` fires —
that hook is exactly the Toffoli-class gate of §3b (fire the action iff
*this* `q_k` is 1 **and** the symbol bit matches this rule).

**Given a working gate `TAND(A,B->T)` of length `g` letters over a window
of `w` extra logical bits**, one full TM step compiles to, for every
`(state k, symbol value v)` pair with a transition rule `(new_sym, dir,
new_state)`:

1. `TAND(q_k, s==v -> "fire_k_v")` — a per-rule scratch bit, 0 unless this
   is the active rule.
2. Gated on `fire_k_v`: `CNOT` the new symbol into `s` if `new_sym != v`
   (else nothing); `CNOT` a "moving" marker; carry `new_state`'s one-hot
   bit into the neighbor group `dir` cells away (a chain of `CNOT`s from
   `fire_k_v` into that neighbor's `q_{new_state}`, and one clearing `q_k`
   in the old head), using the already-correct `NEXT`/`PREV` (`N`/`P`
   chains, or the level-1 `CN`/`CP` conditional-move macros for the actual
   pointer relocation) to reach the neighbor group.
3. Clear the scratch `fire_k_v` back to 0 (it is only ever 1 transiently,
   so this is an unconditional `F` gated the same way it was set, or a
   second `TAND` application, whichever the concrete `TAND` construction
   makes cheaper).

Concatenating this block for every `(k, v)` pair (there are `2|Q|` of them)
gives the whole pass; nothing else in the program depends on the tape
beyond the head's group and its two neighbors, so **program length is a
function of `|Q|` alone**, independent of `N` (the number of TM cells) —
the required property. Symbolically, with `TAND` costing `g` letters and
window `w`, and each rule's write/carry/clear costing a small constant
`c` (dominated by up to `W`-many `CNOT`s at 12 letters each, plus O(`W`)
`N`/`P` housekeeping):

```
L(|Q|) ≈ 2|Q| · (g + c),   c = O(W) = O(|Q|)
```

i.e. **O(|Q|²)** letters in R, and (since every R letter is a level-0 macro
of length 2–12) **O(|Q|²)** level-0 ticks per TM step — constant in the
tape size `N`, which is exactly the claim the task asks to prove by
construction. This is as far as the construction is specified without a
concrete `g`.

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

Not measured end-to-end (the R/level-0 compilation of §4 was not executed,
per the open gate in §3b). What *is* measured: every level-0 macro used
anywhere in this design costs 2–12 ticks (§1 table), and level 1's own
letters are used `O(|Q|²)` times per TM step (§4), so **ticks per TM step
is O(|Q|²) and independent of tape length `N`** — the qualitative claim the
task asks for — but no concrete tick count is reported for the three test
machines because the compiler was not run.

## 7. Where this stands (honest summary)

Fully done and verified, independent of the open gate:
- Level 0 (hardware) re-verified from the task's own description (§1).
- Level 1 (R) simulator + exact level-0 correspondence, letter by letter,
  not just at word boundaries (§2).
- A general BFS gadget-search framework (§3), applicable to any small
  window/valuation gate, with a clean, independently-verified **CNOT**
  gadget found by it (12 letters, 4-bit dual-rail window).
- The full group layout, one-hot dispatch argument, and program-length
  formula for the general TM compiler (§4), modulo one named gate.
- All three required test machines, fully defined and verified as direct
  Turing machines, including the counter's ripple-carry correctness against
  an independent reference and the busy beaver's halting-by-state-slots
  behavior (§5).

Not done: the Toffoli-class (state-AND-symbol) gate search did not
converge (§3b) within this session's time/memory budget, so the R-level
and level-0 programs for the three test machines were not produced or
run, and no ticks-per-TM-step number was measured. This is reported as the
obstruction, per the task's own fallback allowance, rather than papered
over; §3b's partial analysis and the three logged search runs are meant to
let the next attempt start well past where this one had to stop.
