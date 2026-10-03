import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import *
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rc_data

T = rc_data.tables(); TURN = 6; VX0, VY0 = 80, 12
CEIL, FLOOR, BARC = 0x2965, 0x4A69, 0x4208

def sext(b): return 0xFF if b & 0x80 else 0

class Model:
    def __init__(self):
        self.px = self.py = 2 * 256 + 128; self.pa = 0
    def frame(self, btn):
        if btn & 4: self.pa = (self.pa - TURN) & 0x3FF
        if btn & 8: self.pa = (self.pa + TURN) & 0x3FF
        if btn & 3:
            a = self.pa if btn & 1 else (self.pa + 512) & 0x3FF
            mx, my = T["mvx"][a], T["mvy"][a]
            nx = (self.px + mx + (sext(mx) << 8)) & 0xFFFF
            if not T["map"][(self.py >> 8) * 16 + (nx >> 8)]: self.px = nx
            ny = (self.py + my + (sext(my) << 8)) & 0xFFFF
            if not T["map"][(ny >> 8) * 16 + (self.px >> 8)]: self.py = ny
    def ray(self, c):
        off = T["offh"][c] << 8 | T["offl"][c]
        ang = (self.pa + off) & 0xFFFF; a = ang & 0x3FF
        ddx = T["ddxh"][a] << 8 | T["ddxl"][a]; ddy = T["ddyh"][a] << 8 | T["ddyl"][a]
        stx, sty = T["stx"][a], T["sty"][a]
        def side(fr, st, dd):
            ax = fr if st & 0x80 else fr ^ 255
            p = ax * (dd >> 8); lo = (p & 255) + ((ax * (dd & 255)) >> 8)
            return ((p >> 8) + (lo >> 8)) << 8 | (lo & 255)
        sdx, sdy = side(self.px & 255, stx, ddx), side(self.py & 255, sty, ddy)
        idx = (self.py >> 8) * 16 + (self.px >> 8)
        while True:
            if (sdx >> 8, sdx & 255) < (sdy >> 8, sdy & 255):
                sdx = (sdx + ddx) & 0xFFFF; idx = (idx + stx) & 255; sd = 0; hit = T["map"][idx]
                if hit: dist = (sdx - ddx) & 0xFFFF; break
            else:
                sdy = (sdy + ddy) & 0xFFFF; idx = (idx + sty) & 255; sd = 1; hit = T["map"][idx]
                if hit: dist = (sdy - ddy) & 0xFFFF; break
        dh, dl = dist >> 8, dist & 255
        d8 = 255 if dh >= 15 else (((dh * 16) & 255) | ((dl * 16) >> 8))
        d8 = (d8 * T["coso"][c]) >> 8
        h = T["hgt"][d8]
        return h, hit, sd
    def view(self):
        fb = {}
        cols = []
        for c in range(160):
            h, hit, sd = self.ray(c)
            wc = T["wcol"][hit * 4 + sd * 2] << 8 | T["wcol"][hit * 4 + sd * 2 + 1]
            top = (100 - h) >> 1
            cols.append([CEIL] * top + [wc] * h + [FLOOR] * (100 - h - top))
        return cols

def lcd_view(cpu):
    return [[cpu.lcd.fb[(VY0 + y) * 320 + VX0 + c] for y in range(100)] for c in range(160)]

def main():
    P, cpu = build("raycast", tick_cycles=1, debug=True)
    S = P.symbols
    t0 = cpu.run_until_pc(S["frame"], 5_000_000)
    print("raycast: start-up (table fill + status bar): %d cycles" % t0)
    fb = cpu.lcd.fb
    assert fb[130 * 320 + 30] == 0xF800 and fb[200 * 320 + 5] == BARC and fb[50 * 320 + 5] == 0
    m = Model(); cyc = {}
    script = [0] * 2 + [1] * 25 + [8] * 12 + [1] * 15 + [4] * 40 + [2] * 6 + [1] * 60 + [9] * 8 + [1] * 30
    saves = {5: "raycast_1", 30: "raycast_2", 70: "raycast_3", 130: "raycast_4"}
    for f, b in enumerate(script):
        cpu.run_until_pc(S["update"] if "update" in S else S["frame"], 10) if False else None
        cpu.set_buttons(b)
        r = cpu.run_until_pc(S["frame"], 2_000_000)
        m.frame(b)
        got = (cpu.mem[S["pxh"]] << 8 | cpu.mem[S["pxl"]], cpu.mem[S["pyh"]] << 8 | cpu.mem[S["pyl"]], cpu.mem[S["pah"]] << 8 | cpu.mem[S["pal"]])
        assert got == (m.px, m.py, m.pa), (f, got, (m.px, m.py, m.pa))
        cyc[f] = r
        # the picture on the LCD is the view rendered from the state *before* this frame's input? no: after input
        if lcd_view(cpu) != m.view():
            raise AssertionError("view mismatch in frame %d" % f)
        if f in saves: save(cpu, saves[f], x0=80, y0=12, w=160, h=100, scale=2)
    v = list(cyc.values())
    print("raycast: %d frames identical to the integer reference model (pos/angle every frame, all 16000 view pixels)" % len(script))
    print("raycast: cycles/frame min %d max %d avg %d" % (min(v), max(v), sum(v) // len(v)))
    return v

if __name__ == "__main__":
    main()
