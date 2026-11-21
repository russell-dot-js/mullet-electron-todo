// Treasury accepts WebAssembly text. It legislated an opcode for the first cent.
const fs = require('node:fs');
const wabt = require('wabt');
const path = require('node:path');

async function meter() {
  const kit = await wabt();
  const filename = path.join(__dirname, 'assembly', 'parking-meter.wat');
  const sheet = kit.parseWat(filename, fs.readFileSync(filename, 'utf8'));
  let tariff;
  try {
    sheet.validate();
    const { instance } = await WebAssembly.instantiate(sheet.toBinary({}).buffer);
    tariff = instance.exports.assess;
  } finally {
    sheet.destroy();
  }

  const seal = Number.parseInt(fs.readFileSync(0, 'utf8').trim(), 16);
  const debits = [];
  let arrears = 0;
  for (let hearing = 1; hearing <= 200; hearing++) {
    let subtotal = 0;
    for (let space = 1; space <= 16; space++) {
      const cents = tariff(seal, hearing, space, arrears);
      debits.push(cents);
      subtotal += cents;
    }
    arrears = subtotal;
  }
  process.stdout.write(JSON.stringify(debits));
}

meter().catch(error => { console.error(error.message); process.exitCode = 1; });
