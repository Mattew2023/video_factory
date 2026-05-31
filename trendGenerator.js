function minutesFromTime(time) {
  const [hour, minute] = String(time || "00:00").split(":").map(Number);
  return (Number.isFinite(hour) ? hour : 0) * 60 + (Number.isFinite(minute) ? minute : 0);
}

function timeFromMinutes(totalMinutes) {
  const minutesInDay = ((Math.round(totalMinutes) % 1440) + 1440) % 1440;
  const hour = Math.floor(minutesInDay / 60);
  const minute = minutesInDay % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function distributeTotal(weights, total, fractionDigits = 2) {
  const weightTotal = weights.reduce((sum, value) => sum + value, 0) || 1;
  let runningTotal = 0;

  return weights.map((weight, index) => {
    if (index === weights.length - 1) {
      return Number((total - runningTotal).toFixed(fractionDigits));
    }

    const value = Number(((weight / weightTotal) * total).toFixed(fractionDigits));
    runningTotal += value;
    return value;
  });
}

export function generateRealisticTrendData(options = {}) {
  const startMinute = minutesFromTime(options.startTime || "06:45");
  const endMinute = minutesFromTime(options.endTime || "09:45");
  const totalMinutes = Math.max(1, endMinute - startMinute + 1);
  const targetGMV = Number(options.targetGMV) || 0;
  const targetAdCost = Number(options.targetAdCost) || 0;
  const avgOnlineUserCount = Number(options.avgOnlineUserCount) || 30;
  const eventTypes = Array.isArray(options.eventTypes) ? options.eventTypes.filter(Boolean) : [];

  const weights = Array.from({ length: totalMinutes }, (_, index) => {
    const progress = index / Math.max(1, totalMinutes - 1);
    const peak = Math.exp(-Math.pow((progress - 0.42) / 0.24, 2));
    const latePeak = Math.exp(-Math.pow((progress - 0.72) / 0.18, 2)) * 0.48;
    const ripple = Math.sin(index * 0.37) * 0.12 + Math.cos(index * 0.19) * 0.08;
    return Math.max(0.08, 0.18 + peak + latePeak + ripple);
  });

  const amountSeries = distributeTotal(weights, targetGMV, 2);
  const spendSeries = distributeTotal(
    weights.map((weight, index) => weight * (0.72 + Math.sin(index * 0.21) * 0.18)),
    targetAdCost,
    2
  );

  return amountSeries.map((transactionAmount, index) => {
    const progress = index / Math.max(1, totalMinutes - 1);
    const onlineWave = Math.sin(progress * Math.PI) * avgOnlineUserCount * 0.72;
    const onlineRipple = Math.sin(index * 0.41) * Math.max(2, avgOnlineUserCount * 0.08);
    const eventType = index % 24 === 0 && eventTypes.length ? eventTypes[(index / 24) % eventTypes.length] : "";

    return {
      time: timeFromMinutes(startMinute + index),
      transactionAmount,
      adCost: spendSeries[index],
      onlineUserCount: Math.max(1, Math.round(avgOnlineUserCount * 0.55 + onlineWave + onlineRipple)),
      eventType,
    };
  });
}

export function validateTrendData(trendData, targetGMV = 0, targetAdCost = 0) {
  const rows = Array.isArray(trendData) ? trendData : [];
  const transactionTotal = rows.reduce((sum, row) => sum + (Number(row.transactionAmount) || 0), 0);
  const adCostTotal = rows.reduce((sum, row) => sum + (Number(row.adCost) || 0), 0);

  return {
    "trendData 条数": rows.length,
    "transactionAmount 总和": Number(transactionTotal.toFixed(2)),
    "adCost 总和": Number(adCostTotal.toFixed(2)),
    "transactionAmount 误差": Number((transactionTotal - Number(targetGMV || 0)).toFixed(2)),
    "adCost 误差": Number((adCostTotal - Number(targetAdCost || 0)).toFixed(2)),
  };
}
