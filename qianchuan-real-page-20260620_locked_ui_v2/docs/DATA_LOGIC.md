# Data Logic

所有业务数据必须来自 `data/dashboard-data.json`。

包括 GMV、ROI、消耗、成交金额、日期、开播时间、直播时长、最近 7 天数据、趋势图数据、右侧卡片数据、红字提示数量。

后续修改数据时，只能改 `data/dashboard-data.json`，不能顺手改 UI。

`src/data/formulas.js` 只允许放可复用计算和格式化逻辑。

`src/data/trendGenerator.js` 只允许放趋势数据标准化或生成逻辑。

UI 文件不得把业务数值、日期或演示数据硬编码为最终展示内容。
