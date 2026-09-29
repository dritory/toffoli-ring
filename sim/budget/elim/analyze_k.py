import re, sys, collections
from nmos_gen import *
def parse_b(s):
    s = s.strip()[1:-1]; mark = s.endswith('+K'); s = s[:-2] if mark else s
    return B([x for x in s.split(',') if x], mark)
def load(fn):
    menus = collections.OrderedDict()
    for line in open(fn):
        if not line.startswith('OK'): continue
        head, enc, words = line[3:].split(' | ')
        bs = re.findall(r'\([^)]*\)', head)
        key = tuple(bs)
        menus.setdefault(key, []).append((enc.strip(), words.strip()))
    return menus
def truth(m):
    ok = clean = True
    for S in (0, 1):
        for i, b in enumerate(m.menu):
            for r in (0, 1):
                try: got, cl = m.tick(S, i, r)
                except ValueError as e:
                    print('   race', b, S, r); return False, False
                if got != ref_tick(b, S, r): ok = False
                if not cl: clean = False
    return ok, clean
if __name__ == '__main__':
    menus = load(sys.argv[1]); rows = []
    for key, encs in menus.items():
        menu = [parse_b(k) for k in key]
        m = Machine(menu); ok, clean = truth(m)
        c = m.counts(); best = min(encs, key=lambda e: int(re.search(r'tot=(\d+)', e[0]).group(1)))
        rows.append((c['T'] + c['R'], c['T'], c['R'], clean, ok, key, best))
    rows.sort()
    for r in rows: print(r[1], r[2], 'clean' if r[3] else 'glitch', 'ok' if r[4] else 'BAD', ' '.join(r[5]), '|', r[6][0], r[6][1])
