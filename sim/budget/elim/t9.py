from gate import *
from macro import B, templates
import sys, time
FT4 = [B(('F','T0')),B(('P',)),B(('M',)),B((),True)]   # 0=FT 1=N 2=P 3=MARK
enc = {n:(g,tab) for n,g,tab in templates()}
g,tab = enc['(x,1)']
sp = gate_specs(1,2)['TOFF+1+2']
pre = (1,0,3, 2,0,2,3, 1,1,0,2,3)
t=time.time()
w = find(FT4, sp, g, tab, 0, L=24, pad=1, cap=2000000, prefix=pre)
print(w, len(w) if w else None, round(time.time()-t,1))
