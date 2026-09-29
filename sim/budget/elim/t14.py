from progs_flat import *
tabs = {n: (g, t) for n, g, t in templates()}
g, tab = tabs['none~']
base = [parse_b(s) for s in ('(F)','(P)','(M)','(T1)','(+K)')]
print(measure(base, dict(FLIP=(0,), NEXT=(1,), PREV=(2,), IF=(3,), END=(4,)), g, tab, 0))
M1c = [parse_b(s) for s in ('(+K)','(P)','(T1)','(F,M)')]
print(measure(M1c, dict(FLIP=(3,1), NEXT=(1,), PREV=(3,1,3), IF=(2,), END=(0,)), g, tab, 0))
