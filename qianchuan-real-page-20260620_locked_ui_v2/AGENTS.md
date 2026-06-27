# AGENTS.md

## Project Purpose

This project is a local Qianchuan-style livestream dashboard screenshot generator.

The goal is not to redesign a webpage and not to generate UI with images.
The goal is to keep the UI fixed, read business data from configuration files, render a stable dashboard locally, and export a `2560×1348` screenshot.

Core principle:

> Locked UI, open data.

## Current Project

Target project directory:

```text
qianchuan-real-page-20260620_locked_ui_v2
```

Source reference directory:

```text
../qianchuan-real-page-20260620
```

The source reference directory is only a saved real-page snapshot and reference material.
Do not modify it.

## Hard Rules

1. Do not modify the source reference project:

```text
../qianchuan-real-page-20260620
```

2. Do not modify reference images unless the user explicitly asks.

3. Do not mix Luopan-style UI into the Qianchuan-style page.

4. Do not invent platform UI text.

5. Do not add Chinese UI text unless it already exists in `docs/TEXT_WHITELIST.md` or is first added there with a clear source.

6. Do not change UI/CSS/JS just to change numbers.

7. Business data must come from:

```text
data/dashboard-data.json
```

8. Default behavior should be conservative. If a UI detail lacks reference evidence, mark it as missing evidence instead of guessing.

9. Do not commit test data as the default project state.

10. Do not use image generation to create dashboard UI.

## Data Rules

Business data is configured in:

```text
data/dashboard-data.json
```

Common editable fields include:

* `anchor.name`: livestream room / account name
* `liveStatus`: livestream status
* `startTime`: start time
* `duration`: livestream duration
* `date`: dashboard date
* `topMetrics`: main metric values
* `trendData`: trend chart data
* `rightCards`: right-side cards
* `warningCount`: warning count
* `recentSevenDays`: recent 7-day data
* `livePreview`: livestream preview image / empty state

Important notes:

* Current livestream name field is `anchor.name`.
* There is no top-level `shopName` field at this stage.
* `shopName` is only a future extension field unless implemented later.
* `livePreview` controls the livestream image area.
* ROI should stay logically consistent with transaction amount and cost.
* If test data is used, restore default data before committing unless the user explicitly asks to keep it.

## Livestream Preview Rules

Livestream preview configuration is controlled by:

```json
"livePreview": {
  "mode": "empty",
  "image": "",
  "text": "主播暂不在播"
}
```

Supported modes:

* `empty`: show the dark empty state
* `image`: show the configured image

Images should be placed under:

```text
assets/live-preview/
```

If the image path is empty, invalid, or fails to load, the page should fall back to the empty state.

Do not create fake colorful livestream backgrounds, fake people, fake UI overlays, or generated livestream screenshots.

## Preview and Screenshot

Original-size preview:

```text
http://localhost:4173
```

This is the fixed `2560×1348` canvas.
It may require scrolling in a normal browser window.

Fit preview:

```text
http://localhost:4173/?previewScale=fit
```

This is only for browser inspection.
It should scale the whole fixed canvas, not change internal layout proportions.

Screenshot output:

```text
output/locked-ui-screenshot.png
```

Recommended Windows PowerShell command:

```text
npm.cmd run screenshot
```

In `cmd.exe`, this is also valid:

```text
npm run screenshot
```

PowerShell may block `npm run screenshot` because of `npm.ps1` execution policy. Prefer `npm.cmd run screenshot`.

## Git Rules

At the start of each task, run:

```text
git status --short
git log --oneline -5
```

If the working tree is not clean, do not continue development immediately.
First inspect the existing changes and explain what they are.

Do not use:

```text
git add .
```

Stage only the files relevant to the current task.

Before each commit, confirm:

* source reference project was not modified
* `.gitignore` was not modified unless explicitly requested
* data was not modified unless the task is data-related
* UI/CSS/JS were not modified unless the task explicitly allows it
* screenshots were only updated when the task requires screenshot export

Use small stage-based commits.

## Do Not

Do not:

* modify `../qianchuan-real-page-20260620`
* modify reference screenshots casually
* redesign the page freely
* add unverified UI modules
* add hallucinated platform labels
* mix Qianchuan and Luopan visual styles
* change CSS/JS just to edit numbers
* commit smoke-test data as default data
* overwrite the full JSON file with a small example snippet
* use generated images as real dashboard UI
* continue when the working tree is dirty without first checking the diff

## Human Usage Docs

For human operation instructions, read:

```text
README_USAGE.md
docs/DASHBOARD_DATA_CONFIG.md
docs/DATA_EDITING_EXAMPLES.md
docs/DATA_VALIDATION_RULES.md
docs/LIVE_PREVIEW_CONFIG.md
docs/SCREENSHOT_EXPORT_GUIDE.md
```

This `AGENTS.md` file is for Codex working rules, not for general user documentation.
