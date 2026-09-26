import random
# A = flip; set skip iff cell (new value) == 0; move +1.   B = same with move -1.
def run(word, tape, p):
    t = list(tape); n = len(t); flag = 0
    for ch in word:
        if flag: flag = 0; continue
        t[p] ^= 1
        if t[p] == 0: flag = 1
        p = (p + (1 if ch == 'A' else -1)) % n
    return t, p, flag
enc = lambda bs: sum(([b, 1-b] for b in bs), [])
G = 12; n = 2*G
M = {'FLIP':'ABB','NEXT':'ABBAAA','PREV':'BAABBBABBABB','CNEXT':'ABBAAB','CPREV':'ABBABABAABBB'}
ok = {k:0 for k in M}; T = 3000
for _ in range(T):
    bits = [random.randint(0,1) for _ in range(G)]; tape = enc(bits); g = random.randrange(G); p = 2*g
    b = bits[g]
    want = {'FLIP': (enc([x^1 if i==g else x for i,x in enumerate(bits)]), p),
            'NEXT': (tape, (p+2)%n), 'PREV': (tape, (p-2)%n),
            'CNEXT': (tape, (p+2*b)%n), 'CPREV': (tape, (p-2*b)%n)}
    for k,w in M.items():
        t,q,f = run(w, tape, p); ok[k] += (t == want[k][0] and q == want[k][1] and f == 0)
print(ok, "of", T)
