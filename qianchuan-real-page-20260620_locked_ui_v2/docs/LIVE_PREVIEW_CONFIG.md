# Live Preview Config

## 数据入口

直播画面区域由 `data/dashboard-data.json` 的 `livePreview` 控制。

```json
{
  "livePreview": {
    "mode": "empty",
    "image": "",
    "text": "主播暂不在播"
  }
}
```

## 字段说明

- `mode`: 支持 `empty` 和 `image`。
- `image`: `mode` 为 `image` 时使用的图片路径，例如 `assets/live-preview/example.png`。
- `text`: 直播画面空状态文案。当前首版默认使用 `主播暂不在播`。

## 使用图片

1. 将直播画面图片放入 `assets/live-preview/`。
2. 修改 `data/dashboard-data.json`：

```json
{
  "livePreview": {
    "mode": "image",
    "image": "assets/live-preview/example.png",
    "text": ""
  }
}
```

3. 路径从项目根目录开始写，不要写成 Windows 绝对路径。
4. 保持导出地址使用 `http://localhost:4173`，不要使用 `previewScale=fit` 导出。

## 回退规则

- `mode` 为 `empty` 时显示深色空状态。
- `mode` 为 `image` 但 `image` 为空时，显示深色空状态。
- 图片加载失败时，自动回退到深色空状态。
- `text` 为空时，空状态默认显示 `主播暂不在播`。
- 不允许使用自造彩色竖条、渐变直播背景、人物画面或额外 UI 代替真实图片。
