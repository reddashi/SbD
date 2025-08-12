const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('plcAPI', {
  getSensorData: () => ipcRenderer.invoke('get-sensor-data'),
  sendOverride: (sensor, value) => ipcRenderer.send('override-sensor', { sensor, value }),
  clearOverride: (sensor) => ipcRenderer.send('clear-override', { sensor }),
});
