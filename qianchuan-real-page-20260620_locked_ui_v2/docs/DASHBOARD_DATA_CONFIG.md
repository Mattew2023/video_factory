# Dashboard Data Config

本文档说明 `data/dashboard-data.json` 的字段含义。后续只改业务数据时，优先修改这个 JSON，不要改 UI、CSS 或渲染 JS。

## 修改等级

- 可自由修改字段：直播间名称、日期、开播时间、直播状态、时长、金额、ROI、消耗、趋势点、渠道占比、漏斗数值、直播画面图片。
- 谨慎修改字段：字段名、数组结构、趋势事件类型、图片路径、渠道颜色、漏斗宽度。
- 不建议修改字段：平台控件类字段、当前渲染未使用的保留字段、品牌和卡片固定标题。
- 平台固定文案：如 `抖音电商`、`巨量千川`、`直播大屏`、`刷新数据`、`全屏`、`成交渠道构成`、`直播间核心漏斗` 等，应留在 UI 白名单或渲染层，不应写成业务数据随意改。

## 字段实现状态

### 当前已实现字段

当前 `data/dashboard-data.json` 已存在这些字段：

- 顶层：`date`、`liveStatus`、`startTime`、`duration`、`anchor`、`topMetrics`、`notice`、`trendSettings`、`trendData`、`livePreview`、`rightCards`、`comments`、`warningCount`、`recentSevenDays`。
- 直播间信息：`anchor.name`、`anchor.avatarAsset`。
- 顶部指标：`topMetrics.gmv`、`topMetrics.totalCost`、`topMetrics.netTransactionRoi`、`topMetrics.netTransactionAmount`、`topMetrics.gpm`、`topMetrics.viewToTransactionRate`、`topMetrics.onlineViewerCount`、`topMetrics.exposureToViewRate`、`topMetrics.liveRoomViewerCount`。
- 趋势数据：`trendData[].time`、`trendData[].netTransactionAmount`、`trendData[].cost`、`trendData[].events[].type`。
- 右侧卡片：`rightCards.channelComposition.activeMetric`、`rightCards.channelComposition.centerMetric`、`rightCards.channelComposition.items[].name`、`rightCards.channelComposition.items[].percent`、`rightCards.channelComposition.items[].color`、`rightCards.funnel.items[].label`、`rightCards.funnel.items[].value`、`rightCards.funnel.items[].ratio`、`rightCards.funnel.items[].width`、`rightCards.livePanel.mode`、`rightCards.livePanel.coverAsset`。
- 评论/直播画面：`comments.state`、`comments.items`、`livePreview.mode`、`livePreview.image`、`livePreview.text`。
- 最近 7 天：`recentSevenDays[].date`、`recentSevenDays[].gmv`、`recentSevenDays[].roi`、`recentSevenDays[].cost`。

### 当前未实现字段

- 顶层 `shopName`：当前 JSON 中不存在，页面也不会读取这个字段。

### 未来可扩展字段

- `shopName` 可以作为未来更直观的直播间名称字段扩展，但需要同步更新数据结构和渲染逻辑。当前阶段不要只新增该字段来改直播间名称。

## 顶层字段

| 字段 | 类型 | 修改等级 | 含义 |
| --- | --- | --- | --- |
| `date` | string | 可自由修改 | 大屏对应日期，建议格式为 `YYYY-MM-DD`，例如 `2026-06-20`。 |
| `liveStatus` | string | 可自由修改 | 直播状态，例如 `已结束`。如果未来需要新增状态，先确认 UI 是否有对应样式。 |
| `startTime` | string | 可自由修改 | 开播时间，当前展示为完整时间，建议格式为 `YYYY-MM-DD HH:mm:ss`。 |
| `duration` | string | 可自由修改 | 直播时长展示文案，例如 `4小时5分钟`。 |
| `anchor` | object | 可自由修改 | 直播间/主播基础信息。 |
| `topMetrics` | object | 可自由修改 | 顶部核心指标数据。 |
| `notice` | object | 谨慎修改 | 公告条显示状态与页码，不是业务指标。 |
| `trendSettings` | object | 谨慎修改 | 趋势区控件显示值。当前渲染主要读取 `granularity`，指标标签多数仍是固定 UI。 |
| `trendData` | array | 可自由修改 | 趋势图折线与事件点数据。 |
| `livePreview` | object | 可自由修改 | 右侧直播画面配置。 |
| `rightCards` | object | 可自由修改 | 右侧成交渠道和漏斗数据；第三张直播画面卡片主要读取 `comments` 与 `livePreview`。 |
| `comments` | object | 谨慎修改 | 控制第三张卡片是评论空状态还是直播画面状态。 |
| `warningCount` | number | 可自由修改 | 风险提示数量数据。当前锁定 UI 未直接渲染该字段，作为后续提示数据源保留。 |
| `recentSevenDays` | array | 可自由修改 | 最近 7 天 GMV、ROI、消耗数据。当前锁定 UI 未直接渲染该字段，作为数据源保留。 |

## 直播间名称

当前 JSON 没有顶层 `shopName` 字段；页面实际读取的是：

```json
{
  "anchor": {
    "name": "青岛外贸8号店"
  }
}
```

- 当前已实现字段：`anchor.name`。
- 当前未实现字段：顶层 `shopName`。
- 未来可扩展字段：`shopName`，但需要同步更新渲染逻辑后才会生效。
- `shopName` 目前只是业务称呼，当前真实字段是 `anchor.name`。
- 不要只新增 `shopName` 后期待页面自动更新；当前渲染逻辑不会读取它。
- `anchor.avatarAsset` 是头像图片路径，路径从项目根目录开始写。

## Top Metrics

`topMetrics` 控制顶部 8 个核心指标：

| 字段 | 展示指标 | 建议格式 |
| --- | --- | --- |
| `gmv` | GMV 数据源，目前不在顶部 8 格中直接展示，但与最近 7 天数据可保持一致。 | 数字 |
| `totalCost` | 整体消耗(元) | 数字，建议保留 2 位小数 |
| `netTransactionRoi` | 净成交 ROI | 数字，建议等于 `netTransactionAmount / totalCost` 后保留 2 位小数 |
| `netTransactionAmount` | 净成交金额(元) | 数字，建议保留 2 位小数 |
| `gpm` | GPM(元) | 数字，建议保留 2 位小数 |
| `viewToTransactionRate` | 观看成交转化率 | 数字，页面会追加 `%` |
| `onlineViewerCount` | 实时在线人数 | 整数 |
| `exposureToViewRate` | 曝光观看率(次数) | 数字，页面会追加 `%` |
| `liveRoomViewerCount` | 直播间整体观看人数 | 整数 |

## Trend Settings

```json
{
  "trendSettings": {
    "granularity": "5分钟粒度",
    "selectedMetrics": ["净成交金额", "消耗"],
    "availableMetrics": ["综合成本", "净成交金额", "综合ROI", "消耗", "整体成交金额", "整体支付ROI"]
  }
}
```

- `granularity` 当前会显示在趋势区右侧按钮里。
- `selectedMetrics` 和 `availableMetrics` 是业务数据配置意图；当前锁定 UI 的指标标签仍主要由渲染层固定。
- 不建议把平台控件文案改成和截图无关的新文案。

## Trend Data

`trendData` 是趋势图数组，每个元素代表一个时间点：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `time` | string | 横轴时间标签，建议格式为 `MM/DD HH:mm`。 |
| `netTransactionAmount` | number | 当前时间点净成交金额。 |
| `cost` | number | 当前时间点消耗。 |
| `events` | array | 当前时间点的事件点。支持 `投放动作`、`调控动作`。 |

示例：

```json
{
  "time": "06/20 08:25",
  "netTransactionAmount": 615,
  "cost": 15.1,
  "events": [
    { "type": "调控动作" }
  ]
}
```

## Right Cards

### channelComposition

控制右侧 `成交渠道构成`：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `activeMetric` | string | 卡片右上角按钮文案，当前为 `观看次数`。 |
| `centerMetric` | string | 圆环中心指标配置意图；当前中心文案仍固定显示 `成交金额`。 |
| `items[].name` | string | 渠道名称。 |
| `items[].percent` | number | 渠道占比，单位是百分比，不要带 `%`。 |
| `items[].color` | string | 渠道颜色，建议保持现有蓝色系以匹配截图。 |

### funnel

控制右侧 `直播间核心漏斗`：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `items[].label` | string | 漏斗步骤名称。 |
| `items[].value` | number | 漏斗步骤数值。 |
| `items[].ratio` | string | 步骤旁边显示的转化率，包含 `%`。 |
| `items[].width` | number | 漏斗条宽度百分比，只影响视觉宽度。 |

### livePanel

`rightCards.livePanel` 是保留配置：

```json
{
  "mode": "replay",
  "coverAsset": null
}
```

当前锁定 UI 的第三张卡片主要由 `comments` 和 `livePreview` 控制。若只想替换直播画面图片，请改 `livePreview`。

## Comments And Live Preview

`comments.state` 控制第三张卡片模式：

- `comments.state: "empty"`：显示 `直播实时评论` 空状态。
- 其他值，例如当前的 `livePanelEmpty`：显示 `直播间画面`，并读取 `livePreview`。
- `comments.items` 当前已存在，为评论列表保留字段；当前数据为空数组。

`livePreview` 控制直播画面：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `mode` | string | `empty` 显示空状态；`image` 显示图片。 |
| `image` | string | 图片路径，从项目根目录开始写，例如 `assets/live-preview/example.png`。 |
| `text` | string | 空状态文案，空值时默认显示 `主播暂不在播`。 |

## Recent Seven Days

`recentSevenDays` 是最近 7 天数据数组：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `date` | string | 日期，建议格式为 `YYYY-MM-DD`。 |
| `gmv` | number | 当日 GMV。 |
| `roi` | number | 当日 ROI。 |
| `cost` | number | 当日消耗。 |

建议保持 7 条，并按日期从早到晚排列。

## Warning Count

`warningCount` 表示风险提示数量。当前锁定 UI 未直接渲染完整风险提示卡片，但该字段可作为后续风险提示数量的数据源。

## 平台固定文案

以下内容不建议进入 `dashboard-data.json` 作为可变业务数据：

- 品牌：`抖音电商`、`巨量千川`、`直播大屏`。
- 操作按钮：`刷新数据`、`全屏`、`数据口径说明`。
- 卡片标题：`成交渠道构成`、`直播间核心漏斗`、`整体趋势`、`素材表现`。
- 指标名称：`整体消耗(元)`、`净成交ROI`、`净成交金额(元)` 等。
- 平台提示模板、按钮文案、弹层标题、工具栏文案。
