#!/usr/bin/env python3
"""Functional checks of the five programs against independent Python models."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from runprog import load
from scripts import SCRIPTS

ok = True


def report(name, cond, msg=''):
    global ok
    ok &= bool(cond)
    print('%-8s %s %s' % (name, 'PASS' if cond else 'FAIL', msg))


def frames(name, ncycles=None, hook=None):
    """Run program, call hook(cpu) at every frame marker (OUT write)."""
    cycles, events = SCRIPTS[name]
    p, cpu = load(name.split('@')[0])
    n = [0]
    def cb(c):
        if len(c.out_events) != n[0]:
            n[0] = len(c.out_events)
            hook(c, n[0])
    emu.run(cpu, ncycles or cycles, events, cb)
    return cpu


# ---- counter: row 0 = count, row r = count - r (history), 16 bit
def counter():
    bad = []
    def h(c, n):
        rows = c.display_rows()
        for r in range(min(n, 16)):
            if rows[r] != (n - r) & 0xFFFF:
                bad.append((n, r))
    frames('counter', hook=h)
    report('counter', not bad, 'row r shows count-r for every frame')


# ---- life vs reference torus implementation
def life_ref(rows):
    g = [[(r >> (15 - x)) & 1 for x in range(16)] for r in rows]
    out = []
    for y in range(16):
        v = 0
        for x in range(16):
            s = sum(g[(y + dy) % 16][(x + dx) % 16] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
            v = (v << 1) | (1 if s == 3 or (g[y][x] and s == 2) else 0)
        out.append(v)
    return out


def life():
    st = {'ref': None, 'gens': 0, 'bad': 0}
    def h(c, n):
        if st['ref'] is None:
            st['ref'] = life_ref(st['start'])
            return
        if c.display_rows() != st['ref']:
            st['bad'] += 1
        st['ref'] = life_ref(st['ref'])
        st['gens'] += 1
    p, cpu = load('life')
    st['start'] = [(p.data[0x90 + 2 * r] << 8) | p.data[0x91 + 2 * r] for r in range(16)]
    n = [0]
    def cb(c):
        if len(c.out_events) != n[0]:
            n[0] = len(c.out_events)
            if st['ref'] is None:
                st['ref'] = life_ref(st['start'])
            else:
                st['ref'] = life_ref(st['ref'])
            st['gens'] += 1
            if c.display_rows() != st['ref']:
                st['bad'] += 1
    emu.run(cpu, 400000, [], cb)
    report('life', st['bad'] == 0 and st['gens'] > 100, '%d generations identical to a reference torus model' % st['gens'])


# ---- snake: pixel count = length + food; head and food lit
def snake():
    res = {'frames': 0, 'bad': [], 'maxlen': 0, 'eats': 0}
    def h(c, n):
        lit = sum(bin(v).count('1') for v in c.display_rows())
        ln, head, food = c.ram[0x0D], c.ram[2], c.ram[3]
        res['maxlen'] = max(res['maxlen'], ln)
        pix = lambda p: (c.ram[0xE0 + (p >> 3)] >> (7 - (p & 7))) & 1
        res['frames'] += 1
        if lit != ln + 1 or not pix(head) or not pix(food):
            res['bad'].append((c.cycles, lit, ln))
    frames('snake', hook=h)
    report('snake', not res['bad'] and res['maxlen'] >= 7, '%d frames, lit pixels = length+food, max length %d' % (res['frames'], res['maxlen']))
    # death: display fills (flash) and game restarts with length 5
    seen = {'flash': 0, 'restart': 0}
    def h2(c, n):
        pass
    cycles, events = SCRIPTS['snake@death']
    p, cpu = load('snake')
    for _ in range(cycles):
        emu.run(cpu, 1, events)
        if sum(bin(v).count('1') for v in cpu.display_rows()) >= 245:   # inverted picture
            seen['flash'] += 1
    report('snake', seen['flash'] > 0 and cpu.ram[0x0D] == 5, 'self collision flashes the display and restarts (length back to 5)')


# ---- pong
def pong():
    res = {'bad': [], 'pl': set(), 'score': 0, 'bounces': 0, 'lastvx': None}
    def h(c, n):
        lit = sum(bin(v).count('1') for v in c.display_rows())
        if lit != 9:
            res['bad'].append((c.cycles, lit))
        res['pl'].add(c.ram[3])
        res['score'] = c.ram[8]
        vx = c.ram[1]
        if res['lastvx'] is not None and vx != res['lastvx']:
            res['bounces'] += 1
        res['lastvx'] = vx
    frames('pong', hook=h)
    report('pong', not res['bad'] and len(res['pl']) > 1, 'always 9 lit pixels (2x4 paddle + ball); paddle moved to %d positions; %d x-direction changes; score byte 0x%02x' % (len(res['pl']), res['bounces'], res['score']))


# ---- scroll: display = last 16 columns of the rendered message
FONT = {}
def scroll():
    p, cpu0 = load('scroll')
    text = ''
    while p.data[0x10 + len(text)]:
        text += chr(p.data[0x10 + len(text)])
    def glyph(ch):
        if ch == ' ':
            return [0] * 5
        i = ord(ch) - 65
        return [p.data[0x38 + 5 * i + k] for k in range(5)]
    cols = []
    for ch in text:
        cols += glyph(ch) + [0]
    bad = []
    def h(c, n):
        # after n frames columns 0..n-1 have entered; display column x shows stream index n-16+x
        rows = c.display_rows()
        for x in range(16):
            idx = n - 16 + x
            col = cols[idx % len(cols)] if idx >= 0 else 0
            for r in range(16):
                want = (col >> (r - 4)) & 1 if 4 <= r <= 10 else 0
                if ((rows[r] >> (15 - x)) & 1) != want:
                    bad.append((n, x, r))
    frames('scroll', hook=h)
    report('scroll', not bad, 'display equals the last 16 columns of the rendered message at every frame (%d bad)' % len(bad))


if __name__ == '__main__':
    counter(); life(); snake(); pong(); scroll()
    sys.exit(0 if ok else 1)
