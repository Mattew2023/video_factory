export const qianchuanData = {
  basicInfo: {
    brands: [
      { name: "抖音电商", type: "douyin" },
      { name: "巨量千川", type: "qianchuan" },
    ],
    announcement: {
      badge: "公告",
      text: "全域直播大屏全面升级改版，快来体验吧！点击查看详情获取使用手册",
      actions: ["查看详情", "我知道了"],
      pageText: "1 / 2",
    },
    shopName: "青岛外贸8号店",
    liveStatus: "直播中",
    liveDuration: "2小时28分钟",
    startTime: "2026-06-20 06:45:31",
    dataStatus: "数据口径说明",
    dataScope: "全域净成交数据",
    refreshLabel: "刷新数据",
    fullscreenLabel: "全屏",
  },

  topMetrics: {
    gpm: 1886.84,
    totalCost: 338.15,
    netRoi: 21.44,
    netGmv: 7250,
    viewToPayRate: 2.73,
    onlineUserCount: 30,
    exposureViewRate: 8.93,
    totalViewCount: 3703,
  },

  topMetricCards: {
    primary: [
      { key: "totalCost", label: "整体消耗(元)", format: "decimal", decimals: 2 },
      { key: "netRoi", label: "净成交ROI", format: "decimal", decimals: 2 },
      { key: "netGmv", label: "净成交金额(元)", format: "decimal", decimals: 2 },
    ],
    secondary: [
      { key: "gpm", label: "GPM(元)", format: "decimal", decimals: 2 },
      { key: "viewToPayRate", label: "观看成交转化率", format: "percent" },
      { key: "onlineUserCount", label: "实时在线人数", format: "integer" },
      { key: "exposureViewRate", label: "曝光观看率(次数)", format: "percent" },
      { key: "totalViewCount", label: "直播间整体观看人数", format: "integer" },
    ],
  },

  trendConfig: {
    tabs: ["整体趋势", "素材表现"],
    activeTab: "整体趋势",
    granularityLabel: "5分钟粒度",
    filterLabel: "筛选",
    leftAxisLabel: "净成交金额(元)",
    rightAxisLabel: "消耗(元)",
    newControlLabel: "+ 新建调控",
    eventRows: ["投放动作", "调控动作"],
    metricToggles: [
      { key: "compositeCost", label: "综合成本", color: "#252832", active: false },
      { key: "netGmv", label: "净成交金额", color: "#2f73ff", active: true },
      { key: "compositeRoi", label: "综合ROI", color: "#252832", active: false },
      { key: "cost", label: "消耗", color: "#10d3e3", active: true },
      { key: "totalGmv", label: "整体成交金额", color: "#252832", active: false },
      { key: "totalPayRoi", label: "整体支付ROI", color: "#252832", active: false },
    ],
  },

  trendData: [
    { time: "06/20 06:45", netGmv: 128, cost: 1.3, roi: 2.1, totalGmv: 156, eventType: "" },
    { time: "06/20 06:50", netGmv: 432, cost: 8.6, roi: 4.8, totalGmv: 468, eventType: "投放动作" },
    { time: "06/20 06:55", netGmv: 326, cost: 7.1, roi: 4.2, totalGmv: 365, eventType: "" },
    { time: "06/20 07:00", netGmv: 294, cost: 6.7, roi: 4.1, totalGmv: 332, eventType: "" },
    { time: "06/20 07:05", netGmv: 212, cost: 5.1, roi: 3.6, totalGmv: 244, eventType: "投放动作" },
    { time: "06/20 07:10", netGmv: 306, cost: 6.1, roi: 4.2, totalGmv: 352, eventType: "" },
    { time: "06/20 07:15", netGmv: 414, cost: 8.3, roi: 4.5, totalGmv: 472, eventType: "" },
    { time: "06/20 07:20", netGmv: 486, cost: 9.4, roi: 4.9, totalGmv: 528, eventType: "" },
    { time: "06/20 07:25", netGmv: 488, cost: 9.4, roi: 5.1, totalGmv: 538, eventType: "" },
    { time: "06/20 07:30", netGmv: 487, cost: 9.2, roi: 5.2, totalGmv: 536, eventType: "投放动作" },
    { time: "06/20 07:35", netGmv: 472, cost: 9, roi: 5.1, totalGmv: 522, eventType: "" },
    { time: "06/20 07:40", netGmv: 486, cost: 9.5, roi: 5, totalGmv: 535, eventType: "" },
    { time: "06/20 07:45", netGmv: 532, cost: 10.2, roi: 5.1, totalGmv: 582, eventType: "" },
    { time: "06/20 07:50", netGmv: 572, cost: 10.8, roi: 5.3, totalGmv: 618, eventType: "" },
    { time: "06/20 07:55", netGmv: 558, cost: 10.6, roi: 5.2, totalGmv: 604, eventType: "投放动作" },
    { time: "06/20 08:00", netGmv: 642, cost: 12.2, roi: 5, totalGmv: 686, eventType: "" },
    { time: "06/20 08:05", netGmv: 552, cost: 10.6, roi: 4.9, totalGmv: 598, eventType: "" },
    { time: "06/20 08:10", netGmv: 548, cost: 10.7, roi: 4.8, totalGmv: 592, eventType: "" },
    { time: "06/20 08:15", netGmv: 468, cost: 8.8, roi: 5.2, totalGmv: 516, eventType: "调控动作" },
    { time: "06/20 08:20", netGmv: 672, cost: 12.6, roi: 5.3, totalGmv: 718, eventType: "" },
    { time: "06/20 08:25", netGmv: 698, cost: 13.1, roi: 5.4, totalGmv: 742, eventType: "" },
    { time: "06/20 08:30", netGmv: 616, cost: 9.6, roi: 6.1, totalGmv: 662, eventType: "调控动作" },
    { time: "06/20 08:35", netGmv: 624, cost: 11.2, roi: 5.7, totalGmv: 674, eventType: "调控动作" },
    { time: "06/20 08:40", netGmv: 592, cost: 9.4, roi: 6.2, totalGmv: 648, eventType: "" },
    { time: "06/20 08:45", netGmv: 532, cost: 10.5, roi: 5, totalGmv: 586, eventType: "调控动作" },
    { time: "06/20 08:50", netGmv: 752, cost: 14.3, roi: 5.4, totalGmv: 806, eventType: "投放动作" },
    { time: "06/20 08:55", netGmv: 684, cost: 17.7, roi: 4.1, totalGmv: 744, eventType: "" },
    { time: "06/20 09:00", netGmv: 568, cost: 10.4, roi: 5.5, totalGmv: 612, eventType: "" },
    { time: "06/20 09:05", netGmv: 646, cost: 12, roi: 5.3, totalGmv: 694, eventType: "" },
    { time: "06/20 09:10", netGmv: 252, cost: 5.1, roi: 4.8, totalGmv: 296, eventType: "" },
  ],

  sections: {
    channel: {
      title: "成交渠道构成",
      actionLabel: "↯ 观看次数",
      centerLabel: "成交金额",
    },
    funnel: {
      title: "直播间核心漏斗",
    },
    comments: {
      title: "直播实时评论",
      actionLabel: "↯ 直播画面",
    },
  },

  channelComposition: [
    { channelName: "直播推荐", value: 4357.58, percent: 60.09, color: "#d8e2ff" },
    { channelName: "短视频及图文引流", value: 1300.49, percent: 17.94, color: "#9fb7ff" },
    { channelName: "个人主页及店铺&橱窗", value: 610.46, percent: 8.42, color: "#7da0ff" },
    { channelName: "抖音商城推荐", value: 539.45, percent: 7.44, color: "#5d83ef" },
    { channelName: "头条西瓜", value: 266.08, percent: 3.67, color: "#4368dc" },
  ],

  funnelData: [
    { name: "直播间整体曝光次数", value: 38466, conversionRate: 9.22 },
    { name: "直播间观看次数", value: 3547, conversionRate: 69.24 },
    { name: "商品点击次数", value: 2456, conversionRate: 3.58 },
    { name: "成交订单数", value: 88, conversionRate: 2.48 },
  ],

  comments: [
    { user: "凡***", content: "海口两套运费不减一个吗", time: "09:11", tag: "物流问题" },
    { user: "介***", content: "一号链接和二号有什么区别", time: "09:10", tag: "商品咨询" },
    { user: "青岛外贸8号店", content: "有运费险，部分现货现发！！！", time: "09:09", tag: "店铺回复" },
    { user: "叶***", content: "身高155，体重115穿多大", time: "09:08", tag: "尺码问题" },
    { user: "青岛外贸8号店", content: "@叶*** 亲 身高加10拍", time: "09:08", tag: "店铺回复" },
    { user: "青岛外贸8号店", content: "@口*** 170", time: "09:07", tag: "店铺回复" },
  ],
};
