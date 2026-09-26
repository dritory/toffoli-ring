"""CLEAR on a spaced dual-rail pair (c at 0, cbar at 2) using a marker pair (0,1) at m, m+1.
Reference machine R letters: F flip, N +1, P -1, C +1 iff bit, D -1 iff bit.
Branch on c (C), flip cells o and o+1 (FNF), merge on the marker (D), return, then flip 0 and 1 unconditionally."""
import random
def run(word, tape, p=0):
    t = list(tape)
    for ch in word:
        if ch == 'F': t[p] ^= 1
        elif ch == 'N': p += 1
        elif ch == 'P': p -= 1
        elif ch == 'C': p += t[p]
        elif ch == 'D': p -= t[p]
    return t, p
def gap_clear(m):
    return "C" + "FNF" + "N"*(m-1) + "D" + "P"*m + "FNF" + "P"
if __name__ == "__main__":
    for m in (3, 4, 6, 9):
        w = gap_clear(m); good = 0
        for _ in range(300):
            c = random.randint(0, 1)
            tape = [random.randint(0, 1) for _ in range(m + 4)]
            tape[0] = c; tape[2] = 1 - c; tape[m] = 0; tape[m + 1] = 1
            out, p = run(w, tape)
            exp = list(tape); exp[0] = 0; exp[2] = 1
            good += (out == exp and p == 0)
        print(f"gap CLEAR, marker at {m}: {good}/300, length {len(w)}: {w}")
