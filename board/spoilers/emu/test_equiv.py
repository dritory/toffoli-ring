#!/usr/bin/env python3
"""Run every program in emu.py and emu.js with the same button script and compare the state every cycle."""
import json, os, subprocess, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asm, emu
from scripts import SCRIPTS

HERE = os.path.dirname(os.path.abspath(__file__))


def py_trace(prog, events, cycles):
    cpu = emu.CPU(prog.words, prog.data)
    out = []

    def cb(c):
        out.append(c.snap())
        if c.cycles % 1000 == 0:
            out.append('F ' + c.full_state())
    emu.run(cpu, cycles, events, cb)
    return out


def fuzz_cases(n=10):
    """Random instruction words (all opcodes incl. undefined ones), random button events, interrupts enabled."""
    import random
    for seed in range(n):
        r = random.Random(seed)
        # word 0: LD A,1   word 1 (interrupt vector): ST [IE],A   then 300 random words
        words = [0x0801, 0x49C2] + [r.getrandbits(16) for _ in range(300)]
        events = [(r.randrange(20000), r.choice(['press', 'release']), r.randrange(4)) for _ in range(60)]
        yield 'fuzz%d' % seed, words, [(i * 37) & 255 for i in range(256)], events


def main():
    node = shutil.which('node')
    if not node:
        print('node not found: JS comparison skipped')
        return 0
    bad = 0
    tmp = tempfile.mkdtemp()
    for name, (cycles, events) in SCRIPTS.items():
        prog = asm.assemble_file(os.path.join(HERE, 'programs', name.split('@')[0] + '.asm'))
        img = os.path.join(tmp, name + '.json')
        with open(img, 'w') as f:
            json.dump({'prog': prog.words, 'data': prog.data, 'events': events, 'cycles': cycles}, f)
        js = subprocess.run([node, os.path.join(HERE, 'runjs.js'), img], capture_output=True, text=True, check=True).stdout.split('\n')
        js = [l for l in js if l]
        py = py_trace(prog, events, cycles)
        if len(js) != len(py):
            print('%-8s FAIL: %d python lines vs %d js lines' % (name, len(py), len(js)))
            bad += 1
            continue
        diff = next((i for i in range(len(py)) if py[i] != js[i]), None)
        if diff is None:
            print('%-8s OK   %d cycles compared (state every cycle, RAM every 1000)' % (name, cycles))
        else:
            print('%-8s FAIL at line %d\n  py: %s\n  js: %s' % (name, diff, py[diff][:200], js[diff][:200]))
            bad += 1
    for name, words, data, events in fuzz_cases():
        img = os.path.join(tmp, name + '.json')
        with open(img, 'w') as f:
            json.dump({'prog': words, 'data': data, 'events': events, 'cycles': 20000}, f)
        js = [l for l in subprocess.run([node, os.path.join(HERE, 'runjs.js'), img], capture_output=True, text=True, check=True).stdout.split('\n') if l]
        cpu = emu.CPU(words, data)
        py = []
        ints = [0]
        def cb(c):
            py.append(c.snap())
            ints[0] += 1 if c.lines & emu.L['INT'] else 0
            if c.cycles % 1000 == 0:
                py.append('F ' + c.full_state())
        emu.run(cpu, 20000, events, cb)
        diff = next((i for i in range(min(len(py), len(js))) if py[i] != js[i]), None)
        if diff is None and len(py) == len(js):
            print('%-8s OK   20000 random-instruction cycles compared (%d interrupt entries)' % (name, ints[0]))
        else:
            print('%-8s FAIL at %s' % (name, diff))
            bad += 1
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
