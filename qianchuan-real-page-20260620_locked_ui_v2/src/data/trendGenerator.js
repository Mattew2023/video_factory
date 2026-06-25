export function normalizeTrendData(trendData = []) {
  return trendData.map((point) => ({
    time: point.time,
    netTransactionAmount: Number(point.netTransactionAmount || 0),
    cost: Number(point.cost || 0),
    control: Number(point.control || 0),
    events: Array.isArray(point.events) ? point.events : []
  }));
}
