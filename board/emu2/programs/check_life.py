import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import *

W, H = 40, 30
SEED = [(3,2),(4,3),(2,4),(3,4),(4,4),(21,15),(22,15),(20,16),(21,16),(21,17),(33,5),(34,5),(35,5)]

def step(cells):
    n = {}
    for (x, y) in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy: n[(x + dx, y + dy)] = n.get((x + dx, y + dy), 0) + 1
    return {c for c, k in n.items() if 1 <= c[0] <= W and 1 <= c[1] <= H and (k == 3 or (k == 2 and c in cells))}

def read_board(cpu, P, gen):
    base = 0x20 if gen % 2 == 0 else 0x40
    return {(x, y) for y in range(1, H + 1) for x in range(1, W + 1) if cpu.mem[((base + y) << 8) | x]}

def lcd_cells(cpu):
    return {(x + 1, y + 1) for y in range(H) for x in range(W) if cpu.lcd.fb[(y * 8 + 3) * 320 + x * 8 + 3]}

def main(gens=60):
    P, cpu = build("life", tick_cycles=1, debug=True)
    S = P.symbols
    cpu.run_until_pc(S["frame"], 3_000_000)
    model = set(SEED)
    assert read_board(cpu, P, 0) == model and lcd_cells(cpu) == model
    cyc = []
    for g in range(1, gens + 1):
        r = cpu.run_until_pc(S["frame"], 1_000_000)     # one tick wait + one generation
        r += cpu.run_until_pc(S["frame"], 1_000_000) if False else 0
        cyc.append(r)
        model = step(model)
        assert read_board(cpu, P, g) == model, ("generation", g)
        assert lcd_cells(cpu) == model, ("lcd", g)
        assert cpu.led == g & 255
        if g == 40: save(cpu, "life", x0=0, y0=0, w=320, h=240)
    print("life: %d generations identical to the reference model; %d live cells at the end" % (gens, len(model)))
    print("life: cycles per generation: min %d max %d" % (min(cyc), max(cyc)))
    return cyc

if __name__ == "__main__":
    main()
