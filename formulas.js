export function toNumber(value) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

export function safeDivide(numerator, denominator, fallback = 0) {
  const bottom = toNumber(denominator);
  if (bottom === 0) return fallback;
  return toNumber(numerator) / bottom;
}

export function calculateDerivedMetrics(data) {
  const metrics = data.metrics || {};
  return {
    thousandViewerPay: safeDivide(metrics.userPayAmount, metrics.viewerCount) * 1000,
    viewBuyerRate: safeDivide(metrics.buyerCount, metrics.viewerCount) * 100,
    productClickBuyerRate: safeDivide(metrics.buyerCount, metrics.productClickUserCount) * 100,
    exposureViewRate: safeDivide(metrics.viewerCount, metrics.exposureCount) * 100,
    oldFanBuyerRate: safeDivide(metrics.oldFanBuyerCount, metrics.buyerCount) * 100,
    averageOrderValue: safeDivide(metrics.transactionAmount, metrics.buyerCount),
    itemUnitPrice: safeDivide(metrics.transactionAmount, metrics.orderCount),
    roi: safeDivide(metrics.userPayAmount, metrics.adCost),
  };
}

export function formatNumber(value, fractionDigits = 0) {
  return toNumber(value).toLocaleString("zh-CN", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

export function formatMoney(value, fractionDigits = 2) {
  return `¥${formatNumber(value, fractionDigits)}`;
}

export function formatPercent(value) {
  return `${formatNumber(value, 2)}%`;
}

export function formatRatio(value) {
  return toNumber(value) === 0 ? "-" : formatNumber(value, 2);
}

export function getMetricCards(data) {
  const metrics = data.metrics || {};
  const derived = calculateDerivedMetrics(data);
  return [
    {
      label: "直播间成交金额",
      value: formatMoney(metrics.transactionAmount, 2),
      group: "primary",
    },
    {
      label: "直播间用户支付金额",
      value: formatMoney(metrics.userPayAmount, 2),
      group: "primary",
    },
    {
      label: "投放消耗（店铺绑定）",
      value: formatMoney(metrics.adCost, 2),
      group: "primary",
    },
    {
      label: "千次观看用户支付金额",
      value: formatMoney(derived.thousandViewerPay, 2),
      group: "primary",
    },
    {
      label: "成交人数",
      value: formatNumber(metrics.buyerCount),
      group: "primary",
    },
    {
      label: "成交件数",
      value: formatNumber(metrics.orderCount),
      group: "primary",
    },
    {
      label: "直播间成交金额（含异步交易）",
      value: formatMoney(metrics.asyncTransactionAmount, 2),
      group: "secondary",
    },
    {
      label: "观看-成交率",
      value: formatPercent(derived.viewBuyerRate),
      group: "secondary",
    },
    {
      label: "商品点击-成交率",
      value: formatPercent(derived.productClickBuyerRate),
      group: "secondary",
    },
    {
      label: "平均在线人数",
      value: formatNumber(metrics.avgOnlineUserCount),
      group: "secondary",
    },
    {
      label: "曝光-观看率",
      value: formatPercent(derived.exposureViewRate),
      group: "secondary",
    },
    {
      label: "成交老粉占比",
      value: formatPercent(derived.oldFanBuyerRate),
      group: "secondary",
    },
  ];
}

export function getFormulaCards(data) {
  const derived = calculateDerivedMetrics(data);
  return [
    { label: "客单价", value: formatMoney(derived.averageOrderValue, 2) },
    { label: "件单价", value: formatMoney(derived.itemUnitPrice, 2) },
    { label: "投产比", value: formatRatio(derived.roi) },
  ];
}
