"""Defects on traveling periodic backgrounds. Build a ring of many copies of a
background period, insert a defect, evolve, and print spacetime in the
co-moving frame (shift each row left by v*t) so a static background stays put."""
import sys
from ring import pass_, to_str, from_str

def comoving(rows, v, n):
    out = []
    for t, r in enumerate(rows):
        sh = (v * t) % n
        out.append(r[sh:] + r[:sh])
    return out

def demo(k, bg, v, defect, pos, copies, passes, seedfix=True):
    n = copies * len(bg)
    s = from_str(bg) * copies
    d = from_str(defect)
    for i, b in enumerate(d):
        s[(pos + i) % n] = b
    rows = [s]
    for _ in range(passes):
        rows.append(pass_(rows[-1], k))
    cm = comoving(rows, v, n)
    for t, r in enumerate(cm):
        print("%4d %s" % (t, to_str(r)))

if __name__ == "__main__":
    k = int(sys.argv[1]); bg = sys.argv[2]; v = int(sys.argv[3]); defect = sys.argv[4]
    pos = int(sys.argv[5]); copies = int(sys.argv[6]); passes = int(sys.argv[7])
    demo(k, bg, v, defect, pos, copies, passes)
