import { defaultData } from "./defaultData.js";

export const STORAGE_KEY = "live-dashboard-config";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeNumber(value) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

function minuteFromTime(time) {
  const match = String(time || "").match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour > 23 || minute > 59) return null;
  return hour * 60 + minute;
}

function timeFromMinute(totalMinutes) {
  const minutesInDay = ((totalMinutes % 1440) + 1440) % 1440;
  const hour = Math.floor(minutesInDay / 60);
  const minute = minutesInDay % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function interpolate(startValue, endValue, progress) {
  return startValue + (endValue - startValue) * progress;
}

function normalizeTrendRows(trendData) {
  return trendData.map((row) => ({
    time: String(row.time || ""),
    transactionAmount: normalizeNumber(row.transactionAmount),
    adCost: normalizeNumber(row.adCost),
    onlineUserCount: normalizeNumber(row.onlineUserCount),
    eventType: String(row.eventType || ""),
  }));
}

function expandTrendDataToMinuteRows(trendData) {
  const rows = normalizeTrendRows(trendData);
  if (rows.length < 2) return rows;

  let lastAbsoluteMinute = null;
  const points = rows.map((row) => {
    let minute = minuteFromTime(row.time);
    if (minute === null) return { ...row, absoluteMinute: null };

    if (lastAbsoluteMinute !== null) {
      while (minute <= lastAbsoluteMinute) minute += 1440;
    }
    lastAbsoluteMinute = minute;

    return { ...row, absoluteMinute: minute };
  });

  if (points.some((point) => point.absoluteMinute === null)) return rows;

  const hasMinuteGaps = points.some((point, index) => index > 0 && point.absoluteMinute - points[index - 1].absoluteMinute > 1);
  if (!hasMinuteGaps) return rows;

  const expanded = [];
  for (let index = 0; index < points.length - 1; index += 1) {
    const current = points[index];
    const next = points[index + 1];
    const gap = Math.max(1, next.absoluteMinute - current.absoluteMinute);

    for (let offset = 0; offset < gap; offset += 1) {
      const progress = offset / gap;
      expanded.push({
        time: timeFromMinute(current.absoluteMinute + offset),
        transactionAmount: Number(interpolate(current.transactionAmount, next.transactionAmount, progress).toFixed(2)),
        adCost: Number(interpolate(current.adCost, next.adCost, progress).toFixed(2)),
        onlineUserCount: Math.round(interpolate(current.onlineUserCount, next.onlineUserCount, progress)),
        eventType: offset === 0 ? current.eventType : "",
      });
    }
  }

  const last = points.at(-1);
  expanded.push({
    time: timeFromMinute(last.absoluteMinute),
    transactionAmount: last.transactionAmount,
    adCost: last.adCost,
    onlineUserCount: last.onlineUserCount,
    eventType: last.eventType,
  });

  return expanded;
}

function mergeData(input = {}) {
  const merged = {
    ...clone(defaultData),
    ...input,
    basicInfo: { ...defaultData.basicInfo, ...(input.basicInfo || {}) },
    metrics: { ...defaultData.metrics, ...(input.metrics || {}) },
    styleConfig: { ...defaultData.styleConfig, ...(input.styleConfig || {}) },
    eventTypes: Array.isArray(input.eventTypes) && input.eventTypes.length ? input.eventTypes : clone(defaultData.eventTypes),
    trendData: Array.isArray(input.trendData) ? input.trendData : clone(defaultData.trendData),
  };

  Object.keys(merged.metrics).forEach((key) => {
    merged.metrics[key] = normalizeNumber(merged.metrics[key]);
  });

  merged.trendData = expandTrendDataToMinuteRows(merged.trendData);

  merged.styleConfig.screenScale = normalizeNumber(merged.styleConfig.screenScale) || 100;
  merged.styleConfig.showLivePreview = Boolean(merged.styleConfig.showLivePreview);
  merged.styleConfig.showComments = Boolean(merged.styleConfig.showComments);
  merged.styleConfig.showEventTimeline = Boolean(merged.styleConfig.showEventTimeline);
  merged.styleConfig.showVersionTag = Boolean(merged.styleConfig.showVersionTag);

  return merged;
}

export function getDefaultData() {
  return clone(defaultData);
}

export function getLiveData() {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) return getDefaultData();

  try {
    return mergeData(JSON.parse(stored));
  } catch {
    return getDefaultData();
  }
}

export function saveLiveData(data) {
  const normalized = mergeData(data);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

export function resetLiveData() {
  const data = getDefaultData();
  saveLiveData(data);
  return data;
}

export function clearLiveData() {
  window.localStorage.removeItem(STORAGE_KEY);
}

export function exportLiveData(data = getLiveData()) {
  const blob = new Blob([JSON.stringify(mergeData(data), null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "live-dashboard-data.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function dataFromImportedJson(parsed) {
  const currentData = getLiveData();
  if (Array.isArray(parsed)) {
    return {
      ...currentData,
      trendData: parsed,
    };
  }

  if (!parsed || typeof parsed !== "object") {
    throw new Error("JSON 格式不正确");
  }

  if (Array.isArray(parsed.trendData)) {
    return {
      ...currentData,
      ...parsed,
      basicInfo: { ...currentData.basicInfo, ...(parsed.basicInfo || {}) },
      metrics: { ...currentData.metrics, ...(parsed.metrics || {}) },
      styleConfig: { ...currentData.styleConfig, ...(parsed.styleConfig || {}) },
      eventTypes: Array.isArray(parsed.eventTypes) && parsed.eventTypes.length ? parsed.eventTypes : currentData.eventTypes,
      trendData: parsed.trendData,
    };
  }

  throw new Error("JSON 需要是完整配置、包含 trendData 的对象，或趋势数组");
}

export function importLiveData(file) {
  if (!file) {
    return Promise.reject(new Error("请选择 JSON 文件"));
  }

  const readText =
    typeof file.text === "function"
      ? file.text()
      : new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result || "{}"));
          reader.onerror = () => reject(new Error("文件读取失败"));
          reader.readAsText(file, "utf-8");
        });

  return readText.then((text) => {
    const parsed = JSON.parse(String(text || "{}"));
    return saveLiveData(dataFromImportedJson(parsed));
  });
}
