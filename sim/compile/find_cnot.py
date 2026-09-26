"""
Finds the CNOT(A -> T) gadget reported in design.md: flip T iff A==1,
leaving A unchanged, over the R alphabet {F,N,P,CN,CP}, by BFS over the
joint effect across every valuation of the free bits (see gadget_search.py).
"""
import time, itertools
from gadget_search import search, verify

def cnot_target(assign):
    return {'A': assign['A'], 'T': assign['T'] ^ assign['A']}

configs = []
# A dual rail, T plain, various spacer counts/values between and around
for a_orient in ('T','F'):
  for mid in range(0,3):
    for midvals in itertools.product([0,1], repeat=mid):
      layout = [('dual','A',a_orient)] + [('const',v) for v in midvals] + [('free','T')]
      configs.append((f"A dual({a_orient}) mid={midvals}", layout, 0))
# T dual rail too, A dual rail
for a_orient in ('T','F'):
  for t_orient in ('T','F'):
    for mid in range(0,3):
      for midvals in itertools.product([0,1], repeat=mid):
        layout = [('dual','A',a_orient)] + [('const',v) for v in midvals] + [('dual','T',t_orient)]
        configs.append((f"A dual({a_orient}) mid={midvals} T dual({t_orient})", layout, 0))

print(f"total configs: {len(configs)}")
MAXLEN=16
t0=time.time()
found=None
for name, layout, start_idx in configs:
    if time.time()-t0 > 200:
        print("time budget hit, stopping"); break
    res, nv = search(layout, start_idx, cnot_target, MAXLEN, max_visited=1_500_000)
    if res is not None:
        ok = verify(layout, start_idx, cnot_target, res)
        print(f"FOUND {name}: len={len(res)} word={''.join(res)} verify={ok} visited={nv}")
        found=(name,layout,res)
        break
print(f"elapsed={time.time()-t0:.1f}s found={found is not None}")
