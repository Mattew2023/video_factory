# Data Editing Examples

本文档给出常见数据修改案例。除非另有说明，只修改 `data/dashboard-data.json`，不要修改 UI、CSS 或 JS。

所有 JSON 代码块都是“要修改的字段片段”，不是完整文件。实际编辑时要保留未展示的同级字段和数组项，避免误删真实数据结构。

## 修改直播间名称

当前页面读取 `anchor.name`，不是顶层 `shopName`。

- 当前已实现字段：`anchor.name`。
- 当前未实现字段：顶层 `shopName`。
- 未来可扩展字段：`shopName`，但当前只新增它不会改变页面显示。

```json
{
  "anchor": {
    "name": "新的直播间名称",
    "avatarAsset": "assets/images/tos-cn-avt-0015_1a0c26ad77a8c8838835ea1bbf4b7eaf~c5_168x168.webp"
  }
}
```

## 修改直播状态为已结束

```json
{
  "liveStatus": "已结束"
}
```

如需改成其他状态，先确认现有 UI 是否能承载该文案长度和状态样式。

## 修改日期和开播时间

```json
{
  "date": "2026-06-21",
  "startTime": "2026-06-21 07:30:00"
}
```

建议同步检查 `trendData[].time` 和 `recentSevenDays[].date`，避免日期互相矛盾。

## 修改直播时长

```json
{
  "duration": "3小时20分钟"
}
```

建议使用短文案，避免顶部区域溢出。

## 修改 GMV

GMV 目前主要作为业务数据源和最近 7 天数据使用。若本场 GMV 与净成交金额一致，可同步改：

```json
{
  "topMetrics": {
    "gmv": 15800,
    "netTransactionAmount": 15800
  },
  "recentSevenDays": [
    {
      "date": "2026-06-20",
      "gmv": 15800,
      "roi": 23.24,
      "cost": 679.86
    }
  ]
}
```

示例只展示要改的片段。实际 JSON 中要保留 `topMetrics` 的其他指标字段，并保留 `recentSevenDays` 的 7 条结构。

## 修改 ROI

`netTransactionRoi` 建议按 `netTransactionAmount / totalCost` 计算。

```json
{
  "topMetrics": {
    "totalCost": 800,
    "netTransactionAmount": 16000,
    "netTransactionRoi": 20
  }
}
```

如果只改 ROI，不改成交金额和消耗，页面能显示，但数据逻辑会不一致。

## 修改消耗

顶部消耗字段：

```json
{
  "topMetrics": {
    "totalCost": 720.5
  }
}
```

趋势图每个时间点消耗字段：

```json
{
  "trendData": [
    {
      "time": "06/20 08:25",
      "netTransactionAmount": 615,
      "cost": 18.2,
      "events": []
    }
  ]
}
```

最近 7 天消耗字段：

```json
{
  "recentSevenDays": [
    {
      "date": "2026-06-20",
      "gmv": 14872.9,
      "roi": 20.64,
      "cost": 720.5
    }
  ]
}
```

## 修改净成交金额

```json
{
  "topMetrics": {
    "netTransactionAmount": 15200,
    "netTransactionRoi": 22.36
  }
}
```

如趋势图也要对应变化，继续修改 `trendData[].netTransactionAmount`。

## 修改成交渠道占比

```json
{
  "rightCards": {
    "channelComposition": {
      "items": [
        { "name": "直播推荐", "percent": 60, "color": "#dbe5ff" },
        { "name": "短视频及图文引流", "percent": 20, "color": "#aec1f7" },
        { "name": "抖音商城推荐", "percent": 11, "color": "#89a3f2" },
        { "name": "个人主页&店铺&橱窗", "percent": 5, "color": "#5f83ed" },
        { "name": "头条西瓜", "percent": 4, "color": "#3865e9" }
      ]
    }
  }
}
```

`percent` 不要带 `%`。建议所有渠道合计接近 100。

## 修改漏斗数据

```json
{
  "rightCards": {
    "funnel": {
      "items": [
        { "label": "直播间整体曝光次数", "value": 90000, "ratio": "8.50%", "width": 100 },
        { "label": "直播间观看次数", "value": 7650, "ratio": "85.00%", "width": 88 },
        { "label": "商品点击次数", "value": 6100, "ratio": "3.80%", "width": 74 },
        { "label": "成交订单数", "value": 280, "ratio": "4.59%", "width": 62 }
      ]
    }
  }
}
```

建议 `value` 从上到下递减，`width` 也从上到下递减或持平。

## 替换直播画面图片

1. 将图片放入 `assets/live-preview/`。
2. 修改 `livePreview`：

```json
{
  "livePreview": {
    "mode": "image",
    "image": "assets/live-preview/example.png",
    "text": ""
  }
}
```

路径从项目根目录开始写，不要写 Windows 绝对路径。

## 恢复直播画面空状态

```json
{
  "livePreview": {
    "mode": "empty",
    "image": "",
    "text": "主播暂不在播"
  }
}
```

如果 `mode` 是 `image` 但图片路径为空或加载失败，也会回退为空状态。

## 修改趋势图数据

```json
{
  "trendData": [
    {
      "time": "06/20 08:25",
      "netTransactionAmount": 615,
      "cost": 15.1,
      "events": [
        { "type": "调控动作" }
      ]
    },
    {
      "time": "06/20 08:30",
      "netTransactionAmount": 450,
      "cost": 16.3,
      "events": [
        { "type": "投放动作" }
      ]
    }
  ]
}
```

`events` 可以为空数组。事件类型建议只使用 `投放动作` 和 `调控动作`。

## 修改最近 7 天数据

```json
{
  "recentSevenDays": [
    { "date": "2026-06-15", "gmv": 0, "roi": 0, "cost": 0 },
    { "date": "2026-06-16", "gmv": 0, "roi": 0, "cost": 0 },
    { "date": "2026-06-17", "gmv": 0, "roi": 0, "cost": 0 },
    { "date": "2026-06-18", "gmv": 0, "roi": 0, "cost": 0 },
    { "date": "2026-06-19", "gmv": 0, "roi": 0, "cost": 0 },
    { "date": "2026-06-20", "gmv": 14872.9, "roi": 21.88, "cost": 679.86 },
    { "date": "2026-06-21", "gmv": 15800, "roi": 22.5, "cost": 702.22 }
  ]
}
```

建议保持 7 条，按日期从早到晚排列。
