const TREND_PAD = {
  top: 58,
  right: 88,
  bottom: 168,
  left: 86,
};

function getCanvasContext(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.round(canvas.clientWidth || canvas.getBoundingClientRect().width));
  const height = Math.max(1, Math.round(canvas.clientHeight || canvas.getBoundingClientRect().height));

  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  return { ctx, width, height };
}

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function niceCeil(value, step) {
  return Math.max(step, Math.ceil(toNumber(value) / step) * step);
}

function formatAxisNumber(value) {
  const number = toNumber(value);
  return number.toLocaleString("zh-CN", {
    maximumFractionDigits: number % 1 === 0 ? 0 : 1,
  });
}

function drawTrendPath(ctx, points, smoothness = 0.18) {
  if (!points.length) return;

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const offset = (current.x - previous.x) * smoothness;
    ctx.bezierCurveTo(previous.x + offset, previous.y, current.x - offset, current.y, current.x, current.y);
  }
}

function drawSeries(ctx, points, style, plotBottom) {
  if (!points.length) return;

  const { color, fillColor, lineWidth, shadowColor, shadowBlur, smoothness } = style;

  ctx.save();
  drawTrendPath(ctx, points, smoothness);
  ctx.lineTo(points.at(-1).x, plotBottom);
  ctx.lineTo(points[0].x, plotBottom);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();

  drawTrendPath(ctx, points, smoothness);
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.shadowColor = shadowColor;
  ctx.shadowBlur = shadowBlur;
  ctx.stroke();
  ctx.restore();
}

function drawEventTimeline(ctx, trendData, config, plotX, width, height, activeIndex) {
  // TODO：后续完善底部时间线拖拽交互。
  const rows = config.eventRows || [];
  const timelineTop = height - 96;
  const labelX = 28;
  const gridLeft = 108;
  const gridRight = width - 74;
  const rowHeight = 26;
  const activeX = plotX(activeIndex);
  const colors = {
    投放动作: "#ffb31a",
    调控动作: "#2dd28f",
  };

  ctx.save();
  ctx.font = "12px Microsoft YaHei, Arial, sans-serif";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(232, 240, 255, 0.86)";

  rows.forEach((row, rowIndex) => {
    const y = timelineTop + rowIndex * rowHeight;
    ctx.fillText(row, labelX, y);

    ctx.strokeStyle = "rgba(152, 170, 222, 0.26)";
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(gridLeft, y);
    ctx.lineTo(gridRight, y);
    ctx.stroke();

    trendData.forEach((point, pointIndex) => {
      if (point.eventType !== row) return;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(plotX(pointIndex), y, 4.6, 0, Math.PI * 2);
      ctx.fillStyle = colors[row] || "#7ea2ff";
      ctx.fill();
    });
  });

  ctx.setLineDash([]);
  ctx.fillStyle = "rgba(113, 129, 178, 0.64)";
  ctx.fillRect(gridLeft, height - 34, gridRight - gridLeft, 10);
  ctx.fillStyle = "rgba(89, 125, 230, 0.56)";
  ctx.fillRect(gridLeft, height - 36, gridRight - gridLeft, 3);
  ctx.fillStyle = "#7aa1ff";
  ctx.fillRect(gridLeft - 3, height - 38, 6, 18);
  ctx.fillRect(gridRight - 3, height - 38, 6, 18);
  ctx.fillStyle = "#c4d4ff";
  ctx.fillRect(activeX - 4, height - 42, 8, 24);
  ctx.strokeStyle = "rgba(222, 234, 255, 0.9)";
  ctx.strokeRect(activeX - 4, height - 42, 8, 24);

  ctx.fillStyle = "rgba(239, 245, 255, 0.94)";
  ctx.fillText(config.newControlLabel || "", gridRight + 10, timelineTop + rowHeight);
  ctx.restore();
}

function drawSelectedState(ctx, activePoint, activeX, width, plotTop, plotBottom) {
  ctx.save();
  ctx.strokeStyle = "rgba(143, 166, 230, 0.46)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(activeX, plotTop);
  ctx.lineTo(activeX, plotBottom + 102);
  ctx.stroke();

  const tooltipWidth = 170;
  const tooltipHeight = 78;
  const tooltipX = Math.min(width - tooltipWidth - 22, Math.max(TREND_PAD.left + 10, activeX + 14));
  const tooltipY = Math.max(plotTop + 8, plotTop + 22);

  ctx.fillStyle = "rgba(8, 13, 27, 0.9)";
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(tooltipX, tooltipY, tooltipWidth, tooltipHeight, 8);
  } else {
    ctx.rect(tooltipX, tooltipY, tooltipWidth, tooltipHeight);
  }
  ctx.fill();

  ctx.fillStyle = "#eaf2ff";
  ctx.font = "700 13px Microsoft YaHei, Arial, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText(activePoint.time || "-", tooltipX + 12, tooltipY + 20);

  ctx.font = "12px Microsoft YaHei, Arial, sans-serif";
  ctx.fillStyle = "#2f73ff";
  ctx.fillText("●", tooltipX + 12, tooltipY + 44);
  ctx.fillStyle = "#dbe7ff";
  ctx.fillText(`净成交金额 ${formatAxisNumber(activePoint.netGmv)}`, tooltipX + 28, tooltipY + 44);
  ctx.fillStyle = "#10d3e3";
  ctx.fillText("●", tooltipX + 12, tooltipY + 64);
  ctx.fillStyle = "#dbe7ff";
  ctx.fillText(`消耗 ${formatAxisNumber(activePoint.cost)}`, tooltipX + 28, tooltipY + 64);
  ctx.restore();
}

export function drawQianchuanTrendChart(canvas, data, options = {}) {
  if (!canvas) return;

  const { ctx, width, height } = getCanvasContext(canvas);
  const trendData = data.trendData || [];
  if (!trendData.length) return;

  const activeIndex = Math.max(0, Math.min(trendData.length - 1, Number(options.activeIndex) || 0));
  const pad = TREND_PAD;
  const plotWidth = Math.max(1, width - pad.left - pad.right);
  const plotHeight = Math.max(1, height - pad.top - pad.bottom);
  const plotBottom = pad.top + plotHeight;
  const netMax = niceCeil(Math.max(...trendData.map((item) => item.netGmv), ...trendData.map((item) => item.totalGmv)), 100);
  const costMax = niceCeil(Math.max(...trendData.map((item) => item.cost)), 3);
  const plotX = (index) => pad.left + (trendData.length <= 1 ? 0 : (index / (trendData.length - 1)) * plotWidth);
  const netY = (value) => plotBottom - (toNumber(value) / netMax) * plotHeight;
  const costY = (value) => plotBottom - (toNumber(value) / costMax) * plotHeight;

  ctx.save();
  ctx.fillStyle = "rgba(8, 17, 43, 0)";
  ctx.fillRect(0, 0, width, height);
  ctx.restore();

  ctx.save();
  ctx.font = "12px Microsoft YaHei, Arial, sans-serif";
  ctx.textBaseline = "middle";
  ctx.strokeStyle = "rgba(133, 153, 205, 0.16)";
  ctx.fillStyle = "rgba(211, 222, 250, 0.78)";

  for (let index = 0; index <= 4; index += 1) {
    const y = pad.top + (plotHeight / 4) * index;
    const leftValue = netMax - (netMax / 4) * index;
    const rightValue = costMax - (costMax / 4) * index;

    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();

    ctx.textAlign = "right";
    ctx.fillText(formatAxisNumber(leftValue), pad.left - 18, y);
    ctx.textAlign = "left";
    ctx.fillText(formatAxisNumber(rightValue), width - pad.right + 18, y);
  }

  ctx.textAlign = "left";
  ctx.fillStyle = "rgba(238, 244, 255, 0.9)";
  ctx.fillText(data.trendConfig.leftAxisLabel, pad.left - 70, pad.top - 28);
  ctx.textAlign = "right";
  ctx.fillText(data.trendConfig.rightAxisLabel, width - 16, pad.top - 28);
  ctx.restore();

  const labelIndexes = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 21, 24, 27, trendData.length - 1].filter(
    (index, arrayIndex, array) => index >= 0 && index < trendData.length && array.indexOf(index) === arrayIndex,
  );

  ctx.save();
  ctx.font = "12px Microsoft YaHei, Arial, sans-serif";
  ctx.fillStyle = "rgba(219, 228, 250, 0.86)";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  labelIndexes.forEach((index) => {
    ctx.fillText(trendData[index].time, plotX(index), plotBottom + 14);
  });
  ctx.restore();

  const netPoints = trendData.map((item, index) => ({ x: plotX(index), y: netY(item.netGmv) }));
  const costPoints = trendData.map((item, index) => ({ x: plotX(index), y: costY(item.cost) }));
  drawSeries(
    ctx,
    costPoints,
    {
      color: "#16d5e4",
      fillColor: "rgba(16, 211, 227, 0.035)",
      lineWidth: 1.8,
      shadowColor: "rgba(16, 211, 227, 0.16)",
      shadowBlur: 3,
      smoothness: 0.2,
    },
    plotBottom,
  );
  drawSeries(
    ctx,
    netPoints,
    {
      color: "#3478ff",
      fillColor: "rgba(47, 115, 255, 0.055)",
      lineWidth: 2.35,
      shadowColor: "rgba(47, 115, 255, 0.24)",
      shadowBlur: 5,
      smoothness: 0.12,
    },
    plotBottom,
  );

  drawSelectedState(ctx, trendData[activeIndex], plotX(activeIndex), width, pad.top, plotBottom);
  drawEventTimeline(ctx, trendData, data.trendConfig, plotX, width, height, activeIndex);
}

export function drawChannelDonut(canvas, channels, centerLabel) {
  if (!canvas) return;

  const { ctx, width, height } = getCanvasContext(canvas);
  const total = channels.reduce((sum, item) => sum + toNumber(item.percent), 0) || 1;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.42;
  const innerRadius = radius * 0.56;
  let start = -Math.PI / 2;

  channels.forEach((item) => {
    const angle = (toNumber(item.percent) / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = item.color || "#7ea2ff";
    ctx.fill();
    start += angle;
  });

  ctx.beginPath();
  ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
  ctx.fillStyle = "#142040";
  ctx.fill();

  ctx.save();
  ctx.fillStyle = "#dbe7ff";
  ctx.font = "700 12px Microsoft YaHei, Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(centerLabel || "", centerX, centerY);
  ctx.restore();
}
