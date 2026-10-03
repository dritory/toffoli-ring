import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import *

PADH, XL, XR = 6, 1, 38
WHITE, YELLOW = 0xFFFF, 0xFFE0

class Model:
    def __init__(self):
        self.pl = self.pr = 12; self.bx, self.by, self.vx, self.vy = 20, 15, 1, 1
        self.sl = self.sr = 0; self.par = 0; self.rng = 0xACE1
    def rnd(self):
        s = self.rng
        for _ in range(8): s = (s >> 1) ^ (0xB400 if s & 1 else 0)
        self.rng = s; return s & 255
    def frame(self, btn):
        if btn & 1:
            if self.pl > 0: self.pl -= 1
        elif btn & 2:
            if self.pl < 30 - PADH: self.pl += 1
        self.par ^= 1
        if self.par:
            c = self.pr + 2
            if self.by < c:
                if self.pr > 0: self.pr -= 1
            elif self.by > c + 1:
                if self.pr < 30 - PADH: self.pr += 1
        ny = self.by + self.vy
        if not 0 <= ny < 30:
            self.vy = -self.vy; ny = self.by + self.vy
        nx = self.bx + self.vx
        miss = None
        if nx == XL:
            if not 0 <= ny - self.pl < PADH: miss = "l"
        elif nx == XR:
            if not 0 <= ny - self.pr < PADH: miss = "r"
        if miss:
            if miss == "l": self.sr += 1; self.vx = -1
            else: self.sl += 1; self.vx = 1
            self.bx, self.by = 20, 15
            self.vy = 1 if self.rnd() & 1 else -1
        else:
            if nx in (XL, XR): self.vx = -self.vx; nx = self.bx + self.vx
            self.bx, self.by = nx, ny
    def expected_fb(self):
        fb = [0] * (320 * 240)
        def rect(cx, cy, w, h, c):
            for y in range(cy * 8, (cy + h) * 8):
                for x in range(cx * 8, (cx + w) * 8): fb[y * 320 + x] = c
        rect(XL, self.pl, 1, PADH, WHITE); rect(XR, self.pr, 1, PADH, WHITE)
        rect(self.bx, self.by, 1, 1, YELLOW)
        return fb

def main(frames=400):
    # button script: hold DOWN for a while, UP later (by frame number)
    def btn(f): return 2 if 20 <= f < 60 else 1 if 120 <= f < 135 else 2 if 200 <= f < 210 else 0
    P, cpu = build("pong", tick_cycles=1, debug=True)
    S = P.symbols
    t0 = cpu.run_until_pc(S["frame"], 3_000_000)     # includes the real table start-up
    print("pong: start-up incl. table fill: %d cycles" % t0)
    m = Model(); cyc = []; scored = 0
    for f in range(frames):
        cpu.run_until_pc(S["update"], 100000)
        cpu.set_buttons(btn(f))
        c0 = cpu.cycle
        cpu.run_until_pc(S["frame"], 100000)
        cyc.append(cpu.cycle - c0 + 3)
        m.frame(btn(f))
        mem = cpu.mem
        got = tuple(mem[S[k]] for k in ("pl", "pr", "bx", "by", "vx", "vy", "sl", "sr"))
        want = (m.pl, m.pr, m.bx, m.by, m.vx & 255, m.vy & 255, m.sl, m.sr)
        assert got == want, ("frame", f, got, want)
        assert cpu.led == (m.sl << 4 | m.sr) & 255 if (m.sl or m.sr) else True
        if f % 25 == 0 or f == frames - 1:
            assert cpu.lcd.fb == m.expected_fb(), ("lcd mismatch at frame", f)
        if f == 90: save(cpu, "pong", x0=0, y0=0, w=320, h=240)
    print("pong: %d frames identical to the model; score %d:%d; cycles/frame min %d max %d" % (frames, m.sl, m.sr, min(cyc), max(cyc)))
    return cyc

if __name__ == "__main__":
    main()
