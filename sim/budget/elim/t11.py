from progs_flat import *
tabs = {n: (g, t) for n, g, t in templates()}
g, tab = tabs['none']
M2 = [parse_b(s) for s in ('(+K)','(P)','(F,M)','(F,T0)')]
print(measure(M2, dict(FLIP=(2,1), NEXT=(1,), PREV=(2,1,2), IF=(2,1,3), END=(0,)), g, tab, 0))
