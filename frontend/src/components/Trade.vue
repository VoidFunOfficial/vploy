<template>
  <div class="trade-container">
    <div class="trade-header">
      <h2>交易管理</h2>
      <p class="header-desc">审核待交易任务，执行市场交易</p>
    </div>

    <!-- 操作面板 -->
    <div class="action-panel">
      <button class="btn btn-primary" @click="loadPendingTasks" :disabled="loading">
        {{ loading ? '加载中...' : '刷新列表' }}
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">{{ error }}</div>

    <!-- 待交易任务列表 -->
    <div class="tasks-section">
      <div class="section-header">
        <h3>待交易任务</h3>
        <span class="count-badge">{{ pendingTasks.length }}</span>
      </div>

      <div v-if="pendingTasks.length === 0 && !loading" class="empty-state">
        <div class="empty-icon">💱</div>
        <p>暂无待交易任务</p>
      </div>

      <div v-else class="tasks-list">
        <div v-for="task in pendingTasks" :key="task.id" class="task-card">
          <!-- 任务头部 -->
          <div class="task-header">
            <div class="task-header-left">
              <span class="task-id">任务 #{{ task.id }}</span>
              <span v-if="task.metadata?.marks?.length" class="marks-inline">
                <span v-for="mark in task.metadata.marks" :key="mark" class="mark-tag">{{ mark }}</span>
              </span>
            </div>
            <span class="task-time">{{ formatTime(task.create_time) }}</span>
          </div>

          <!-- 市场问题 -->
          <div class="market-question" v-if="task.metadata?.market">
            {{ task.metadata.market.question }}
          </div>

          <!-- 核心信息卡片 -->
          <div class="core-info-grid">
            <!-- 市场概率 vs AI预测 -->
            <div class="info-card probability-card">
              <div class="card-title">概率对比</div>
              <div class="probability-comparison">
                <div class="prob-column">
                  <div class="prob-header">YES</div>
                  <div class="prob-row">
                    <span class="prob-label">市场</span>
                    <span class="prob-value market">{{ formatPricePercent(task.metadata?.market?.outcome_prices, 0) }}</span>
                  </div>
                  <div class="prob-row">
                    <span class="prob-label">预测</span>
                    <span class="prob-value predict">{{ formatPercent(task.metadata?.analysis?.p) }}</span>
                  </div>
                  <div class="prob-row diff">
                    <span class="prob-label">差值</span>
                    <span :class="['prob-value', getDiffClass(calculateDiff(task.metadata?.analysis?.p, task.metadata?.market?.outcome_prices, 0))]">
                      {{ formatDiff(calculateDiff(task.metadata?.analysis?.p, task.metadata?.market?.outcome_prices, 0)) }}
                    </span>
                  </div>
                  <!-- 交易操作 -->
                  <div v-if="task.result?.decision === 'trade' && task.result?.allocation?.side === 'YES'" class="trade-action">
                    <div class="action-badge buy">买入 YES</div>
                    <div class="action-amount">${{ task.result.allocation.dollars?.toFixed(2) }}</div>
                  </div>
                  <div v-else-if="task.result?.decision === 'skip'" class="trade-action">
                    <div class="action-badge skip">不交易</div>
                  </div>
                </div>

                <div class="prob-column">
                  <div class="prob-header">NO</div>
                  <div class="prob-row">
                    <span class="prob-label">市场</span>
                    <span class="prob-value market">{{ formatPricePercent(task.metadata?.market?.outcome_prices, 1) }}</span>
                  </div>
                  <div class="prob-row">
                    <span class="prob-label">预测</span>
                    <span class="prob-value predict">{{ formatPercent(task.metadata?.analysis?.n) }}</span>
                  </div>
                  <div class="prob-row diff">
                    <span class="prob-label">差值</span>
                    <span :class="['prob-value', getDiffClass(calculateDiff(task.metadata?.analysis?.n, task.metadata?.market?.outcome_prices, 1))]">
                      {{ formatDiff(calculateDiff(task.metadata?.analysis?.n, task.metadata?.market?.outcome_prices, 1)) }}
                    </span>
                  </div>
                  <!-- 交易操作 -->
                  <div v-if="task.result?.decision === 'trade' && task.result?.allocation?.side === 'NO'" class="trade-action">
                    <div class="action-badge buy">买入 NO</div>
                    <div class="action-amount">${{ task.result.allocation.dollars?.toFixed(2) }}</div>
                  </div>
                  <div v-else-if="task.result?.decision === 'skip'" class="trade-action">
                    <div class="action-badge skip">不交易</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 交易详情 -->
            <div class="info-card trade-details-card" v-if="task.result?.decision === 'trade'">
              <div class="card-title">交易详情</div>
              <div class="trade-details">
                <div class="detail-row">
                  <span class="detail-label">方向</span>
                  <span :class="['detail-value', 'side-' + task.result.allocation.side.toLowerCase()]">
                    {{ task.result.allocation.side }}
                  </span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">投入</span>
                  <span class="detail-value">${{ task.result.allocation.dollars?.toFixed(2) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">份额</span>
                  <span class="detail-value">{{ task.result.allocation.shares?.toFixed(2) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">成本</span>
                  <span class="detail-value">{{ (task.result.allocation.cost * 100)?.toFixed(1) }}%</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">仓位占比</span>
                  <span class="detail-value">{{ (task.result.allocation.fraction_of_gross * 100)?.toFixed(2) }}%</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">评分</span>
                  <span class="detail-value">{{ task.result.allocation.score?.toFixed(4) }}</span>
                </div>
              </div>
            </div>

            <!-- 市场信息 -->
            <div class="info-card market-info-card">
              <div class="card-title">市场信息</div>
              <div class="market-details">
                <div class="detail-row">
                  <span class="detail-label">市场ID</span>
                  <span class="detail-value small">{{ task.metadata?.market?.id }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">流动性</span>
                  <span class="detail-value">${{ formatNumber(task.metadata?.market?.liquidity) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">交易量</span>
                  <span class="detail-value">${{ formatNumber(task.metadata?.market?.volume) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">风险因子</span>
                  <span class="detail-value">{{ formatPercent(task.metadata?.analysis?.a) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- AI分析理由 -->
          <div class="analysis-reasons" v-if="task.metadata?.analysis">
            <div class="reasons-section" v-if="task.metadata.analysis.reasons_y?.length">
              <div class="reasons-header">
                <span class="reasons-icon">✓</span>
                <span class="reasons-title">支持理由</span>
              </div>
              <ul class="reasons-list">
                <li v-for="(reason, idx) in task.metadata.analysis.reasons_y" :key="idx">{{ reason }}</li>
              </ul>
            </div>
            <div class="reasons-section" v-if="task.metadata.analysis.reasons_n?.length">
              <div class="reasons-header">
                <span class="reasons-icon">✗</span>
                <span class="reasons-title">反对理由</span>
              </div>
              <ul class="reasons-list">
                <li v-for="(reason, idx) in task.metadata.analysis.reasons_n" :key="idx">{{ reason }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 已完成交易列表 -->
    <div class="tasks-section">
      <div class="section-header">
        <h3>已完成交易</h3>
        <span class="count-badge finished">{{ finishedTasks.length }}</span>
      </div>

      <div v-if="finishedTasks.length === 0 && !loading" class="empty-state">
        <div class="empty-icon">✅</div>
        <p>暂无已完成的交易</p>
      </div>

      <div v-else class="tasks-list compact">
        <div v-for="task in finishedTasks" :key="task.id" class="task-card finished-card">
          <div class="finished-header">
            <div class="finished-left">
              <span class="task-id">任务 #{{ task.id }}</span>
              <span :class="['side-badge', task.result?.allocation?.side?.toLowerCase()]">
                {{ task.result?.allocation?.side }}
              </span>
              <span class="finished-amount">${{ task.result?.allocation?.dollars?.toFixed(2) }}</span>
            </div>
            <span class="task-time">{{ formatTime(task.update_time) }}</span>
          </div>
          <div class="finished-question">{{ task.metadata?.market?.question }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { getPendingTradeTasks, getTasks } from '@/api/tasks'

export default {
  name: 'Trade',
  setup() {
    const pendingTasks = ref([])
    const finishedTasks = ref([])
    const loading = ref(false)
    const error = ref('')

    // 加载待交易任务
    const loadPendingTasks = async () => {
      loading.value = true
      error.value = ''
      try {
        const res = await getPendingTradeTasks()
        if (res && res.success) {
          pendingTasks.value = res.data.tasks || []
        } else {
          error.value = res?.message || '加载失败'
        }
      } catch (e) {
        error.value = e.response?.data?.message || '加载待交易任务失败'
      } finally {
        loading.value = false
      }
    }

    // 加载已完成交易任务
    const loadFinishedTasks = async () => {
      try {
        const res = await getTasks({
          stage: 'trade',
          status: 'finished',
          limit: 50
        })
        if (res && res.success) {
          finishedTasks.value = res.data.tasks || []
        }
      } catch (e) {
        console.error('加载已完成交易任务失败:', e)
      }
    }

    // 格式化时间
    const formatTime = (timeStr) => {
      if (!timeStr) return '-'
      try {
        const date = new Date(timeStr)
        return date.toLocaleString('zh-CN')
      } catch {
        return timeStr
      }
    }

    // 格式化数字
    const formatNumber = (val) => {
      if (!val) return '0'
      const num = parseFloat(val)
      if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M'
      if (num >= 1000) return (num / 1000).toFixed(2) + 'K'
      return num.toFixed(2)
    }

    // 格式化价格为百分比
    const formatPricePercent = (pricesStr, index) => {
      try {
        let prices = pricesStr
        if (typeof pricesStr === 'string') {
          prices = JSON.parse(pricesStr)
        }
        return (parseFloat(prices[index]) * 100).toFixed(1) + '%'
      } catch {
        return '-'
      }
    }

    // 格式化百分比
    const formatPercent = (value) => {
      if (value === null || value === undefined) return '-'
      return (value * 100).toFixed(1) + '%'
    }

    // 计算差值 (预测概率 - 市场概率)
    const calculateDiff = (predictProb, pricesStr, index) => {
      try {
        if (predictProb === null || predictProb === undefined) return null
        let prices = pricesStr
        if (typeof pricesStr === 'string') {
          prices = JSON.parse(pricesStr)
        }
        const marketProb = parseFloat(prices[index])
        return predictProb - marketProb
      } catch {
        return null
      }
    }

    // 格式化差值
    const formatDiff = (diff) => {
      if (diff === null || diff === undefined) return '-'
      const sign = diff >= 0 ? '+' : ''
      return sign + (diff * 100).toFixed(1) + '%'
    }

    // 获取差值的CSS类
    const getDiffClass = (diff) => {
      if (diff === null || diff === undefined) return ''
      if (diff > 0.05) return 'positive-high'
      if (diff > 0) return 'positive'
      if (diff < -0.05) return 'negative-high'
      if (diff < 0) return 'negative'
      return 'neutral'
    }

    onMounted(() => {
      loadPendingTasks()
      loadFinishedTasks()
    })

    return {
      pendingTasks,
      finishedTasks,
      loading,
      error,
      loadPendingTasks,
      formatTime,
      formatNumber,
      formatPricePercent,
      formatPercent,
      calculateDiff,
      formatDiff,
      getDiffClass
    }
  }
}
</script>

<style scoped>
.trade-container { padding: 20px; max-width: 1400px; margin: 0 auto; }
.trade-header { margin-bottom: 20px; }
.trade-header h2 { font-size: 20px; color: #333; margin-bottom: 5px; }
.header-desc { color: #666; font-size: 13px; }

.action-panel { display: flex; gap: 10px; margin-bottom: 20px; }
.btn { height: 40px; padding: 0 20px; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; transition: background 0.2s; }
.btn-primary { background: #20a53a; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1a8c31; }
.btn:disabled { background: #ccc; cursor: not-allowed; }

.error-message { padding: 12px 15px; background: #ffebee; border: 1px solid #ef5350; border-radius: 6px; color: #c62828; margin-bottom: 20px; }

.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }
.section-header h3 { font-size: 16px; color: #333; margin: 0; }
.count-badge { padding: 3px 10px; background: #20a53a; color: #fff; border-radius: 12px; font-size: 12px; font-weight: 600; }
.count-badge.finished { background: #2196f3; }

.empty-state { text-align: center; padding: 60px 20px; background: #fff; border: 1px solid #ddd; border-radius: 8px; }
.empty-icon { font-size: 48px; margin-bottom: 15px; }
.empty-state p { color: #666; margin: 0; }

.tasks-list { display: flex; flex-direction: column; gap: 20px; }
.task-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }

/* 任务头部 */
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0; }
.task-header-left { display: flex; align-items: center; gap: 10px; }
.task-id { font-weight: 600; color: #333; font-size: 14px; }
.task-time { font-size: 12px; color: #999; }
.marks-inline { display: flex; gap: 6px; }
.mark-tag { padding: 2px 8px; background: #e3f2fd; color: #1976d2; border-radius: 4px; font-size: 11px; }

/* 市场问题 */
.market-question { font-size: 16px; font-weight: 500; color: #222; margin-bottom: 20px; line-height: 1.5; }

/* 核心信息网格 */
.core-info-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 15px; margin-bottom: 20px; }

/* 信息卡片 */
.info-card { background: #fafafa; border: 1px solid #e8e8e8; border-radius: 6px; padding: 15px; }
.card-title { font-size: 13px; font-weight: 600; color: #666; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }

/* 概率对比卡片 */
.probability-card { grid-column: span 1; }
.probability-comparison { display: flex; gap: 20px; }
.prob-column { flex: 1; }
.prob-header { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 10px; text-align: center; padding-bottom: 8px; border-bottom: 2px solid #e0e0e0; }
.prob-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
.prob-row.diff { margin-top: 4px; padding-top: 10px; border-top: 1px dashed #ddd; }
.prob-label { font-size: 11px; color: #888; text-transform: uppercase; }
.prob-value { font-size: 15px; font-weight: 600; }
.prob-value.market { color: #666; }
.prob-value.predict { color: #2196f3; }
.prob-value.positive { color: #4caf50; }
.prob-value.positive-high { color: #2e7d32; font-weight: 700; }
.prob-value.negative { color: #f44336; }
.prob-value.negative-high { color: #c62828; font-weight: 700; }
.prob-value.neutral { color: #999; }

/* 交易操作 */
.trade-action { margin-top: 12px; padding-top: 12px; border-top: 1px solid #e0e0e0; text-align: center; }
.action-badge { display: inline-block; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.action-badge.buy { background: #4caf50; color: #fff; }
.action-badge.skip { background: #999; color: #fff; }
.action-amount { font-size: 16px; font-weight: 700; color: #333; }

/* 交易详情卡片 */
.trade-details-card { grid-column: span 1; }
.trade-details { display: flex; flex-direction: column; gap: 8px; }
.detail-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
.detail-label { font-size: 11px; color: #888; text-transform: uppercase; }
.detail-value { font-size: 14px; font-weight: 600; color: #333; }
.detail-value.small { font-size: 11px; font-weight: 400; color: #666; word-break: break-all; }
.detail-value.side-yes { color: #4caf50; }
.detail-value.side-no { color: #f44336; }

/* 市场信息卡片 */
.market-info-card { grid-column: span 1; }
.market-details { display: flex; flex-direction: column; gap: 8px; }

/* AI分析理由 */
.analysis-reasons { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.reasons-section { background: #f9f9f9; border-left: 3px solid #ddd; border-radius: 4px; padding: 12px; }
.reasons-section:first-child { border-left-color: #4caf50; }
.reasons-section:last-child { border-left-color: #f44336; }
.reasons-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.reasons-icon { font-size: 16px; font-weight: 700; }
.reasons-title { font-size: 13px; font-weight: 600; color: #555; }
.reasons-list { margin: 0; padding-left: 20px; }
.reasons-list li { font-size: 12px; color: #666; line-height: 1.6; margin-bottom: 6px; }

/* 已完成交易卡片 */
.tasks-list.compact { gap: 10px; }
.finished-card { padding: 12px 15px; border-left: 4px solid #2196f3; background: #fafafa; }
.finished-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.finished-left { display: flex; align-items: center; gap: 10px; }
.side-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.side-badge.yes { background: #4caf50; color: #fff; }
.side-badge.no { background: #f44336; color: #fff; }
.finished-amount { font-size: 14px; font-weight: 700; color: #333; }
.finished-question { font-size: 13px; color: #666; line-height: 1.4; }

.tasks-section { margin-bottom: 40px; }

/* 响应式 */
@media (max-width: 1200px) {
  .core-info-grid { grid-template-columns: 1fr; }
  .analysis-reasons { grid-template-columns: 1fr; }
}
</style>

