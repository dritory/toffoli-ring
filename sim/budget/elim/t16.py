import random
from ft4_gates import *
rng = random.Random(3)
# cyclic tape emulate by window without wrap: use 8 pairs then check one pass over all bits
n = 8
src = [rng.randint(0,1) for _ in range(n)]
lg = []
for i in range(n): lg += [rng.randint(0,1), src[i]]   # d_i garbage, s_i
ph = enc(lg + [0, 0]); ptr = 0
word = ''
for i in range(n):
    word += W['RESET'] + W['NEXT'] + W['CNOTm'] + W['NEXT']
# last NEXT moves to group 2n (spacer) fine
ph, ptr = apply(word, ph, ptr)
out = [ph[4*i] for i in range(n)]
print(out == src, len(word)//n)
