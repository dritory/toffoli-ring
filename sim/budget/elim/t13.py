from verify import *
from analyze_k import parse_b
mk = lambda *s: [parse_b(x) for x in s]
report('baseline5 with IFNZ {FLIP,NEXT,PREV,IFNZ,MARK}', mk('(F)','(P)','(M)','(T1)','(+K)'))
report('ISA4 NEXT-only IFNZ', mk('(F)','(P)','(T1)','(+K)'))
report('M1c {MARK,NEXT,IFNZ,FM}', mk('(+K)','(P)','(T1)','(F,M)'))
report('FT4 {FT,NEXT,PREV,MARK}', mk('(F,T0)','(P)','(M)','(+K)'))
