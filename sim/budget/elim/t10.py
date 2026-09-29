from verify import *
from analyze_k import parse_b
M1 = [parse_b(s) for s in ('(+K)','(P)','(T0)','(F,M)')]
report('M1 {MARK,NEXT,IFZ,FM}', M1)
M2 = [parse_b(s) for s in ('(+K)','(P)','(F,M)','(F,T0)')]
report('M2 {MARK,NEXT,FM,FT}', M2)
base = [parse_b(s) for s in ('(F)','(P)','(M)','(T0)','(+K)')]
report('baseline5', base)
