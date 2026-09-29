from nmos_gen import *
ft = [B(('F','T0')),B(('P',)),B(('M',)),B((),True)]
m = Machine(ft); print(m.counts())
for S in (0,1):
  for i,b in enumerate(ft):
    for r in (0,1):
      got,clean = m.tick(S,i,r)
      print(b,S,r,got==ref_tick(b,S,r),clean)
