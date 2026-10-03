"""Cycle-accurate emulator, one instruction per clock. Semantics: ENCODING.md + isa.py."""
import sys, zlib
from isa import *


class Fault(Exception):
    pass


class LCD:
    """ILI9341-like: 0x2A column window, 0x2B row window, 0x2C memory write (RGB565, hi byte first),
    0x36 MADCTL (bit 5 = row/column exchange: cursor moves down first). Other commands ignored."""
    def __init__(self):
        self.fb = [0] * (LCD_W * LCD_H)
        self.cmd = 0; self.params = []
        self.sc, self.ec, self.sp, self.ep = 0, LCD_W - 1, 0, LCD_H - 1
        self.x = self.y = 0; self.mv = 0; self.half = None
        self.pixels = 0

    def write_cmd(self, c):
        self.cmd = c; self.params = []; self.half = None
        if c == 0x2C:
            self.x, self.y = self.sc, self.sp

    def write_data(self, d):
        c = self.cmd
        if c == 0x2C:
            if self.half is None:
                self.half = d; return
            px = (self.half << 8) | d; self.half = None
            if self.x < LCD_W and self.y < LCD_H:
                self.fb[self.y * LCD_W + self.x] = px
            self.pixels += 1
            if self.mv:
                self.y += 1
                if self.y > self.ep:
                    self.y = self.sp; self.x += 1
                    if self.x > self.ec: self.x = self.sc
            else:
                self.x += 1
                if self.x > self.ec:
                    self.x = self.sc; self.y += 1
                    if self.y > self.ep: self.y = self.sp
        elif c in (0x2A, 0x2B):
            p = self.params; p.append(d)
            if len(p) == 4:
                a = (p[0] << 8) | p[1]; b = (p[2] << 8) | p[3]
                if c == 0x2A: self.sc, self.ec = a, b
                else: self.sp, self.ep = a, b
                self.params = []
        elif c == 0x36:
            self.mv = (d >> 5) & 1

    def crc(self):
        return zlib.crc32(b"".join(p.to_bytes(2, "big") for p in self.fb))

    def rgb(self):
        out = bytearray()
        for p in self.fb:
            r = (p >> 11) & 31; g = (p >> 5) & 63; b = p & 31
            out += bytes(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)))
        return bytes(out)


def rgb565(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


class CPU:
    def __init__(self, prog=(), data=(), tick_cycles=TICK_CYCLES, fast_tables=False,
                 debug=False, regions=None):
        self.prog = [w & 0xFFFFFFFF for w in prog]
        self.dec = [self._decode(w) for w in self.prog]
        self.empty = self._decode(0)
        self.mem = bytearray(65536)
        for addr, bs in data:
            self.mem[addr:addr + len(bs)] = bytes(bs)
        self.tables = [bytearray(65536) for _ in range(8)]
        self.tptr = [0] * 8
        self.lcd = LCD()
        self.tick_cycles = tick_cycles
        self.debug = debug; self.regions = regions
        self.reset()
        if fast_tables: self.fill_tables()

    def reset(self):
        self.pc = PC_RESET; self.a = 0; self.c = 0; self.x = 0
        self.sp = SP_RESET; self.rsp = RSP_RESET; self.z = 0; self.cf = 0
        self.rstack = [0] * 256
        self.cycle = 0
        self.btn = 0; self.pend = 0; self.en = 0; self.cause = 0
        self.tick = 0; self.next_tick = self.tick_cycles
        self.rng = 0xACE1; self.led = 0
        self.sdepth = 0; self.rdepth = 0
        self.wlog = None          # set to a list to record (addr, value) writes
        self.halted = False

    @staticmethod
    def _decode(w):
        d = decode(w)
        return (d['op'], d['R'], d['S'], d['K'], d['G'], d['Y'], d['O'], d['addr'])

    # ---- tables ----
    def fill_tables(self):
        """Fast path: what the start-up routine produces. Index = op<<8 | A."""
        for b in range(256):
            for a in range(256):
                i = (b << 8) | a
                self.tables[T_MUL][i] = (a * b) & 255
                self.tables[T_MULH][i] = (a * b) >> 8
                self.tables[T_DIV][i] = a // b if b else 255
                self.tables[T_MOD][i] = a % b if b else a

    # ---- devices ----
    def set_buttons(self, mask):
        rise = mask & ~self.btn & 15
        self.btn = mask & 15
        self.pend |= rise

    def rd(self, addr):
        if addr < DEV_BASE: return self.mem[addr]
        if addr == BTN: return self.btn
        if addr == IRQ_EN: return self.en
        if addr == IRQ_CAUSE: return self.cause
        if addr == FRAME:
            t = self.tick; self.tick = 0; return t
        if addr == RNG:
            s = self.rng
            for _ in range(8):
                s = (s >> 1) ^ (0xB400 if s & 1 else 0)
            self.rng = s; return s & 255
        if addr == LED: return self.led
        return 0

    def wr(self, addr, v):
        if self.wlog is not None: self.wlog.append((addr, v))
        if addr < DEV_BASE:
            if self.regions is not None and not any(lo <= addr < hi for lo, hi in self.regions):
                raise Fault("write outside declared regions: %04X at pc=%04X" % (addr, self.pc))
            self.mem[addr] = v; return
        if addr == IRQ_EN: self.en = v & 15
        elif addr == IRQ_CAUSE: self.pend = 0
        elif addr == LCD_CMD: self.lcd.write_cmd(v)
        elif addr == LCD_DATA: self.lcd.write_data(v)
        elif addr == LED: self.led = v
        elif TBL0 <= addr < TBL0 + 8:
            t = addr - TBL0; self.tables[t][self.tptr[t]] = v; self.tptr[t] = (self.tptr[t] + 1) & 0xFFFF

    def flags(self): return self.z | (self.cf << 1)

    def setreg(self, g, v):
        if g == R_A: self.a = v & 255
        elif g == R_C: self.c = v & 255
        elif g == R_XL: self.x = (self.x & 0xFF00) | (v & 255)
        elif g == R_XH: self.x = (self.x & 0x00FF) | ((v & 255) << 8)
        elif g == R_X: self.x = v & 0xFFFF
        elif g == R_SP: self.sp = v & 255
        elif g == R_RSP: self.rsp = v & 255
        else: self.z = v & 1; self.cf = (v >> 1) & 1

    def getreg(self, g):
        if g == R_A: return self.a
        if g == R_C: return self.c
        if g == R_XL or g == R_X: return self.x & 255
        if g == R_XH: return self.x >> 8
        if g == R_SP: return self.sp
        if g == R_RSP: return self.rsp
        return self.flags()

    def rpush(self, pc):
        if self.debug:
            self.rdepth += 1
            if self.rdepth > RSTACK_DEPTH: raise Fault("return stack overflow at pc=%04X" % self.pc)
        self.rsp = (self.rsp - 1) & 255
        self.rstack[self.rsp] = pc | (self.z << 16) | (self.cf << 17)

    def rpop(self):
        if self.debug:
            self.rdepth -= 1
            if self.rdepth < 0: raise Fault("return stack underflow at pc=%04X" % self.pc)
        e = self.rstack[self.rsp]; self.rsp = (self.rsp + 1) & 255
        return e

    def operand(self, o, addr):
        if o == S_CONST: return addr & 255
        if o == S_ABS: return self.rd(addr)
        if o == S_X: return self.rd(self.x)
        if o == S_XINC:
            v = self.rd(self.x); self.x = (self.x + 1) & 0xFFFF; return v
        if o == S_A: return self.a
        if o == S_C: return self.c
        if o == S_XL: return self.x & 255
        return self.x >> 8

    # ---- one clock ----
    def step(self):
        if self.cycle >= self.next_tick:
            self.tick = 1; self.next_tick += self.tick_cycles
        self.cycle += 1
        if self.pend & self.en:
            self.cause = self.pend & self.en; self.pend &= ~self.cause
            self.rpush(self.pc); self.pc = IRQ_VECTOR
            return
        pc = self.pc
        op, R, S, K, G, Y, O, addr = self.dec[pc] if pc < len(self.dec) else self.empty
        npc = (pc + 1) & 0xFFFF
        if op < 8:
            a = self.a
            if op == ADD or op == SUB:
                v = self.operand(O, addr)
                cin = self.cf if Y else 0
                t = a + v + cin if op == ADD else a - v - cin
                res = t & 255; self.cf = 1 if (t > 255 or t < 0) else 0
            elif op == SHL:
                res = ((a << 1) | (self.cf if Y else 0)) & 255; self.cf = a >> 7
            elif op == SHR:
                res = (a >> 1) | ((self.cf << 7) if Y else 0); self.cf = a & 1
            else:
                v = self.operand(O, addr)
                if op == AND: res = a & v
                elif op == OR: res = a | v
                elif op == XOR: res = a ^ v
                else: res = self.tables[S][(v << 8) | a]
            self.z = 1 if res == 0 else 0
            if K: self.a = res
        elif op == LOAD:
            if G == R_X and O == S_CONST: self.x = addr
            else: self.setreg(G, self.operand(O, addr))
        elif op == STORE:
            v = self.getreg(G)
            if O == S_ABS: self.wr(addr, v)
            elif O == S_X: self.wr(self.x, v)
            elif O == S_XINC:
                self.wr(self.x, v); self.x = (self.x + 1) & 0xFFFF
        elif op == PUSH:
            if self.debug:
                self.sdepth += 1
                if self.sdepth > 256: raise Fault("data stack overflow at pc=%04X" % pc)
            v = self.getreg(G)
            self.sp = (self.sp - 1) & 255; self.wr(STACK_PAGE | self.sp, v)
        elif op == POP:
            if self.debug:
                self.sdepth -= 1
                if self.sdepth < 0: raise Fault("data stack underflow at pc=%04X" % pc)
            v = self.mem[STACK_PAGE | self.sp]; self.sp = (self.sp + 1) & 255
            self.setreg(G, v)
        elif op == JUMP:
            if cond_true(S, self.z, self.cf):
                npc = addr
                if addr == pc and S == C_ALWAYS: self.halted = True
        elif op == DJNZ:
            self.c = (self.c - 1) & 255
            if self.c: npc = addr
        elif op == CALL:
            if cond_true(S, self.z, self.cf):
                self.rpush(npc); npc = addr
        else:  # RET
            if cond_true(S, self.z, self.cf):
                e = self.rpop(); npc = e & 0xFFFF
                if R: self.z = (e >> 16) & 1; self.cf = (e >> 17) & 1
        self.pc = npc

    def state(self):
        return (self.pc, self.a, self.c, self.x, self.sp, self.rsp, self.z, self.cf)

    def run(self, n, events=None, stop_on_halt=True):
        """Run n clocks. events: list of (cycle, button_mask) sorted by cycle."""
        end = self.cycle + n
        ev = list(events or []); i = 0
        while i < len(ev) and ev[i][0] < self.cycle: i += 1
        while self.cycle < end:
            while i < len(ev) and ev[i][0] <= self.cycle:
                self.set_buttons(ev[i][1]); i += 1
            self.halted = False
            self.step()
            if stop_on_halt and self.halted and not (self.en and ev[i:]):
                break
        return self.cycle

    def run_until_pc(self, pc, maxcycles, events=None):
        """Run until the next fetch is at pc (returns cycles used, or None)."""
        start = self.cycle
        ev = list(events or []); i = 0
        while self.cycle - start < maxcycles:
            while i < len(ev) and ev[i][0] <= self.cycle:
                self.set_buttons(ev[i][1]); i += 1
            self.step()
            if self.pc == pc: return self.cycle - start
        return None


def write_png(path, w, h, rgb, scale=1):
    if scale > 1:
        rows = []
        for y in range(h):
            row = b"".join(rgb[(y * w + x) * 3:(y * w + x) * 3 + 3] * scale for x in range(w))
            rows += [row] * scale
        w, h = w * scale, h * scale
    else:
        rows = [rgb[y * w * 3:(y + 1) * w * 3] for y in range(h)]
    raw = b"".join(b"\x00" + r for r in rows)
    def chunk(t, d):
        c = t + d
        return len(d).to_bytes(4, "big") + c + zlib.crc32(c).to_bytes(4, "big")
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", w.to_bytes(4, "big") + h.to_bytes(4, "big") + bytes((8, 2, 0, 0, 0)))
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def save_frame(cpu, path, x0=0, y0=0, w=LCD_W, h=LCD_H, scale=1):
    rgb = cpu.lcd.rgb()
    sub = b"".join(rgb[((y0 + y) * LCD_W + x0) * 3:((y0 + y) * LCD_W + x0 + w) * 3] for y in range(h))
    write_png(path, w, h, sub, scale)
