const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('parking', {
  list: () => ipcRenderer.invoke('parking:list'),
  file: (title, token) => ipcRenderer.invoke('parking:file', title, token),
  tow: id => ipcRenderer.invoke('parking:tow', id),
  receipt: id => ipcRenderer.invoke('parking:receipt', id),
});
