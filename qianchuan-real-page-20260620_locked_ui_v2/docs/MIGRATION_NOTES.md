# Migration Notes

## Paths

源项目路径：`C:\Users\27110\.codex\worktrees\a0e2\直播大盘\qianchuan-real-page-20260620`

目标项目路径：`C:\Users\27110\.codex\worktrees\a0e2\直播大盘\qianchuan-real-page-20260620_locked_ui_v2`

## Copied Reference Images

- `千川页面截图-回放版本.png`
- `千川页面截图-评论版.png`
- `顶部导航栏局部截图.png`
- `趋势图局部截图.png`
- `右侧卡片局部截图.png`
- `reference-luopan-dashboard-v2.png.png`

## Copied Image Assets

- `474628ec198f2c3ca1de2adb682aee9d.png~tplv-55ejei7tpt-webp.webp`
- `a940c0ca29b1a56488b43b916096598d.png~tplv-55ejei7tpt-webp.webp`
- `tos-cn-avt-0015_1a0c26ad77a8c8838835ea1bbf4b7eaf~c5_168x168.webp`

## Files Not Copied

没有复制 `.js.下载` 文件。

没有复制监控、安全、SDK、埋点、浏览器插件相关文件。

没有复制线上打包后的 JS chunk 作为新项目源码。

没有复制旧 HTML 作为新项目入口页面。

## Why Not Copy Online JS Bundles

源项目中的线上 JS bundle 是压缩后的运行产物，混有业务代码、框架运行时、监控、安全、SDK、埋点和第三方逻辑。

这些文件不适合作为可维护源码，也不适合作为“锁 UI，只开放数据层”的工程基础。新项目应以明确的渲染模块、数据文件和文档约束重建。

## Why Not Use Static Business Values From Old HTML

旧 HTML 中的业务数值来自一次网页保存或截图时的页面状态，包含具体直播间、时间、金额、ROI、趋势点和右侧卡片数据。

这些数值可以作为参考样例，但不能成为 UI 白名单或硬编码内容。新项目的业务数据必须统一来自 `data/dashboard-data.json`。
