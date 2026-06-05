# 直播大屏拟合

这是从原工作区单独迁移出来的直播大屏工作文件夹，只保留直播概览、直播复盘大屏、数据配置页和本地静态服务相关文件。

视频压缩、视频合并工具已留在上一级目录，不再和直播大屏文件混放。

## 启动

双击 `open-dashboard.bat` 打开直播复盘大屏。

双击 `open-admin.bat` 打开数据配置页。

也可以在当前文件夹运行：

```bat
node serve-local.mjs 10809
```

然后访问：

- `http://127.0.0.1:10809/overview`
- `http://127.0.0.1:10809/dashboard`
- `http://127.0.0.1:10809/admin`

## 文件说明

- `index.html`：统一入口页面。
- `app.js`：路由和直播复盘大屏主逻辑。
- `admin.js`：数据配置页。
- `overview.js`：直播概览页。
- `styles.css`：页面样式。
- `storage.js`、`defaultData.js`、`overviewData.js`、`trendGenerator.js`、`formulas.js`：数据、公式和趋势生成逻辑。
- `trend-data-1min.example.json`：分钟级趋势数据示例。
- `serve-local.mjs`：本地静态服务。
