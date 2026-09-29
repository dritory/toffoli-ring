import sys, time
from gate import *
from macro import B, templates
from analyze_k import parse_b
menus = {
 'AB+K  A=(F,T0,P) B=(F,T0,M) K': ['(F,T0,P)','(F,T0,M)','(+K)'],
 'AB+K v1 (F,T1,..)': ['(F,T1,P)','(F,T1,M)','(+K)'],
 'AB+K test-first (T0,F,..)': ['(T0,F,P)','(T0,F,M)','(+K)'],
 'AB+K test-first v1': ['(T1,F,P)','(T1,F,M)','(+K)'],
 'AB+K mixed (F,T0,P)(T1,F,M)': ['(F,T0,P)','(T1,F,M)','(+K)'],
 '2: A=(F,T0,P) B=(F,T0,M+K)': ['(F,T0,P)','(F,T0,M+K)'],
 '2: A=(F,T0,P+K) B=(F,T0,M)': ['(F,T0,P+K)','(F,T0,M)'],
 '2: A=(T0,F,P) B=(T0,F,M+K)': ['(T0,F,P)','(T0,F,M+K)'],
 '2: A=(F,T1,P) B=(F,T1,M+K)': ['(F,T1,P)','(F,T1,M+K)'],
}
sel = sys.argv[1:]
encs = [(n,g,t) for n,g,t in templates() if g<=2]
for nm, spec in menus.items():
    if sel and not any(s in nm for s in sel): continue
    L = [parse_b(s) for s in spec]
    t0 = time.time(); res = {}
    for gn in ('NOT','CNOT+1'):
        sp = gate_specs()[gn]; hit = None
        for n,g,tab in encs:
            for rest in range(g):
                w = find(L, sp, g, tab, rest, L=20 if gn=='CNOT+1' else 12, cap=300000)
                if w is not None: hit = (n,g,rest,w); break
            if hit: break
        res[gn] = hit
        print(nm, gn, hit, round(time.time()-t0,1), flush=True)
        if hit is None: break
