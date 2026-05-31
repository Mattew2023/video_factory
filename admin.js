import { formatMoney, getFormulaCards } from "./formulas.js";
import {
  clearLiveData,
  exportLiveData,
  getDefaultData,
  getLiveData,
  importLiveData,
  resetLiveData,
  saveLiveData,
} from "./storage.js";
import { generateRealisticTrendData, validateTrendData } from "./trendGenerator.js";

let rootElement;
let workingData;

const REALISTIC_METRICS = {
  transactionAmount: 21231,
  userPayAmount: 21058.36,
  adCost: 1246.8,
  viewerCount: 7820,
  buyerCount: 238,
  orderCount: 327,
  asyncTransactionAmount: 22084.57,
  productClickUserCount: 1910,
  avgOnlineUserCount: 58,
  exposureCount: 98200,
  oldFanBuyerCount: 31,
};

const basicFields = [
  ["roomName", "直播间名称"],
  ["platformName", "平台名称"],
  ["screenTitle", "页面标题"],
  ["versionName", "版本名称"],
  ["startTime", "开播时间"],
  ["duration", "直播时长"],
  ["selectedTime", "当前选中时间"],
];

const metricFields = [
  ["transactionAmount", "直播间成交金额"],
  ["userPayAmount", "直播间用户支付金额"],
  ["adCost", "投放消耗"],
  ["viewerCount", "观看人数"],
  ["buyerCount", "成交人数"],
  ["orderCount", "成交件数"],
  ["asyncTransactionAmount", "直播间成交金额（含异步交易）"],
  ["productClickUserCount", "商品点击人数"],
  ["avgOnlineUserCount", "平均在线人数"],
  ["exposureCount", "曝光人数"],
  ["oldFanBuyerCount", "老粉成交人数"],
];

const themeOptions = ["默认蓝紫", "暗黑科技", "蓝黑商务"];
const scaleOptions = [100, 90, 80];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function numberValue(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function createField(path, label, value, type = "text") {
  return `
    <label class="admin-field">
      <span>${escapeHtml(label)}</span>
      <input type="${type}" data-path="${escapeHtml(path)}" value="${escapeHtml(value)}" />
    </label>
  `;
}

function createCheckbox(path, label, checked) {
  return `
    <label class="admin-check">
      <input type="checkbox" data-path="${escapeHtml(path)}" ${checked ? "checked" : ""} />
      <span>${escapeHtml(label)}</span>
    </label>
  `;
}

function createSelect(path, label, options, current) {
  const optionHtml = options
    .map((option) => `<option value="${escapeHtml(option)}" ${String(option) === String(current) ? "selected" : ""}>${escapeHtml(option)}</option>`)
    .join("");
  return `
    <label class="admin-field">
      <span>${escapeHtml(label)}</span>
      <select data-path="${escapeHtml(path)}">${optionHtml}</select>
    </label>
  `;
}

function createLiveImageField(value) {
  const hasImage = Boolean(value);
  return `
    <div class="admin-field image-upload-field">
      <span>右侧直播预览图片地址</span>
      <div class="image-input-row">
        <input id="liveImageUrlInput" type="text" data-path="basicInfo.liveImageUrl" value="${escapeHtml(value)}" placeholder="可粘贴图片 URL，或上传本地图片" />
        <label class="file-action compact">
          <input id="liveImageFile" type="file" accept="image/*" />
          <span>上传本地图片</span>
        </label>
        <button type="button" data-action="clear-live-image">清空图片</button>
      </div>
      <div class="image-preview ${hasImage ? "" : "empty"}" id="liveImagePreview">
        ${hasImage ? `<img src="${escapeHtml(value)}" alt="直播预览图片预览" />` : "<p>未设置图片时，大屏将使用默认直播预览素材。</p>"}
      </div>
      <p class="image-helper">本地图片会压缩为 Data URL 并随配置保存，适合几 MB 以内的图片。</p>
    </div>
  `;
}

function trendRowTemplate(row, index, eventTypes) {
  const options = ["", ...eventTypes]
    .map((type) => `<option value="${escapeHtml(type)}" ${type === row.eventType ? "selected" : ""}>${escapeHtml(type || "无事件")}</option>`)
    .join("");

  return `
    <tr data-trend-index="${index}">
      <td><input class="trend-time" value="${escapeHtml(row.time)}" /></td>
      <td><input class="trend-amount" type="number" step="0.01" value="${escapeHtml(row.transactionAmount)}" /></td>
      <td><input class="trend-cost" type="number" step="0.01" value="${escapeHtml(row.adCost)}" /></td>
      <td><input class="trend-online" type="number" step="1" value="${escapeHtml(row.onlineUserCount)}" /></td>
      <td><select class="trend-event">${options}</select></td>
      <td><button class="table-icon-btn" type="button" data-action="delete-trend" aria-label="删除趋势行">×</button></td>
    </tr>
  `;
}

function formulaPreviewTemplate(data) {
  return getFormulaCards(data)
    .map((item) => `<article><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong></article>`)
    .join("");
}

function adminTemplate(data) {
  return `
    <main class="admin-shell">
      <header class="admin-topbar">
        <div>
          <p>Live Dashboard Admin</p>
          <h1>直播大屏配置</h1>
        </div>
        <nav>
          <a class="admin-link" href="/dashboard">查看大屏</a>
          <a class="admin-link subtle" href="/">返回首页</a>
        </nav>
      </header>

      <form class="admin-form" id="adminForm">
        <section class="admin-section">
          <div class="section-heading">
            <span>01</span>
            <h2>基础信息配置</h2>
          </div>
          <div class="admin-grid two-cols">
            ${basicFields.map(([key, label]) => createField(`basicInfo.${key}`, label, data.basicInfo[key] || "")).join("")}
            ${createLiveImageField(data.basicInfo.liveImageUrl || "")}
          </div>
        </section>

        <section class="admin-section">
          <div class="section-heading">
            <span>02</span>
            <h2>核心数据配置</h2>
          </div>
          <div class="admin-grid three-cols">
            ${metricFields.map(([key, label]) => createField(`metrics.${key}`, label, data.metrics[key] || 0, "number")).join("")}
          </div>
          <div class="formula-preview" id="formulaPreview">
            ${formulaPreviewTemplate(data)}
          </div>
        </section>

        <section class="admin-section">
          <div class="section-heading with-actions">
            <div>
              <span>03</span>
              <h2>趋势数据配置</h2>
            </div>
            <div class="section-actions">
              <button type="button" data-action="add-trend">新增一行</button>
              <button type="button" data-action="random-trend">生成高拟真罗盘曲线</button>
              <button type="button" data-action="clear-trend">清空趋势数据</button>
            </div>
          </div>
          <div class="admin-table-wrap">
            <table class="trend-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>成交金额</th>
                  <th>投放消耗</th>
                  <th>在线人数</th>
                  <th>事件类型</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody id="trendRows">
                ${data.trendData.map((row, index) => trendRowTemplate(row, index, data.eventTypes)).join("")}
              </tbody>
            </table>
          </div>
        </section>

        <section class="admin-section">
          <div class="section-heading">
            <span>04</span>
            <h2>样式配置</h2>
          </div>
          <div class="admin-grid three-cols">
            ${createSelect("styleConfig.themeName", "主题名称", themeOptions, data.styleConfig.themeName)}
            ${createSelect("styleConfig.screenScale", "大屏缩放比例", scaleOptions, data.styleConfig.screenScale)}
            ${createCheckbox("styleConfig.showLivePreview", "显示右侧直播预览", data.styleConfig.showLivePreview)}
            ${createCheckbox("styleConfig.showComments", "显示评论区域", data.styleConfig.showComments)}
            ${createCheckbox("styleConfig.showEventTimeline", "显示事件时间线", data.styleConfig.showEventTimeline)}
            ${createCheckbox("styleConfig.showVersionTag", "显示顶部版本标签", data.styleConfig.showVersionTag)}
          </div>
        </section>

        <section class="admin-section">
          <div class="section-heading">
            <span>05</span>
            <h2>数据操作</h2>
          </div>
          <div class="data-actions">
            <button class="primary-action" type="button" data-action="save">保存配置</button>
            <button type="button" data-action="reset">恢复默认数据</button>
            <button type="button" data-action="export">导出 JSON</button>
            <label class="file-action">
              <input id="importFile" type="file" accept="application/json,.json" />
              <span>导入 JSON</span>
            </label>
            <button type="button" data-action="clear-local">清空本地数据</button>
          </div>
          <p class="admin-status" id="adminStatus" role="status"></p>
        </section>
      </form>
    </main>
  `;
}

function setNestedValue(target, path, value) {
  const [group, key] = path.split(".");
  if (!target[group]) target[group] = {};
  target[group][key] = value;
}

function collectTrendData() {
  return Array.from(document.querySelectorAll("#trendRows tr")).map((row) => ({
    time: row.querySelector(".trend-time").value.trim(),
    transactionAmount: numberValue(row.querySelector(".trend-amount").value),
    adCost: numberValue(row.querySelector(".trend-cost").value),
    onlineUserCount: numberValue(row.querySelector(".trend-online").value),
    eventType: row.querySelector(".trend-event").value,
  }));
}

function collectFormData() {
  const data = {
    ...workingData,
    basicInfo: { ...workingData.basicInfo },
    metrics: { ...workingData.metrics },
    styleConfig: { ...workingData.styleConfig },
    eventTypes: [...workingData.eventTypes],
    trendData: collectTrendData(),
  };

  document.querySelectorAll("[data-path]").forEach((input) => {
    const path = input.dataset.path;
    let value = input.type === "checkbox" ? input.checked : input.value;
    if (path.startsWith("metrics.") || path === "styleConfig.screenScale") {
      value = numberValue(value);
    }
    setNestedValue(data, path, value);
  });

  return data;
}

function setStatus(message, isError = false) {
  const status = document.getElementById("adminStatus");
  if (!status) return;
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("图片读取失败"));
    reader.readAsDataURL(file);
  });
}

function loadImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("图片解析失败"));
    image.src = dataUrl;
  });
}

async function fileToStoredImageUrl(file) {
  if (!file.type.startsWith("image/")) {
    throw new Error("请选择图片文件");
  }

  const originalDataUrl = await readFileAsDataUrl(file);
  if (file.type === "image/gif" || file.type === "image/svg+xml") {
    return originalDataUrl;
  }

  const image = await loadImage(originalDataUrl);
  const maxWidth = 900;
  const maxHeight = 1600;
  const ratio = Math.min(1, maxWidth / image.naturalWidth, maxHeight / image.naturalHeight);
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(image.naturalWidth * ratio));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * ratio));
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.86);
}

function updateLiveImagePreview(value) {
  const preview = document.getElementById("liveImagePreview");
  if (!preview) return;
  preview.classList.toggle("empty", !value);
  preview.innerHTML = value
    ? `<img src="${escapeHtml(value)}" alt="直播预览图片预览" />`
    : "<p>未设置图片时，大屏将使用默认直播预览素材。</p>";
}

function refreshFormulaPreview() {
  const preview = document.getElementById("formulaPreview");
  if (!preview) return;
  preview.innerHTML = formulaPreviewTemplate(collectFormData());
}

function renderTrendRows() {
  const rows = document.getElementById("trendRows");
  if (!rows) return;
  rows.innerHTML = workingData.trendData.map((row, index) => trendRowTemplate(row, index, workingData.eventTypes)).join("");
}

function handleAction(action, event) {
  if (action === "save") {
    workingData = saveLiveData(collectFormData());
    setStatus("已保存配置，展示页将在 2 秒内自动刷新。");
    refreshFormulaPreview();
    return;
  }

  if (action === "reset") {
    workingData = resetLiveData();
    renderAdmin(rootElement);
    setStatus("已恢复默认数据。");
    return;
  }

  if (action === "export") {
    exportLiveData(collectFormData());
    setStatus("已导出 live-dashboard-data.json。");
    return;
  }

  if (action === "clear-local") {
    clearLiveData();
    workingData = getDefaultData();
    renderAdmin(rootElement);
    setStatus("已清空本地数据，表单回到默认演示数据。");
    return;
  }

  if (action === "clear-live-image") {
    const input = document.getElementById("liveImageUrlInput");
    if (input) {
      input.value = "";
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    updateLiveImagePreview("");
    setStatus("已清空直播预览图片，保存后大屏将使用默认素材。");
    return;
  }

  if (action === "add-trend") {
    workingData = collectFormData();
    workingData.trendData.push({
      time: "",
      transactionAmount: 0,
      adCost: 0,
      onlineUserCount: 0,
      eventType: "",
    });
    renderTrendRows();
    setStatus("已新增趋势行，保存后生效。");
    return;
  }

  if (action === "random-trend") {
    workingData = collectFormData();
    const trendData = generateRealisticTrendData({
      startTime: "06:45",
      endTime: "09:45",
      targetGMV: 21231,
      targetAdCost: 1246.8,
      avgOnlineUserCount: 58,
      eventTypes: workingData.eventTypes,
    });
    const validation = validateTrendData(trendData, 21231, 1246.8);
    workingData = saveLiveData({
      ...workingData,
      metrics: {
        ...workingData.metrics,
        ...REALISTIC_METRICS,
      },
      trendData,
    });
    renderAdmin(rootElement);
    setStatus(
      `已生成高拟真罗盘曲线，共 ${validation["trendData 条数"]} 分钟，成交金额合计 ${formatMoney(
        validation["transactionAmount 总和"],
        2
      )}，投放消耗合计 ${formatMoney(validation["adCost 总和"], 2)}`
    );
    return;
  }

  if (action === "clear-trend") {
    workingData = collectFormData();
    workingData.trendData = [];
    renderTrendRows();
    setStatus("已清空趋势数据，保存后生效。");
    return;
  }

  if (action === "delete-trend") {
    workingData = collectFormData();
    const row = event.target.closest("tr");
    const index = Number(row?.dataset.trendIndex);
    workingData.trendData.splice(index, 1);
    renderTrendRows();
    setStatus("已删除趋势行，保存后生效。");
  }
}

function bindAdminEvents() {
  const form = document.getElementById("adminForm");
  if (!form) return;

  form.addEventListener("input", (event) => {
    if (event.target.matches("[data-path], .trend-amount, .trend-cost, .trend-online")) {
      refreshFormulaPreview();
    }
    if (event.target.id === "liveImageUrlInput") {
      updateLiveImagePreview(event.target.value.trim());
    }
  });

  form.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    handleAction(button.dataset.action, event);
  });

  document.getElementById("importFile").addEventListener("change", async (event) => {
    try {
      workingData = await importLiveData(event.target.files[0]);
      renderAdmin(rootElement);
      setStatus(`导入成功，当前趋势数据 ${workingData.trendData.length} 行，配置已写入本地存储。`);
    } catch (error) {
      setStatus(error.message || "导入失败，请检查 JSON 文件。", true);
    }
  });

  document.getElementById("liveImageFile").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      setStatus("正在处理本地图片...");
      const imageUrl = await fileToStoredImageUrl(file);
      const input = document.getElementById("liveImageUrlInput");
      input.value = imageUrl;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      updateLiveImagePreview(imageUrl);
      setStatus("图片已载入，点击“保存配置”后会同步到大屏。");
    } catch (error) {
      setStatus(error.message || "图片上传失败，请换一张图片。", true);
    } finally {
      event.target.value = "";
    }
  });
}

export function renderAdmin(root) {
  rootElement = root;
  workingData = getLiveData();
  document.body.className = "admin-page";
  document.title = "直播大屏配置";
  root.innerHTML = adminTemplate(workingData);
  bindAdminEvents();
}
