// JavaScript port of emu.py: identical semantics, usable from node (CommonJS) or a browser (window.Emu).
(function () {
  'use strict';
  const LINE_NAMES = ['SRC_IMM', 'SRC_MEM', 'SRC_REG', 'IDX', 'ADDER', 'INV', 'AND', 'OR', 'XOR', 'ROL', 'ROR', 'PASS',
    'WR', 'MEMW', 'UPZ', 'UPC', 'BR', 'BR_Z', 'BR_C', 'BR_NOT', 'RETI', 'R_B', 'INT'];
  const L = {};
  LINE_NAMES.forEach((n, i) => { L[n] = 1 << i; });
  const OPS = {
    NOP: [0, []], LD: [1, ['PASS', 'WR', 'UPZ']], ADD: [2, ['ADDER', 'WR', 'UPZ', 'UPC']],
    SUB: [3, ['ADDER', 'INV', 'WR', 'UPZ', 'UPC']], AND: [4, ['AND', 'WR', 'UPZ']],
    OR: [5, ['OR', 'WR', 'UPZ']], XOR: [6, ['XOR', 'WR', 'UPZ']],
    ROL: [7, ['ROL', 'WR', 'UPZ', 'UPC']], ROR: [8, ['ROR', 'WR', 'UPZ', 'UPC']], ST: [9, ['MEMW']],
    JMP: [16, ['BR']], JZ: [17, ['BR', 'BR_Z']], JNZ: [18, ['BR', 'BR_Z', 'BR_NOT']],
    JC: [19, ['BR', 'BR_C']], JNC: [20, ['BR', 'BR_C', 'BR_NOT']], RETI: [21, ['RETI']],
  };
  const FUNC = new Array(32).fill(0);
  for (const n in OPS) FUNC[OPS[n][0]] = OPS[n][1].reduce((m, x) => m | L[x], 0);
  const SLINES = [];
  for (let d = 0; d < 2; d++) for (let s = 0; s < 4; s++) {
    let m = [L.SRC_IMM, L.SRC_MEM, L.SRC_MEM | L.IDX, L.SRC_REG][s];
    if (d) m |= L.R_B;
    SLINES.push(m);
  }
  function decode(ir) {
    const op = ir >> 11;
    let m = FUNC[op];
    if (op < 16) m |= SLINES[(ir >> 8) & 7];
    return m;
  }
  const RAM_END = 0xC0, IO_BASE = 0xC0, DISP_BASE = 0xE0, VECTOR = 1, PROG_WORDS = 1024;
  const hex = (v, n) => (v >>> 0).toString(16).padStart(n, '0');

  class CPU {
    constructor(prog, data) {
      this.prog = new Array(PROG_WORDS).fill(0);
      prog.forEach((w, i) => { this.prog[i] = w; });
      this.initData = data ? data.slice() : new Array(256).fill(0);
      this.reset();
    }
    reset() {
      this.pc = 0; this.a = 0; this.b = 0; this.z = 0; this.c = 0; this.ie = 0; this.pend = 0; this.btn = 0;
      this.spc = 0; this.sz = 0; this.sc = 0; this.out = 0; this.cycles = 0; this.icount = 0; this.lines = 0;
      this.ram = new Array(256).fill(0); this.ramsum = 0;
      this.initData.forEach((v, i) => {
        if (i < RAM_END || i >= DISP_BASE) { this.ram[i] = v & 255; this.ramsum += (v & 255) * (2 * i + 1); }
      });
      this.ramsum = this.ramsum >>> 0;
      this.hist = {}; this.outEvents = [];
    }
    press(n) { this.btn |= 1 << n; this.pend |= 1 << n; }
    release(n) { this.btn &= ~(1 << n) & 15; }
    read(addr) {
      if (addr >= IO_BASE && addr < DISP_BASE) {
        const k = addr & 3;
        return k === 0 ? this.btn : k === 1 ? this.pend : k === 2 ? this.ie : 0;
      }
      return this.ram[addr];
    }
    write(addr, v) {
      if (addr >= IO_BASE && addr < DISP_BASE) {
        const k = addr & 3;
        if (k === 0) { this.out = v; this.outEvents.push([this.cycles, v]); }
        else if (k === 1) this.pend &= ~v & 15;
        else if (k === 2) this.ie = v & 1;
        return;
      }
      const old = this.ram[addr];
      this.ram[addr] = v;
      this.ramsum = (this.ramsum + (v - old) * (2 * addr + 1)) >>> 0;
    }
    step() {
      const ir = this.prog[this.pc];
      if (this.ie && this.pend) {
        this.lines = L.INT;
        this.spc = this.pc; this.sz = this.z; this.sc = this.c;
        this.pc = VECTOR; this.ie = 0; this.cycles++;
        return;
      }
      const ln = decode(ir);
      this.lines = ln;
      const op = ir >> 11;
      this.hist[op] = (this.hist[op] || 0) + 1;
      this.icount++;
      let pcNext = (this.pc + 1) & 0x3FF;
      if (ln & L.RETI) {
        pcNext = this.spc; this.z = this.sz; this.c = this.sc; this.ie = 1;
      } else if (ln & L.BR) {
        let t;
        if (ln & L.BR_Z) t = this.z; else if (ln & L.BR_C) t = this.c; else t = 1;
        if (ln & L.BR_NOT) t ^= 1;
        if (t) pcNext = ir & 0x3FF;
      } else {
        const imm = ir & 255;
        const rb = (ln & L.R_B) !== 0;
        const x = rb ? this.b : this.a;
        const addr = (imm + ((ln & L.IDX) ? this.b : 0)) & 255;
        let y;
        if (ln & L.SRC_IMM) y = imm;
        else if (ln & L.SRC_MEM) y = this.read(addr);
        else if (ln & L.SRC_REG) y = rb ? this.a : this.b;
        else y = 0;
        let res = 0, cout = this.c;
        if (ln & L.ADDER) {
          const inv = (ln & L.INV) ? 1 : 0;
          const s = x + (y ^ (inv ? 255 : 0)) + inv;
          res = s & 255; cout = s >> 8;
        } else if (ln & L.AND) res = x & y;
        else if (ln & L.OR) res = x | y;
        else if (ln & L.XOR) res = x ^ y;
        else if (ln & L.ROL) { res = ((x << 1) | this.c) & 255; cout = x >> 7; }
        else if (ln & L.ROR) { res = (this.c << 7) | (x >> 1); cout = x & 1; }
        else if (ln & L.PASS) res = y;
        if (ln & L.MEMW) this.write(addr, x);
        if (ln & L.WR) { if (rb) this.b = res; else this.a = res; }
        if (ln & L.UPZ) this.z = res === 0 ? 1 : 0;
        if (ln & L.UPC) this.c = cout;
      }
      this.pc = pcNext;
      this.cycles++;
    }
    snap() {
      return this.cycles + ' ' + hex(this.pc, 3) + ' ' + hex(this.a, 2) + ' ' + hex(this.b, 2) + ' ' +
        this.z + this.c + ' ' + this.ie + hex(this.pend, 1) + ' ' + hex(this.spc, 3) + this.sz + this.sc + ' ' +
        hex(this.out, 2) + ' ' + hex(this.btn, 1) + ' ' + hex(this.ramsum, 8) + ' ' + hex(this.lines, 6);
    }
    fullState() { return this.snap() + ' ' + this.ram.map(v => hex(v, 2)).join(''); }
    displayRows() {
      const r = [];
      for (let i = 0; i < 16; i++) r.push((this.ram[DISP_BASE + 2 * i] << 8) | this.ram[DISP_BASE + 2 * i + 1]);
      return r;
    }
    render(on = '#', off = '.') {
      return this.displayRows().map(v => {
        let s = '';
        for (let x = 0; x < 16; x++) s += ((v >> (15 - x)) & 1) ? on : off;
        return s;
      }).join('\n');
    }
  }

  function run(cpu, ncycles, events, onCycle) {
    const ev = (events || []).filter(e => e[0] >= cpu.cycles).sort((p, q) => p[0] - q[0]);   // past events are not replayed
    let i = 0;
    const end = cpu.cycles + ncycles;
    while (cpu.cycles < end) {
      while (i < ev.length && ev[i][0] <= cpu.cycles) {
        if (ev[i][1] === 'press') cpu.press(ev[i][2]); else cpu.release(ev[i][2]);
        i++;
      }
      cpu.step();
      if (onCycle) onCycle(cpu);
    }
    return cpu;
  }

  const api = { CPU, run, L, LINE_NAMES, decode };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else if (typeof window !== 'undefined') window.Emu = api;
})();
