import { formatInteger, formatPercent, splitMetricValue } from "../data/formulas.js";
import { normalizeTrendData } from "../data/trendGenerator.js";
import { renderStaticTrendChart } from "./charts.js";

const ASSETS = {
  douyinLogo: "assets/images/474628ec198f2c3ca1de2adb682aee9d.png~tplv-55ejei7tpt-webp.webp",
  qianchuanLogo: "assets/images/a940c0ca29b1a56488b43b916096598d.png~tplv-55ejei7tpt-webp.webp"
};

const topMetricDefs = [
  { label: "整体消耗(元)", key: "totalCost", decimals: 2 },
  { label: "净成交ROI", key: "netTransactionRoi", decimals: 2 },
  { label: "净成交金额(元)", key: "netTransactionAmount", decimals: 2 },
  { label: "GPM(元)", key: "gpm", decimals: 2 },
  { label: "观看成交转化率", key: "viewToTransactionRate", decimals: 2, suffix: "%" },
  { label: "实时在线人数", key: "onlineViewerCount", decimals: 0 },
  { label: "曝光观看率(次数)", key: "exposureToViewRate", decimals: 2, suffix: "%" },
  { label: "直播间整体观看人数", key: "liveRoomViewerCount", decimals: 0 }
];

const trendMetricLabels = [
  { label: "综合成本", active: false, colorClass: "" },
  { label: "净成交金额", active: true, colorClass: "trend-metric-net" },
  { label: "综合ROI", active: false, colorClass: "" },
  { label: "消耗", active: true, colorClass: "trend-metric-cost" },
  { label: "整体成交金额", active: false, colorClass: "" },
  { label: "整体支付ROI", active: false, colorClass: "" }
];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMetricValue(value, options = {}) {
  const parts = splitMetricValue(value, options);

  return `
    <span class="metric-number-main">${escapeHtml(parts.integerPart)}</span>
    ${parts.decimalPart ? `<span class="metric-number-decimal">${escapeHtml(parts.decimalPart)}</span>` : ""}
    ${parts.suffix ? `<span class="metric-number-suffix">${escapeHtml(parts.suffix)}</span>` : ""}
  `;
}

function renderTopMetrics(topMetrics = {}) {
  return topMetricDefs
    .map((metric, index) => {
      const value = topMetrics[metric.key];
      const className = index < 3 ? "metric-item metric-item-primary" : "metric-item";

      return `
        <article class="${className}">
          <div class="metric-name">${metric.label}</div>
          <div class="metric-number">${renderMetricValue(value, metric)}</div>
        </article>
      `;
    })
    .join("");
}

function renderTrendMetrics() {
  return trendMetricLabels
    .map((metric) => `
      <span class="trend-metric ${metric.active ? "trend-metric-active" : ""} ${metric.colorClass}">
        <i></i>${metric.label}
      </span>
    `)
    .join("");
}

function buildDoughnutSegments(items = []) {
  let cursor = 0;
  const fallbackColors = ["#dbe5ff", "#aec1f7", "#89a3f2", "#5f83ed", "#3865e9"];

  const segments = items.map((item, index) => {
    const percent = Math.max(Number(item.percent || 0), 0);
    const start = cursor;
    const end = Math.min(cursor + percent, 100);
    cursor = end;
    const color = item.color || fallbackColors[index % fallbackColors.length];

    return `${color} ${start}% ${end}%`;
  });

  if (cursor < 100) {
    segments.push(`rgba(255, 255, 255, 0.08) ${cursor}% 100%`);
  }

  return segments.join(", ");
}

function renderChannelCard(channelComposition = {}) {
  const items = channelComposition.items || [];

  return `
    <section class="side-card channel-card">
      <div class="side-card-header">
        <h2>成交渠道构成</h2>
        <button class="pill-button" type="button">↔ ${escapeHtml(channelComposition.activeMetric || "观看次数")}</button>
      </div>
      <div class="channel-body">
        <div class="doughnut" style="--doughnut-segments: ${buildDoughnutSegments(items)};">
          <span>成交金额</span>
        </div>
        <ul class="channel-legend">
          ${items
            .map((item) => `
              <li>
                <i style="background:${escapeHtml(item.color || "#dbe5ff")}"></i>
                <span>${escapeHtml(item.name)}</span>
                <strong>${formatPercent(item.percent)}</strong>
              </li>
            `)
            .join("")}
        </ul>
      </div>
    </section>
  `;
}

function renderFunnelCard(funnel = {}) {
  const items = funnel.items || [];

  return `
    <section class="side-card funnel-card">
      <div class="side-card-header">
        <h2>直播间核心漏斗</h2>
      </div>
      <div class="funnel-body">
        <div class="funnel-bars">
          ${items
            .map((item, index) => `
              <div class="funnel-row">
                <div class="funnel-bar funnel-bar-${index + 1}" style="width:${Number(item.width || 70)}%">
                  <span>${escapeHtml(item.label)}</span>
                  <strong>${formatInteger(item.value)}</strong>
                </div>
              </div>
            `)
            .join("")}
        </div>
        <div class="funnel-ratios">
          ${items
            .slice(0, 4)
            .map((item, index) => `<span class="funnel-ratio funnel-ratio-${index + 1}">${escapeHtml(item.ratio || "")}</span>`)
            .join("")}
        </div>
      </div>
    </section>
  `;
}

function renderLiveCard(rightCards = {}, comments = {}) {
  const isCommentMode = comments.state === "empty";
  const title = isCommentMode ? "直播实时评论" : "直播间画面";
  const buttonText = isCommentMode ? "直播画面" : "直播评论";
  const emptyText = isCommentMode ? "暂无评论" : "主播暂不在播";

  return `
    <section class="side-card live-card">
      <div class="side-card-header">
        <h2>${title}</h2>
        <button class="pill-button" type="button">↔ ${buttonText}</button>
      </div>
      <div class="live-preview ${rightCards.livePanel?.coverAsset ? "live-preview-with-image" : ""}"
        ${rightCards.livePanel?.coverAsset ? `style="background-image:url('${escapeHtml(rightCards.livePanel.coverAsset)}')"` : ""}>
        <div class="live-preview-mask">${emptyText}</div>
      </div>
    </section>
  `;
}

export function renderDashboardSkeleton(root, data) {
  if (!root) {
    return;
  }

  const trendData = normalizeTrendData(data.trendData);
  const anchor = data.anchor || {};
  const topMetrics = data.topMetrics || {};
  const notice = data.notice || {};
  const rightCards = data.rightCards || {};

  root.innerHTML = `
    <section class="dashboard-shell" aria-label="locked dashboard">
      <header class="top-bar">
        <div class="brand-cluster">
          <img class="douyin-logo" src="${ASSETS.douyinLogo}" alt="抖音电商" />
          <span class="brand-divider"></span>
          <img class="qianchuan-logo" src="${ASSETS.qianchuanLogo}" alt="巨量千川" />
        </div>
        <div class="live-meta">
          <img class="anchor-avatar" src="${escapeHtml(anchor.avatarAsset)}" alt="" />
          <span class="anchor-name">${escapeHtml(anchor.name)}</span>
          <span class="status-pill">${escapeHtml(data.liveStatus)}</span>
          <span class="duration">${escapeHtml(data.duration)}</span>
          <span class="meta-divider"></span>
          <span class="start-time">开播时间：${escapeHtml(data.startTime)}</span>
          <span class="meta-divider"></span>
          <button class="link-button" type="button">数据口径说明</button>
          <button class="toolbar-button refresh-button" type="button">↻ 刷新数据</button>
          <button class="toolbar-button fullscreen-button" type="button">□ 全屏</button>
        </div>
      </header>

      <div class="notice-bar ${notice.visible === false ? "is-hidden" : ""}">
        <span class="notice-tag">公告</span>
        <span class="notice-text">全域直播大屏全面升级改版，快来体验吧！点击查看详情获取使用手册</span>
        <button type="button">查看详情</button>
        <button type="button">我知道了</button>
        <span class="notice-count">${formatInteger(notice.currentIndex || 1)} / ${formatInteger(notice.total || 2)}</span>
        <span class="notice-close">×</span>
      </div>

      <div class="dashboard-grid">
        <main class="main-column">
          <section class="metrics-card">
            <div class="metrics-actions">
              <button type="button">全域净成交数据⌄</button>
              <button class="circle-button" type="button">☷</button>
              <button class="circle-button" type="button">□</button>
            </div>
            <div class="metrics-grid">
              ${renderTopMetrics(topMetrics)}
            </div>
          </section>

          <section class="trend-card">
            <div class="trend-top">
              <div class="trend-tabs">
                <button class="trend-tab trend-tab-active" type="button">整体趋势</button>
                <button class="trend-tab" type="button">素材表现</button>
              </div>
              <button class="circle-button" type="button">□</button>
            </div>
            <div class="trend-controls">
              <div class="trend-metrics">
                <span class="trend-arrow">‹</span>
                ${renderTrendMetrics()}
                <span class="trend-arrow">›</span>
              </div>
              <div class="trend-selectors">
                <button type="button">${escapeHtml(data.trendSettings?.granularity || "5分钟粒度")}⌄</button>
                <button class="circle-button" type="button">▽</button>
              </div>
            </div>
            <div class="trend-chart" id="trend-chart"></div>
            <button class="new-control-button" type="button">＋ 新建调控</button>
          </section>
        </main>

        <aside class="side-column">
          ${renderChannelCard(rightCards.channelComposition)}
          ${renderFunnelCard(rightCards.funnel)}
          ${renderLiveCard(rightCards, data.comments || {})}
        </aside>
      </div>
    </section>
  `;

  renderStaticTrendChart(root.querySelector("#trend-chart"), trendData);
}
