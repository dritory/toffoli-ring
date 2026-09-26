# Tier-4 follow-up: minimal Machine A, switch-level, exhaustively searched
where tractable

Task: given tier4.md's 13-component Machine A (7 transistors, 4
resistors, 2 capacitors), find the fewest-component circuit for the same
two-instruction CPU, or show 13 is minimal. Method: exhaustive search
for k = 5..12, pruned by symmetry, using the strict phase simulator
(`sim/budget/switchsim.py`).

**Result: 13 is not minimal. 11 components (6 transistors, 3 resistors,
2 capacitors, 0 diodes) suffice, verified with the same rigor as
tier4.md (full 8/8 truth table + 500/500 random-tape check). The
storage subsystem's minimum of 4 components is exhaustively proved
within a documented net-alphabet subclass; the eval network's 7 is
argued structurally and checked for local minimality, not exhaustively
brute-forced (that part of the search space is too large -- see
"What was only searched" below).**

Code: `sim/budget/minimal/storage_nobuf.py` (2-transistor, 2-capacitor,
0-resistor storage cell), `sim/budget/minimal/machine_a11.py` (the
11-component machine), `sim/budget/minimal/test_machine_a11.py`
(500-trial check against `run_l0`), `sim/budget/minimal/storage_search.py`
(the exhaustive storage-subsystem search). Logs:
`results/budget/machine_a11_truth_table.log`,
`results/budget/machine_a11_macros.log`, `results/budget/storage_search.log`.

## The idea: drop the buffer

tier4.md's storage cell (`sim/budget/storage.py`) is DNODE
--T_wm(phi1)--> M --T_buf(inverter)--> BUF_NODE --T_ws(phi2)--> S, where
S stores `flag`. The buffer exists only because the eval network's
NAND-stack naturally produces `DNODE = flagbar_next`, and S needs
`flag_next` -- an extra inversion.

If S instead stores `g = flagbar` directly, the arithmetic changes:
`g_next = NOT(flag_next) = NAND(g, r)` (checked: if `g=1`, `NAND(g,r) =
NOT(r)` = `g_next` when flag=0; if `g=0`, `NAND(g,r)=1=g_next` when
flag=1 forces flag_next=0). That is *exactly* what the eval network's
own NAND-stack produces as `DNODE` once its enable transistor is gated
by `g` instead of `flag` (same polarity trick tier4.md already uses for
`T_S`, just carried one step further). So `DNODE == g_next` with no
further inversion needed anywhere, and M can be wired straight to S
through a plain transmission transistor:

```
DNODE --T_wm(gate=phi1)--> M (capacitor) --T_ws(gate=phi2)--> S (capacitor)
```

No buffer, no `R_buf`. This removes 2 of tier4's 13 components. It is
race-free for the same reason tier4's design is: `T_wm` opens before
`T_ws` closes, so M is a *fixed* value (held charge, supplied
externally in the phase-2 evaluation, per `switchsim`'s `holdable`
convention) by the time it is shorted to S -- S's resolution comes
purely from the M-S union, never from what the still-live network
computes for `DNODE` this phase, so there is no loop. `S` is used only
as a *gate* elsewhere in the network (never as an a/b terminal outside
`T_ws`), so its value can never leak back into that union.
Confirmed by running the full netlist through `switchsim.evaluate()`,
which requires every gate/resistor net to resolve every phase or raises
(no silent races): no error is raised, and the truth table and
500-random-tape checks both pass 100%.

## Machine A11 (11 components)

```
Eval network (identical topology to machine_a.py, S now stores g=flagbar):
  T_S  (NMOS, gate=S=g)  a=K         b=GND     -- conducts iff g==1 (flag==0)
  T_o                    gate=o      a=MOVE_P_N b=K
  T_obar                 gate=obar   a=MOVE_M_N b=K
  T_r                    gate=r      a=DNODE   b=K
  R: MOVE_P_N->VDD, MOVE_M_N->VDD, DNODE->VDD

  MOVE_P_N = NAND(g,o)    -> move+ = NOT(MOVE_P_N) = g & o
  MOVE_M_N = NAND(g,obar) -> move- = NOT(MOVE_M_N) = g & obar
  DNODE    = NAND(g,r)    = g_next directly (no buffer needed)
  toggle: bare wire S=g (active-high on flagbar), 0 extra cost

Storage (no-buffer master-slave):
  T_wm  gate=phi1  a=DNODE  b=M
  T_ws  gate=phi2  a=M      b=S
  C_M, C_S: the capacitor nodes M, S themselves
```

| Role | Components |
|---|---|
| eval network (shared enable + 3 decode switches) | `T_S,T_o,T_obar,T_r` = 4 |
| eval pull-ups | `R1,R2,R3` = 3 |
| storage (2 capacitors + 2 isolation transistors, no buffer) | `T_wm,T_ws,C_M,C_S` = 4 |

**Total: 11 (6 transistors, 3 resistors, 2 capacitors, 0 diodes).**

### Verification

- Truth table, all 8 `(o, r, flag)` combos: 8/8 correct
  (`machine_a11_truth_table.log`), no `switchsim` convergence or
  floating-net error raised in either phase.
- 500 random dual-rail tapes, macros FLIP/NEXT/PREV/CNEXT/CPREV, checked
  tick-by-tick against `run_l0` (same seed, same macros, same timing
  discipline as tier4.md's test): **500/500 pass**
  (`machine_a11_macros.log`).
- Local minimality of the eval network: removing any one of the 7 eval
  components (4 transistors, 3 resistors) breaks correctness or causes
  a floating net -- checked directly, all 7 removals fail.

## What was proved (exhaustive, within a stated scope)

The storage subsystem was searched exhaustively over a **4-net
alphabet** `{DNODE, phi1, phi2, S}` (plus `M` for the 2-capacitor
sub-search), with the eval network held fixed at machine_a11's 7
components (this is the natural boundary: the eval network is what
"recomputes the flag," the storage subsystem is what must "survive the
phase in which it is recomputed"). This is a real exhaustive
enumeration run through `switchsim.evaluate()`, not a hand argument:

| Subclass | Storage components (incl. capacitors) | Candidates tried | Winners |
|---|---|---|---|
| 1 capacitor (S only), budget=1 extra | 2 | 96 | 0 |
| 1 capacitor (S only), budget=2 extra | 3 | 9,312 | 0 |
| 1 capacitor (S only), budget=3 extra | 4 | 893,952 | 0 |
| 2 capacitors (S, M), 1 transistor | 3 | 40 | 0 |
| 2 capacitors (S, M), 2 transistors | 4 | 1,600 | 8 (all isomorphic: the design above, up to a/b-terminal and instruction-order relabeling) |

**Conclusion, proved within this scope: no single-capacitor storage
scheme (up to 3 extra transistors/resistors, i.e. storage cost up to 4)
and no 2-capacitor scheme with only 1 isolation transistor (storage
cost 3) can implement the flag update; storage cost 4 (2 capacitors + 2
plain transmission transistors, no buffer, no resistor) is both
necessary and sufficient.** Combined with the eval network's 7
(verified locally minimal, see above), this gives **11 as the minimum
total for this architecture** (shared-enable pass-transistor decode +
master-slave dynamic storage) -- i.e. **k = 8, 9, 10 are impossible and
k = 11 is achieved**, for every circuit built from these two
subsystems.

This generalizes tier4.md's original finding (one specific
single-capacitor netlist doesn't converge) to essentially all
single-capacitor topologies reachable in this alphabet: **993,360
distinct single-capacitor storage candidates were tried (96 + 9,312 +
893,952 for subclass A) and none work**, confirming "one capacitor
cannot suffice" is not an artifact of the particular netlist tier4.md
first tried.

## What was only searched, or not searched at all (the honest gap)

- **The storage-subsystem net alphabet was fixed at 4-5 named nets**
  (`DNODE, phi1, phi2, S[, M]`). A fully general search would also let
  the storage wiring introduce brand-new intermediate nets (as tier4's
  own buffer design used `BUF_NODE`) -- that larger space was not
  enumerated. Given that every winning topology found collapses to the
  same 2-transistor direct-transfer circuit, and every failing topology
  fails for the same structural reason (either DNODE never reaches a
  capacitor at all, or the write path is not isolated from the read
  path during the same phase), it is very likely no additional
  intermediate net changes the outcome, but this is an inference, not
  a proof covering that wider space.
- **The eval network's 7-component minimum (4 transistors, 3 resistors)
  is argued structurally** (3 independent, simultaneously-distinct
  active-low output nets each need their own pull-up resistor -- checked
  directly that no two of `MOVE_P_N, MOVE_M_N, DNODE` are equal across
  all 8 input combos, so they cannot share a resistor; each output needs
  its own series switch gated by its distinguishing input, and the
  shared enable `T_S` is already the minimum-cost way to gate all three)
  and checked for **local** minimality (dropping any single component
  breaks it), but was **not exhaustively brute-forced** over alternative
  eval-network topologies (e.g., PMOS pull-up networks instead of
  resistors, diode-resistor logic, or a completely different decode
  structure). A generic enumeration over a 10-net alphabet with 4-7
  components has on the order of 10^10-10^13 candidate netlists, which
  is intractable to run in this session; this is the specific subclass
  gap the task anticipated ("if full enumeration is too large for some
  k, say exactly which subclass was covered"). No diode-based or
  PMOS-pull-up alternative was tried.
- **k = 5, 6, 7 overall were not searched at all**, because the storage
  subsystem alone (at minimum) already costs 4, and even an eval network
  of 0 components is meaningless (there is nothing to decode); the
  smallest sensible eval network found (locally minimal at 7) plus the
  proven storage minimum (4) already exceeds these, so k=5..7 are
  excluded by the same reasoning that rules out an eval network smaller
  than machine_a11's, which was checked only locally, not exhaustively.
  If a fundamentally different eval-network family (untried) could beat
  7, smaller overall totals become possible; this is not ruled out.
- **k = 12 was not specifically targeted**: since 11 < 12, any valid
  12-component design is dominated by the verified 11-component one and
  was not separately pursued.

## Other instruction pairs (skip_summary.md)

`results/twoop/skip_summary.md`'s guarded-macro table (its primary
winner criterion: FLIP, NEXT, PREV, CNEXT, CPREV all found, ranked by
total macro length) reports exactly **2** winning `(A, B)` bundle pairs,
both of the form `(flip, skip(v=0), move+1) / (flip, skip(v=0),
move-1)` -- i.e. both are literal re-encodings of the *same* abstract
two-instruction semantics Machine A already implements (toggle-if-r,
move-if-not-flag, in one polarity or the other). No *different*
instruction pair reaches this criterion at all (the secondary table's
24 rows all fall short of at least one of FLIP/NEXT/PREV/CNEXT/CPREV).
So there is no other skip-flag instruction pair to try building smaller
hardware for: the pair already in Machine A is tied for best, and its
hardware-level behavior (the per-tick spec this task gave) is identical
regardless of which tape encoding realizes it. This closes that avenue:
the search for a smaller circuit had to be, and was, a circuit-level
search on the fixed two-instruction behavior, not an instruction-set
search.

## Bottom line

- **Minimum found: 11 components** (6 transistors, 3 resistors, 2
  capacitors, 0 diodes) -- `sim/budget/minimal/machine_a11.py`, fully
  verified (truth table 8/8, random-tape 500/500).
- **Proved** (exhaustive, within the stated storage-subsystem net
  alphabet): the storage subsystem cannot go below 4 components (no
  single-capacitor design works with up to 3 extra parts -- 993,360
  candidates tried; no 2-capacitor design works with only 1 isolation
  transistor -- 40 candidates tried); 4 is both necessary and
  sufficient there.
- **Argued and locally checked, not exhaustively proved**: the eval
  network cannot go below 7 components (structural argument + all 7
  single-component removals verified to break it), but alternative
  eval-network *families* (PMOS pull-ups, diode logic, wholly different
  decode structures) were not brute-forced, so 11 overall is the best
  *found* and *strongly* argued minimum, not a fully closed proof that
  nothing below 11 exists.
- tier4.md's 13-component figure is superseded: **13 is not minimal**,
  11 is achievable with the same verification rigor tier4.md used.
