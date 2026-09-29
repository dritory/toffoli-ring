from verify import *
from analyze_k import parse_b
mk = lambda *s: [parse_b(x) for x in s]
report('ISA4 NEXT-only {FLIP,NEXT,IFZ,MARK}', mk('(F)','(P)','(T0)','(+K)'))
report('FT4 {FT,NEXT,PREV,MARK}', mk('(F,T0)','(P)','(M)','(+K)'))
report('FT4 v1 {FT1,..} (test1 after flip)', mk('(F,T1)','(P)','(M)','(+K)'))
report('M1 {MARK,NEXT,IFZ,FM}', mk('(+K)','(P)','(T0)','(F,M)'))
report('M2 {MARK,NEXT,FM,FT}', mk('(+K)','(P)','(F,M)','(F,T0)'))
report('M3 {MARK,IFZ,FP,FM}', mk('(+K)','(T0)','(F,P)','(F,M)'))
report('AB+K', mk('(F,T0,P)','(F,T0,M)','(+K)'))
report('AB+K v(T1 first)', mk('(T1,F,P)','(T1,F,M)','(+K)'))
report('2: A, B+K', mk('(F,T0,P)','(F,T0,M+K)'))
