"""Sequential Toffoli ring.

A pass applies, for i = 0..N-1 in order,
    s[i+k] ^= s[i] & s[i+1]        (indices mod N)
The write at step i is visible to later steps of the same pass.

Two equivalent views are implemented and cross-checked:

  * pass(s, k): the literal sequential rule on a list of bits.
  * transducer view: the new row y is produced left to right by a
    k-bit shift register of the *outputs*,
        y[j] = x[j] ^ (y[j-k] & y[j-k+1])
    with y[j] for j < 0 taken from the tail of the previous row (helix).

The second view is the NLFSR  e_t = e_{t-N} ^ e_{t-k} e_{t-k+1}.
"""


def pass_(s, k):
    n = len(s)
    s = list(s)
    for i in range(n):
        if s[i] and s[(i + 1) % n]:
            s[(i + k) % n] ^= 1
    return s


def pass_transducer(s, k):
    """Same map, written as the k-window transducer. Row index j corresponds
    to ring cell (j + k) mod N; the window seed is the tail of the old row."""
    n = len(s)
    # row view: x[j] = s[(j+k) % n]
    x = [s[(j + k) % n] for j in range(n)]
    y = [0] * n
    for j in range(n):
        a = y[j - k] if j - k >= 0 else x[j - k + n]
        b = y[j - k + 1] if j - k + 1 >= 0 else x[j - k + 1 + n]
        y[j] = x[j] ^ (a & b)
    out = [0] * n
    for j in range(n):
        out[(j + k) % n] = y[j]
    return out


def inverse_pass(s, k):
    n = len(s)
    s = list(s)
    for i in reversed(range(n)):
        if s[i] and s[(i + 1) % n]:
            s[(i + k) % n] ^= 1
    return s


def to_int(bits):
    v = 0
    for b in reversed(bits):
        v = (v << 1) | b
    return v


def from_int(v, n):
    return [(v >> i) & 1 for i in range(n)]


def to_str(bits):
    return "".join("#" if b else "." for b in bits)


def from_str(t):
    return [1 if c in "#1" else 0 for c in t]


def orbit_period(s, k, limit=10**7):
    """Period of the orbit through s (every orbit is a cycle: the map is a bijection)."""
    s0 = list(s)
    cur = pass_(s0, k)
    t = 1
    while cur != s0:
        cur = pass_(cur, k)
        t += 1
        if t > limit:
            return None
    return t


def run(s, k, passes):
    out = [list(s)]
    for _ in range(passes):
        out.append(pass_(out[-1], k))
    return out


if __name__ == "__main__":
    import random
    for _ in range(2000):
        n = random.randint(4, 40)
        k = random.randint(2, min(6, n - 1))
        s = [random.randint(0, 1) for _ in range(n)]
        assert pass_(s, k) == pass_transducer(s, k), (s, k)
        assert inverse_pass(pass_(s, k), k) == s
    print("ok: sequential rule == transducer/NLFSR view; inverse verified")
