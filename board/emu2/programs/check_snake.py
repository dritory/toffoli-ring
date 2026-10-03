import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import *

GREEN, RED, WHITE = 0x07E0, 0xF800, 0xFFFF

class Model:
    """Reference model of snake.asm (same rules, same LFSR)."""
    def __init__(self):
        self.snake = [115, 116, 117]; self.dir = 8; self.score = 0; self.food = 122
        self.rng = 0xACE1; self.dead = False
    def rnd(self):
        s = self.rng
        for _ in range(8): s = (s >> 1) ^ (0xB400 if s & 1 else 0)
        self.rng = s; return s & 255
    def move(self, pend):
        amask = 12 if self.dir & 3 else 3
        pf = pend & amask
        if pf: self.dir = pf & -pf
        h = self.snake[-1]; d = self.dir
        if d == 1: nh = h - 16; bad = nh < 0
        elif d == 2: nh = h + 16; bad = nh >= 240
        elif d == 4: nh = h - 1; bad = h & 15 == 0
        else: nh = h + 1; bad = h & 15 == 15
        if bad or nh in self.snake: self.dead = True; return
        self.snake.append(nh)
        if nh == self.food:
            self.score += 1
            while True:
                r = self.rnd()
                if r < 240 and r not in self.snake: break
            self.food = r
        else:
            self.snake.pop(0)

def cell_colour(cpu, idx):
    x, y = (idx & 15) * 16 + 8, (idx >> 4) * 16 + 8
    return cpu.lcd.fb[y * 320 + x]

def check_state(cpu, P, m, label):
    S = P.symbols
    assert cpu.mem[S["head"]] == m.snake[-1], (label, "head", cpu.mem[S["head"]], m.snake[-1])
    assert cpu.mem[S["dir"]] == m.dir, (label, "dir")
    assert cpu.mem[S["score"]] == m.score and cpu.led == m.score, (label, "score")
    b = S["board"]
    for i in range(240):
        want = 1 if i in m.snake else 2 if i == m.food else 0
        assert cpu.mem[b + i] == want, (label, "board", i, cpu.mem[b + i], want)
        col = cell_colour(cpu, i)
        wc = GREEN if want == 1 else RED if want == 2 else 0
        assert col == wc, (label, "lcd cell", i, hex(col), hex(wc))

def bot_script(nmoves):
    """Greedy food-chasing player; returns {move: button} by simulating the model."""
    m = Model(); script = {}
    for k in range(nmoves):
        h = m.snake[-1]; hx, hy = h & 15, h >> 4; fx, fy = m.food & 15, m.food >> 4
        best = None
        for b, (dx, dy) in ((1, (0, -1)), (2, (0, 1)), (4, (-1, 0)), (8, (1, 0))):
            if (b & 3 and m.dir & 3) or (b & 12 and m.dir & 12) and b != m.dir:
                if b != m.dir: continue
            x, y = hx + dx, hy + dy
            if not (0 <= x < 16 and 0 <= y < 15) or (y * 16 + x) in m.snake: continue
            d = abs(x - fx) + abs(y - fy)
            if best is None or d < best[0]: best = (d, b)
        if best is None: break
        if best[1] != m.dir: script[k] = best[1]
        m.move(script.get(k, 0))
        if m.dead: break
    return script

def play(script, nmoves, tick=1500, save_as=None, quiet=False):
    """script: {move_number: button mask} pressed during the interval before that move."""
    P, cpu = build("snake", tick_cycles=tick, debug=True)
    m = Model(); S = P.symbols; saved = []
    cpu.run_until_pc(S["frame"], 100000)
    moves = 0; cycles0 = cpu.cycle
    for k in range(nmoves):
        if k in script:
            cpu.set_buttons(script[k]); cpu.run(2, stop_on_halt=False); cpu.set_buttons(0)
        pend = script.get(k, 0)
        r = cpu.run_until_pc(S["move"], 200000)
        if r is None: break
        r = cpu.run_until_pc(S["frame"], 200000)
        m.move(pend)
        if m.dead:
            r = cpu.run_until_pc(S["frame"], 20000)   # runs into dead: halts
            assert cpu.mem[S["over"]] == 1 or r is None
            assert cpu.halted or cpu.mem[S["over"]] == 1
            return P, cpu, m, k
        check_state(cpu, P, m, "move %d" % k)
        moves += 1
        if save_as and k == 100: save(cpu, save_as, x0=0, y0=0, w=256, h=240)
    return P, cpu, m, nmoves

def main():
    # a loop around the board, eating on the way; presses by button interrupt
    UP, DOWN, LEFT, RIGHT = 1, 2, 4, 8
    script = bot_script(300)
    P, cpu, m, n = play(script, 300, save_as='snake')
    print("snake: %d moves checked against the model, score %d, length %d, dead=%s" % (n, m.score, len(m.snake), m.dead))
    # reverse presses are ignored; wall kills
    P, cpu, m, n = play({1: LEFT}, 30)   # left while moving right: ignored; hits the wall
    assert m.dead and cpu.halted, "should die at the right wall"
    print("snake: reverse press ignored, died at wall after %d moves (model agrees)" % n)
    # eat food: path to 122 is straight along the row
    P, cpu, m, n = play({}, 8)
    assert m.score == 1 and cpu.mem[P.symbols["score"]] == 1
    print("snake: first food eaten, next food at cell", m.food)

if __name__ == "__main__":
    main()
