import { getMetricCards } from "./formulas.js";
import { getLiveData } from "./storage.js";

const DEFAULT_LIVE_IMAGE = `data:image/svg+xml,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="360" height="640" viewBox="0 0 360 640">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#18234f"/>
      <stop offset=".55" stop-color="#2f68ff"/>
      <stop offset="1" stop-color="#f05a8a"/>
    </linearGradient>
  </defs>
  <rect width="360" height="640" fill="url(#bg)"/>
  <circle cx="280" cy="108" r="48" fill="rgba(255,255,255,.18)"/>
  <rect x="42" y="396" width="220" height="22" rx="11" fill="rgba(255,255,255,.76)"/>
  <rect x="42" y="436" width="148" height="18" rx="9" fill="rgba(255,255,255,.46)"/>
  <text x="42" y="120" fill="#fff" font-size="40" font-family="Arial, sans-serif" font-weight="700">LIVE</text>
  <text x="42" y="166" fill="rgba(255,255,255,.78)" font-size="22" font-family="Arial, sans-serif">Dashboard Preview</text>
</svg>
`)}`;

const state = {
  data: null,
  chartIndex: 0,
  serializedData: "",
  refreshTimer: null,
  lastChartDebugKey: "",
};

const themeClassMap = {
  "默认蓝紫": "theme-default",
  "暗黑科技": "theme-tech",
  "蓝黑商务": "theme-business",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getThemeClass(data) {
  return themeClassMap[data.styleConfig?.themeName] || "theme-default";
}

function setBodyMode(mode, data) {
  document.body.className = `${mode} ${getThemeClass(data)}`;
}

function dashboardTemplate(data) {
  const showVersion = data.styleConfig.showVersionTag;
  const showLivePreview = data.styleConfig.showLivePreview;
  const showComments = data.styleConfig.showComments;
  const showEventTimeline = data.styleConfig.showEventTimeline;

  return `
    <div class="app-shell dashboard-shell" style="--screen-scale:${data.styleConfig.screenScale / 100};--scaled-width:${100 / (data.styleConfig.screenScale / 100)}vw;--scaled-height:${100 / (data.styleConfig.screenScale / 100)}vh">
      <header class="topbar">
        <div class="brand">
          <span class="douyin-mark" aria-hidden="true"></span>
          <span class="brand-name" data-dashboard="platformName"></span>
          <span class="brand-pill">经营</span>
        </div>
        <div class="title-group">
          <h1 data-dashboard="screenTitle"></h1>
          <button class="version-btn" data-dashboard="versionName" type="button" ${showVersion ? "" : "hidden"}></button>
        </div>
        <div class="notice">
          <span class="notice-dot">i</span>
          <span>直播复盘录屏、评论数据仅保留14天，本地演示数据可在配置页修改</span>
          <button class="icon-btn" type="button" aria-label="关闭提示">×</button>
        </div>
        <a class="ghost-btn more-action route-link" href="/admin">配置数据</a>
        <div class="network">
          <span></span>
          本地数据
        </div>
        <div class="store">
          <div class="store-avatar"></div>
          <div>
            <strong data-dashboard="roomName"></strong>
            <p><span>开播时间&nbsp;</span><span data-dashboard="startTime"></span><span>开播，共</span><span data-dashboard="duration"></span></p>
          </div>
        </div>
        <button class="icon-btn wide" type="button" aria-label="切换">⇄</button>
        <a class="ghost-btn return-btn route-link" href="/dashboard">大屏</a>
        <button class="icon-btn" type="button" aria-label="投屏">▱</button>
        <button class="icon-btn" type="button" aria-label="提醒">●</button>
        <button class="icon-btn" type="button" aria-label="全屏">⛶</button>
      </header>

      <div class="screen ${showLivePreview ? "" : "no-live"}">
        <aside class="sidebar" aria-label="侧边导航">
          <button class="side-item active" type="button">
            <span class="side-icon line-chart" aria-hidden="true"></span>
            <span>数据</span>
          </button>
          <button class="side-item" type="button">
            <span class="side-icon bag" aria-hidden="true"></span>
            <span>商品</span>
          </button>
          <button class="side-item" type="button">
            <span class="side-icon people" aria-hidden="true"></span>
            <span>人群</span>
          </button>
          <button class="side-item" type="button">
            <span class="side-icon cube" aria-hidden="true"></span>
            <span>千川</span>
          </button>
        </aside>

        <main class="dashboard">
          <section class="summary-card" id="summaryCard" aria-label="直播数据概览">
            <div class="summary-texture"></div>
          </section>

          <section class="analysis-panel ${showEventTimeline ? "" : "no-events"}">
            <div class="tab-row">
              <button class="tab active" type="button">综合趋势</button>
              <button class="tab" type="button">流量分析</button>
              <button class="tab" type="button">主播分析</button>
              <button class="tab" type="button">流量诊断<span class="new-dot"></span></button>
              <button class="tab" type="button">引流短视频</button>
              <button class="tab" type="button">违规情况</button>
              <button class="marker-btn" type="button">添加场记</button>
            </div>

            <div class="chip-row">
              <button class="chip active" type="button"><span></span>成交金额</button>
              <button class="chip cyan" type="button"><span></span>投放消耗</button>
              <button class="chip" type="button"><span></span>在线人数</button>
              <button class="chip" type="button"><span></span>事件</button>
              <button class="round-switch" type="button" aria-label="向左">‹</button>
              <button class="round-switch" type="button" aria-label="向右">›</button>
              <button class="config-btn" type="button">▦ 指标配置</button>
            </div>

            <div class="chart-wrap">
              <div class="axis-label axis-left">成交金额</div>
              <div class="axis-label axis-right">投放消耗</div>
              <canvas id="trendChart" aria-label="直播趋势折线图"></canvas>
              <div class="chart-tooltip" id="chartTooltip">
                <strong id="tipTime"></strong>
                <p>数据</p>
                <div><span class="dot blue"></span>成交金额 <b id="tipAmount"></b></div>
                <div><span class="dot cyan"></span>投放消耗 <b id="tipSpend"></b></div>
                <section class="tooltip-event" id="tipEventBlock">
                  <p>事件</p>
                  <div><span class="dot gold"></span><span id="tipEvent"></span><b id="tipEventDetail"></b></div>
                </section>
              </div>
            </div>

            <div class="event-timeline" id="eventTimeline">
              <div class="event-labels" id="eventLabels"></div>
              <div class="event-grid" id="eventGrid" aria-hidden="true"></div>
            </div>
            <div class="range-bar">
              <span class="handle left"></span>
              <span class="range-fill"></span>
              <span class="handle right"></span>
            </div>
          </section>
        </main>

        <aside class="live-panel" id="livePanel" ${showLivePreview ? "" : "hidden"}>
          <div class="video-card">
            <img id="livePreviewImage" alt="直播商品预览" />
            <div class="video-shade"></div>
            <div class="selected-time"><span></span>已选&nbsp;&nbsp;<b data-dashboard="selectedTime"></b></div>
            <button class="play-btn" type="button" aria-label="播放">▶</button>
            <button class="float-chat" type="button" aria-label="评论助手"></button>
          </div>
          <div class="comment-tabs" id="commentTabs" ${showComments ? "" : "hidden"}>
            <button class="active" type="button">全部评论</button>
            <button type="button">关键评论</button>
          </div>
          <div class="empty-comments" id="commentEmpty" ${showComments ? "" : "hidden"}>
            <div class="assistant-avatar"></div>
            <p>评论生成中，配置保存后可同步查看</p>
          </div>
        </aside>
      </div>
      <button class="feedback" type="button">▱<span>问题反馈</span></button>
    </div>
  `;
}

function updateText(selector, value) {
  document.querySelectorAll(`[data-dashboard="${selector}"]`).forEach((element) => {
    element.textContent = value;
  });
}

function renderMetricCards(data) {
  const summary = document.getElementById("summaryCard");
  if (!summary) return;

  const texture = summary.querySelector(".summary-texture");
  summary.innerHTML = "";
  if (texture) summary.appendChild(texture);

  getMetricCards(data).forEach((card, index) => {
    const article = document.createElement("article");
    article.className = `metric metric-${card.group}${index === 0 ? " hero-metric" : ""}`;
    article.innerHTML = `<span>${escapeHtml(card.label)}</span><strong>${escapeHtml(card.value)}</strong>`;
    summary.appendChild(article);
  });
}

function renderEventTimeline(data) {
  const labels = document.getElementById("eventLabels");
  const grid = document.getElementById("eventGrid");
  if (!labels || !grid) return;

  const eventTypes = data.eventTypes?.length ? data.eventTypes : [];
  labels.innerHTML = eventTypes.map((type) => `<span>${escapeHtml(type)}</span>`).join("");
  grid.innerHTML = "";
  grid.style.gridTemplateRows = `repeat(${Math.max(1, eventTypes.length)}, 1fr)`;

  const trendData = data.trendData || [];
  eventTypes.forEach((type, rowIndex) => {
    const row = document.createElement("div");
    row.className = "event-row";
    trendData.forEach((item, index) => {
      if (item.eventType !== type) return;
      const dot = document.createElement("span");
      dot.className = rowIndex % 2 === 0 ? "event-dot blue" : "event-dot gold";
      dot.style.left = `${trendData.length > 1 ? (index / (trendData.length - 1)) * 100 : 0}%`;
      row.appendChild(dot);
    });
    grid.appendChild(row);
  });

  const cursor = document.createElement("div");
  cursor.className = "event-cursor";
  cursor.style.left = `${trendData.length > 1 ? (state.chartIndex / (trendData.length - 1)) * 100 : 0}%`;
  grid.appendChild(cursor);
}

function formatChartNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  return number.toLocaleString("zh-CN", {
    minimumFractionDigits: number % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function niceCeil(value, step) {
  return Math.max(step, Math.ceil(Number(value || 0) / step) * step);
}

function drawLine(ctx, points, color, glowColor, width) {
  if (points.length === 0) return;
  ctx.save();
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.lineWidth = width + 1.8;
  ctx.strokeStyle = glowColor;
  ctx.globalAlpha = 0.18;
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.lineWidth = width;
  ctx.strokeStyle = color;
  ctx.stroke();
  ctx.restore();
}

function drawCanvasEventTimeline(ctx, data, trendData, plotX, cursorX, rect, eventAreaTop) {
  const eventTypes = data.eventTypes?.length ? data.eventTypes : [];
  const rowHeight = 18;
  const labelX = 18;
  const gridLeft = 54;
  const gridRight = rect.width - 42;
  const rowsTop = eventAreaTop + 24;

  ctx.save();
  ctx.font = "13px Microsoft YaHei, Arial";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(177, 188, 214, 0.78)";
  eventTypes.forEach((type, rowIndex) => {
    const y = rowsTop + rowIndex * rowHeight;
    ctx.fillText(type, labelX, y);

    ctx.strokeStyle = "rgba(127, 142, 180, 0.16)";
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(gridLeft, y);
    ctx.lineTo(gridRight, y);
    ctx.stroke();
  });

  ctx.setLineDash([]);
  ctx.strokeStyle = "rgba(116, 133, 178, 0.22)";
  ctx.beginPath();
  ctx.moveTo(gridLeft, rowsTop - rowHeight / 2);
  ctx.lineTo(gridLeft, rowsTop + Math.max(1, eventTypes.length) * rowHeight - rowHeight / 2);
  ctx.stroke();

  trendData.forEach((item, index) => {
    const rowIndex = eventTypes.indexOf(item.eventType);
    if (rowIndex < 0) return;
    const x = plotX(index);
    const y = rowsTop + rowIndex * rowHeight;
    ctx.beginPath();
    ctx.arc(x, y, 3.2, 0, Math.PI * 2);
    ctx.fillStyle = rowIndex % 2 === 0 ? "#20b8ff" : "#f2aa2e";
    ctx.fill();
  });

  ctx.strokeStyle = "rgba(108, 126, 174, 0.34)";
  ctx.beginPath();
  ctx.moveTo(cursorX, eventAreaTop - 2);
  ctx.lineTo(cursorX, rect.height - 44);
  ctx.stroke();

  const rangeY = rect.height - 28;
  ctx.fillStyle = "rgba(124, 143, 193, 0.56)";
  ctx.fillRect(gridLeft, rangeY, gridRight - gridLeft, 10);
  ctx.fillStyle = "rgba(173, 190, 234, 0.78)";
  ctx.fillRect(gridLeft, rangeY - 1, 6, 18);
  ctx.fillRect(gridRight - 6, rangeY - 1, 6, 18);
  ctx.restore();
}

function renderChart(data, requestedIndex = state.chartIndex) {
  const canvas = document.getElementById("trendChart");
  const tooltip = document.getElementById("chartTooltip");
  if (!canvas || !tooltip) return;

  const trendData = data.trendData || [];
  const parent = canvas.parentElement;
  const rect = parent.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * dpr));
  canvas.height = Math.max(1, Math.round(rect.height * dpr));
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);

  if (trendData.length === 0) {
    ctx.fillStyle = "#a8b6d8";
    ctx.font = "16px Microsoft YaHei, Arial";
    ctx.textAlign = "center";
    ctx.fillText("暂无趋势数据", rect.width / 2, rect.height / 2);
    tooltip.style.display = "none";
    return;
  }

  tooltip.style.display = "block";

  const pad = { top: 48, right: 42, bottom: 148, left: 54 };
  const width = Math.max(1, rect.width - pad.left - pad.right);
  const height = Math.max(1, rect.height - pad.top - pad.bottom);
  const amountMax = Math.max(100, ...trendData.map((item) => Number(item.transactionAmount) || 0));
  const spendMax = Math.max(10, ...trendData.map((item) => Number(item.adCost) || 0));
  const amountCeil = niceCeil(amountMax, amountMax > 300 ? 100 : 70);
  const spendCeil = niceCeil(spendMax, spendMax > 12 ? 3 : 2);
  const plotX = (index) => pad.left + (trendData.length === 1 ? 0 : (index / (trendData.length - 1)) * width);
  const amountY = (value) => pad.top + height - ((Number(value) || 0) / amountCeil) * height;
  const spendY = (value) => pad.top + height - ((Number(value) || 0) / spendCeil) * height;

  ctx.save();
  ctx.strokeStyle = "rgba(132, 148, 184, 0.14)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.fillStyle = "rgba(173, 185, 213, 0.72)";
  ctx.font = "12px Microsoft YaHei, Arial";
  ctx.textBaseline = "middle";
  for (let index = 0; index <= 5; index += 1) {
    const value = (amountCeil / 5) * index;
    const y = amountY(value);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + width, y);
    ctx.stroke();
    ctx.fillText(String(Math.round(value)), 20, y);
  }
  ctx.textAlign = "right";
  for (let index = 0; index <= 5; index += 1) {
    const value = (spendCeil / 5) * index;
    ctx.fillText(String(value.toFixed(value % 1 === 0 ? 0 : 1)), rect.width - 18, spendY(value));
  }
  ctx.restore();

  ctx.save();
  ctx.strokeStyle = "rgba(108, 127, 184, 0.22)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + height + 28);
  ctx.lineTo(pad.left + width, pad.top + height + 28);
  ctx.stroke();

  ctx.fillStyle = "rgba(174, 187, 216, 0.7)";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const labelIndexes = Array.from(new Set([0, Math.floor(trendData.length * 0.25), Math.floor(trendData.length * 0.5), Math.floor(trendData.length * 0.75), trendData.length - 1]));
  labelIndexes.forEach((index) => {
    ctx.fillText(trendData[index]?.time || "", plotX(index), pad.top + height + 12);
  });
  ctx.restore();

  const amountPoints = trendData.map((item, index) => ({ x: plotX(index), y: amountY(item.transactionAmount) }));
  const spendPoints = trendData.map((item, index) => ({ x: plotX(index), y: spendY(item.adCost) }));
  drawLine(ctx, amountPoints, "#2f68ff", "#4d7cff", 1.45);
  drawLine(ctx, spendPoints, "#13b8ff", "#1ccaff", 1.65);

  state.chartIndex = Math.max(0, Math.min(trendData.length - 1, requestedIndex));
  const active = trendData[state.chartIndex];
  const x = plotX(state.chartIndex);
  const amountPoint = { x, y: amountY(active.transactionAmount) };
  const spendPoint = { x, y: spendY(active.adCost) };

  drawCanvasEventTimeline(ctx, data, trendData, plotX, x, rect, pad.top + height + 52);

  ctx.save();
  ctx.strokeStyle = "rgba(115, 137, 198, 0.32)";
  ctx.beginPath();
  ctx.moveTo(x, pad.top);
  ctx.lineTo(x, rect.height - 44);
  ctx.stroke();

  [amountPoint, spendPoint].forEach((point, index) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = index === 0 ? "#2f68ff" : "#17bfff";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(225, 236, 255, 0.92)";
    ctx.stroke();
  });
  ctx.restore();

  tooltip.style.left = `${Math.min(rect.width - 188, Math.max(64, x + 12))}px`;
  tooltip.style.top = `${Math.max(8, Math.min(rect.height - 178, Math.min(amountPoint.y, spendPoint.y) - 96))}px`;
  document.getElementById("tipTime").textContent = active.time || "-";
  document.getElementById("tipAmount").textContent = formatChartNumber(active.transactionAmount);
  document.getElementById("tipSpend").textContent = formatChartNumber(active.adCost);
  document.getElementById("tipEvent").textContent = active.eventType || "";
  document.getElementById("tipEventDetail").textContent = active.eventType === "投放" ? "全域投放" : active.eventType || "";
  const eventBlock = document.getElementById("tipEventBlock");
  if (eventBlock) eventBlock.hidden = !active.eventType;

  const debugKey = `${trendData.length}|${canvas.width}|${canvas.height}|${amountPoints.length}`;
  if (debugKey !== state.lastChartDebugKey) {
    state.lastChartDebugKey = debugKey;
    console.info("[live-dashboard-chart]", {
      trendDataLength: trendData.length,
      canvasWidth: canvas.width,
      canvasHeight: canvas.height,
      cssCanvasWidth: Math.round(rect.width),
      cssCanvasHeight: Math.round(rect.height),
      drawnPoints: amountPoints.length,
    });
  }
}

function indexFromPointer(event, trendLength) {
  const canvas = document.getElementById("trendChart");
  const rect = canvas.getBoundingClientRect();
  const padLeft = 54;
  const padRight = 42;
  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left - padLeft) / (rect.width - padLeft - padRight)));
  return Math.round(ratio * Math.max(0, trendLength - 1));
}

function bindDashboardEvents() {
  const canvas = document.getElementById("trendChart");
  if (!canvas) return;

  canvas.addEventListener("mousemove", (event) => {
    const trendLength = state.data?.trendData?.length || 0;
    renderChart(state.data, indexFromPointer(event, trendLength));
    renderEventTimeline(state.data);
  });
  canvas.addEventListener("mouseleave", () => {
    const trendLength = state.data?.trendData?.length || 0;
    renderChart(state.data, Math.floor(trendLength * 0.62));
    renderEventTimeline(state.data);
  });
  window.addEventListener("resize", () => renderChart(state.data, state.chartIndex));
}

function updateDashboard(data) {
  state.data = data;
  setBodyMode("dashboard-page", data);
  document.title = data.basicInfo.screenTitle || "直播大屏";
  updateText("platformName", data.basicInfo.platformName);
  updateText("screenTitle", data.basicInfo.screenTitle);
  updateText("versionName", data.basicInfo.versionName);
  updateText("roomName", data.basicInfo.roomName);
  updateText("startTime", data.basicInfo.startTime);
  updateText("duration", data.basicInfo.duration);
  updateText("selectedTime", data.basicInfo.selectedTime);

  const versionButton = document.querySelector("[data-dashboard='versionName']");
  if (versionButton) versionButton.hidden = !data.styleConfig.showVersionTag;

  const liveImage = document.getElementById("livePreviewImage");
  if (liveImage) liveImage.src = data.basicInfo.liveImageUrl || DEFAULT_LIVE_IMAGE;

  const screen = document.querySelector(".screen");
  if (screen) screen.classList.toggle("no-live", !data.styleConfig.showLivePreview);

  const livePanel = document.getElementById("livePanel");
  if (livePanel) livePanel.hidden = !data.styleConfig.showLivePreview;

  ["commentTabs", "commentEmpty"].forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.hidden = !data.styleConfig.showComments;
  });

  const analysisPanel = document.querySelector(".analysis-panel");
  if (analysisPanel) analysisPanel.classList.toggle("no-events", !data.styleConfig.showEventTimeline);

  const shell = document.querySelector(".dashboard-shell");
  if (shell) {
    const scale = data.styleConfig.screenScale / 100;
    shell.style.setProperty("--screen-scale", scale);
    shell.style.setProperty("--scaled-width", `${100 / scale}vw`);
    shell.style.setProperty("--scaled-height", `${100 / scale}vh`);
  }

  renderMetricCards(data);
  renderChart(data, Math.min(state.chartIndex, Math.max(0, data.trendData.length - 1)));
  renderEventTimeline(data);
}

function renderDashboard(root) {
  if (state.refreshTimer) window.clearInterval(state.refreshTimer);
  const data = getLiveData();
  state.chartIndex = Math.floor((data.trendData?.length || 1) * 0.62);
  state.serializedData = JSON.stringify(data);
  setBodyMode("dashboard-page", data);
  root.innerHTML = dashboardTemplate(data);
  updateDashboard(data);
  bindDashboardEvents();

  state.refreshTimer = window.setInterval(() => {
    const nextData = getLiveData();
    const serialized = JSON.stringify(nextData);
    if (serialized === state.serializedData) return;
    state.serializedData = serialized;
    updateDashboard(nextData);
  }, 2000);
}

async function renderRoute() {
  const root = document.getElementById("app");
  if (!root) return;

  if (window.location.pathname === "/qianchuan-dashboard") {
    if (state.refreshTimer) window.clearInterval(state.refreshTimer);
    const { renderQianchuanDashboard } = await import("./qianchuanDashboard.js");
    renderQianchuanDashboard(root);
    return;
  }

  if (window.location.pathname === "/admin") {
    if (state.refreshTimer) window.clearInterval(state.refreshTimer);
    const { renderAdmin } = await import("./admin.js");
    renderAdmin(root);
    return;
  }

  if (window.location.pathname === "/" || window.location.pathname === "/overview") {
    if (state.refreshTimer) window.clearInterval(state.refreshTimer);
    const { renderOverview } = await import("./overview.js");
    renderOverview(root);
    return;
  }

  renderDashboard(root);
}

renderRoute();
