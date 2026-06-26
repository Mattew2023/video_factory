# Phase 4.5 Screenshot Export Notes

## Scope

This phase stabilizes local preview and screenshot export commands only. It does not change UI layout, dashboard data, source rendering code, reference images, or asset folders.

## Stable Commands

```bash
npm.cmd run preview
npm.cmd run screenshot
```

Equivalent non-Windows form:

```bash
npm run preview
npm run screenshot
```

## Fixed Export Rules

- The preview server uses port `4173` by default.
- Final export uses `http://localhost:4173`.
- Final export does not append `?previewScale=fit`.
- Output path is `output/locked-ui-screenshot.png`.
- Output dimensions must verify as `2560x1348`.

## Files Updated

- `package.json`: adds the `preview` script.
- `scripts/serve-local.js`: exports reusable server helpers while keeping direct CLI startup.
- `scripts/export-screenshot.js`: ensures the preview server is available, captures the fixed viewport, and validates PNG dimensions.
- `docs/SCREENSHOT_EXPORT_GUIDE.md`: records the command contract.
