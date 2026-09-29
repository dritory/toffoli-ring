from macro import *
def mk(*specs):
    out=[]
    for s in specs:
        k = s.endswith('+K'); s2 = s[:-2] if k else s
        out.append(B([x for x in s2.split(',') if x], k))
    return out
import time
menus = {'baseline5': mk('F','P','M','T0','K'), }
menus['baseline5'] = [B(('F',)),B(('P',)),B(('M',)),B(('T0',)),B((),True)]
menus['FT4'] = [B(('F','T0')),B(('P',)),B(('M',)),B((),True)]
menus['AB+K'] = [B(('F','T0','P')),B(('F','T0','M')),B((),True)]
menus['AB+K v1'] = [B(('F','T1','P')),B(('F','T1','M')),B((),True)]
menus['AB+K tf'] = [B(('T0','F','P')),B(('T0','F','M')),B((),True)]
for name, L in menus.items():
    for mode in 'ab':
        t=time.time(); g = search_all_enc(L, L=8, mode=mode)
        print(name, mode, len(g), g[0][:4] if g else None, [ ''.join('FNPIE'[0] for _ in [])], round(time.time()-t,1))
        if g: print('  ', {k:v for k,v in g[0][4].items()})
