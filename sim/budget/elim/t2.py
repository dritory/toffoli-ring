from gate import *
from macro import B
import time, sys
menus = {
 'FT4': [B(('F','T0')),B(('P',)),B(('M',)),B((),True)],
}
for nm, L in menus.items():
    for gn, spec in gate_specs().items():
        t=time.time(); r = best(L, spec, L=16, gmax=2)
        print(nm, gn, r and r[:4], r and r[4], round(time.time()-t,1), flush=True)
