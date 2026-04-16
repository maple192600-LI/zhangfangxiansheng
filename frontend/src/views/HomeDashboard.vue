<template>
  <div class="section">
    <div class="filters-bar">
      <div class="filter">日期：2026-04-10</div>
      <div class="filter">口径：全部法人</div>
      <div class="filter">状态：今日待办优先</div>
    </div>
    <div class="btn-row" style="margin-bottom: 14px;">
      <button class="btn btn-primary">进入工作台</button>
      <button class="btn btn-secondary">查看异常</button>
      <button class="btn btn-secondary">生成基础数据表</button>
    </div>
    <div class="metric-strip">
      <div class="metric">
        <div class="label">待处理任务</div>
        <div class="value">7</div>
        <div class="sub">未导入 2，待确认 3，待生成 2</div>
      </div>
      <div class="metric">
        <div class="label">异常提醒</div>
        <div class="value">4</div>
        <div class="sub">收付款异常 2，规则未命中 2</div>
      </div>
      <div class="metric">
        <div class="label">今日生成状态</div>
        <div class="value">未完成</div>
        <div class="sub">基础数据表未生成，日报未更新</div>
      </div>
      <div class="metric">
        <div class="label">重点账户变化</div>
        <div class="value">3 项</div>
        <div class="sub">适合快速看一眼，不做完整汇报</div>
      </div>
    </div>
  </div>

  <div class="dashboard-grid">
    <div class="section">
      <div class="section-title">
        <h3>今日处理进度</h3>
        <span>工作导向，不是汇报导向</span>
      </div>
      <div class="progress-list">
        <div class="progress-row"><div>网银导入</div><div class="progress-bar"><span style="width: 80%"></span></div><div>80%</div></div>
        <div class="progress-row"><div>手工流水</div><div class="progress-bar"><span style="width: 60%"></span></div><div>60%</div></div>
        <div class="progress-row"><div>异常处理</div><div class="progress-bar"><span style="width: 35%"></span></div><div>35%</div></div>
        <div class="progress-row"><div>基础数据表</div><div class="progress-bar"><span style="width: 0%"></span></div><div>0%</div></div>
        <div class="progress-row"><div>日报生成</div><div class="progress-bar"><span style="width: 0%"></span></div><div>0%</div></div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">
        <h3>系统提醒</h3>
        <span>轻量显示</span>
      </div>
      <div class="warning-list">
        <div class="warning warn">有 2 条手工流水未指定归属账户，暂不能进入基础数据表。</div>
        <div class="warning info">最近一次日报生成时间：2026-04-09 18:36。</div>
        <div class="warning ok">最近一次备份完成，时间：2026-04-10 08:10。</div>
      </div>
    </div>
  </div>

  <div class="dashboard-grid-2">
    <div class="section">
      <div class="section-title">
        <h3>待办追踪</h3>
        <span>按今天工作流拆开</span>
      </div>
      <div class="kanban">
        <div class="kanban-col">
          <h5>待导入</h5>
          <div class="task">中行流水 1 份待上传</div>
          <div class="task">农行流水 1 份待上传</div>
        </div>
        <div class="kanban-col">
          <h5>待确认</h5>
          <div class="task">手工流水 2 条待确认归属</div>
          <div class="task">1 条摘要待归类</div>
        </div>
        <div class="kanban-col">
          <h5>待生成</h5>
          <div class="task">基础数据表未生成</div>
          <div class="task">资金日报未生成</div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">
        <h3>快捷入口</h3>
        <span>只保留高频动作</span>
      </div>
      <div class="quick-grid">
        <div class="quick"><strong>进入工作台</strong><span>开始今天的导入、录入和维护</span></div>
        <div class="quick"><strong>查看基础数据表</strong><span>核对识别结果，确认是否可生成</span></div>
        <div class="quick"><strong>异常中心</strong><span>集中处理待确认和规则未命中</span></div>
        <div class="quick"><strong>OCR识别</strong><span>进入发票、合同、回单识别入口</span></div>
        <div class="quick"><strong>重点账户余额</strong><span>快速查看关键账户状态</span></div>
        <div class="quick"><strong>操作日志</strong><span>回看今天的主要动作</span></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './common.css';
</style>
