from nmos_gen import *
base = [B(('F',)),B(('P',)),B(('M',)),B(('T0',)),B((),True)]
m = Machine(base); print(m.counts())
bad=0
for S in (0,1):
  for i,b in enumerate(base):
    for r in (0,1):
      got,clean = m.tick(S,i,r)
      if got != ref_tick(b,S,r) or not clean: bad+=1; print(b,S,r,got,ref_tick(b,S,r),clean)
print('bad',bad)
