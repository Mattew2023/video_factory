const anchorPoints = [
  ["06:45", 80, 0.5, 12, "投放"],
  ["06:55", 126, 1.1, 18, ""],
  ["07:05", 168, 1.8, 24, "讲解"],
  ["07:15", 220, 2.7, 33, ""],
  ["07:25", 310, 3.6, 46, "福袋"],
  ["07:35", 286, 4.1, 42, ""],
  ["07:45", 364, 5.1, 51, "投放"],
  ["07:55", 455, 6.8, 58, ""],
  ["08:05", 420, 6.2, 49, "讲解"],
  ["08:15", 512, 7.4, 62, ""],
  ["08:25", 618, 8.1, 74, "场记"],
  ["08:35", 586, 7.7, 67, ""],
  ["08:45", 690, 9.2, 81, "投放"],
  ["08:55", 548, 8.6, 55, ""],
  ["09:05", 436, 6.7, 43, "预警"],
  ["09:15", 382, 5.4, 38, ""],
  ["09:25", 318, 4.2, 31, "主播"],
  ["09:35", 284, 3.3, 28, ""],
  ["09:45", 232, 2.5, 22, "讲解"],
  ["10:05", 165, 1.2, 17, ""],
  ["10:20", 96, 0.7, 11, "投放"],
  ["10:32", 42, 0.2, 6, ""],
];

function minutesFromTime(time) {
  const [hour, minute] = time.split(":").map(Number);
  return hour * 60 + minute;
}

function timeFromMinutes(totalMinutes) {
  const hour = Math.floor(totalMinutes / 60);
  const minute = totalMinutes % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function smoothStep(value) {
  return value * value * (3 - 2 * value);
}

function interpolate(startValue, endValue, progress) {
  return startValue + (endValue - startValue) * smoothStep(progress);
}

function generateMinuteTrendData() {
  const anchors = anchorPoints.map(([time, transactionAmount, adCost, onlineUserCount, eventType]) => ({
    time,
    minute: minutesFromTime(time),
    transactionAmount,
    adCost,
    onlineUserCount,
    eventType,
  }));
  const eventByTime = new Map(anchors.filter((item) => item.eventType).map((item) => [item.time, item.eventType]));
  const result = [];

  for (let index = 0; index < anchors.length - 1; index += 1) {
    const current = anchors[index];
    const next = anchors[index + 1];
    const span = next.minute - current.minute;

    for (let offset = 0; offset < span; offset += 1) {
      const minute = current.minute + offset;
      const progress = offset / span;
      const time = timeFromMinutes(minute);
      const ripple = Math.sin((result.length + 1) * 0.72) * 4.5;
      const spendRipple = Math.sin((result.length + 3) * 0.53) * 0.08;
      const onlineRipple = Math.sin((result.length + 5) * 0.61) * 1.4;

      result.push({
        time,
        transactionAmount: Math.max(0, Math.round(interpolate(current.transactionAmount, next.transactionAmount, progress) + ripple)),
        adCost: Number(Math.max(0, interpolate(current.adCost, next.adCost, progress) + spendRipple).toFixed(2)),
        onlineUserCount: Math.max(0, Math.round(interpolate(current.onlineUserCount, next.onlineUserCount, progress) + onlineRipple)),
        eventType: eventByTime.get(time) || "",
      });
    }
  }

  const last = anchors.at(-1);
  result.push({
    time: last.time,
    transactionAmount: last.transactionAmount,
    adCost: last.adCost,
    onlineUserCount: last.onlineUserCount,
    eventType: last.eventType,
  });

  return result;
}

export const defaultData = {
  basicInfo: {
    roomName: "青岛外贸8号店",
    platformName: "抖音电商·罗盘",
    screenTitle: "直播大屏",
    versionName: "专业版",
    startTime: "2026/05/26 06:45",
    duration: "3小时47分钟",
    selectedTime: "05/26 06:45",
    liveImageUrl: "",
  },
  metrics: {
    transactionAmount: 24265,
    userPayAmount: 24143.88,
    adCost: 918.09,
    viewerCount: 6887,
    buyerCount: 273,
    orderCount: 367,
    asyncTransactionAmount: 24774,
    productClickUserCount: 2254,
    avgOnlineUserCount: 30,
    exposureCount: 106704,
    oldFanBuyerCount: 27,
  },
  styleConfig: {
    themeName: "默认蓝紫",
    showLivePreview: true,
    showComments: true,
    showEventTimeline: true,
    showVersionTag: true,
    screenScale: 100,
  },
  trendData: generateMinuteTrendData(),
  eventTypes: ["投放", "讲解", "福袋", "场记", "预警", "主播"],
};
