import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, normalize, delimiter } from "node:path";
import { pathToFileURL } from "node:url";
import { startLockedUiServer } from "./serve-local.js";

const root = normalize(join(import.meta.dirname, ".."));
const port = 4173;
const url = `http://localhost:${port}`;
const output = join(root, "output", "locked-ui-screenshot.png");
const viewport = { width: 2560, height: 1348 };
const serverHost = "127.0.0.1";
const expectedIndexMarkers = ['<main id="app"></main>', './src/main.js'];
const browserArgs = [
  "--disable-gpu",
  "--disable-gpu-compositing",
  "--disable-gpu-sandbox",
  "--disable-dev-shm-usage",
  "--disable-extensions",
  "--disable-background-networking",
  "--disable-component-update",
  "--disable-default-apps",
  "--disable-sync",
  "--no-first-run",
  "--no-default-browser-check"
];

function closeServer(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

async function fetchText(targetUrl) {
  const response = await fetch(targetUrl, {
    cache: "no-store",
    signal: AbortSignal.timeout(1000)
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.text();
}

async function verifyPreviewServer() {
  const html = await fetchText(url);
  const missingMarker = expectedIndexMarkers.find((marker) => !html.includes(marker));

  if (missingMarker) {
    throw new Error(`Port ${port} is not serving the locked UI preview.`);
  }
}

async function ensurePreviewServer() {
  try {
    await verifyPreviewServer();
    return null;
  } catch (error) {
    if (!["TypeError", "TimeoutError"].includes(error.name) && !String(error.message).includes("fetch failed")) {
      throw error;
    }
  }

  const server = await startLockedUiServer({ port, host: serverHost, silent: true });
  await verifyPreviewServer();
  return server;
}

function getPngSize(filePath) {
  const buffer = readFileSync(filePath);
  const signature = buffer.subarray(0, 8).toString("hex");

  if (signature !== "89504e470d0a1a0a") {
    throw new Error(`Output is not a PNG file: ${filePath}`);
  }

  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20)
  };
}

function assertScreenshotOutput(filePath, minMtimeMs) {
  if (!existsSync(filePath) || statSync(filePath).size === 0) {
    throw new Error(`Screenshot was not written: ${filePath}`);
  }

  const stats = statSync(filePath);
  if (stats.mtimeMs < minMtimeMs) {
    throw new Error(`Screenshot output was not refreshed by this run: ${filePath}`);
  }

  const size = getPngSize(filePath);

  if (size.width !== viewport.width || size.height !== viewport.height) {
    throw new Error(`Screenshot size is ${size.width}x${size.height}; expected ${viewport.width}x${viewport.height}.`);
  }
}

function getBundledNodeModuleRoots() {
  const roots = [];

  if (process.env.NODE_PATH) {
    roots.push(...process.env.NODE_PATH.split(delimiter).filter(Boolean));
  }

  if (process.env.USERPROFILE) {
    roots.push(join(process.env.USERPROFILE, ".cache", "codex-runtimes", "codex-primary-runtime", "dependencies", "node", "node_modules"));
  }

  return [...new Set(roots)];
}

function getPnpmPlaywrightCandidates(nodeModulesRoot) {
  const pnpmRoot = join(nodeModulesRoot, ".pnpm");

  if (!existsSync(pnpmRoot)) {
    return [];
  }

  return readdirSync(pnpmRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name.startsWith("playwright@"))
    .map((entry) => join(pnpmRoot, entry.name, "node_modules", "playwright", "index.mjs"));
}

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    // Fall through to known bundled runtime locations.
  }

  for (const nodeModulesRoot of getBundledNodeModuleRoots()) {
    const candidates = [
      join(nodeModulesRoot, "playwright", "index.mjs"),
      ...getPnpmPlaywrightCandidates(nodeModulesRoot)
    ];

    for (const candidate of candidates) {
      if (!existsSync(candidate)) {
        continue;
      }

      try {
        return await import(pathToFileURL(candidate).href);
      } catch {
        // Try the next available capture method.
      }
    }
  }

  return null;
}

async function exportWithPlaywright(playwright) {
  const errors = [];

  try {
    const browser = await playwright.chromium.launch({ args: browserArgs });

    try {
      await captureWithPlaywrightBrowser(browser);
    } finally {
      await browser.close();
    }

    return "playwright";
  } catch (error) {
    errors.push(error.message);
  }

  for (const browserPath of getBrowserCandidates()) {
    if (browserPath.includes("\\") && !existsSync(browserPath)) {
      continue;
    }

    try {
      const browser = await playwright.chromium.launch({
        args: browserArgs,
        executablePath: browserPath
      });

      try {
        await captureWithPlaywrightBrowser(browser);
      } finally {
        await browser.close();
      }

      return `playwright:${browserPath}`;
    } catch (error) {
      errors.push(error.message);
    }
  }

  throw new Error(`Playwright could not launch a browser. ${errors.join(" ")}`);
}

async function captureWithPlaywrightBrowser(browser) {
  const page = await browser.newPage({
    deviceScaleFactor: 1,
    viewport
  });
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForSelector("#app > *", { timeout: 5000 });
  await page.evaluate(() => document.fonts?.ready);
  await page.screenshot({ path: output, fullPage: false });
}

function getBrowserCandidates() {
  if (process.platform === "win32") {
    return [
      process.env.CHROME_PATH,
      "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
      "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
    ].filter(Boolean);
  }

  if (process.platform === "darwin") {
    return [
      process.env.CHROME_PATH,
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
      "google-chrome",
      "chromium",
      "microsoft-edge"
    ].filter(Boolean);
  }

  return [
    process.env.CHROME_PATH,
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge"
  ].filter(Boolean);
}

function runBrowserScreenshot(browserPath, headlessFlag) {
  const args = [
    headlessFlag,
    ...browserArgs,
    "--hide-scrollbars",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=2000",
    "--force-device-scale-factor=1",
    `--window-size=${viewport.width},${viewport.height}`,
    `--screenshot=${output}`,
    url
  ];

  return new Promise((resolve, reject) => {
    const child = spawn(browserPath, args, { windowsHide: true });
    let stderr = "";

    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });

    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${browserPath} exited with code ${code}. ${stderr.trim()}`.trim()));
      }
    });
  });
}

async function exportWithBrowserCli() {
  const errors = [];

  for (const browserPath of getBrowserCandidates()) {
    if (browserPath.includes("\\") && !existsSync(browserPath)) {
      continue;
    }

    for (const headlessFlag of ["--headless=new", "--headless"]) {
      try {
        const attemptStartedAt = Date.now() - 1000;
        await runBrowserScreenshot(browserPath, headlessFlag);
        assertScreenshotOutput(output, attemptStartedAt);
        return browserPath;
      } catch (error) {
        errors.push(error.message);
      }
    }
  }

  throw new Error(`No usable Playwright, Chrome, Chromium, or Edge screenshot runner was found. ${errors.join(" ")}`);
}

try {
  mkdirSync(dirname(output), { recursive: true });
  const server = await ensurePreviewServer();
  const captureStartedAt = Date.now() - 1000;

  try {
    const playwright = await loadPlaywright();
    const runner = playwright ? await exportWithPlaywright(playwright) : await exportWithBrowserCli();

    assertScreenshotOutput(output, captureStartedAt);
    console.log(`Screenshot exported: ${output}`);
    console.log(`Source URL: ${url}`);
    console.log(`Viewport: ${viewport.width}x${viewport.height}`);
    console.log(`Runner: ${runner}`);
  } finally {
    if (server) {
      await closeServer(server);
    }
  }
} catch (error) {
  console.log("Screenshot export failed.");
  console.log(`Target URL: ${url}`);
  console.log(`Output: ${output}`);
  console.log(`Reason: ${error.message}`);
  process.exitCode = 1;
}
