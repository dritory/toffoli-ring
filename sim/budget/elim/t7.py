from translate import *
import programs as P
from analyze_k import parse_b
menu = [parse_b(s) for s in ('(+K)','(P)','(T0)','(F,M)')]
words = dict(FLIP=(3,1), NEXT=(1,), PREV=(3,1,3), IF=(2,), END=(0,))
tabs = {n:(g,t) for n,g,t in templates()}
g,tab = tabs['none']
D = Derived(menu, words, g, tab, 0)
prog = P.counter_prog()
lg = [0]+[1]*8
print(len(prog), sum(len(D.words[{'FLIP':'FLIP','NEXT':'NEXT','PREV':'PREV','IFZ':'IF','MARK':'END'}[i]]) for i in prog))
tk = lockstep(D, prog, lg, 0, passes=300)
print('counter ok ticks/pass', tk/300)
