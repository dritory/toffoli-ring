"""General model: cyclic ring s of N bits, offset k, latch bit q.

Pass: for i = 0..N-1 in order:
    x = s[i+k]; a = s[i]; b = s[i+1]           (indices mod N)
    s[i+k] = f(q, x, a, b)
    q       = g(q, x, a, b)

f, g given as 16-bit truth tables, input order (q,x,a,b) as bits (3,2,1,0):
    idx = 8*q + 4*x + 2*a + b
    f(q,x,a,b) = (f_tt >> idx) & 1
"""


def eval_tt(tt, q, x, a, b):
    idx = (q << 3) | (x << 2) | (a << 1) | b
    return (tt >> idx) & 1


def pass_latch(s, q, k, f_tt, g_tt):
    n = len(s)
    s = list(s)
    for i in range(n):
        x = s[(i + k) % n]
        a = s[i]
        b = s[(i + 1) % n]
        y = eval_tt(f_tt, q, x, a, b)
        q = eval_tt(g_tt, q, x, a, b)
        s[(i + k) % n] = y
    return s, q


# f = x XOR (a AND b): as a function of (q,x,a,b), independent of q.
# truth table: for idx=8q+4x+2a+b, value = x ^ (a & b)
def build_xor_ab_tt():
    tt = 0
    for idx in range(16):
        q = (idx >> 3) & 1
        x = (idx >> 2) & 1
        a = (idx >> 1) & 1
        b = idx & 1
        v = x ^ (a & b)
        tt |= (v << idx)
    return tt


if __name__ == "__main__":
    import random
    import sys
    sys.path.insert(0, "/home/user/toffoli-ring/sim")
    import ring

    f_tt = build_xor_ab_tt()
    g_tt = 0  # ignored / irrelevant; use constant, q never affects f here

    trials = 2000
    for _ in range(trials):
        n = random.randint(4, 40)
        k = random.randint(2, min(6, n - 1))
        s = [random.randint(0, 1) for _ in range(n)]
        q0 = random.randint(0, 1)
        expected = ring.pass_(s, k)
        got, q1 = pass_latch(s, q0, k, f_tt, g_tt)
        assert got == expected, (s, k, got, expected)
    print(f"OK: {trials} random (N,k,s,q) trials match sim/ring.py pass_ exactly "
          f"with f = x^(a&b), g ignored (f_tt=0x{f_tt:04x}).")
