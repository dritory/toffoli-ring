import random
from ft4_gates import *
rng = random.Random(7)
def run_test(trials=500, ng=8, steps=25):
    fails = 0
    for _ in range(trials):
        lg = [rng.randint(0, 1) for _ in range(ng)]; ph = enc(lg); ptr = 1 * G; gp = 1
        for _ in range(steps):
            opts = ['NOT', 'RESET', 'NEXT', 'PREV', 'CMOV']
            if gp + 1 < ng: opts.append('CNOTp')
            if gp - 1 >= 0: opts.append('CNOTm')
            if gp + 2 < ng and gp - 1 >= 0 and lg[gp - 1] == 0: opts.append('TOFF')
            op = rng.choice(opts)
            if op == 'NOT': lg[gp] ^= 1; w = W['NOT']
            elif op == 'RESET': lg[gp] = 0; w = W['RESET']
            elif op == 'NEXT':
                if gp + 2 >= ng: continue
                gp += 1; w = W['NEXT']
            elif op == 'PREV':
                if gp - 2 < 0: continue
                gp -= 1; w = W['PREV']
            elif op == 'CMOV':
                if gp + 2 >= ng: continue
                w = W['CMOVp']
                if lg[gp]: lg[gp] = 0; gp += 1
            elif op == 'CNOTp': lg[gp + 1] ^= lg[gp]; w = W['CNOTp']
            elif op == 'CNOTm': lg[gp - 1] ^= lg[gp]; w = W['CNOTm']
            else: lg[gp + 2] ^= lg[gp] & lg[gp + 1]; w = W['TOFF']
            ph, ptr = apply(w, ph, ptr)
            if ph != enc(lg) or ptr != gp * G: fails += 1; break
    return trials, fails
print(run_test())
