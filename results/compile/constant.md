# Milestone 2: pointer follows the head (constant ticks per TM step)

Status: **done**. Reproduce: `python3 sim/compile/verify_follow.py` (log:
`results/compile/follow_verify.log`; `--no-l0` skips level 0). Compiler:
`sim/compile/follow.py` (a copy of `sweep.py`, which is still unchanged, as is
`verify_sweep.py`). Plan: `constant_plan.md`.

## Construction
- One pass = the milestone-1 group word run on the head group only, then a
  conditional group move. It starts and ends at offset 0 of the head group.
- Each group gets a 14-cell MOVE block after its state blocks: `dp` and `dm`,
  each a forward dual-rail pair `(t, gap, tbar)` with write markers 0,1,1 at
  t+3..5, plus two padding constants.
- Deviation from the brief: there are **two** direction bits. `dp=1` means
  move +1 and `dm=1` means move -1. One bit `d` cannot say "stay", and both the
  counter (`C0,0 -> 1,0,C0`) and HALT use direction 0. Each rule with a
  non-zero direction adds one forward `GAPCNOT(firebar -> dp|dm)`. It sits next
  to the milestone-1 neighbour write of the new state bit, which is unchanged.
- **+G chain.** The chain starts with `CN` on `dp`. Then, for D = 1..G-1:
  1. Move unconditionally to a cell r where `const(r)=0` and `const(r+D)=1`.
  2. Emit `CN`.

  The branch that is not moving sits on a 0 and stays. The moving branch sits
  on a 1 and advances. The constants are 32 whitelisted permanent cells per
  group (the same in every group), audited across the whole ring before every
  move.
- **-G chain.** The same idea with `CP`, starting on `dm`. The +G branch now
  reads the same offset one group ahead, which is a constant 0 or that group's
  own `dm` (0), so it stays.
- **Clear.** After the move, from the new head: `GAPCLEAR(m=3)` of
  `(dp,dpbar)` and `(dm,dmbar)` in groups -1, 0 and +1. This does not depend on
  the values, and it covers the old head whichever way the move went.
- The pass word is **bit-identical for 12, 24 and 48 groups** (asserted by
  comparing the words). It needs n_groups >= 3.

## Numbers
Level-0 ticks per letter: F=3, N=6, P=12, CN=6, CP=12 (MACRO lengths).
Every tick counts, including skipped instructions.

| machine | \|Q\| | G | R letters/pass (group word + move/clear) | level-0 ticks/pass | ticks per TM step, 12 / 24 / 48 groups |
|---|---:|---:|---:|---:|---|
| counter L=3 | 4 | 150 | 13,615 (10,733 + 2,882) | 120,750 | 120,750 / 120,750 / 120,750 |
| echo | 3 | 119 | 10,807 (8,539 + 2,268) | 95,880 | 95,880 / 95,880 / 95,880 |
| BB(2,2) | 3 | 119 | 8,449 (6,181 + 2,268) | 74,808 | 74,808 / 74,808 / 74,808 |

- One pass is exactly one TM step, so ticks per step = ticks per pass. This is
  independent of the number of groups.
- The move/clear part costs 20–26k ticks. G is 14 more than in milestone 1.
- For comparison, milestone 1 averaged 112k ticks per step for the counter on
  a 3-group ring (the counter's cost grows with ring size), and 251k for
  BB(2,2) on 12 groups.

## Verification (all passed)
After **every pass**, at both levels:
- **R level:** the whole ring is compared cell for cell with the tape
  expected from `tm.py`'s reference config. That means the symbols, the state
  token in the new head's `arrL` / `arrR` / `q`, and every other cell at its
  rest value, including dp/dm cleared. The pointer must equal `head*G`. All
  permanent constants in the ring are also audited in the middle of each
  pass, before the move.
- **Level 0:** `run_l0` (copied verbatim) runs on the dual-rail tape. Its tape
  and pointer are compared with the R run.

| machine | per ring size | 12 + 24 + 48 total (R and level 0 each) |
|---|---|---:|
| counter | 300 steps | 900 |
| echo | 50 steps, fresh random input poked into group 0 before each READ pass | 150 |
| BB(2,2) | halts after 6 steps (4 ones, state HALT), plus 3 idle passes after halting | 27 |

Mutation checks: both of these broken words were caught.
- Deleting one `CP` from the chain: caught by the pointer check.
- Omitting the dp/dm clear: caught by the full-tape check.

## Bugs found
1. The chain generator found no (const 0, const 1) pair at offset
   D = 136 for the counter (G = 148 before the fix), i.e. exactly the milestone-1 group width, the one distance
   that all the periodic constants miss. Fixed by adding two padding constants
   (`pad0=0`, `pad1=1`) to the MOVE block.

No other failures. Everything passed on the first full run after that.

## Unresolved / not done
- The chain is greedy and not optimised: about 2,300–2,900 letters for 2G
  conditional steps. A longer run of constant 1s would shorten it.
- A direction-0 rule that goes to a different state is still
  `NotImplementedError`, as in milestone 1. None of the test machines needs it.
- n_groups <= 2 was not tested; it is not supported, because the left and
  right neighbours coincide.
