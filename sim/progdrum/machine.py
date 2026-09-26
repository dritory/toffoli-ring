"""Program-drum machine (HANDOVER-C, sec 0/1/3 task 1).

Data ring s of N bits, offset k >= 2, program loop p of P bits.
Global tick tau = 0,1,2,...; cell i = tau mod N. At tick tau:
    if p[tau mod P] == 1:  s[(i+k) mod N] = NAND(s[i], s[(i+1) mod N])
    else:                  nothing

Three equivalent formulations, all implemented here:
  (a) literal machine   -- run_literal / trace_literal
  (b) helix recurrence  -- trace_helix
  (c) static frame (N = mP-1, M = N+1 = mP) -- static_frame_rows

Derivation of (b) from (a):
  Define e_tau = value of cell ((tau mod N) + k) mod N right after tick tau
  (this is exactly the cell written -- or that would have been written -- at
  tick tau). Let i = tau mod N.

  Claim: e_{tau-k} is the value of cell i right after tick tau-k, and
  e_{tau-k+1} is the value of cell i+1 right after tick tau-k+1. Proof:
  ((tau-k) mod N + k) mod N = tau mod N = i (mod-N arithmetic), and likewise
  for tau-k+1 landing on i+1. Moreover cell i is only ever a *target* at
  ticks tau' with tau' = i-k (mod N), i.e. spaced exactly N apart, so the
  tick tau-k is the most recent candidate target-write of cell i before tau
  (since the next one, tau-k+N, is >= tau because N>k). Hence if the program
  bit fires at tau, s[i] and s[i+1] used in the NAND are exactly e_{tau-k}
  and e_{tau-k+1}.

  If the program bit does NOT fire at tau, cell i+k keeps whatever value it
  had after the previous tick that targeted it. Cell i+k is targeted only at
  ticks == i (mod N), spaced N apart, so the previous candidate is tau-N,
  and nothing between tau-N and tau can have touched it. So e_tau = e_{tau-N}
  (whether or not the program fired at tau-N -- e_{tau-N} already reflects
  whichever happened).

  This gives, for all tau >= 0:
      e_tau = p(tau mod P) ? NAND(e_{tau-k}, e_{tau-k+1}) : e_{tau-N}

  Initial condition: for tau in [-N,-1], set e_tau = s0[(tau+k) mod N], i.e.
  a copy of s0 rotated left by k. Consistency check: this is precisely
  "the value of the target cell after the (nonexistent) tick tau", read off
  directly from s0, which is what the definition of e demands at the start
  of time. Implemented as a circular buffer hist[j] for j = tau mod N,
  holding e_{tau-N} until it is overwritten by e_tau -- so hist is read
  *before* being written at each step, mirroring the derivation above
  exactly (it never indexes "cell i" or "cell i+k" as such; it only ever
  uses e-history at lags k, k-1, N).

Derivation of (c) from (b):
  Put M = N+1 = mP (m,P integers, so N = mP-1), write tau = r*M + x with
  x in [0,M). Since M = m*P, tau mod P = x mod P: the program's enable
  pattern depends only on the column x, identical in every row -- this is
  what makes the frame static. Define u_r(x) = e_{r*M+x}.

  For an offset d (d = k, k-1, or N = M-1), the recurrence always looks up
  e_{tau-d} = u_r(x-d) if x-d >= 0 (same row, already computed since d>0
  and we sweep x increasing), or u_{r-1}(x-d+M) if x-d < 0 (previous row;
  note x-d > -M always since d <= M-1, so a single +M wrap suffices).
  Call this ref(x,d).

  gate site   (p(x mod P)=1): u_r(x) = NAND(ref(x,k), ref(x,k-1))
  copy site   (p(x mod P)=0): u_r(x) = ref(x, M-1)     [since N = M-1]

  Two of these wrap to a *different* row than the naive same-row formula
  would suggest -- these are exactly the "exact boundary rules" asked for:

  * Gate sites at x < k: x-k < 0 always, so the first argument always reads
    the PREVIOUS row (u_{r-1}(x-k+M)). The second argument (offset k-1)
    reads the previous row too unless x = k-1 exactly, where x-(k-1) = 0 and
    it reads u_r(0) of the CURRENT row (already computed, since column 0 is
    swept first).
  * Copy sites at x = M-1 (the last column): x-(M-1) = 1-M+? -- concretely
    x-N = (M-1)-(M-1) = 0 >= 0, so instead of the generic "copy from row
    r-1, column x+1" rule (which would need a nonexistent column M), the
    LAST column of a row that is a copy site copies column 0 of its OWN row
    (already computed). All other copy sites x in [0,M-2] use the generic
    u_r(x) = u_{r-1}(x+1).

  Row r=0 is seeded directly from the first M ticks of (a)/(b) (the natural
  initial condition; no row "-1" is needed for verification since we only
  compare rows r>=1, generated purely by the frame rule, against the
  literal/helix trace).
"""
from __future__ import annotations
import random


def nand(a, b):
    return 1 - (a & b)


# ---------------------------------------------------------------- (a) -----
def run_literal_ticks(s0, p, k, ticks):
    """Run `ticks` individual ticks of the literal machine.

    Returns (s_final, e_trace) where e_trace[tau] is the value of cell
    ((tau mod N)+k) mod N right after tick tau, for tau=0..ticks-1.
    """
    N = len(s0)
    P = len(p)
    s = list(s0)
    e = [0] * ticks
    for tau in range(ticks):
        i = tau % N
        target = (i + k) % N
        if p[tau % P]:
            s[target] = nand(s[i], s[(i + 1) % N])
        e[tau] = s[target]
    return s, e


def run_literal_pass(s, p, k, n_start_tau=0):
    """Run exactly N ticks (one full pass) starting at global tick
    n_start_tau (only its value mod P matters through the loop below),
    mutating and returning a new list `s`. Used for full-state period
    checks (Brent) where only "one pass = one step" matters and phase
    continuity across passes is preserved by the caller via tau0 tracking.
    """
    N = len(s)
    P = len(p)
    s = list(s)
    for di in range(N):
        tau = n_start_tau + di
        i = tau % N
        if p[tau % P]:
            target = (i + k) % N
            s[target] = nand(s[i], s[(i + 1) % N])
    return s


# ---------------------------------------------------------------- (b) -----
def trace_helix(s0, p, k, ticks):
    """Pure recurrence form: e_tau = p(tau%P) ? NAND(e_{tau-k},e_{tau-k+1})
    : e_{tau-N}, implemented with only a size-N circular history buffer
    (no s[i]/s[i+k] indexing). Returns e_trace[0..ticks-1].
    """
    N = len(s0)
    P = len(p)
    assert N > k, "need N > k for the lag-k/lag-(k-1) reads to stay within one pass"
    hist = [s0[(j + k) % N] for j in range(N)]  # hist[j] = e_{j-N}
    e = [0] * ticks
    for tau in range(ticks):
        j = tau % N
        if p[tau % P]:
            a = hist[(tau - k) % N]
            b = hist[(tau - k + 1) % N]
            val = nand(a, b)
        else:
            val = hist[j]  # this is e_{tau-N}, not yet overwritten
        hist[j] = val
        e[tau] = val
    return e


# ---------------------------------------------------------------- (c) -----
def static_frame_rows(p, k, m, row0, n_rows, s=1):
    """Given row0 (length M = m*len(p) list of bits = e_0..e_{M-1}), compute
    n_rows further rows (r=1..n_rows) by the static-frame rule. Returns a
    list of rows (each length M), rows[0] = row0, rows[1..n_rows] computed.

    s generalises N = M-1 (task 1) to N = M-s (task 2b), s = 1..P-1
    (s=0 is the dead case, P|N, out of scope here). Copy sites then read
    u_{r-1}(x+s) when x+s < M, and -- the generalised boundary rule --
    u_r(x+s-M) (the SAME row's column x+s-M, in [0,s-1], already computed)
    when x+s >= M, i.e. for the last s columns of the row.
    """
    P = len(p)
    M = m * P
    N = M - s

    def ref(cur, prev, x, d):
        idx = x - d
        if idx >= 0:
            return cur[idx]
        return prev[idx + M]

    rows = [list(row0)]
    prev = row0
    for _r in range(n_rows):
        cur = [0] * M
        for x in range(M):
            if p[x % P]:
                a = ref(cur, prev, x, k)
                b = ref(cur, prev, x, k - 1)
                cur[x] = nand(a, b)
            else:
                cur[x] = ref(cur, prev, x, N)
        rows.append(cur)
        prev = cur
    return rows


# ------------------------------------------------------------ helpers -----
def to_str(bits):
    return "".join("#" if b else "." for b in bits)


def random_bits(n, rng):
    return [rng.randint(0, 1) for _ in range(n)]


def find_period_brent(s0, step_fn, cap=200000):
    """Brent cycle detection on the sequence s0, step_fn(s0), step_fn^2(s0),
    ... . Returns (mu, lam) transient/period in units of step_fn calls, or
    (None, None) if cap exceeded.
    """
    s0 = list(s0)
    power = lam = 1
    tortoise = s0
    hare = step_fn(s0)
    steps = 1
    while tortoise != hare:
        if power == lam:
            tortoise = hare
            power *= 2
            lam = 0
        hare = step_fn(hare)
        lam += 1
        steps += 1
        if steps > cap:
            return None, None
    tortoise = list(s0)
    hare = list(s0)
    for _ in range(lam):
        hare = step_fn(hare)
        steps += 1
        if steps > cap:
            return None, None
    mu = 0
    while tortoise != hare:
        tortoise = step_fn(tortoise)
        hare = step_fn(hare)
        mu += 1
        steps += 1
        if steps > cap:
            return None, None
    return mu, lam


def find_M(e, search_max, verify_window):
    """Smallest M in [1,search_max] with e[M:M+verify_window] == e[0:verify_window].
    e must have length >= search_max + verify_window."""
    pattern = "".join("1" if b else "0" for b in e[:verify_window])
    full = "".join("1" if b else "0" for b in e)
    idx = full.find(pattern, 1)
    if idx == -1 or idx > search_max:
        return None
    return idx


def helix_period_search(s0, p, k, warmup_passes, search_mult, verify_mult):
    """Run trace_helix long enough, skip warmup_passes*N ticks, then search
    for the smallest M (tick lag) with e_tau=e_{tau-M}. Returns M or None."""
    N = len(s0)
    warmup = warmup_passes * N
    search_max = search_mult * N
    verify = verify_mult * N
    total = warmup + search_max + verify + 1
    e = trace_helix(s0, p, k, total)
    return find_M(e[warmup:], search_max, verify)
