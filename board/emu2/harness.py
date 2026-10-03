import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asm, emu, isa

PROG = os.path.join(HERE, "programs")
FRAMES = os.path.join(HERE, "frames")

def build(name, **kw):
    """Assemble programs/<name>.asm, return (Program, CPU)."""
    P = asm.assemble_file(os.path.join(PROG, name + ".asm"))
    cpu = emu.CPU(P.words, P.data_image(), regions=P.regions, **kw)
    return P, cpu

def read16(cpu, addr): return cpu.mem[addr] | (cpu.mem[addr + 1] << 8)

def run_to_label(cpu, P, label, maxc, events=None):
    return cpu.run_until_pc(P.symbols[label], maxc, events)

def frame_cycles(cpu, P, label, nframes, events=None, skip=1, maxc=5_000_000):
    """Cycles between successive arrivals at `label` (tick_cycles=1: wait loop never blocks)."""
    out = []
    ev = list(events or []); 
    for i in range(nframes + skip):
        r = cpu.run_until_pc(P.symbols[label], maxc, ev)
        if r is None: raise RuntimeError("label not reached")
        out.append(r)
    return out[skip:]

def save(cpu, name, **kw):
    os.makedirs(FRAMES, exist_ok=True)
    emu.save_frame(cpu, os.path.join(FRAMES, name + ".png"), **kw)
