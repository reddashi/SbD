const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let py;
let latestData = {};

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 1000,
    webPreferences: {
      preload: path.join(__dirname, 'renderer.js'),
      contextIsolation: true
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(() => {
  py = spawn('python', [path.join(__dirname, 'plc1_collector.py')]);

  py.stdout.on('data', (data) => {
    try {
      const lines = data.toString().split('\n');
      for (const line of lines) {
        if (line.trim()) latestData = JSON.parse(line);
      }
    } catch (err) {
      console.error("JSON error:", err);
    }
  });

  py.stderr.on('data', (data) => {
    console.error("PY ERROR:", data.toString());
  });

  // Send data to renderer
  ipcMain.handle('get-sensor-data', async () => latestData);

  // Handle overrides
  ipcMain.on('override-sensor', (event, { sensor, value }) => {
    if (py) {
      py.stdin.write(JSON.stringify({ type: 'override', sensor, value }) + '\n');
    }
  });

  ipcMain.on('clear-override', (event, { sensor }) => {
    if (py) {
      py.stdin.write(JSON.stringify({ type: 'clear_override', sensor }) + '\n');
    }
  });

  createWindow();
});

app.on('window-all-closed', () => {
  if (py) py.kill();
  if (process.platform !== 'darwin') app.quit();
});
