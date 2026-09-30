#!/usr/bin/env python3
"""Run a program with its button script; print text frames and frame-cost statistics.
usage: runprog.py NAME [frame_cycle ...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asm, emu
from scripts import SCRIPTS
from isa import OPNAME

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    p = asm.assemble_file(os.path.join(HERE, 'programs', name.split('@')[0] + '.asm'))
    return p, emu.CPU(p.words, p.data)


def frame_stats(cpu, skip=1):
    ev = [c for c, _ in cpu.out_events]
    d = [ev[i + 1] - ev[i] for i in range(skip, len(ev) - 1)]
    return (len(ev), min(d), sum(d) / len(d), max(d)) if d else None


def main():
    name = sys.argv[1]
    marks = [int(x) for x in sys.argv[2:]]
    cycles, events = SCRIPTS[name]
    p, cpu = load(name)
    for m in sorted(marks) + [cycles]:
        emu.run(cpu, m - cpu.cycles, events)
        if m in marks:
            print('--- %s, cycle %d (out=0x%02x, pc=%03x, frames=%d)' % (name, cpu.cycles, cpu.out, cpu.pc, len(cpu.out_events)))
            print(cpu.render())
    print('program words: %d, cycles: %d, frames: %d, cycles/frame (min/mean/max): %s' % (p.size, cpu.cycles, len(cpu.out_events), frame_stats(cpu)))
    print('opcode histogram:', {OPNAME[k]: v for k, v in sorted(cpu.hist.items())})


if __name__ == '__main__':
    main()
