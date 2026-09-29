from gate import *
from macro import B
import sys, time
FT4 = [B(('F','T0')),B(('P',)),B(('M',)),B((),True)]
spec = gate_specs(1,2)['CNOT+1']
for g in (1,2,3):
  for name,gg,tab in templates():
    if gg!=g: continue
    for rest in range(g):
        for pad in (1,2):
            t=time.time()
            w = find(FT4, spec, g, tab, rest, L=22, pad=pad, cap=400000)
            print(name, g, rest, pad, w, round(time.time()-t,1), flush=True)
            if w: sys.exit()
