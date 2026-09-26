import itertools
# Reference machine R on a logical bit tape: F flip, N +1, P -1, C = CN (+1 iff bit), D = CP (-1 iff bit).
def run(word, tape, p=0):
    t = list(tape)
    for ch in word:
        if ch == 'F': t[p] ^= 1
        elif ch == 'N': p += 1
        elif ch == 'P': p -= 1
        elif ch == 'C': p += t[p]
        elif ch == 'D': p -= t[p]
    return t, p
# Layout: 0:a  1:b  2..3 spare  K=4: g0  5: t  6: g1  7: tbar  8..9 spare  R=10,11,12: markers 0,1,1
K, R = 4, 10
M = R - (K + 1)
core = "CC" + "N"*K + "FNF" + "N"*M + "DD" + "P"*R
ok = bad = 0
for a, b, t, s2, s3, s8, s9 in itertools.product((0,1), repeat=7):
    tape = [a, b, s2, s3, 0, t, 0, 1-t, s8, s9, 0, 1, 1]
    out, p = run(core, tape)
    exp = list(tape); exp[5] ^= (a&b) ^ 1; exp[7] ^= (a&b); exp[4] ^= 1 - a; exp[6] ^= a
    if out == exp and p == 0: ok += 1
    else: bad += 1; print("FAIL", tape, out, p)
print("core:", ok, "ok,", bad, "bad; word length", len(core))
print("core word:", core)

# Garbage-free Toffoli: core with CC, then the same core with a single C (cancels ¬a, a, and the constant flip).
if __name__ == "__main__":
    core2 = "C" + "N"*K + "FNF" + "N"*M + "DD" + "P"*R
    TOFF = core + core2
    good = 0
    for a, b, t, s2, s3, s8, s9 in itertools.product((0,1), repeat=7):
        tape = [a, b, s2, s3, 0, t, 0, 1-t, s8, s9, 0, 1, 1]
        out, p = run(TOFF, tape)
        exp = list(tape); exp[5] ^= a & b; exp[7] ^= a & b
        good += (out == exp and p == 0)
    print("TOFFOLI:", good, "of 128; length", len(TOFF), TOFF)
