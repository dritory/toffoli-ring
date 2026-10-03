'use strict';
// usage: node runjs.js spec.json  -> prints chunk hashes (every `chunk` cycles) and final digests
const fs = require('fs');
const { CPU, K, crc32 } = require('./emu.js');
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
if (spec.consts) { console.log(JSON.stringify(K)); process.exit(0); }
const cpu = new CPU(spec.words, spec.data.map(([a, b]) => [a, b]), { tick_cycles: spec.tick, fast_tables: spec.fast });
const ev = spec.events || []; let ei = 0;
const chunk = spec.chunk || 1000, from = spec.from, to = spec.to;
let h = 0x811C9DC5; const out = [];
function mix(v) { h = Math.imul(h ^ (v & 0xFFFFFFFF), 16777619) >>> 0; }
cpu.wlog = [];
for (let i = 0; i < spec.cycles; i++) {
  while (ei < ev.length && ev[ei][0] <= cpu.cycle) cpu.setButtons(ev[ei++][1]);
  cpu.step();
  mix(cpu.pc); mix(cpu.a); mix(cpu.c); mix(cpu.x); mix(cpu.sp); mix(cpu.rsp); mix(cpu.z); mix(cpu.cf);
  for (const [a, v] of cpu.wlog) { mix(a); mix(v); }
  if (from !== undefined && cpu.cycle > from && cpu.cycle <= to)
    out.push([cpu.cycle, cpu.pc, cpu.a, cpu.c, cpu.x, cpu.sp, cpu.rsp, cpu.z, cpu.cf, cpu.wlog.map(w => w.join(':')).join(',')].join(' '));
  cpu.wlog.length = 0;
  if (cpu.cycle % chunk === 0) out.push('H ' + cpu.cycle + ' ' + h);
}
let lcdb = Buffer.alloc(cpu.lcd.fb.length * 2);
for (let i = 0; i < cpu.lcd.fb.length; i++) { lcdb[2 * i] = cpu.lcd.fb[i] >> 8; lcdb[2 * i + 1] = cpu.lcd.fb[i] & 255; }
out.push('F ' + [cpu.cycle, h, crc32(cpu.mem), crc32(lcdb), cpu.led, cpu.pc, cpu.a, cpu.x].join(' '));
console.log(out.join('\n'));
