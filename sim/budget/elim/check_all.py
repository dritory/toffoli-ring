"""Reproduce the numbers in results/budget/elim.md (all light-weight checks)."""
import subprocess, sys
from verify import report
from analyze_k import parse_b
from progs_flat import measure
from macro import templates
mk = lambda *s: [parse_b(x) for x in s]
print('== netlists (truth table 20/..., 500 random programs tick by tick vs reference) ==')
report('baseline (IFZ, blockskip.md)      ', mk('(F)','(P)','(M)','(T0)','(+K)'))
report('baseline with IFNZ                ', mk('(F)','(P)','(M)','(T1)','(+K)'))
report('C1 FT4 {FT,NEXT,PREV,MARK}        ', mk('(F,T0)','(P)','(M)','(+K)'))
report('C2 flat {MARK,NEXT,IFNZ,FM}       ', mk('(+K)','(P)','(T1)','(F,M)'))
report('C2 flat {MARK,NEXT,FM,FT}         ', mk('(+K)','(P)','(F,M)','(F,T0)'))
report('C2 3-op {A=(F,T0,P),B=(F,T0,M),MK}', mk('(F,T0,P)','(F,T0,M)','(+K)'))
report('C2 2-op {A,B+K} (mark+test letter)', mk('(F,T0,P)','(F,T0,M+K)'))
report('C4 NEXT-only {F,N,IFNZ,MARK}      ', mk('(F)','(P)','(T1)','(+K)'))
print('== programs through the netlist, lock step with the baseline reference ==')
tabs = {n: (g, t) for n, g, t in templates()}
g, tab = tabs['none']; gc, tabc = tabs['none~']
print('baseline IFNZ (data complemented):', measure(mk('(F)','(P)','(M)','(T1)','(+K)'), dict(FLIP=(0,),NEXT=(1,),PREV=(2,),IF=(3,),END=(4,)), gc, tabc, 0))
print('C2 {MARK,NEXT,IFNZ,FM}           :', measure(mk('(+K)','(P)','(T1)','(F,M)'), dict(FLIP=(3,1),NEXT=(1,),PREV=(3,1,3),IF=(2,),END=(0,)), gc, tabc, 0))
print('C2 {MARK,NEXT,FM,FT}             :', measure(mk('(+K)','(P)','(F,M)','(F,T0)'), dict(FLIP=(2,1),NEXT=(1,),PREV=(2,1,2),IF=(2,1,3),END=(0,)), g, tab, 0))
print('== FT4 gate library + counter ==')
subprocess.run([sys.executable, 'ft4_gates.py']); subprocess.run([sys.executable, 'ft4.py']); subprocess.run([sys.executable, 't15.py']); subprocess.run([sys.executable, 't16.py'])
print('== NEXT-only ==')
subprocess.run([sys.executable, 'nextonly.py'])
