# Milestone 2 plan: pointer follows the head (constant ticks per TM step)

Files: sim/compile/follow.py (copy of sweep.py, extended), sim/compile/verify_follow.py.
sweep.py / verify_sweep.py stay untouched.

## Layout change
Group = milestone-1 group (s-block + |Q| state blocks) + a 12-cell MOVE block appended:
  +0 dp (rest 0)  +1 dp_gap (1)  +2 dpbar (1)  +3..5 dp write markers (0,1,1)
  +6 dm (rest 0)  +7 dm_gap (1)  +8 dmbar (1)  +9..11 dm write markers (0,1,1)
dp = 1 iff the fired rule moves +1, dm = 1 iff it moves -1 (two bits, because the
counter uses direction-0 rules (C0,0 -> 1,0,C0) and HALT idles with direction 0;
a single d bit cannot express "stay").

## One pass (fixed R word, same for every n_groups >= 3)
1. milestone-1 group word on the head group (arrival merge, TOFF compute, symbol
   write, neighbour state write, self-clear), plus for every rule with dir=+1:
   forward GAPCNOT(firebar -> dp); dir=-1: forward GAPCNOT(firebar -> dm).
   (firebar+1 = sp8 = const 1, markers dp+3..5 / dm+3..5.)
2. dp chain: at dp emit CN (branch+ moves, others read dp=0 and stay), then for
   D = 1..G-1 move unconditionally to a cell r with const(r)=0 and const(r+D)=1
   (constants = whitelisted permanent cells, periodic in the group) and emit CN.
   Branch+ ends offset +G.
3. dm chain: same with CP: CP at dm, then r with const(r)=0, const(r-E)=1.
   Branch+ reads r+G = same offset in the next group -> const 0 -> stays.
   Branch- ends offset -G, branch0 (dir 0) offset 0.
4. goto reference 0 (= start of the new head group in every branch).
5. GAPCLEAR (dp,dpbar) and (dm,dmbar) in groups -1, 0, +1 relative to the new
   head (value-independent; covers the old head in all three branches), goto 0.

## Verification
- R level: one pass = one TM step exactly. After every pass compare the WHOLE ring
  cell-for-cell with the expected tape built from tm.py's reference config
  (symbols, state token in arrL/arrR/q of the new head, every other cell at rest),
  and pointer == G*head. Counter 300, echo 50 (poke input into group 0 before
  READ passes), BB(2,2) to halt; 12/24/48 groups each.
- Assert the pass word is identical for 12/24/48 groups.
- Level 0: expand with MACRO, run_l0 (copied verbatim; importing
  verify_level0_independent runs its main), compare dual-rail tape and pointer
  with the R run after every pass, all three machines, 12/24/48 groups.
- Also: exhaustive-ish unit check of the chains (random constant-respecting tapes).

## Steps
a. copy sweep.py -> follow.py; add MOVE block + dp/dm writes; test milestone-1-style.
b. chain generator + unit test.  c. pass assembly + R verify.  d. level 0.  e. report.
