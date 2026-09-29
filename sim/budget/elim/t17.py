import nextonly as NO, programs as P
from nmos_gen import Machine
from analyze_k import parse_b
menu = [parse_b(s) for s in ('(F)','(P)','(T1)','(+K)')]
m = Machine(menu); lm = {'FLIP':0,'NEXT':1,'IFZ':2,'MARK':3}
def run_net(prog, data, dp, passes):
    data = [1-x for x in data]          # complemented storage
    S = 0; n = len(data)
    for _ in range(passes):
        for ins in prog:
            (tg, mp, mm, S), _c = m.tick(S, lm[ins], data[dp])
            if tg: data[dp] ^= 1
            dp = (dp + mp - mm) % n
    return [1-x for x in data], dp, S
prog = NO.counter_nextonly(); d = NO.counter_tape(); dp = 0
for k in range(1, 60):
    d, dp, S = run_net(prog, d, dp, 1)
    val = sum((1 - d[2*i]) << i for i in range(8)); assert val == k % 256 and dp == 0 and S == 0
print('NEXT-only counter on 8T/4R netlist ok')
base = P.bb22_prog(); prog2 = NO.subst_prev(base, 54)
d1, dp1 = P.bb22_tape(6); d2 = list(d1)
r1 = NO.run(base, d1, dp1, passes=2); r2 = run_net(prog2, d2, dp1, 2)
print('BB NEXT-only 2 steps on netlist equal baseline:', r1[0] == r2[0] and r1[1] == r2[1])
