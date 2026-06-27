# 千川直播大屏截图生成器使用说明

## 1. 项目用途

这是一个本地运行的千川风格直播大屏截图生成器。

它的页面样式、布局和截图尺寸已经锁定，日常使用时主要修改业务数据。业务数据来自：

```text
data/dashboard-data.json
```

最终导出的截图固定为：

```text
2560×1348
```

这个项目适合用来长期生成同一套千川风格直播大屏截图，而不是当作后台系统或在线编辑器使用。

## 2. 项目目录

当前项目路径是：

```text
C:\Users\27110\.codex\worktrees\a0e2\直播大盘\qianchuan-real-page-20260620_locked_ui_v2
```

所有命令都需要先进入这个目录再执行。

Windows PowerShell 中可以先执行：

```powershell
cd "C:\Users\27110\.codex\worktrees\a0e2\直播大盘\qianchuan-real-page-20260620_locked_ui_v2"
```

## 3. 常用命令

Windows PowerShell 推荐使用：

```powershell
npm.cmd run preview
npm.cmd run screenshot
```

等价非 Windows 写法：

```bash
npm run preview
npm run screenshot
```

命令实际调用关系：

```text
npm.cmd run preview    -> node scripts/serve-local.js
npm.cmd run screenshot -> node scripts/export-screenshot.js
```

`preview` 用来启动本地预览服务，`screenshot` 用来导出正式截图。

## 4. 预览地址

本地预览地址：

[http://localhost:4173](http://localhost:4173/)

浏览器窗口适配预览地址：

[http://localhost:4173/?previewScale=fit](http://localhost:4173/?previewScale=fit)

说明：

- 普通地址用于查看原始页面。
- `previewScale=fit` 用于在浏览器窗口里看完整页面。
- 正式截图脚本固定使用 [http://localhost:4173](http://localhost:4173/)，不使用 `previewScale=fit`。

## 5. 截图导出

截图命令：

```powershell
npm.cmd run screenshot
```

截图输出路径：

```text
output/locked-ui-screenshot.png
```

固定截图尺寸：

```text
2560×1348
```

截图脚本会固定输出到 `output` 目录，导出的正式截图应保持 2560×1348。

## 6. 数据修改入口

业务数据只改这个文件：

```text
data/dashboard-data.json
```

不要为了修改业务数据去改页面代码、CSS 或布局文件。

如果只是要改直播间名称、直播状态、金额、ROI、趋势图、右侧卡片、评论、直播画面图片，优先检查并修改 `data/dashboard-data.json`。

## 7. dashboard-data.json 主要字段说明

`data/dashboard-data.json` 是整个大屏的主要数据入口。下面是常用字段和大致控制区域。

| 字段 | 大致作用 |
| --- | --- |
| `date` | 当前大屏对应的业务日期。 |
| `liveStatus` | 直播状态，例如已结束、直播中等。 |
| `startTime` | 开播时间。 |
| `duration` | 直播时长。 |
| `anchor` | 主播或直播间基础信息。 |
| `topMetrics` | 顶部核心指标数据。 |
| `notice` | 页面公告条显示状态和页码。 |
| `trendSettings` | 趋势区域的粒度和指标配置意图。 |
| `trendData` | 趋势图折线数据和事件点。 |
| `livePreview` | 右侧直播画面区域配置。 |
| `rightCards` | 右侧成交渠道、漏斗等卡片数据。 |
| `comments` | 评论区域或直播画面切换状态，以及评论列表。 |
| `warningCount` | 风险提示数量数据，具体显示位置以页面实际效果为准。 |
| `recentSevenDays` | 最近 7 天 GMV、ROI、消耗数据。 |

关键子结构说明：

| 字段 | 大致作用 |
| --- | --- |
| `anchor.name` | 页面顶部显示的直播间或主播名称。 |
| `anchor.avatarAsset` | 页面顶部头像图片路径。 |
| `topMetrics.*` | 顶部指标数字，例如消耗、ROI、成交金额、GPM、观看人数等。 |
| `trendData[].time` | 趋势图每个点的时间。 |
| `trendData[].netTransactionAmount` | 趋势图中的净成交金额。 |
| `trendData[].cost` | 趋势图中的消耗。 |
| `trendData[].events[]` | 趋势图上的事件点，例如投放动作、调控动作。 |
| `rightCards.channelComposition.items[]` | 右侧成交渠道构成列表，包括渠道名称、占比和颜色。 |
| `rightCards.funnel.items[]` | 右侧直播间核心漏斗列表，包括步骤、数值、转化率和宽度。 |
| `comments.state` | 控制第三张右侧卡片显示评论状态还是直播画面状态。 |
| `comments.items` | 评论列表，目前可作为后续评论数据入口。 |

这些字段不需要懂代码也可以维护，但要保持 JSON 格式正确。

## 8. 直播画面图片替换

直播画面图片配置字段是：

```text
livePreview.mode
livePreview.image
livePreview.text
```

当前推荐示例：

```json
{
  "livePreview": {
    "mode": "image",
    "image": "assets/live-preview/example.png",
    "text": ""
  }
}
```

说明：

- 替换直播画面图片时，应修改 `livePreview.image`。
- 图片路径从项目根目录开始写，例如 `assets/live-preview/example.png`。
- 渲染代码实际读取 `data.livePreview`。
- `rightCards.livePanel.coverAsset` 当前是保留字段，不作为正式直播画面替换入口。
- 如果 `mode` 是 `empty`，或 `mode` 是 `image` 但 `image` 为空，页面会显示空状态。

## 9. 可改、慎改、不建议改

### 可改

- 业务日期。
- 直播状态。
- 开播时间。
- 直播时长。
- 主播信息。
- 顶部指标。
- 趋势数据。
- 右侧卡片数据。
- 评论数据。
- 近 7 天数据。
- 直播画面图片。

### 慎改

- `trendSettings`。
- `trendData[].events[]`。
- `comments.state`。
- 率值字段。
- 百分比字段。
- 图片路径。

这些字段会影响页面显示逻辑或视觉结果，修改后一定要预览确认。

### 不建议改

- 页面代码。
- CSS。
- 布局结构。
- 截图尺寸。
- 输出文件名。
- 截图脚本 URL。
- 锁定 UI 相关结构。

如果只是业务数字或图片不对，不要为了一个数字去动 CSS。

## 10. 标准使用流程

1. 进入项目目录。
2. 修改 `data/dashboard-data.json`。
3. 执行 `npm.cmd run preview`。
4. 打开 [http://localhost:4173/?previewScale=fit](http://localhost:4173/?previewScale=fit) 检查预览。
5. 确认数据和画面无误。
6. 执行 `npm.cmd run screenshot`。
7. 检查 `output/locked-ui-screenshot.png`。
8. 如数据有误，回到 `data/dashboard-data.json` 修改。
9. 确认无误后再提交。

## 11. 常见问题

### Q1：预览页打不开怎么办？

先确认已经在项目目录执行了：

```powershell
npm.cmd run preview
```

再打开 [http://localhost:4173](http://localhost:4173/)。如果端口被占用，先确认是不是已经有一个预览服务在运行。

### Q2：数据改了但页面没变怎么办？

先确认改的是：

```text
data/dashboard-data.json
```

然后刷新浏览器页面。还没有变化时，检查 JSON 格式是否正确、字段名是否写错、数字是否写成了不该写的字符串。

### Q3：截图尺寸不对怎么办？

正式截图必须使用：

```powershell
npm.cmd run screenshot
```

不要手动用浏览器截图，也不要用 `previewScale=fit` 地址导出正式图。脚本固定导出 `2560×1348`。

### Q4：直播画面图片没更新怎么办？

检查 `livePreview.mode` 是否为 `image`，检查 `livePreview.image` 是否写了正确路径。

图片路径应从项目根目录开始写，例如：

```text
assets/live-preview/example.png
```

不要写 Windows 绝对路径。

### Q5：截图命令失败怎么办？

先确认预览能打开，再确认本机有可用的浏览器或 Playwright 运行环境。还失败时，查看命令行里的错误信息，优先检查端口、图片路径和 JSON 格式。

## 12. 当前已知限制

1. `shopName` 字段当前未实现，不要误以为修改 `shopName` 一定会影响页面；当前页面读取的是 `anchor.name`。
2. `rightCards.livePanel` 当前是保留结构，直播画面替换以 `livePreview` 为准。
3. `AGENTS.md` 当前文件存在但内容为空，项目操作规则暂未从 `AGENTS.md` 中确认。
4. UI 已锁定，后续修改应优先走数据配置，不要直接改 UI。

## 13. 给未来自己的提醒

这是截图生成器，不是后台系统。

先改数据，再预览，再截图。

不要为了一个数字去动 CSS。

每次让 Codex 工作前，先说明“只允许改哪些文件”。
