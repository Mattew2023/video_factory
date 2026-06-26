# Screenshot Export Guide

## Commands

Start the local preview server:

```bash
npm.cmd run preview
```

or:

```bash
npm run preview
```

Export the locked UI screenshot:

```bash
npm.cmd run screenshot
```

or:

```bash
npm run screenshot
```

On Windows PowerShell, prefer `npm.cmd` if the system blocks `npm.ps1` through execution policy. In `cmd.exe`, `npm run screenshot` works normally.

## Contract

- Preview URL: `http://localhost:4173`
- Human fit preview URL: `http://localhost:4173/?previewScale=fit`
- Screenshot URL: `http://localhost:4173`
- Screenshot output: `output/locked-ui-screenshot.png`
- Screenshot size: `2560x1348`
- Device scale factor: `1`

The screenshot command does not use `?previewScale=fit`. That query string is only for browser preview.

## How The Screenshot Command Works

1. Checks whether `http://localhost:4173` is already serving this locked UI page.
2. Starts the local static preview server if the port is free.
3. Captures a `2560x1348` PNG.
4. Verifies that the output PNG dimensions are exactly `2560x1348`.
5. Stops only the preview server that it started itself.

The capture runner is selected in this order:

1. Local `playwright` package, when installed.
2. Bundled Codex runtime Playwright, when available.
3. System Chrome, Chromium, or Edge driven by Playwright.
4. System Chrome, Chromium, or Edge in headless CLI mode.

If another app is already using port `4173`, the command refuses to capture from it unless it serves this locked UI page.
