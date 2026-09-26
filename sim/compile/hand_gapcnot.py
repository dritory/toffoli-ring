import random
exec(open(__import__('os').path.join(__import__('os').path.dirname(__file__),'hand_toffoli_core.py')).read().split("# Layout")[0])
def gap_cnot(K):
    R = K + 4; M = R - (K + 1)
    c1 = "CC" + "N"*K + "FNF" + "N"*M + "DD" + "P"*R
    c2 = "C"  + "N"*K + "FNF" + "N"*M + "DD" + "P"*R
    return c1 + c2, R
for K in range(2, 13):
    w, R = gap_cnot(K); good = 0; T = 400
    for _ in range(T):
        a, t = random.randint(0,1), random.randint(0,1)
        tape = [random.randint(0,1) for _ in range(R + 3)]
        tape[0] = a; tape[1] = 1
        tape[K+1] = t; tape[K+3] = 1 - t
        tape[R:R+3] = [0, 1, 1]
        out, p = run(w, tape)
        exp = list(tape); exp[K+1] ^= a; exp[K+3] ^= a
        good += (out == exp and p == 0)
    print(f"K={K:2d} gap CNOT: {good}/{T}  length {len(w)}")
for c in (0,1):
    out, p = run("FNDFD", [c, 1-c]); print("CLEAR c=%d ->" % c, out, "ptr", p)
