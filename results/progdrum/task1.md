# Task 1: machine equivalence, dead case, contrast

## (a) = (b) = (c) check

2000 random instances of (m, P, k, p, s0), N = mP-1. For each: P in [2,14], m in [2,10], k in [2,6] with N > k+1 enforced by resampling. Compare the literal machine (a) and the pure helix recurrence (b) tick-by-tick over 6 rows (6 * M ticks), and the static frame (c) row-by-row for rows 1..5 (row 0 seeded from (a)/(b)).

* (a) == (b): 2000/2000 instances matched on every tick.

* (a) == (c): 2000/2000 instances matched on every row checked.


No failures. (a), (b) and (c) are numerically identical on every instance.


## Dead case: P | N (N = mP)

200 random instances with N = mP (P divides N exactly), random p, random s0. For each: (i) helix-period search (as in `sim/nand/helix.py`) for the smallest tick-lag M' with e_tau = e_{tau-M'}, warmup 5N ticks, search up to 40N, verify over 5N; (ii) full ring-state period in PASSES via Brent's algorithm on one-pass-at-a-time state transitions (state = the whole s array after a full pass, phase-continuous across passes), cap 4*2^k passes. Lemma A predicts state period <= 2^k passes (independent of N).

* helix-period M' found (<=40N) for 200/200 instances.

  M'/N: min=0.12 median=1.00 max=2.00 (bounded by a small multiple of N regardless of N -- this is the 'small M' after a short transient' the dead case predicts).

* full ring-state period (passes) within the <=2^k bound: 200/200 (remaining had lam=None, i.e. exceeded the 4*2^k-pass cap -- see below).

* Brent search exceeded cap (state period > 4*2^k passes, or not periodic in cap): 0/200


| k | 2^k | count | min(lam) | median(lam) | max(lam) | all <= 2^k? |

|---|---|---|---|---|---|---|

| 2 | 4 | 40 | 1 | 1.0 | 3 | True |

| 3 | 8 | 54 | 1 | 1.0 | 2 | True |

| 4 | 16 | 69 | 1 | 1.0 | 7 | True |

| 5 | 32 | 37 | 1 | 1.0 | 3 | True |


## Contrast: N = mP-1 (live case), random p

Same two measurements (helix-period search, full-state period via Brent on whole passes) for N = mP-1, fixed (P,k), m increasing, random p and s0 (30 seeds per (P,k,m)). Question: does the helix-period / full-state period grow with N, unlike the dead case above?


| P | k | m | N | helix-M' found/n | median M'/N (found only) | full-state period found/n (cap 200 passes) | median period (passes, found only) |

|---|---|---|---|---|---|---|---|

| 5 | 2 | 2 | 9 | 14/20 | 0.333 | 8/20 | 1.0 |

| 5 | 2 | 4 | 19 | 9/20 | 1.579 | 4/20 | 60.0 |

| 5 | 2 | 8 | 39 | 7/20 | 1.154 | 2/20 | 20.5 |

| 5 | 2 | 16 | 79 | 4/20 | 2.025 | 0/20 | - |

| 5 | 2 | 24 | 119 | 7/20 | 1.050 | 3/20 | 1.0 |

| 5 | 3 | 2 | 9 | 14/20 | 0.556 | 6/20 | 5.0 |

| 5 | 3 | 4 | 19 | 12/20 | 0.263 | 6/20 | 1.0 |

| 5 | 3 | 8 | 39 | 11/20 | 0.128 | 5/20 | 5.0 |

| 5 | 3 | 16 | 79 | 9/20 | 0.063 | 4/20 | 5.0 |

| 5 | 3 | 24 | 119 | 9/20 | 0.042 | 3/20 | 5.0 |

| 5 | 4 | 2 | 9 | 11/20 | 2.778 | 10/20 | 1.0 |

| 5 | 4 | 4 | 19 | 15/20 | 2.368 | 2/20 | 20.0 |

| 5 | 4 | 8 | 39 | 14/20 | 2.179 | 1/20 | 1.0 |

| 5 | 4 | 16 | 79 | 11/20 | 2.089 | 0/20 | - |

| 5 | 4 | 24 | 119 | 15/20 | 2.059 | 0/20 | - |

| 8 | 2 | 2 | 15 | 4/20 | 0.700 | 3/20 | 16.0 |

| 8 | 2 | 4 | 31 | 4/20 | 1.677 | 1/20 | 1.0 |

| 8 | 2 | 8 | 63 | 4/20 | 2.032 | 0/20 | - |

| 8 | 2 | 16 | 127 | 2/20 | 1.543 | 0/20 | - |

| 8 | 2 | 24 | 191 | 4/20 | 2.010 | 0/20 | - |

| 8 | 3 | 2 | 15 | 11/20 | 0.333 | 5/20 | 1.0 |

| 8 | 3 | 4 | 31 | 8/20 | 1.806 | 3/20 | 11.0 |

| 8 | 3 | 8 | 63 | 7/20 | 2.159 | 1/20 | 5.0 |

| 8 | 3 | 16 | 127 | 9/20 | 2.079 | 0/20 | - |

| 8 | 3 | 24 | 191 | 6/20 | 1.592 | 1/20 | 5.0 |

| 8 | 4 | 2 | 15 | 2/20 | 2.000 | 5/20 | 1.0 |

| 8 | 4 | 4 | 31 | 2/20 | 1.097 | 0/20 | - |

| 8 | 4 | 8 | 63 | 0/20 | - | 0/20 | - |

| 8 | 4 | 16 | 127 | 1/20 | 2.331 | 0/20 | - |

| 8 | 4 | 24 | 191 | 4/20 | 2.220 | 0/20 | - |

| 11 | 2 | 2 | 21 | 1/20 | 0.143 | 5/20 | 22.0 |

| 11 | 2 | 4 | 43 | 1/20 | 2.047 | 0/20 | - |

| 11 | 2 | 8 | 87 | 0/20 | - | 0/20 | - |

| 11 | 2 | 16 | 175 | 3/20 | 2.011 | 0/20 | - |

| 11 | 2 | 24 | 263 | 1/20 | 2.008 | 0/20 | - |

| 11 | 3 | 2 | 21 | 5/20 | 1.048 | 2/20 | 11.5 |

| 11 | 3 | 4 | 43 | 0/20 | - | 0/20 | - |

| 11 | 3 | 8 | 87 | 0/20 | - | 0/20 | - |

| 11 | 3 | 16 | 175 | 0/20 | - | 0/20 | - |

| 11 | 3 | 24 | 263 | 1/20 | 2.133 | 0/20 | - |

| 11 | 4 | 2 | 21 | 9/20 | 0.333 | 3/20 | 11.0 |

| 11 | 4 | 4 | 43 | 3/20 | 2.814 | 3/20 | 1.0 |

| 11 | 4 | 8 | 87 | 2/20 | 2.402 | 0/20 | - |

| 11 | 4 | 16 | 175 | 2/20 | 2.137 | 0/20 | - |

| 11 | 4 | 24 | 263 | 3/20 | 2.133 | 0/20 | - |


Interpretation: in the dead case (P|N) the helix-period M' stays a small multiple of N and the full-state period stays <= 2^k passes *for every N tested* (a fixed constant, independent of N). In the live case (N=mP-1), search bounds scaled to 3N/5N frequently find NO M' at all as m grows (period, if any, exceeds the bound tested), and the full-state period search (cap 200 passes) also increasingly fails to terminate -- consistent with periods that grow with N rather than saturating at a k-dependent constant.
