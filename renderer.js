const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('plcAPI', {
  getSensorData: () => ipcRenderer.invoke('get-sensor-data')
});
