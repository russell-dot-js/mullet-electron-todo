const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { randomUUID } = require('node:crypto');

const inspection = process.argv.includes('--inspect-the-counter');
const sheet = path.join(__dirname, 'counter.html');
if (inspection) {
  app.setPath('userData', fs.mkdtempSync(path.join(os.tmpdir(), 'mullet-parking-')));
  if (process.platform === 'linux' && process.env.MULLET_SCREENSHOT) app.disableHardwareAcceleration();
}
let desk;
function registrar(request) {
  return new Promise((resolve, reject) => {
    const clerk = spawn(process.platform === 'win32' ? 'python' : 'python3', [
      path.join(__dirname, 'registrar.py'), path.join(app.getPath('userData'), 'parking.sqlite3'),
    ], { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, MULLET_NODE: process.execPath, ELECTRON_RUN_AS_NODE: '1' } });
    let answer = '';
    let error = '';
    clerk.stdout.on('data', chunk => { answer += chunk; });
    clerk.stderr.on('data', chunk => { error += chunk; });
    clerk.on('error', reject);
    clerk.stdin.on('error', reject);
    clerk.on('close', status => {
      if (status !== 0) return reject(new Error(error || 'Counter closed'));
      try { resolve(JSON.parse(answer)); } catch (err) { reject(err); }
    });
    clerk.stdin.end(JSON.stringify(request));
  });
}

async function openDesk() {
  desk = new BrowserWindow({
    width: 800, height: 640, minWidth: 480, minHeight: 420,
    title: 'Department of Unfinished Parking',
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), nodeIntegration: false, contextIsolation: true, sandbox: true },
  });
  desk.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  desk.webContents.on('will-navigate', event => event.preventDefault());
  await desk.loadFile(sheet);
}

app.whenReady().then(async () => {
  const operations = {
    list: () => ({ action: 'list' }),
    file: (title, token) => ({ action: 'file', title, token }),
    tow: task => ({ action: 'tow', task, token: randomUUID() }),
    receipt: task => ({ action: 'receipt', task }),
  };
  for (const [name, petition] of Object.entries(operations)) {
    ipcMain.handle('parking:' + name, (event, ...args) => {
      if (event.senderFrame !== desk.webContents.mainFrame || event.senderFrame.url !== pathToFileURL(sheet).href)
        throw Error('Petition must originate at this counter.');
      return registrar(petition(...args));
    });
  }
  await openDesk();
  if (inspection) {
    try { await require('./tests/window.cjs')(desk); app.exit(0); }
    catch (error) { console.error(error); app.exit(1); }
  }
}).catch(error => { console.error(error); app.exit(1); });
app.on('window-all-closed', () => app.quit());
