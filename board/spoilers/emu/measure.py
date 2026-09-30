#!/usr/bin/env python3
"""Measure size, instructions per frame, required clock and instruction use of the five programs."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from isa import *
from runprog import load
from scripts import SCRIPTS

PROGS = ['counter', 'life', 'snake', 'pong', 'scroll']
FRAME = {'counter': 'one scroll+count step', 'life': 'one generation', 'snake': 'one move', 'pong': 'one ball step', 'scroll': 'one pixel of scroll'}


def collect():
    out = {}
    for name in PROGS:
        cyc, ev = SCRIPTS[name]
        p, cpu = load(name)
        marks, isr, st = [], [], {'n': 0, 'int': None, 'idx': 0, 'sreg': 0, 'wrb': 0}

        def cb(c):
            if len(c.out_events) != st['n']:
                st['n'] = len(c.out_events)
                marks.append((c.cycles, c.icount))
            if c.lines & L['INT']:
                st['int'] = c.cycles
            if c.lines & L['RETI'] and st['int'] is not None:
                isr.append(c.cycles - st['int'] + 1)
                st['int'] = None
            if c.lines & L['IDX']:
                st['idx'] += 1
            if c.lines & L['SRC_REG']:
                st['sreg'] += 1
        emu.run(cpu, cyc, ev, cb)
        ins = [marks[i + 1][1] - marks[i][1] for i in range(1, len(marks) - 1)]
        cy = [marks[i + 1][0] - marks[i][0] for i in range(1, len(marks) - 1)]
        static = {}
        for a, w, ln, t in p.listing:
            n = OPNAME.get(w >> 11, '?')
            static[n] = static.get(n, 0) + 1
        out[name] = dict(
            words=p.size, data_bytes=sum(p.data_used), frames=len(marks), frame_is=FRAME[name],
            ins_min=min(ins), ins_mean=sum(ins) / len(ins), ins_max=max(ins),
            cyc_min=min(cy), cyc_mean=sum(cy) / len(cy), cyc_max=max(cy),
            isr_cycles=isr[0] if isr else None, isr_count=len(isr),
            static=static, dynamic={OPNAME[k]: v for k, v in sorted(cpu.hist.items())},
            total_instr=cpu.icount, idx_dyn=st['idx'], sreg_dyn=st['sreg'],
            idx_static=sum(1 for a, w, l, t in p.listing if (w >> 11) < 16 and ((w >> 8) & 3) == 2),
            sreg_static=sum(1 for a, w, l, t in p.listing if (w >> 11) < 16 and ((w >> 8) & 3) == 3),
        )
    return out


if __name__ == '__main__':
    m = collect()
    print('| program | words | frame | instr/frame min / mean / max | clock 10 fps (mean / max) | clock 30 fps (mean / max) |')
    print('|---|---|---|---|---|---|')
    for n, r in m.items():
        print('| %s | %d | %s | %d / %.0f / %d | %.1f / %.1f kHz | %.1f / %.1f kHz |' % (
            n, r['words'], r['frame_is'], r['cyc_min'], r['cyc_mean'], r['cyc_max'],
            10 * r['cyc_mean'] / 1e3, 10 * r['cyc_max'] / 1e3, 30 * r['cyc_mean'] / 1e3, 30 * r['cyc_max'] / 1e3))
    json.dump(m, open('measure.json', 'w'), indent=1)
