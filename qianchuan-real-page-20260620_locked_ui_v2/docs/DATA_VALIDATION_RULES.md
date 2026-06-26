# Data Validation Rules

本文档说明修改 `data/dashboard-data.json` 时建议遵守的数据规则。目标是让页面数据可信，同时不需要改 UI。

## 字段实现状态

### 当前已实现字段

- 直播间名称字段：`anchor.name`。
- 顶层业务字段：`date`、`liveStatus`、`startTime`、`duration`、`topMetrics`、`trendData`、`rightCards`、`warningCount`、`recentSevenDays`、`livePreview`。
- 辅助配置字段：`anchor.avatarAsset`、`notice`、`trendSettings`、`comments`。

### 当前未实现字段

- 顶层 `shopName`：当前 JSON 中不存在，不能把它当成已支持字段来修改。

### 未来可扩展字段

- `shopName`：未来可以作为直播间名称的直观别名或替代字段，但需要同步更新数据结构和渲染逻辑后才会生效。

## 可自由修改字段

这些字段属于业务数据，可以按真实直播情况修改：

- `anchor.name`：当前已实现的直播间名称字段，也就是业务上常说的 `shopName`。
- `liveStatus`：直播状态。
- `date`、`startTime`、`duration`：日期、开播时间、直播时长。
- `topMetrics.gmv`、`topMetrics.totalCost`、`topMetrics.netTransactionRoi`、`topMetrics.netTransactionAmount`。
- `topMetrics.gpm`、`topMetrics.viewToTransactionRate`、`topMetrics.onlineViewerCount`。
- `topMetrics.exposureToViewRate`、`topMetrics.liveRoomViewerCount`。
- `trendData`：趋势图时间点、净成交金额、消耗、事件点。
- `rightCards.channelComposition.items`：成交渠道名称、占比、颜色。
- `rightCards.funnel.items`：漏斗步骤、数值、转化率、宽度。
- `warningCount`：风险提示数量数据。
- `recentSevenDays`：最近 7 天 GMV、ROI、消耗。
- `livePreview`：直播画面模式、图片路径、空状态文案。

## 谨慎修改字段

这些字段会影响结构或交互含义，修改前要确认页面是否支持：

- 字段名本身，例如把 `netTransactionAmount` 改成别的名字会导致页面读不到数据。
- `trendData[].events[].type`，建议只用 `投放动作` 和 `调控动作`。
- `trendSettings.selectedMetrics`、`trendSettings.availableMetrics`，当前锁定 UI 的趋势指标标签主要还是固定渲染。
- `comments.state`，它会影响第三张右侧卡片显示评论空状态还是直播画面。
- `rightCards.channelComposition.items[].color`，颜色会直接进入圆环和图例。
- `rightCards.funnel.items[].width`，宽度只影响视觉，不会自动根据 `value` 计算。
- `rightCards.livePanel`，当前主要是保留字段，直播画面请优先改 `livePreview`。

## 不建议修改字段

- `notice` 中的公告条配置，除非明确要改变公告显示。
- `trendSettings` 中的平台指标文案，除非后续渲染逻辑已经支持动态指标。
- `rightCards.livePanel.coverAsset`，当前直播画面图片不读取这个字段。
- 新增没有渲染逻辑支持的顶层字段，例如只新增当前未实现的 `shopName` 不会改变页面显示。

## 平台固定文案不应进入业务数据

这些是平台 UI 文案或固定控件文案，不应作为可随意修改的业务数据写入 JSON：

- 品牌和标题：`抖音电商`、`巨量千川`、`直播大屏`。
- 顶部操作：`数据口径说明`、`刷新数据`、`全屏`。
- 公告按钮：`公告`、`查看详情`、`我知道了`。
- 卡片标题：`整体趋势`、`素材表现`、`成交渠道构成`、`直播间核心漏斗`。
- 指标名称：`整体消耗(元)`、`净成交ROI`、`净成交金额(元)`、`GPM(元)` 等。
- 第三张卡片固定标题和切换按钮：`直播实时评论`、`直播间画面`、`直播画面`、`直播评论`。

业务数据可以改变数值和业务名称，不要把平台按钮、标题、工具栏文案当作直播业务字段来改。

## ROI 规则

`topMetrics.netTransactionRoi` 建议与成交金额和消耗保持一致：

```text
净成交 ROI = 净成交金额 / 整体消耗
```

对应字段：

- 净成交金额：`topMetrics.netTransactionAmount`
- 整体消耗：`topMetrics.totalCost`
- 净成交 ROI：`topMetrics.netTransactionRoi`

示例：

```text
14872.90 / 679.86 = 21.88
```

如果 `totalCost` 为 `0`，ROI 建议写 `0`，避免出现无法解释的无限大。

## 百分比规则

- `topMetrics.viewToTransactionRate` 和 `topMetrics.exposureToViewRate` 写数字，不要带 `%`，页面会自动追加 `%`。
- `rightCards.channelComposition.items[].percent` 写数字，不要带 `%`。
- `rightCards.funnel.items[].ratio` 当前写字符串，需要包含 `%`，例如 `"8.32%"`。
- 百分比建议保留 1 到 2 位小数，避免页面过长。

## 渠道占比规则

`rightCards.channelComposition.items[].percent` 建议合计接近 100。

- 合计低于 100 时，圆环剩余部分会显示为淡色空段。
- 合计超过 100 时，后面的部分会被截断到 100，图例数值仍会显示原始百分比，容易造成不一致。
- 渠道数量建议保持 5 到 7 个以内，避免右侧图例拥挤。

## 漏斗规则

`rightCards.funnel.items` 建议从上到下逐步递减：

```text
曝光次数 >= 观看次数 >= 商品点击次数 >= 成交订单数
```

同时建议：

- `width` 从上到下递减或持平。
- `ratio` 与相邻步骤的转化关系保持合理。
- `value` 使用数字，不要写逗号，例如写 `84840`，不要写 `"84,840"`。
- 漏斗步骤数量当前建议保持 4 条，以匹配锁定 UI。

## 日期和时间格式

- `date`：建议 `YYYY-MM-DD`，例如 `2026-06-20`。
- `startTime`：建议 `YYYY-MM-DD HH:mm:ss`，例如 `2026-06-20 06:45:31`。
- `trendData[].time`：建议 `MM/DD HH:mm`，例如 `06/20 08:25`。
- `recentSevenDays[].date`：建议 `YYYY-MM-DD`。

修改日期时，建议同时检查：

- 顶层 `date`
- 顶层 `startTime`
- `trendData[].time`
- `recentSevenDays[].date`

## 趋势图规则

- `trendData` 建议按时间从早到晚排序。
- 每个点都保留 `time`、`netTransactionAmount`、`cost`、`events`。
- `events` 没有事件时写空数组 `[]`。
- 事件类型建议只写 `投放动作` 或 `调控动作`，否则当前图上不会出现对应事件点。
- 当前趋势图坐标轴上限固定：净成交金额按 800、消耗按 34 映射。超过上限的值会贴近顶部，不会自动扩轴。

## 图片路径规则

直播画面图片由 `livePreview` 控制：

```json
{
  "livePreview": {
    "mode": "image",
    "image": "assets/live-preview/example.png",
    "text": ""
  }
}
```

规则：

- 图片路径从项目根目录开始写。
- 不要写 Windows 绝对路径。
- 建议把可替换直播画面放在 `assets/live-preview/`。
- 不要把参考截图放进 `assets/live-preview/`；参考图保留在 `assets/reference/`。
- `mode` 为 `empty` 时显示空状态。
- `mode` 为 `image` 但 `image` 为空时显示空状态。
- 图片路径错误或图片加载失败时，页面会回退到空状态。

## JSON 格式规则

- `dashboard-data.json` 必须保持合法 JSON。
- 不能在 JSON 里写注释。
- 字符串必须使用双引号。
- 数字字段尽量写数字，不要写字符串。
- 数组最后一项后面不能有多余逗号。
- 修改前后可以用编辑器或 JSON 校验工具确认格式合法。
