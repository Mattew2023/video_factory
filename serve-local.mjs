import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const args = process.argv.slice(2).filter(Boolean);
const quiet = args.includes("--quiet");
const positionalArgs = args.filter((arg) => arg !== "--quiet");
const port = Number(positionalArgs[0] || process.env.PORT || 10809);
const host = positionalArgs[1] || process.env.HOST || "127.0.0.1";

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
};

const server = http.createServer(async (request, response) => {
  const requestUrl = new URL(request.url || "/", `http://${host}:${port}`);
  const pathname = decodeURIComponent(requestUrl.pathname);
  const relativePath = pathname === "/" ? "index.html" : pathname.slice(1);
  const filePath = path.resolve(root, relativePath);

  if (!filePath.startsWith(root + path.sep) && filePath !== root) {
    response.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Forbidden");
    return;
  }

  try {
    const body = await readFile(filePath);
    response.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream",
    });
    response.end(request.method === "HEAD" ? undefined : body);
  } catch {
    if (!path.extname(filePath)) {
      const body = await readFile(path.resolve(root, "index.html"));
      response.writeHead(200, {
        "Cache-Control": "no-store",
        "Content-Type": contentTypes[".html"],
      });
      response.end(request.method === "HEAD" ? undefined : body);
      return;
    }

    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not found");
  }
});

server.listen(port, host, () => {
  if (!quiet) {
    console.log(`Serving ${root} at http://${host}:${port}/`);
  }
});
