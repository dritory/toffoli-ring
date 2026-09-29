from gate import *
from macro import B, templates
import sys, time
FT4 = [B(('F','T0')),B(('P',)),B(('M',)),B((),True)]
enc = {n:(g,tab) for n,g,tab in templates()}
g,tab = enc['(x,1)']
def spec_toff(o1,o2,ot): return dict(offs=sorted({0,o1,o2,ot}), f=lambda x,o1=o1,o2=o2,ot=ot: ({ot: x[ot]^(x[o1]&x[o2])},0))
def spec_cnot(c,t): return dict(offs=sorted({c,t,0}), f=lambda x,c=c,t=t: ({t: x[t]^x[c]},0))
gates = {'CNOT(0->+1)':spec_cnot(0,1),'CNOT(0->-1)':spec_cnot(0,-1),'CNOT(0->+2)':spec_cnot(0,2),
         'TOFF(0,1->2)':spec_toff(0,1,2),'TOFF(0,1->-1)':spec_toff(0,1,-1)}
for nm,sp in gates.items():
    for rest in range(g):
        t=time.time(); w=find(FT4,sp,g,tab,rest,L=26,pad=1,cap=1500000)
        print(nm,'rest',rest,len(w) if w else None,w,round(time.time()-t,1),flush=True)
        if w: break
