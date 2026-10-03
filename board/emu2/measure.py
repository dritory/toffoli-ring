"""Measurements for REPORT.md: sizes, cycles per frame, clocks for 10 / 30 fps, start-up time, encoding workarounds."""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "programs"))
from harness import *
import check_snake, check_pong, check_life, check_scroll, check_raycast, check_bf
from isa import *

R = {}

def init_size():
    P = asm.assemble_text("CALL init_tables\nJUMP $\n.include \"%s/programs/lib/init_tables.inc\"\n" % HERE)
    return len(P.words)

def startup():
    P = asm.assemble_text("CALL init_tables\nJUMP $\n.include \"%s/programs/lib/init_tables.inc\"\n" % HERE)
    c = emu.CPU(P.words, P.data_image()); n = c.run(3_000_000)
    ref = emu.CPU([]); ref.fill_tables()
    assert all(c.tables[i] == ref.tables[i] for i in range(4))
    return n

# ---- profiling of executed instruction patterns ----
def profile(cpu, ncycles, events=None):
    trace = []; ev = list(events or []); i = 0
    for _ in range(ncycles):
        while i < len(ev) and ev[i][0] <= cpu.cycle: cpu.set_buttons(ev[i][1]); i += 1
        pc = cpu.pc; pe = cpu.pend & cpu.en
        trace.append(None if pe else cpu.dec[pc] if pc < len(cpu.dec) else cpu.empty)
        cpu.step()
    return [t for t in trace if t is not None]

def profile_frames(cpu, start_pc, end_pc, n, events=None):
    """Record executed instructions for n segments from start_pc to the next arrival at end_pc."""
    tr = []
    for _ in range(n):
        cpu.run_until_pc(start_pc, 3_000_000, events)
        while True:
            pc = cpu.pc; pe = cpu.pend & cpu.en
            if not pe: tr.append(cpu.dec[pc] if pc < len(cpu.dec) else cpu.empty)
            cpu.step()
            if cpu.pc == end_pc or len(tr) > 2_000_000: break
    return tr

def patterns(tr):
    n = len(tr); P = collections.Counter()
    for i, t in enumerate(tr):
        op, Rr, S, K, G, Y, O, addr = t
        nx = tr[i + 1] if i + 1 < n else None; nn = tr[i + 2] if i + 2 < n else None
        if op == LOAD and G == R_A and O == S_CONST and nx and nx[0] == STORE and nx[4] == R_A:
            P["store_const (LOAD A,#k + STORE)"] += 1
            if nx[6] == S_ABS and nx[7] >= DEV_BASE: P["store_const to a device port"] += 1
        if op == LOAD and G == R_A and O == S_ABS and nx and nn and nn[0] == STORE and nn[4] == R_A and nn[6] == S_ABS and nn[7] == addr and nx[0] < 7:
            P["read-modify-write memory (LOAD,op,STORE same address)"] += 1
            if nx[0] in (ADD, SUB) and nx[6] == S_CONST and nx[7] == 1 and not nx[5]: P["  of which +1 / -1 (INC/DEC memory)"] += 1
        if op == LOAD and G == R_A and nx and nx[0] == AND and nx[3] == 0 and nx[6] == S_CONST and nx[7] == 255:
            P["LOAD then TEST #255 (LOAD sets no flags)"] += 1
        if op == LOAD and G in (R_XL, R_XH, R_X): P["pointer setup (LOAD XL/XH/X)"] += 1
        if op == DJNZ and i >= 2 and tr[i - 1][0] == STORE and tr[i - 2][0] == STORE: P["DJNZ closing a 2-store pixel loop"] += 1
        if op == STORE and O == S_ABS and addr == LCD_DATA: P["STORE to LCD data (bus writes)"] += 1
        if op == SHL and K and not Y and i >= 1 and tr[i - 1][0] != SHL: 
            run = 1
            while i + run < n and tr[i + run][0] == SHL: run += 1
            if run >= 3: P["shift runs of >= 3 SHL (candidates for MUL #2^n)"] += 1; P["  cycles in those runs"] += run
        if op == LOAD and G in (R_A,) and O == S_ABS: P["LOAD A,[addr]"] += 1
    P["instructions"] = n
    return P

SAVE = {"store_const (LOAD A,#k + STORE)": 1, "read-modify-write memory (LOAD,op,STORE same address)": 2,
        "LOAD then TEST #255 (LOAD sets no flags)": 1}

def report_patterns(name, P, prog=None):
    if prog is not None: print('  static (words that a store-immediate / memory-destination op / flag-setting LOAD would remove): ' + str(dict(static_counts(prog))))
    tot = P["instructions"]
    R[name]["patterns"] = dict(P)
    print("  patterns in %s (%d instructions profiled):" % (name, tot))
    for k, v in sorted(P.items()):
        if k != "instructions": print("    %-62s %8d  (%.1f%%)" % (k, v, 100.0 * v / tot))

def static_counts(P):
    d = [emu.CPU._decode(w) for w in P.words]
    out = collections.Counter()
    for i in range(len(d) - 2):
        op, Rr, S, K, G, Y, O, addr = d[i]; nx = d[i + 1]; nn = d[i + 2]
        if op == LOAD and G == R_A and O == S_CONST and nx[0] == STORE and nx[4] == R_A: out["store_const"] += 1
        if op == LOAD and G == R_A and O == S_ABS and nn[0] == STORE and nn[4] == R_A and nn[6] == S_ABS and nn[7] == addr and nx[0] < 7: out["rmw"] += 1
        if op == LOAD and G == R_A and nx[0] == AND and nx[3] == 0 and nx[6] == S_CONST and nx[7] == 255: out["load_test"] += 1
    return out

def main():
    R["init"] = dict(words=init_size(), cycles=startup())
    print("table start-up: %d words, %d cycles" % (R["init"]["words"], R["init"]["cycles"]))
    # ---- counter ----
    P, c = build("counter", tick_cycles=1); c.run_until_pc(P.symbols["wait"], 100)
    cyc = [c.run_until_pc(P.symbols["wait"], 100) for _ in range(5)][-1]
    R["counter"] = dict(words=len(P.words), cycles_per_op=cyc)
    print("counter: %d words, %d cycles per increment (tick always ready)" % (len(P.words), cyc))
    # ---- snake ----
    P, c = build("snake", tick_cycles=1500); S = P.symbols
    script = check_snake.bot_script(300); m = check_snake.Model()
    c.run_until_pc(S["frame"], 100000); steps = []
    for k in range(150):
        if k in script: c.set_buttons(script[k]); c.run(2, stop_on_halt=False); c.set_buttons(0)
        c.run_until_pc(S["step"], 200000)
        r = c.run_until_pc(S["frame"], 200000); steps.append(r)
        m.move(script.get(k, 0))
        if m.dead: break
    steps = steps[:-1] if m.dead else steps
    R["snake"] = dict(words=len(P.words), data=sum(len(b) for _, b in P.data), step_min=min(steps), step_max=max(steps), step_avg=sum(steps) // len(steps))
    print("snake: %d words; cycles per step min %d avg %d max %d" % (len(P.words), min(steps), sum(steps) // len(steps), max(steps)))
    P, c = build("snake", tick_cycles=1500); S = P.symbols; c.run_until_pc(S["frame"], 100000)
    report_patterns("snake", patterns(profile_frames(c, S["step"], S["frame"], 9)), P)
    # ---- pong ----
    P, c = build("pong", tick_cycles=1); S = P.symbols
    c.run_until_pc(S["frame"], 3_000_000)
    cyc = []; btn = lambda f: 2 if 20 <= f < 60 else 1 if 120 <= f < 135 else 0
    for f in range(300):
        c.set_buttons(btn(f)); cyc.append(c.run_until_pc(S["frame"], 100000))
    R["pong"] = dict(words=len(P.words), data=sum(len(b) for _, b in P.data), frame_min=min(cyc), frame_max=max(cyc), frame_avg=sum(cyc) // len(cyc))
    print("pong: %d words; cycles/frame min %d avg %d max %d" % (len(P.words), min(cyc), sum(cyc) // len(cyc), max(cyc)))
    report_patterns("pong", patterns(profile_frames(c, S["frame"], S["frame"], 100)), P)
    # ---- life ----
    P, c = build("life", tick_cycles=1); S = P.symbols
    c.run_until_pc(S["frame"], 3_000_000)
    cyc = [c.run_until_pc(S["frame"], 1_000_000) for _ in range(60)]
    R["life"] = dict(words=len(P.words), data=sum(len(b) for _, b in P.data), frame_min=min(cyc), frame_max=max(cyc), frame_avg=sum(cyc) // len(cyc))
    print("life: %d words; cycles/generation min %d avg %d max %d" % (len(P.words), min(cyc), sum(cyc) // len(cyc), max(cyc)))
    report_patterns("life", patterns(profile_frames(c, S["frame"], S["frame"], 4)), P)
    # ---- scroll ----
    P, c = build("scroll", tick_cycles=1); S = P.symbols
    c.run_until_pc(S["frame"], 3_000_000)
    cyc = [c.run_until_pc(S["frame"], 1_000_000) for _ in range(30)]
    R["scroll"] = dict(words=len(P.words), data=sum(len(b) for _, b in P.data), frame_min=min(cyc), frame_max=max(cyc), frame_avg=sum(cyc) // len(cyc))
    print("scroll: %d words; cycles/frame min %d avg %d max %d" % (len(P.words), min(cyc), sum(cyc) // len(cyc), max(cyc)))
    report_patterns("scroll", patterns(profile_frames(c, S["frame"], S["frame"], 4)), P)
    # ---- raycast ----
    P, c = build("raycast", tick_cycles=1); S = P.symbols
    c.run_until_pc(S["frame"], 5_000_000)
    script = [0] * 2 + [1] * 25 + [8] * 12 + [1] * 15 + [4] * 40 + [2] * 6 + [1] * 60 + [9] * 8 + [1] * 30
    cyc = []
    for b in script: c.set_buttons(b); cyc.append(c.run_until_pc(S["frame"], 2_000_000))
    R["raycast"] = dict(words=len(P.words), data=sum(len(b) for _, b in P.data), frame_min=min(cyc), frame_max=max(cyc), frame_avg=sum(cyc) // len(cyc))
    print("raycast: %d words; cycles/frame min %d avg %d max %d" % (len(P.words), min(cyc), sum(cyc) // len(cyc), max(cyc)))
    save(c, "raycast_full", x0=0, y0=0, w=320, h=240)
    report_patterns("raycast", patterns(profile_frames(c, S["frame"], S["frame"], 3)), P)
    # ---- brainfuck ----
    rows = check_bf.main()
    R["bf"] = [dict(name=a, opt=b, tape8=c_, words=d, cycles=e) for a, b, c_, d, e in rows if a == "hello"]
    # ---- fps table ----
    print("\nclock needed (MHz) = cycles per frame x frames per second")
    for name, key in (("snake", "step"), ("pong", "frame"), ("life", "frame"), ("scroll", "frame"), ("raycast", "frame")):
        d = R[name]; avg, mx = d[key + "_avg"], d[key + "_max"]
        print("  %-8s avg %7d / max %7d cycles:  10 fps %.2f / %.2f MHz   30 fps %.2f / %.2f MHz" % (name, avg, mx, avg * 10e-6, mx * 10e-6, avg * 30e-6, mx * 30e-6))
    json.dump(R, open(os.path.join(HERE, "measure_results.json"), "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
