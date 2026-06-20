import { formatNumber, formatPercent } from "./formulas.js";
import { drawChannelDonut, drawQianchuanTrendChart } from "./qianchuanChart.js";
import { qianchuanData } from "./qianchuanData.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function ensureQianchuanStylesheet() {
  const existing = document.getElementById("qianchuanStylesheet");
  if (existing) {
    return existing.sheet
      ? Promise.resolve()
      : new Promise((resolve) => {
          existing.addEventListener("load", resolve, { once: true });
          existing.addEventListener("error", resolve, { once: true });
          window.setTimeout(resolve, 200);
        });
  }

  const link = document.createElement("link");
  link.id = "qianchuanStylesheet";
  link.rel = "stylesheet";
  link.href = "qianchuan.css";
  document.head.appendChild(link);

  return new Promise((resolve) => {
    link.addEventListener("load", resolve, { once: true });
    link.addEventListener("error", resolve, { once: true });
    window.setTimeout(resolve, 200);
  });
}

function metricValue(metrics, card) {
  const value = metrics[card.key];
  if (card.format === "percent") return formatPercent(value);
  if (card.format === "integer") return formatNumber(value, 0);
  return formatNumber(value, card.decimals ?? 2);
}

function renderBrand(brand) {
  const markClass = brand.type === "qianchuan" ? "qc-brand-mark-qianchuan" : "qc-brand-mark-douyin";
  return `
    <span class="qc-brand-item">
      <span class="qc-brand-mark ${markClass}" aria-hidden="true"></span>
      <strong>${escapeHtml(brand.name)}</strong>
    </span>
  `;
}

function renderTopMetric(card, metrics, className) {
  return `
    <article class="qc-metric ${className}">
      <span>${escapeHtml(card.label)}</span>
      <strong>${escapeHtml(metricValue(metrics, card))}</strong>
    </article>
  `;
}

function renderTopMetrics(data) {
  const primary = data.topMetricCards.primary.map((card) => renderTopMetric(card, data.topMetrics, "qc-metric-primary")).join("");
  const secondary = data.topMetricCards.secondary.map((card) => renderTopMetric(card, data.topMetrics, "qc-metric-secondary")).join("");

  return `
    <section class="qc-metrics-card" aria-label="顶部核心指标">
      <div class="qc-metrics-actions">
        <button class="qc-select-btn" type="button">${escapeHtml(data.basicInfo.dataScope)}</button>
        <button class="qc-icon-btn" type="button" aria-label="指标设置">☷</button>
        <button class="qc-icon-btn" type="button" aria-label="展开指标">⛶</button>
      </div>
      <div class="qc-primary-metrics">${primary}</div>
      <div class="qc-secondary-metrics">${secondary}</div>
    </section>
  `;
}

function renderTrendPanel(data) {
  const tabs = data.trendConfig.tabs
    .map((tab) => `<button class="qc-tab ${tab === data.trendConfig.activeTab ? "active" : ""}" type="button">${escapeHtml(tab)}</button>`)
    .join("");
  const toggles = data.trendConfig.metricToggles
    .map(
      (toggle) => `
        <button class="qc-legend ${toggle.active ? "active" : ""}" type="button">
          <span style="--legend-color:${escapeHtml(toggle.color)}"></span>
          ${escapeHtml(toggle.label)}
        </button>
      `,
    )
    .join("");

  return `
    <section class="qc-trend-card" aria-label="左侧主趋势图">
      <div class="qc-trend-header">
        <div class="qc-tabs">${tabs}</div>
        <button class="qc-icon-btn qc-expand-btn" type="button" aria-label="展开趋势图">⛶</button>
      </div>
      <div class="qc-trend-tools">
        <div class="qc-legends">${toggles}</div>
        <div class="qc-tool-actions">
          <button class="qc-granularity" type="button">${escapeHtml(data.trendConfig.granularityLabel)}</button>
          <button class="qc-filter-btn" type="button" aria-label="${escapeHtml(data.trendConfig.filterLabel)}">⌯</button>
        </div>
      </div>
      <canvas id="qianchuanTrendCanvas" class="qc-trend-canvas" aria-label="全域直播趋势图"></canvas>
    </section>
  `;
}

function renderChannelCard(data) {
  const channels = data.channelComposition
    .map(
      (item) => `
        <li>
          <span class="qc-channel-dot" style="--channel-color:${escapeHtml(item.color)}"></span>
          <span>${escapeHtml(item.channelName)}</span>
          <strong>${escapeHtml(formatPercent(item.percent))}</strong>
        </li>
      `,
    )
    .join("");

  return `
    <section class="qc-side-card qc-channel-card" aria-label="成交渠道构成">
      <div class="qc-card-title">
        <h2>${escapeHtml(data.sections.channel.title)}</h2>
        <button type="button">${escapeHtml(data.sections.channel.actionLabel)}</button>
      </div>
      <div class="qc-channel-layout">
        <canvas id="qianchuanChannelCanvas" class="qc-channel-canvas" aria-label="成交渠道环形图"></canvas>
        <ul class="qc-channel-list">${channels}</ul>
      </div>
    </section>
  `;
}

function renderFunnelCard(data) {
  const maxValue = Math.max(...data.funnelData.map((item) => Number(item.value) || 0), 1);
  const rows = data.funnelData
    .map((item) => {
      const scale = Math.max(0.08, (Number(item.value) || 0) / maxValue);
      return `
        <li class="qc-funnel-row" style="--funnel-scale:${scale}">
          <div class="qc-funnel-bar">
            <span>${escapeHtml(item.name)}</span>
            <strong>${escapeHtml(formatNumber(item.value, 0))}</strong>
          </div>
          <em>${escapeHtml(formatPercent(item.conversionRate))}</em>
        </li>
      `;
    })
    .join("");

  return `
    <section class="qc-side-card qc-funnel-card" aria-label="直播间核心漏斗">
      <div class="qc-card-title">
        <h2>${escapeHtml(data.sections.funnel.title)}</h2>
      </div>
      <ul class="qc-funnel-list">${rows}</ul>
    </section>
  `;
}

function renderCommentsCard(data) {
  const comments = data.comments
    .map(
      (comment) => `
        <li>
          <div>
            <strong>${escapeHtml(comment.user)}</strong>
            <time>${escapeHtml(comment.time)}</time>
            <span>${escapeHtml(comment.tag)}</span>
          </div>
          <p>${escapeHtml(comment.content)}</p>
        </li>
      `,
    )
    .join("");

  return `
    <section class="qc-side-card qc-comments-card" aria-label="直播实时评论">
      <div class="qc-card-title">
        <h2>${escapeHtml(data.sections.comments.title)}</h2>
        <button type="button">${escapeHtml(data.sections.comments.actionLabel)}</button>
      </div>
      <ul class="qc-comment-list">${comments}</ul>
    </section>
  `;
}

function renderTemplate(data) {
  const brands = data.basicInfo.brands.map(renderBrand).join('<span class="qc-brand-divider"></span>');
  const announcementActions = data.basicInfo.announcement.actions
    .map((action) => `<button type="button">${escapeHtml(action)}</button>`)
    .join("");

  return `
    <div class="qianchuan-shell">
      <header class="qc-topbar">
        <div class="qc-brand">${brands}</div>
        <div class="qc-live-info">
          <span class="qc-avatar" aria-hidden="true"></span>
          <strong>${escapeHtml(data.basicInfo.shopName)}</strong>
          <em>${escapeHtml(data.basicInfo.liveStatus)} | ${escapeHtml(data.basicInfo.liveDuration)}</em>
          <span class="qc-separator"></span>
          <span>开播时间：${escapeHtml(data.basicInfo.startTime)}</span>
          <span class="qc-separator"></span>
          <button type="button">${escapeHtml(data.basicInfo.dataStatus)}</button>
          <button class="qc-top-action" type="button">⟳ ${escapeHtml(data.basicInfo.refreshLabel)}</button>
          <button class="qc-top-action" type="button">⛶ ${escapeHtml(data.basicInfo.fullscreenLabel)}</button>
        </div>
      </header>

      <div class="qc-announcement">
        <span>${escapeHtml(data.basicInfo.announcement.badge)}</span>
        <p>${escapeHtml(data.basicInfo.announcement.text)}</p>
        ${announcementActions}
        <i>${escapeHtml(data.basicInfo.announcement.pageText)}</i>
        <button class="qc-announcement-close" type="button" aria-label="关闭公告">×</button>
      </div>

      <main class="qc-board">
        <div class="qc-main-column">
          ${renderTopMetrics(data)}
          ${renderTrendPanel(data)}
        </div>
        <aside class="qc-side-column">
          ${renderChannelCard(data)}
          ${renderFunnelCard(data)}
          ${renderCommentsCard(data)}
        </aside>
      </main>
    </div>
  `;
}

function drawCharts(data) {
  drawQianchuanTrendChart(document.getElementById("qianchuanTrendCanvas"), data);
  drawChannelDonut(document.getElementById("qianchuanChannelCanvas"), data.channelComposition, data.sections.channel.centerLabel);
}

export function renderQianchuanDashboard(root) {
  const stylesheetReady = ensureQianchuanStylesheet();
  document.body.className = "qianchuan-page";
  document.title = "巨量千川直播大屏";
  root.innerHTML = renderTemplate(qianchuanData);

  stylesheetReady.then(() => requestAnimationFrame(() => drawCharts(qianchuanData)));
  window.addEventListener("resize", () => drawCharts(qianchuanData), { passive: true });
}
