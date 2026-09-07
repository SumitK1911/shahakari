const { app, BrowserWindow } = require("electron");
const fs = require("fs");
const http = require("http");
const path = require("path");

const role = process.env.SAHAKARI_DESKTOP_ROLE || "admin";
const devUrl = process.env.SAHAKARI_WEB_URL || "http://127.0.0.1:5173";
const distDir = path.join(__dirname, "..", "dist");
const runtimeDir = path.join(__dirname, "..", ".electron-runtime", role);
const userDataDir = path.join(runtimeDir, "user-data");
const cacheDir = path.join(runtimeDir, "cache");
const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2"
};

fs.mkdirSync(userDataDir, { recursive: true });
fs.mkdirSync(cacheDir, { recursive: true });
app.setPath("userData", userDataDir);
app.setPath("cache", cacheDir);
app.commandLine.appendSwitch("disk-cache-dir", cacheDir);
app.commandLine.appendSwitch("disable-gpu-shader-disk-cache");
app.commandLine.appendSwitch("disable-gpu-program-cache");

let staticServer;
let staticServerUrl;

function safeJoin(baseDir, requestPath) {
  const decodedPath = decodeURIComponent(requestPath.split("?")[0]);
  const normalizedPath = decodedPath === "/" ? "/index.html" : decodedPath;
  const target = path.normalize(path.join(baseDir, normalizedPath));
  return target.startsWith(baseDir) ? target : path.join(baseDir, "index.html");
}

function startStaticServer() {
  if (staticServerUrl) return Promise.resolve(staticServerUrl);
  staticServer = http.createServer((req, res) => {
    const filePath = safeJoin(distDir, req.url || "/");
    fs.readFile(filePath, (error, content) => {
      if (error) {
        fs.readFile(path.join(distDir, "index.html"), (indexError, indexContent) => {
          if (indexError) {
            res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
            res.end(`Sahakari desktop build is missing. Run npm run build.\n${indexError.message}`);
            return;
          }
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(indexContent);
        });
        return;
      }
      res.writeHead(200, { "Content-Type": mimeTypes[path.extname(filePath).toLowerCase()] || "application/octet-stream" });
      res.end(content);
    });
  });
  return new Promise((resolve) => {
    staticServer.listen(0, "127.0.0.1", () => {
      const address = staticServer.address();
      staticServerUrl = `http://127.0.0.1:${address.port}`;
      resolve(staticServerUrl);
    });
  });
}

async function loadBuiltApp(win) {
  const url = await startStaticServer();
  await win.loadURL(`${url}/index.html?desktopRole=${encodeURIComponent(role)}`);
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1120,
    minHeight: 720,
    title: `Sahakari ${role[0].toUpperCase()}${role.slice(1)} Desktop`,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (process.env.SAHAKARI_LOAD_DIST === "1") {
    await loadBuiltApp(win);
  } else {
    win.webContents.once("did-fail-load", () => loadBuiltApp(win));
    await win.loadURL(`${devUrl}?desktopRole=${encodeURIComponent(role)}`);
  }
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (staticServer) staticServer.close();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

