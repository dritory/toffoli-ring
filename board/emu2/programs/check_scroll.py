import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import *
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkfont

FG, BG, YTOP = 0xFD20, 0x0010, 106
TEXT = "HELLO FROM THE VISIBLE 8-BIT COMPUTER   "

def text_columns(n):
    out = []
    while len(out) < n:
        for ch in TEXT:
            out += mkfont.col_bytes(ch) + [0]
    return out

def expected(k, cols):
    fb = [0] * (320 * 240)
    for i in range(80):
        idx = k + i
        b = cols[idx - 80] if idx >= 80 else 0
        for r in range(7):
            c = FG if (b >> r) & 1 else BG
            for dy in range(4):
                for dx in range(4):
                    fb[(YTOP + r * 4 + dy) * 320 + i * 4 + dx] = c
    return fb

def main(frames=240):
    P, cpu = build("scroll", tick_cycles=1, debug=True)
    S = P.symbols; cols = text_columns(frames + 100)
    cpu.run_until_pc(S["frame"], 3_000_000)
    cyc = []
    for k in range(frames):
        r = cpu.run_until_pc(S["frame"], 1_000_000)
        cyc.append(r)
        if k % 20 == 0 or k > frames - 3:
            assert cpu.lcd.fb == expected(k, cols), ("frame", k)
        if k == 150: save(cpu, "scroll", x0=0, y0=90, w=320, h=60)
    print("scroll: %d frames match the font model; cycles/frame %d..%d" % (frames, min(cyc[1:]), max(cyc)))

if __name__ == "__main__":
    main()
