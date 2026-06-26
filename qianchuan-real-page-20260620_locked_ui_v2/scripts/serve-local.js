import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, isAbsolute, join, normalize, relative } from "node:path";
import { pathToFileURL } from "node:url";

export const root = normalize(join(import.meta.dirname, ".."));
export const defaultPort = 4173;
const expectedIndexMarkers = ['<main id="app"></main>', './src/main.js'];

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".webp": "image/webp"
};

export function getPreviewPort() {
  const port = Number(process.env.PORT || defaultPort);

  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid PORT value: ${process.env.PORT}`);
  }

  return port;
}

function isInsideRoot(filePath) {
  const relativePath = relative(root, filePath);
  return relativePath === "" || (!relativePath.startsWith("..") && !isAbsolute(relativePath));
}

function resolveRequestPath(url, port) {
  const requestPath = decodeURIComponent(new URL(url, `http://localhost:${port}`).pathname);
  const safePath = normalize(join(root, requestPath));

  if (!isInsideRoot(safePath)) {
    return null;
  }

  if (existsSync(safePath) && statSync(safePath).isDirectory()) {
    return join(safePath, "index.html");
  }

  return safePath;
}

export function createLockedUiServer({ port = getPreviewPort() } = {}) {
  return createServer((request, response) => {
    const filePath = resolveRequestPath(request.url || "/", port);

    if (!filePath || !existsSync(filePath)) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }

    response.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Type": mimeTypes[extname(filePath)] || "application/octet-stream"
    });
    createReadStream(filePath).pipe(response);
  });
}

export async function isLockedUiPreviewAvailable({ port = getPreviewPort() } = {}) {
  try {
    const response = await fetch(`http://localhost:${port}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1000)
    });

    if (!response.ok) {
      return false;
    }

    const html = await response.text();
    return expectedIndexMarkers.every((marker) => html.includes(marker));
  } catch {
    return false;
  }
}

export function startLockedUiServer({ port = getPreviewPort(), host, silent = false } = {}) {
  const server = createLockedUiServer({ port });

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, () => {
      server.off("error", reject);
      if (!silent) {
        console.log(`Locked UI preview: http://localhost:${port}`);
        console.log(`Fit preview only: http://localhost:${port}/?previewScale=fit`);
      }
      resolve(server);
    });
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = getPreviewPort();

  startLockedUiServer({ port }).catch(async (error) => {
    if (error.code === "EADDRINUSE" && await isLockedUiPreviewAvailable({ port })) {
      console.log(`Locked UI preview already running: http://localhost:${port}`);
      console.log(`Fit preview only: http://localhost:${port}/?previewScale=fit`);
      return;
    }

    console.error(error.message);
    process.exitCode = 1;
  });
}
