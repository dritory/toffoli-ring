"""Cycle-accurate emulator of the visible 8-bit computer. One step() = one clock.
Execution is driven by the control lines from isa.decode(), as the hardware is."""
from isa import *

M8 = 0xFF


class CPU:
    def __init__(self, prog, data=None):
        self.prog = list(prog) + [0] * (PROG_WORDS - len(prog))
        self.init_data = list(data) if data else [0] * 256
        self.reset()

    def reset(self):
        self.pc = 0
        self.a = self.b = 0
        self.z = self.c = 0
        self.ie = 0
        self.pend = 0
        self.btn = 0
        self.spc = 0
        self.sz = self.sc = 0
        self.out = 0
        self.cycles = 0
        self.icount = 0          # instructions executed (interrupt-entry cycles excluded)
        self.lines = 0
        self.ram = [0] * 256
        self.ramsum = 0
        for i, v in enumerate(self.init_data):
            if i < RAM_END or i >= DISP_BASE:
                self.ram[i] = v & M8
                self.ramsum += (v & M8) * (2 * i + 1)
        self.ramsum &= 0xFFFFFFFF
        self.hist = {}
        self.out_events = []     # (cycle, value) for every OUT write; used as frame markers

    # ---- buttons -------------------------------------------------
    def press(self, n):
        self.btn |= 1 << n
        self.pend |= 1 << n

    def release(self, n):
        self.btn &= ~(1 << n) & 0xF

    # ---- data space ----------------------------------------------
    def read(self, addr):
        if IO_BASE <= addr < DISP_BASE:
            k = addr & 3
            return self.btn if k == 0 else self.pend if k == 1 else self.ie if k == 2 else 0
        return self.ram[addr]

    def write(self, addr, v):
        if IO_BASE <= addr < DISP_BASE:
            k = addr & 3
            if k == 0:
                self.out = v
                self.out_events.append((self.cycles, v))
            elif k == 1:
                self.pend &= ~v & 0xF
            elif k == 2:
                self.ie = v & 1
            return
        old = self.ram[addr]
        self.ram[addr] = v
        self.ramsum = (self.ramsum + (v - old) * (2 * addr + 1)) & 0xFFFFFFFF

    # ---- one clock -----------------------------------------------
    def step(self):
        ir = self.prog[self.pc]
        if self.ie and self.pend:
            # interrupt entry: the fetched instruction is suppressed
            self.lines = L['INT']
            self.spc, self.sz, self.sc = self.pc, self.z, self.c
            self.pc = VECTOR
            self.ie = 0
            self.cycles += 1
            return
        ln = decode(ir)
        self.lines = ln
        op = ir >> 11
        self.hist[op] = self.hist.get(op, 0) + 1
        self.icount += 1
        pc_next = (self.pc + 1) & 0x3FF
        if ln & L['RETI']:
            pc_next = self.spc
            self.z, self.c = self.sz, self.sc
            self.ie = 1
        elif ln & L['BR']:
            if ln & L['BR_Z']:
                t = self.z
            elif ln & L['BR_C']:
                t = self.c
            else:
                t = 1
            if ln & L['BR_NOT']:
                t ^= 1
            if t:
                pc_next = ir & 0x3FF
        else:
            imm = ir & M8
            rb = (ln & L['R_B']) != 0
            x = self.b if rb else self.a
            addr = (imm + (self.b if ln & L['IDX'] else 0)) & M8
            if ln & L['SRC_IMM']:
                y = imm
            elif ln & L['SRC_MEM']:
                y = self.read(addr)
            elif ln & L['SRC_REG']:
                y = self.a if rb else self.b
            else:
                y = 0
            res = 0
            cout = self.c
            if ln & L['ADDER']:
                inv = 1 if ln & L['INV'] else 0
                s = x + (y ^ (M8 if inv else 0)) + inv
                res, cout = s & M8, s >> 8
            elif ln & L['AND']:
                res = x & y
            elif ln & L['OR']:
                res = x | y
            elif ln & L['XOR']:
                res = x ^ y
            elif ln & L['ROL']:
                res, cout = ((x << 1) | self.c) & M8, x >> 7
            elif ln & L['ROR']:
                res, cout = (self.c << 7) | (x >> 1), x & 1
            elif ln & L['PASS']:
                res = y
            if ln & L['MEMW']:
                self.write(addr, x)
            if ln & L['WR']:
                if rb:
                    self.b = res
                else:
                    self.a = res
            if ln & L['UPZ']:
                self.z = 1 if res == 0 else 0
            if ln & L['UPC']:
                self.c = cout
        self.pc = pc_next
        self.cycles += 1

    # ---- observation ---------------------------------------------
    def snap(self):
        """Compact state string compared cycle by cycle against emu.js."""
        return "%d %03x %02x %02x %d%d %d%x %03x%d%d %02x %x %08x %06x" % (
            self.cycles, self.pc, self.a, self.b, self.z, self.c, self.ie, self.pend,
            self.spc, self.sz, self.sc, self.out, self.btn, self.ramsum, self.lines)

    def full_state(self):
        return "%s %s" % (self.snap(), ''.join('%02x' % v for v in self.ram))

    def display_rows(self):
        return [(self.ram[DISP_BASE + 2 * r] << 8) | self.ram[DISP_BASE + 2 * r + 1] for r in range(16)]

    def render(self, on='#', off='.'):
        return '\n'.join(''.join(on if (v >> (15 - x)) & 1 else off for x in range(16))
                         for v in self.display_rows())


def run(cpu, ncycles, events=(), on_cycle=None):
    """Run ncycles clocks. events: (cycle, 'press'|'release', button) applied just before that cycle."""
    ev = sorted((e for e in events if e[0] >= cpu.cycles), key=lambda e: e[0])   # events in the past are not replayed
    i = 0
    end = cpu.cycles + ncycles
    while cpu.cycles < end:
        while i < len(ev) and ev[i][0] <= cpu.cycles:
            (cpu.press if ev[i][1] == 'press' else cpu.release)(ev[i][2])
            i += 1
        cpu.step()
        if on_cycle:
            on_cycle(cpu)
    return cpu
