"""CNOT(0->+1) existence for named non-flat menus, all g<=2 encodings, C++ BFS."""
import subprocess, sys
from macro import templates
menus = {
 'FT4 {FT,N,P,MK}': ['F,T0','P','M','+K'],
 'A,B,MK  A=(F,T0,P) B=(F,T0,M)': ['F,T0,P','F,T0,M','+K'],
 'A,B,MK  (F,T1,..)': ['F,T1,P','F,T1,M','+K'],
 'A,B,MK  (T0,F,..)': ['T0,F,P','T0,F,M','+K'],
 'A,B,MK  (T1,F,..)': ['T1,F,P','T1,F,M','+K'],
 'A,B,MK  mixed (F,T0,P),(T1,F,M)': ['F,T0,P','T1,F,M','+K'],
 'A,B+K   (F,T0,P),(F,T0,M+K)': ['F,T0,P','F,T0,M+K'],
 'A+K,B   (F,T0,P+K),(F,T0,M)': ['F,T0,P+K','F,T0,M'],
}
sel = sys.argv[1:]
encs = [(n, g, [sum(b << j for j, b in enumerate(x)) for x in t]) for n, g, t in templates() if g <= 2]
for nm, letters in menus.items():
    if sel and not any(s in nm for s in sel): continue
    res = {}
    for n, g, tb in encs:
        for rest in range(g):
            out = subprocess.run(['./gsearch', 'CNOT:0:1', str(g), str(tb[0]), str(tb[1]), str(rest), '1', '40', '5000000', '0'] + letters,
                                 capture_output=True, text=True).stdout.strip()
            key = out.split()[0]
            res.setdefault(key, []).append((n, rest, out))
            if key == 'FOUND': print(nm, n, rest, out, flush=True)
    print(nm, {k: len(v) for k, v in res.items()}, flush=True)
