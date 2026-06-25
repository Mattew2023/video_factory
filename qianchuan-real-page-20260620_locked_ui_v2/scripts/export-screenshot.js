import { mkdirSync } from "node:fs";
import { dirname, join, normalize } from "node:path";

const root = normalize(join(import.meta.dirname, ".."));
const url = process.env.LOCKED_UI_URL || "http://localhost:4173";
const output = process.env.SCREENSHOT_OUTPUT || join(root, "output", "locked-ui-screenshot.png");

try {
  mkdirSync(dirname(output), { recursive: true });

  const { chromium } = await import("playwright");
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 2560, height: 1348 } });

  await page.goto(url, { waitUntil: "networkidle" });
  await page.screenshot({ path: output, fullPage: false });
  await browser.close();
  console.log(`Screenshot exported: ${output}`);
} catch (error) {
  console.log("Screenshot export requires Playwright in the local environment.");
  console.log(`Target URL: ${url}`);
  console.log(`Planned output: ${output}`);
  console.log(`Reason: ${error.message}`);
  process.exitCode = 1;
}
