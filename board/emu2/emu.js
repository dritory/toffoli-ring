'use strict';
// Same semantics as emu.py / isa.py. Memory-map constants repeated here (tests check they agree).
const K = {
  STACK_PAGE: 0x0100, DEV_BASE: 0xFF00, BTN: 0xFF00, IRQ_EN: 0xFF01, IRQ_CAUSE: 0xFF02, FRAME: 0xFF03,
  RNG: 0xFF04, LCD_CMD: 0xFF10, LCD_DATA: 0xFF11, LED: 0xFF20, TBL0: 0xFF30,
  PC_RESET: 0, IRQ_VECTOR: 1, SP_RESET: 0, RSP_RESET: 0, TICK_CYCLES: 16667, LCD_W: 320, LCD_H: 240,
};
const ADD = 0, SUB = 1, SHL = 2, SHR = 3, AND = 4, OR = 5, XOR = 6, LOOKUP = 7, LOAD = 8, STORE = 9,
  PUSH = 10, POP = 11, JUMP = 12, DJNZ = 13, CALL = 14, RET = 15;

function condTrue(S, Z, C) {
  const hit = ((S & 1) && Z) || ((S & 2) && C);
  return !!hit !== !!(S & 4);
}

class LCD {
  constructor() {
    this.fb = new Uint16Array(K.LCD_W * K.LCD_H);
    this.cmd = 0; this.params = [];
    this.sc = 0; this.ec = K.LCD_W - 1; this.sp = 0; this.ep = K.LCD_H - 1;
    this.x = 0; this.y = 0; this.mv = 0; this.half = -1; this.pixels = 0;
  }
  writeCmd(c) {
    this.cmd = c; this.params = []; this.half = -1;
    if (c === 0x2C) { this.x = this.sc; this.y = this.sp; }
  }
  writeData(d) {
    const c = this.cmd;
    if (c === 0x2C) {
      if (this.half < 0) { this.half = d; return; }
      const px = (this.half << 8) | d; this.half = -1;
      if (this.x < K.LCD_W && this.y < K.LCD_H) this.fb[this.y * K.LCD_W + this.x] = px;
      this.pixels++;
      if (this.mv) {
        this.y++;
        if (this.y > this.ep) { this.y = this.sp; this.x++; if (this.x > this.ec) this.x = this.sc; }
      } else {
        this.x++;
        if (this.x > this.ec) { this.x = this.sc; this.y++; if (this.y > this.ep) this.y = this.sp; }
      }
    } else if (c === 0x2A || c === 0x2B) {
      const p = this.params; p.push(d);
      if (p.length === 4) {
        const a = (p[0] << 8) | p[1], b = (p[2] << 8) | p[3];
        if (c === 0x2A) { this.sc = a; this.ec = b; } else { this.sp = a; this.ep = b; }
        this.params = [];
      }
    } else if (c === 0x36) this.mv = (d >> 5) & 1;
  }
}

const CRC_T = (() => { const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
  return t; })();
function crc32(bytes) { let c = 0xFFFFFFFF; for (let i = 0; i < bytes.length; i++) c = CRC_T[(c ^ bytes[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }

class CPU {
  constructor(prog, data, opt) {
    opt = opt || {};
    this.prog = Uint32Array.from(prog);
    this.mem = new Uint8Array(65536);
    for (const [addr, bs] of data || []) this.mem.set(bs, addr);
    this.tables = []; for (let i = 0; i < 8; i++) this.tables.push(new Uint8Array(65536));
    this.tptr = new Array(8).fill(0);
    this.lcd = new LCD();
    this.tickCycles = opt.tick_cycles || K.TICK_CYCLES;
    this.reset();
    if (opt.fast_tables) this.fillTables();
  }
  reset() {
    this.pc = K.PC_RESET; this.a = 0; this.c = 0; this.x = 0; this.sp = K.SP_RESET; this.rsp = K.RSP_RESET;
    this.z = 0; this.cf = 0; this.rstack = new Array(256).fill(0); this.cycle = 0;
    this.btn = 0; this.pend = 0; this.en = 0; this.cause = 0; this.ie = 1; this.tick = 0; this.nextTick = this.tickCycles;
    this.rngs = 0xACE1; this.led = 0; this.wlog = null; this.halted = false;
  }
  fillTables() {
    for (let b = 0; b < 256; b++) for (let a = 0; a < 256; a++) {
      const i = (b << 8) | a, p = a * b;
      this.tables[0][i] = p & 255; this.tables[1][i] = p >> 8;
      this.tables[2][i] = b ? Math.floor(a / b) : 255; this.tables[3][i] = b ? a % b : a;
    }
  }
  setButtons(m) { const rise = m & ~this.btn & 15; this.btn = m & 15; this.pend |= rise; }
  rd(addr) {
    if (addr < K.DEV_BASE) return this.mem[addr];
    switch (addr) {
      case K.BTN: return this.btn;
      case K.IRQ_EN: return this.en;
      case K.IRQ_CAUSE: return this.cause;
      case K.FRAME: { const t = this.tick; this.tick = 0; return t; }
      case K.RNG: { let s = this.rngs; for (let i = 0; i < 8; i++) s = (s >> 1) ^ ((s & 1) ? 0xB400 : 0); this.rngs = s; return s & 255; }
      case K.LED: return this.led;
    }
    return 0;
  }
  wr(addr, v) {
    if (this.wlog) this.wlog.push([addr, v]);
    if (addr < K.DEV_BASE) { this.mem[addr] = v; return; }
    if (addr === K.IRQ_EN) this.en = v & 15;
    else if (addr === K.IRQ_CAUSE) this.pend = 0;
    else if (addr === K.LCD_CMD) this.lcd.writeCmd(v);
    else if (addr === K.LCD_DATA) this.lcd.writeData(v);
    else if (addr === K.LED) this.led = v;
    else if (addr >= K.TBL0 && addr < K.TBL0 + 8) {
      const t = addr - K.TBL0; this.tables[t][this.tptr[t]] = v; this.tptr[t] = (this.tptr[t] + 1) & 0xFFFF;
    }
  }
  flags() { return this.z | (this.cf << 1); }
  setreg(g, v) {
    switch (g) {
      case 0: this.a = v & 255; break; case 1: this.c = v & 255; break;
      case 2: this.x = (this.x & 0xFF00) | (v & 255); break;
      case 3: this.x = (this.x & 0x00FF) | ((v & 255) << 8); break;
      case 4: this.x = v & 0xFFFF; break; case 5: this.sp = v & 255; break; case 6: this.rsp = v & 255; break;
      default: this.z = v & 1; this.cf = (v >> 1) & 1;
    }
  }
  getreg(g) {
    switch (g) {
      case 0: return this.a; case 1: return this.c; case 2: case 4: return this.x & 255;
      case 3: return this.x >> 8; case 5: return this.sp; case 6: return this.rsp;
    }
    return this.flags();
  }
  rpush(pc) { this.rsp = (this.rsp - 1) & 255; this.rstack[this.rsp] = pc | (this.z << 16) | (this.cf << 17); }
  rpop() { const e = this.rstack[this.rsp]; this.rsp = (this.rsp + 1) & 255; return e; }
  operand(o, addr) {
    switch (o) {
      case 0: return addr & 255;
      case 1: return this.rd(addr);
      case 2: return this.rd(this.x);
      case 3: { const v = this.rd(this.x); this.x = (this.x + 1) & 0xFFFF; return v; }
      case 4: return this.a; case 5: return this.c; case 6: return this.x & 255;
    }
    return this.x >> 8;
  }
  step() {
    if (this.cycle >= this.nextTick) { this.tick = 1; this.nextTick += this.tickCycles; }
    this.cycle++;
    if (this.ie && (this.pend & this.en)) {
      this.cause = this.pend & this.en; this.pend &= ~this.cause;
      this.rpush(this.pc); this.pc = K.IRQ_VECTOR; this.ie = 0; return;
    }
    const pc = this.pc;
    const w = pc < this.prog.length ? this.prog[pc] : 0;
    const op = w >>> 28, R = (w >>> 27) & 1, S = (w >>> 24) & 7, Kp = (w >>> 23) & 1, G = (w >>> 20) & 7,
      Y = (w >>> 19) & 1, O = (w >>> 16) & 7, addr = w & 0xFFFF;
    let npc = (pc + 1) & 0xFFFF;
    if (op < 8) {
      const a = this.a; let res, v;
      if (op === ADD || op === SUB) {
        v = this.operand(O, addr); const cin = Y ? this.cf : 0;
        const t = op === ADD ? a + v + cin : a - v - cin;
        res = t & 255; this.cf = (t > 255 || t < 0) ? 1 : 0;
      } else if (op === SHL) { res = ((a << 1) | (Y ? this.cf : 0)) & 255; this.cf = a >> 7; }
      else if (op === SHR) { res = (a >> 1) | (Y ? this.cf << 7 : 0); this.cf = a & 1; }
      else {
        v = this.operand(O, addr);
        if (op === AND) res = a & v; else if (op === OR) res = a | v; else if (op === XOR) res = a ^ v;
        else res = this.tables[S][(v << 8) | a];
      }
      this.z = res === 0 ? 1 : 0;
      if (Kp) this.a = res;
    } else if (op === LOAD) {
      if (G === 4 && O === 0) this.x = addr; else this.setreg(G, this.operand(O, addr));
    } else if (op === STORE) {
      const v = this.getreg(G);
      if (O === 1) this.wr(addr, v);
      else if (O === 2) this.wr(this.x, v);
      else if (O === 3) { this.wr(this.x, v); this.x = (this.x + 1) & 0xFFFF; }
    } else if (op === PUSH) {
      const v = this.getreg(G); this.sp = (this.sp - 1) & 255; this.wr(K.STACK_PAGE | this.sp, v);
    } else if (op === POP) {
      const v = this.mem[K.STACK_PAGE | this.sp]; this.sp = (this.sp + 1) & 255; this.setreg(G, v);
    } else if (op === JUMP) {
      if (condTrue(S, this.z, this.cf)) { npc = addr; if (addr === pc && S === 4) this.halted = true; }
    } else if (op === DJNZ) {
      this.c = (this.c - 1) & 255; if (this.c) npc = addr;
    } else if (op === CALL) {
      if (condTrue(S, this.z, this.cf)) { this.rpush(npc); npc = addr; }
    } else {
      if (condTrue(S, this.z, this.cf)) {
        const e = this.rpop(); npc = e & 0xFFFF;
        if (R) { this.z = (e >> 16) & 1; this.cf = (e >> 17) & 1; this.ie = 1; }
      }
    }
    this.pc = npc;
  }
}
module.exports = { CPU, K, crc32 };
