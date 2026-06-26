# Phase 4.4 Data Smoke Test

本次测试只验证修改 `data/dashboard-data.json` 是否能驱动页面业务数据变化，不修改 UI、CSS、JS 或渲染逻辑。

## 修改字段

- `anchor.name`: `测试直播间-数据冒烟`
- `liveStatus`: 保持 `已结束`
- `duration`: `5小时12分钟`
- `startTime`: `2026-06-25 08:18:36`
- `topMetrics.gmv`: `192921.50`
- `topMetrics.netTransactionAmount`: `192921.50`
- `topMetrics.totalCost`: `3132.12`
- `topMetrics.netTransactionRoi`: `61.59`
- `livePreview.mode`: 保持 `empty`
- `livePreview.image`: 保持空字符串
- `livePreview.text`: 保持 `主播暂不在播`

## ROI 说明

当前 ROI 展示值来自独立字段 `topMetrics.netTransactionRoi`。本次设置为 `61.59`，与 `192921.50 / 3132.12 = 61.5945` 四舍五入后的结果一致。

## 验证范围

- 只允许业务数据和导出截图发生变化。
- 不改趋势图算法。
- 不改页面结构。
- 不改 CSS/JS。
- 不改源项目 `qianchuan-real-page-20260620`。
