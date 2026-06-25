export function formatNumber(value, options = {}) {
  return Number(value ?? 0).toLocaleString("zh-CN", options);
}

export function formatCurrency(value) {
  return formatNumber(value, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

export function formatInteger(value) {
  return formatNumber(value, {
    maximumFractionDigits: 0
  });
}

export function formatPercent(value) {
  return `${formatNumber(value, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}%`;
}

export function splitMetricValue(value, options = {}) {
  const decimals = options.decimals ?? 2;
  const suffix = options.suffix || "";
  const formatted = formatNumber(value, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });

  const [integerPart, decimalPart] = formatted.split(".");

  return {
    integerPart,
    decimalPart: decimalPart ? `.${decimalPart}` : "",
    suffix
  };
}

export function calculateRoi(netTransactionAmount, cost) {
  if (!cost) {
    return 0;
  }

  return Number((netTransactionAmount / cost).toFixed(2));
}
