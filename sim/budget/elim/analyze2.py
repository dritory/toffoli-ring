import re, sys, collections
from analyze_k import *
def compl(b):
    ops = [('T1' if o == 'T0' else 'T0' if o == 'T1' else o) for o in b.ops]
    return B(ops, b.mark)
menus = load(sys.argv[1]); rows = []
for key, encs in menus.items():
    menu = [parse_b(k) for k in key]
    best = None
    for variant, mm in (('as', menu), ('compl', [compl(b) for b in menu])):
        m = Machine(mm)
        try: ok, clean = truth(m)
        except Exception: continue
        c = m.counts(); cand = (c['T'] + c['R'], c['T'], c['R'], clean, ok, variant)
        if best is None or cand[:2] < best[:2]: best = cand
    tot = min(int(re.search(r'tot=(\d+)', e[0]).group(1)) for e in encs)
    rows.append((best, key, tot, len(encs)))
rows.sort(key=lambda r: (r[0][0], not r[0][3], r[2]))
print(len(rows), 'distinct canonical 4-letter flat menus (no mark+test letter)')
cnt = collections.Counter((r[0][1], r[0][2], r[0][3]) for r in rows)
for k, v in sorted(cnt.items()): print('T,R,clean =', k, ':', v, 'menus')
for r in rows[:25]:
    print(r[0][1], r[0][2], 'clean' if r[0][3] else 'glitch', r[0][5], ' '.join(r[1]), 'minTotalMacroLen', r[2])
