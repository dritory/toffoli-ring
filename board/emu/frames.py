#!/usr/bin/env python3
"""Capture text frames of each program (with its button script) for the report."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from runprog import load
from scripts import SCRIPTS

# (script key, program, [('cycle', n) | ('frame', k)], caption)
CAPTURES = [
    ('counter', [('frame', 3), ('frame', 10), ('frame', 150)]),
    ('life', [('cycle', 140), ('frame', 1), ('frame', 3), ('frame', 8), ('frame', 20), ('frame', 23)]),
    ('snake', [('cycle', 300), ('cycle', 700), ('cycle', 1900), ('cycle', 2600), ('cycle', 4800), ('cycle', 8000)]),
    ('snake@death', [('cycle', 430), ('cycle', 500), ('cycle', 570), ('cycle', 1000)]),
    ('pong', [('cycle', 200), ('cycle', 1500), ('cycle', 4000), ('cycle', 6500), ('cycle', 9000), ('cycle', 12000)]),
    ('scroll', [('frame', 12), ('frame', 30), ('frame', 60), ('frame', 100), ('frame', 140), ('frame', 190)]),
]


def capture(key, points):
    cycles, events = SCRIPTS[key]
    p, cpu = load(key.split('@')[0])
    got = {}
    want_frames = {v: i for i, (k, v) in enumerate(points) if k == 'frame'}
    want_cycles = {v: i for i, (k, v) in enumerate(points) if k == 'cycle'}
    n = [0]

    def cb(c):
        if c.cycles in want_cycles:
            got[want_cycles[c.cycles]] = ('cycle %d' % c.cycles, c.render())
        if len(c.out_events) != n[0]:
            n[0] = len(c.out_events)
            if n[0] in want_frames:
                got[want_frames[n[0]]] = ('frame %d' % n[0], c.render())
    emu.run(cpu, cycles, events, cb)
    return [got[i] for i in sorted(got)]


def side_by_side(frames, per_row=3):
    out = []
    for i in range(0, len(frames), per_row):
        chunk = frames[i:i + per_row]
        out.append('   '.join(t.ljust(16) for t, _ in chunk).rstrip())
        for r in range(16):
            out.append('   '.join(f.split('\n')[r] for _, f in chunk))
        out.append('')
    return '\n'.join(out).rstrip()


def all_frames():
    return {k: side_by_side(capture(k, pts)) for k, pts in CAPTURES}


if __name__ == '__main__':
    for k, v in all_frames().items():
        print('==', k)
        print(v)
