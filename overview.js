import { overviewData } from "./overviewData.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderRow(row) {
  return `
    <tr data-has-ad="${row.adCost === "¥0" ? "false" : "true"}">
      <td class="room-cell">
        <img class="room-thumb" src="${escapeHtml(row.thumbnail)}" alt="${escapeHtml(row.title)}" />
        <div class="room-copy">
          <strong>${escapeHtml(row.title)}</strong>
          <p><span class="account-avatar"></span>${escapeHtml(row.account)} <em>${escapeHtml(row.tag)}</em></p>
          <a href="#" class="problem-link">发现${escapeHtml(row.issueCount)}个导致流量下降的问题 ></a>
        </div>
      </td>
      <td class="time-cell">
        <strong>${escapeHtml(row.startedAt)}</strong>
        <span>${escapeHtml(row.duration)}</span>
      </td>
      <td>${escapeHtml(row.transactionAmount)}</td>
      <td>${escapeHtml(row.userPayAmount)}</td>
      <td>${escapeHtml(row.viewCount)}</td>
      <td>${escapeHtml(row.orderCount)}</td>
      <td>${escapeHtml(row.netOrderCount)}</td>
      <td>${escapeHtml(row.adCost)}</td>
      <td class="action-cell">
        <a href="#">诊断</a>
        <a href="#">详情</a>
        <a href="#">直播PK</a>
      </td>
    </tr>
  `;
}

function overviewTemplate(data) {
  return `
    <div class="overview-layout">
      <aside class="overview-sidebar">
        <div class="sidebar-title">
          <span class="sidebar-live-icon"></span>
          <strong>直播</strong>
        </div>
        <nav>
          <a class="active" href="/">直播概览及列表</a>
          <a href="/dashboard">直播复盘</a>
          <a href="#">主播分析</a>
          <a href="#">直播计划</a>
          <a href="#">直播对比</a>
        </nav>
      </aside>

      <header class="compass-header">
        <a class="compass-brand" href="/">
          <span class="compass-logo" aria-hidden="true"></span>
          <strong>抖音电商 · 罗盘</strong>
          <em>经营</em>
        </a>
        <nav class="compass-nav">
          <a href="#">首页</a>
          <a href="#">交易</a>
          <a class="active" href="#">直播</a>
          <a href="#">短视频</a>
          <a href="#">商品卡</a>
          <span></span>
          <a href="#">搜索</a>
          <a href="#">达人</a>
          <a href="#">商品</a>
          <a href="#">营销</a>
          <span></span>
          <a href="#">体验</a>
          <a href="#">人群</a>
          <a href="#">市场</a>
          <span></span>
          <a href="#">数据工厂</a>
        </nav>
        <div class="header-actions">
          <label class="search-box">
            <input aria-label="搜索" />
            <span></span>
          </label>
          <button class="header-icon" type="button" aria-label="消息"></button>
          <button class="header-icon user" type="button" aria-label="账号"></button>
          <button class="header-icon help" type="button" aria-label="帮助"></button>
          <button class="store-switch" type="button"><span></span>${escapeHtml(data.shopName)}</button>
        </div>
      </header>

      <main class="overview-main">
        <section class="upgrade-banner">
          <div class="banner-illustration">
            <span></span>
          </div>
          <p>直播列表新升级，新增直播概览总数据，还可选择具体的自营/合作账号查看对应直播列表及大屏，一键掌握自己及同行直播情况！</p>
        </section>

        <section class="hero-overview">
          <div class="hero-heading">
            <h1>直播概览</h1>
            <p>近一场直播</p>
            <span>直播时间：${escapeHtml(data.recentLive.time)}</span>
          </div>
          <div class="recent-room">
            <img src="${escapeHtml(data.recentLive.thumbnail)}" alt="${escapeHtml(data.recentLive.title)}" />
            <div>
              <strong>${escapeHtml(data.recentLive.title)}</strong>
              <p><span class="account-avatar"></span>${escapeHtml(data.recentLive.account)} <i></i></p>
            </div>
          </div>
          <dl class="recent-metrics">
            <div>
              <dt>${escapeHtml(data.recentLive.userPayAmount)}</dt>
              <dd>用户支付金额</dd>
            </div>
            <div>
              <dt>${escapeHtml(data.recentLive.viewCount)}</dt>
              <dd>观看次数</dd>
            </div>
            <div>
              <dt>${escapeHtml(data.recentLive.thousandPayAmount)}</dt>
              <dd>千次观看用户支付金额</dd>
            </div>
          </dl>
          <a class="detail-link" href="/dashboard">查看详情 ></a>
          <button class="hero-warning" type="button" data-action="toggle-warning">
            <span></span>
            <strong>直播间存在<em>${escapeHtml(data.recentLive.issueCount)}个</em>会导致流量下降的因素，优化后可获取更多流量</strong>
            <i>展开⌃</i>
          </button>
          <div class="warning-detail" hidden>
            重点关注成交转化、投放消耗和观看承接指标。建议优先复盘流量下滑时段，并对商品讲解节奏做二次标记。
          </div>
        </section>

        <section class="list-panel">
          <div class="panel-tabs">
            <button type="button">数据概览</button>
            <button class="active" type="button">直播间列表</button>
          </div>
          <div class="filter-row">
            <button class="select-like" type="button">自营账号</button>
            <button class="select-like wide" type="button">请选择账号</button>
            <label class="ad-only"><input type="checkbox" data-action="ad-filter" /> 仅看投放直播间</label>
            <div class="range-tabs">
              <button type="button">实时</button>
              <button type="button">近1天</button>
              <button type="button">近7天</button>
              <button class="active" type="button">近30天</button>
              <button type="button">自定义</button>
              <button type="button">更多</button>
            </div>
            <button class="outline-action" type="button"><span class="download-icon"></span>下载明细</button>
            <button class="outline-action" type="button">指标配置</button>
          </div>
          <div class="live-table-wrap">
            <table class="live-table">
              <thead>
                <tr>
                  <th>直播间</th>
                  <th>开播时间 <span class="sort"></span></th>
                  <th>直播间成交金额 <span class="sort"></span></th>
                  <th>直播间用户支付金额 <span class="sort active"></span></th>
                  <th>直播间观看次数 <span class="hint">?</span> <span class="sort"></span></th>
                  <th>直播间成交订单数 <span class="hint">?</span> <span class="sort"></span></th>
                  <th>净成交订单数 <span class="hint">?</span> <span class="sort"></span></th>
                  <th>投放消耗（店铺被投放）</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                ${data.rows.map(renderRow).join("")}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <button class="ai-float" type="button"><span></span><strong>AI</strong><em>待办</em></button>
    </div>
  `;
}

function bindOverviewEvents(root) {
  root.querySelectorAll(".range-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      root.querySelectorAll(".range-tabs button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });

  root.querySelector("[data-action='toggle-warning']")?.addEventListener("click", () => {
    const detail = root.querySelector(".warning-detail");
    if (!detail) return;
    detail.hidden = !detail.hidden;
  });

  root.querySelector("[data-action='ad-filter']")?.addEventListener("change", (event) => {
    root.querySelectorAll(".live-table tbody tr").forEach((row) => {
      row.hidden = event.target.checked && row.dataset.hasAd !== "true";
    });
  });
}

export function renderOverview(root) {
  document.body.className = "overview-page";
  document.title = "直播概览及列表复刻";
  root.innerHTML = overviewTemplate(overviewData);
  bindOverviewEvents(root);
}
