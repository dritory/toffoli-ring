#!/usr/bin/env python3
"""Assembler for the visible 8-bit computer.

Syntax (one statement per line, ';' starts a comment):
  label:                     labels (program address in .text, data address in .data)
  .equ NAME, expr            constant
  .text / .data              switch section (text = program words, data = initial data RAM image)
  .org expr                  set location counter of the current section
  .byte e,...  .word e,...   data bytes / 16-bit little endian (in .text: .word is a raw program word)
  .ascii "s"  .asciz "s"     string bytes
  .space n[,fill]            reserve bytes
  .macro NAME p1,p2 ... .endm   text macros; \\p1 substitutes argument, \\@ is a unique number
Instructions:
  LD/ADD/SUB/AND/OR/XOR      R, src     R = A|B; src = expr | [expr] | [B+expr] | A|B (the other register)
  ROL/ROR R                  ST [expr], R   ST [B+expr], R
  JMP/JZ/JNZ/JC/JNC label    RETI   NOP
Expressions: numbers (dec, 0x, 0b), 'c', symbols, + - * / % << >> & | ^ ~ ( ), lo(x) hi(x).
"""
import json
import re
import sys
from isa import *


class AsmError(Exception):
    pass


def split_args(s):
    out, depth, cur, q = [], 0, '', None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in '"\'':
            q = ch
            cur += ch
        elif ch in '[(':
            depth += 1
            cur += ch
        elif ch in '])':
            depth -= 1
            cur += ch
        elif ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip() or out:
        out.append(cur.strip())
    return out


def strip_comment(line):
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in '"\'':
            q = ch
        elif ch == ';':
            return line[:i]
    return line


class Program:
    def __init__(self):
        self.words = [0] * PROG_WORDS
        self.size = 0
        self.data = [0] * 256
        self.data_used = [False] * 256
        self.symbols = {}
        self.listing = []      # (addr, word, srcline, text)

    def to_json(self):
        return {'prog': self.words[:max(self.size, 1)], 'data': self.data[:RAM_END], 'symbols': self.symbols,
                'lines': {str(a): ln for a, w, ln, t in self.listing}}


def preprocess(text):
    """Expand macros. Returns list of (srcline, text)."""
    lines = [(i + 1, strip_comment(l).rstrip()) for i, l in enumerate(text.splitlines())]
    macros, body, cur = {}, None, None
    flat = []
    for n, l in lines:
        s = l.strip()
        m = re.match(r'\.macro\s+(\w+)\s*(.*)$', s, re.I)
        if m:
            if cur:
                raise AsmError('line %d: nested .macro' % n)
            cur = (m.group(1).upper(), [p.strip() for p in m.group(2).split(',') if p.strip()])
            body = []
            continue
        if re.match(r'\.endm\b', s, re.I):
            macros[cur[0]] = (cur[1], body)
            cur = None
            continue
        if cur:
            body.append((n, l))
        else:
            flat.append((n, l))
    uid = [0]

    def expand(items, depth):
        if depth > 8:
            raise AsmError('macro nesting too deep')
        out = []
        for n, l in items:
            s = l.strip()
            m = re.match(r'((?:\w+:\s*)*)(\w+)\s*(.*)$', s)
            if m and m.group(2).upper() in macros:
                params, body = macros[m.group(2).upper()]
                args = split_args(m.group(3))
                if len(args) != len(params):
                    raise AsmError('line %d: macro %s wants %d args' % (n, m.group(2), len(params)))
                uid[0] += 1
                sub = []
                for bn, bl in body:
                    t = bl
                    for p, a in sorted(zip(params, args), key=lambda x: -len(x[0])):
                        t = t.replace('\\' + p, a)
                    t = t.replace('\\@', str(uid[0]))
                    sub.append((n, t))
                if m.group(1).strip():
                    out.append((n, m.group(1)))
                out.extend(expand(sub, depth + 1))
            else:
                out.append((n, l))
        return out
    return expand(flat, 0)


class Asm:
    def __init__(self):
        self.sym = {}

    def ev(self, expr, n, final):
        s = expr.strip()
        if not s:
            raise AsmError('line %d: empty expression' % n)

        def sub(m):
            t = m.group(0)
            if t[0] == "'":
                return str(ord(t[1]))
            if t[0].isdigit():
                return t
            tl = t.lower()
            if tl in ('lo', 'hi'):
                return t
            if t in self.sym:
                return str(self.sym[t])
            if final:
                raise AsmError('line %d: undefined symbol %s' % (n, t))
            return '0'
        py = re.sub(r"'.'|0[xX][0-9a-fA-F]+|0[bB][01]+|\d+|[A-Za-z_@.][\w.@]*", sub, s)
        py = py.replace('/', '//')
        py = re.sub(r'\blo\b', '_lo', py)
        py = re.sub(r'\bhi\b', '_hi', py)
        if not re.fullmatch(r'[\w\s+\-*/%<>&|^~()]*', py):
            raise AsmError('line %d: bad expression %r' % (n, expr))
        try:
            return int(eval(py, {'__builtins__': {}}, {'_lo': lambda x: x & 255, '_hi': lambda x: (x >> 8) & 255}))
        except Exception as e:
            raise AsmError('line %d: cannot evaluate %r (%s)' % (n, expr, e))

    def assemble(self, text):
        items = preprocess(text)
        prog = Program()
        for final in (False, True):
            loc = {'text': 0, 'data': 0}
            sec = 'text'
            prog = Program()
            for n, l in items:
                s = l.strip()
                while True:
                    m = re.match(r'([A-Za-z_][\w.@]*)\s*:\s*(.*)$', s)
                    if not m:
                        break
                    if not final:
                        if m.group(1) in self.sym and self.sym.get('__def_' + m.group(1)):
                            raise AsmError('line %d: duplicate label %s' % (n, m.group(1)))
                        self.sym[m.group(1)] = loc[sec]
                        self.sym['__def_' + m.group(1)] = 1
                    s = m.group(2)
                if not s:
                    continue
                mm = re.match(r'(\.?\w+)\s*(.*)$', s)
                mn, rest = mm.group(1).upper(), mm.group(2).strip()
                args = split_args(rest)
                if mn == '.EQU':
                    if len(args) != 2:
                        raise AsmError('line %d: .equ NAME, expr' % n)
                    self.sym[args[0]] = self.ev(args[1], n, final)
                elif mn == '.TEXT':
                    sec = 'text'
                elif mn == '.DATA':
                    sec = 'data'
                elif mn == '.ORG':
                    loc[sec] = self.ev(rest, n, True)
                elif mn in ('.BYTE', '.WORD', '.ASCII', '.ASCIZ', '.SPACE'):
                    vals = []
                    if mn == '.BYTE':
                        vals = [self.ev(a, n, final) & 255 for a in args]
                    elif mn == '.WORD':
                        if sec == 'text':
                            for a in args:
                                w = self.ev(a, n, final) & 0xFFFF
                                if final:
                                    prog.words[loc['text']] = w
                                    prog.listing.append((loc['text'], w, n, s))
                                loc['text'] += 1
                            continue
                        for a in args:
                            w = self.ev(a, n, final)
                            vals += [w & 255, (w >> 8) & 255]
                    elif mn in ('.ASCII', '.ASCIZ'):
                        st = re.match(r'"(.*)"$', rest)
                        if not st:
                            raise AsmError('line %d: string expected' % n)
                        vals = [ord(ch) for ch in st.group(1)] + ([0] if mn == '.ASCIZ' else [])
                    else:
                        cnt = self.ev(args[0], n, True)
                        fill = self.ev(args[1], n, final) & 255 if len(args) > 1 else 0
                        vals = [fill] * cnt
                    if sec == 'text':
                        raise AsmError('line %d: %s only in .data' % (n, mn.lower()))
                    for v in vals:
                        a = loc['data']
                        if a >= RAM_END:
                            raise AsmError('line %d: initial data at 0x%02x is outside RAM (0x00-0xBF)' % (n, a))
                        if final:
                            if prog.data_used[a]:
                                raise AsmError('line %d: data address 0x%02x initialised twice' % (n, a))
                            prog.data[a] = v
                            prog.data_used[a] = True
                        loc['data'] += 1
                elif mn.startswith('.'):
                    raise AsmError('line %d: unknown directive %s' % (n, mn))
                else:
                    if sec != 'text':
                        raise AsmError('line %d: instruction in .data' % n)
                    a = loc['text']
                    if a >= PROG_WORDS:
                        raise AsmError('line %d: program memory full' % n)
                    w = self.encode(mn, args, n, final)
                    if final:
                        prog.words[a] = w
                        prog.listing.append((a, w, n, s))
                    loc['text'] += 1
            prog.size = max([a for a, _, _, _ in prog.listing] + [-1]) + 1
        prog.symbols = {k: v for k, v in self.sym.items() if not k.startswith('__def_')}
        return prog

    def operand(self, tok, n, final):
        """Classify a source operand -> (S, imm)."""
        t = tok.strip()
        if t.upper() in ('A', 'B'):
            return 3, 0, t.upper()
        m = re.fullmatch(r'\[\s*(.*)\]', t)
        if m:
            inner = m.group(1).strip()
            mi = re.fullmatch(r'[Bb]\s*(?:\+\s*(.*))?', inner)
            if mi:
                return 2, self.imm(mi.group(1) or '0', n, final), None
            mi = re.fullmatch(r'(.*?)\s*\+\s*[Bb]', inner)
            if mi:
                return 2, self.imm(mi.group(1), n, final), None
            return 1, self.imm(inner, n, final), None
        return 0, self.imm(t, n, final), None

    def imm(self, e, n, final):
        v = self.ev(e, n, final)
        if final and not -128 <= v <= 255:
            raise AsmError('line %d: value %d does not fit in 8 bits' % (n, v))
        return v & 255

    def encode(self, mn, args, n, final):
        if mn not in OPCODE:
            raise AsmError('line %d: unknown instruction %s' % (n, mn))
        op = OPCODE[mn]
        if mn in ('NOP', 'RETI'):
            if args:
                raise AsmError('line %d: %s takes no operands' % (n, mn))
            return op << 11
        if op >= 16:
            if len(args) != 1:
                raise AsmError('line %d: %s label' % (n, mn))
            t = self.ev(args[0], n, final)
            if final and not 0 <= t < PROG_WORDS:
                raise AsmError('line %d: jump target %d out of range' % (n, t))
            return (op << 11) | (t & 0x3FF)
        if mn in ('ROL', 'ROR'):
            if len(args) != 1 or args[0].upper() not in ('A', 'B'):
                raise AsmError('line %d: %s A|B' % (n, mn))
            return (op << 11) | ((1 if args[0].upper() == 'B' else 0) << 10)
        if mn == 'ST':
            if len(args) != 2 or args[1].upper() not in ('A', 'B') or not args[0].startswith('['):
                raise AsmError('line %d: ST [addr], A|B' % (n))
            s, imm, _ = self.operand(args[0], n, final)
            return (op << 11) | ((1 if args[1].upper() == 'B' else 0) << 10) | (s << 8) | imm
        if len(args) != 2 or args[0].upper() not in ('A', 'B'):
            raise AsmError('line %d: %s A|B, src' % (n, mn))
        d = 1 if args[0].upper() == 'B' else 0
        s, imm, reg = self.operand(args[1], n, final)
        if reg and reg == args[0].upper():
            raise AsmError('line %d: %s %s,%s: a register cannot be its own source (use ROL/ROR)' % (n, mn, reg, reg))
        return (op << 11) | (d << 10) | (s << 8) | imm


def assemble(text):
    return Asm().assemble(text)


def assemble_file(path):
    with open(path) as f:
        return assemble(f.read())


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('-o', help='write JSON image (prog, data, symbols, lines)')
    ap.add_argument('-l', action='store_true', help='print listing')
    a = ap.parse_args()
    try:
        p = assemble_file(a.src)
    except AsmError as e:
        sys.exit('error: %s' % e)
    if a.l:
        for addr, w, ln, t in p.listing:
            print('%03x  %04x  %4d  %s' % (addr, w, ln, t))
    print('%d words, %d data bytes' % (p.size, sum(p.data_used)), file=sys.stderr)
    if a.o:
        with open(a.o, 'w') as f:
            json.dump(p.to_json(), f)
