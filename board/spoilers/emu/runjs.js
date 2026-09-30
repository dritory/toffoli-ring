// usage: node runjs.js image.json  -> one state line per cycle (see CPU.snap), full RAM every 1000 cycles
const fs = require('fs');
const { CPU, run } = require('./emu.js');
const img = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const cpu = new CPU(img.prog, img.data);
const out = [];
run(cpu, img.cycles, img.events, c => {
  out.push(c.snap());
  if (c.cycles % 1000 === 0) out.push('F ' + c.fullState());
});
process.stdout.write(out.join('\n') + '\n');
