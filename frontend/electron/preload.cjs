const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("sahakariDesktop", {
  role: process.env.SAHAKARI_DESKTOP_ROLE || "admin",
  platform: process.platform
});
