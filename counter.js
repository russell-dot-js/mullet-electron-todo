const form = document.querySelector('form');
const title = document.querySelector('#title');
const bays = document.querySelector('#bays');
const ticket = document.querySelector('#receipt');
const statusLine = document.querySelector('#status');
let token = crypto.randomUUID();
let busy = false;
title.addEventListener('input', () => { token = crypto.randomUUID(); });

async function showTicket(id) {
  const deeds = await window.parking.receipt(id);
  ticket.replaceChildren(...deeds.map(d => {
    const line = document.createElement('p');
    line.textContent = d.action + ' · seal ' + d.seal + ' · ' + d.hearings + ' hearings · ' +
      d.policies + ' policies · ' + d.cents + ' cents payable to ' + d.creditor;
    return line;
  }));
}

async function update() {
  const rows = await window.parking.list();
  bays.replaceChildren(...rows.map(task => {
    const bay = document.createElement('li');
    const label = document.createElement('span');
    label.textContent = (task.closed ? '[x] ' : '[ ] ') + task.title;
    const tow = document.createElement('button');
    tow.textContent = 'Mark done';
    tow.disabled = Boolean(task.closed);
    tow.addEventListener('click', () => conduct(async () => {
      await window.parking.tow(task.id); await update(); await showTicket(task.id);
    }));
    const receipt = document.createElement('button');
    receipt.textContent = 'Receipt';
    receipt.addEventListener('click', () => conduct(() => showTicket(task.id)));
    bay.append(label, tow, receipt);
    return bay;
  }));
}

async function conduct(work) {
  if (busy) return;
  busy = true;
  form.inert = bays.inert = true;
  statusLine.textContent = 'Clerk at the meter…';
  try { await work(); statusLine.textContent = ''; }
  catch (error) { statusLine.textContent = error.message; }
  finally { form.inert = bays.inert = false; busy = false; }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  conduct(async () => {
    const id = await window.parking.file(title.value, token);
    title.value = ''; token = crypto.randomUUID();
    await update(); await showTicket(id);
  });
});
conduct(update);
