"""Sequential one-NAND ring, and R3 (three-input NAND) ring.

General one-NAND geometry (a,b,c), a<b, any c:
    s[i+c] = NOT(s[i+a] AND s[i+b])       (indices mod N)
applied for i = 0..N-1 in order, each write visible to later steps.

R3(k):
    s[i+k] = NOT(s[i] AND s[i+1] AND s[i+k])
"""
import random


def nand_pass(s, a, b, c):
    """One pass of s[i+c] = NOT(s[i+a] & s[i+b]), i=0..N-1 in order."""
    n = len(s)
    s = list(s)
    for i in range(n):
        va = s[(i + a) % n]
        vb = s[(i + b) % n]
        s[(i + c) % n] = 1 - (va & vb)
    return s


def nand_ahead_pass(s, k):
    """s[i+k] = NOT(s[i] & s[i+1]); the specified rule, a=0,b=1,c=k."""
    return nand_pass(s, 0, 1, k)


def r3_pass(s, k):
    """s[i+k] = NOT(s[i] & s[i+1] & s[i+k])."""
    n = len(s)
    s = list(s)
    for i in range(n):
        v0 = s[i % n]
        v1 = s[(i + 1) % n]
        vk = s[(i + k) % n]
        s[(i + k) % n] = 1 - (v0 & v1 & vk)
    return s


def to_str(bits):
    return "".join("#" if b else "." for b in bits)


def from_str(t):
    return [1 if c in "#1" else 0 for c in t]


def random_bits(n, rng):
    return [rng.randint(0, 1) for _ in range(n)]


def find_period(s0, step_fn, cap=10**6):
    """Return (transient, period) by Floyd/Brent-style cycle detection using a
    dict of seen states -> step index (states are tuples, hashable)."""
    seen = {}
    cur = tuple(s0)
    t = 0
    seen[cur] = 0
    while True:
        cur = tuple(step_fn(list(cur)))
        t += 1
        if cur in seen:
            transient = seen[cur]
            period = t - transient
            return transient, period
        seen[cur] = t
        if t > cap:
            return None, None  # exceeded cap


def find_period_brent(s0, step_fn, cap=10**6):
    """Brent's cycle-detection algorithm: O(1) extra memory (besides the two
    current states), O(transient+period) step_fn calls (each bounded by cap).
    Returns (transient mu, period lam), or (None, None) if cap exceeded."""
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
    # find mu: first index where the cycle is entered
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
