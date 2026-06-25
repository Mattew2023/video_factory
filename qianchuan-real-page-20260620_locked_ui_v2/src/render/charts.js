function getChartPoints(trendData, key, maxValue, chart) {
  const count = Math.max(trendData.length - 1, 1);

  return trendData
    .map((point, index) => {
      const x = chart.x + (index / count) * chart.width;
      const value = Number(point[key] || 0);
      const y = chart.y + chart.height - (Math.min(value, maxValue) / maxValue) * chart.height;

      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function getEventDots(trendData, type, chart, rowY) {
  const count = Math.max(trendData.length - 1, 1);

  return trendData
    .flatMap((point, index) => {
      const hasEvent = point.events.some((event) => event.type === type);

      if (!hasEvent) {
        return [];
      }

      const x = chart.x + (index / count) * chart.width;
      return [`<circle cx="${x.toFixed(1)}" cy="${rowY}" r="7" />`];
    })
    .join("");
}

function renderGrid(chart) {
  const ticks = [0, 200, 400, 600, 800];
  const rightTicks = ["0", "8.5", "17", "25.5", "34"];

  return ticks
    .map((tick, index) => {
      const y = chart.y + chart.height - (index / (ticks.length - 1)) * chart.height;
      return `
        <line class="chart-grid-line" x1="${chart.x}" y1="${y}" x2="${chart.x + chart.width}" y2="${y}" />
        <text class="chart-axis-text" x="${chart.x - 54}" y="${y + 6}">${tick}</text>
        <text class="chart-axis-text chart-axis-text-right" x="${chart.x + chart.width + 42}" y="${y + 6}">${rightTicks[index]}</text>
      `;
    })
    .join("");
}

function renderTimeLabels(trendData, chart) {
  const labelIndexes = [0, 2, 4, 6, 8, 10, 12, 14];
  const count = Math.max(trendData.length - 1, 1);

  return labelIndexes
    .filter((index) => trendData[index])
    .map((index) => {
      const x = chart.x + (index / count) * chart.width;
      return `<text class="chart-time-text" x="${x}" y="${chart.y + chart.height + 34}">${trendData[index].time}</text>`;
    })
    .join("");
}

export function renderStaticTrendChart(container, trendData) {
  if (!container) {
    return;
  }

  const chart = { x: 88, y: 52, width: 1648, height: 404 };
  const netPoints = getChartPoints(trendData, "netTransactionAmount", 800, chart);
  const costPoints = getChartPoints(trendData, "cost", 34, chart);
  const actionRowY = chart.y + chart.height + 104;
  const controlRowY = chart.y + chart.height + 146;

  container.innerHTML = `
    <svg class="trend-svg" viewBox="0 0 1840 670" role="img" aria-label="trend chart">
      <text class="chart-label chart-label-left" x="0" y="24">净成交金额(元)</text>
      <text class="chart-label chart-label-right" x="1778" y="24">消耗(元)</text>
      ${renderGrid(chart)}
      <polyline class="trend-line trend-line-net" points="${netPoints}" />
      <polyline class="trend-line trend-line-cost" points="${costPoints}" />
      ${renderTimeLabels(trendData, chart)}
      <rect class="range-track" x="${chart.x}" y="${chart.y + chart.height + 58}" width="${chart.width}" height="22" rx="0" />
      <rect class="range-handle" x="${chart.x + chart.width * 0.42}" y="${chart.y + chart.height + 52}" width="8" height="34" rx="3" />
      <rect class="range-handle" x="${chart.x + chart.width - 8}" y="${chart.y + chart.height + 52}" width="8" height="34" rx="3" />
      <text class="event-label" x="0" y="${actionRowY + 5}">投放动作</text>
      <text class="event-label" x="0" y="${controlRowY + 5}">调控动作</text>
      <g class="action-dots">${getEventDots(trendData, "投放动作", chart, actionRowY)}</g>
      <g class="control-dots">${getEventDots(trendData, "调控动作", chart, controlRowY)}</g>
    </svg>
  `;
}
