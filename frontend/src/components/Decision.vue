<template>
  <div class="decision-container">
    <div class="decision-header">
      <h2>决策管理</h2>
    </div>

    <!-- 操作面板 -->
    <div class="action-panel">
      <button class="btn btn-primary" @click="loadPendingTasks" :disabled="loading">
        {{ loading ? '加载中...' : '刷新列表' }}
      </button>
      <button 
        class="btn btn-success" 
        @click="executeDecisionHandler" 
        :disabled="loading || pendingTasks.length === 0"
      >
        {{ executing ? '处理中...' : '同意并执行决策' }}
      </button>
    </div>

    <!-- 执行结果展示 -->
    <div v-if="executionResult" class="result-panel">
      <div class="result-header">
        <h3>决策执行结果</h3>
        <button class="close-btn" @click="executionResult = null">×</button>
      </div>
      <div class="result-summary">
        <div class="summary-item">
          <span class="label">处理任务数</span>
          <span class="value">{{ executionResult.processed_count }}</span>
        </div>
        <div class="summary-item">
          <span class="label">可交易市场</span>
          <span class="value">{{ executionResult.summary?.tradable_markets || 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="label">账户资金</span>
          <span class="value">${{ (executionResult.summary?.gross_wealth || 0).toFixed(2) }}</span>
        </div>
      </div>
      <div v-if="executionResult.allocations?.length > 0" class="allocations-list">
        <h4>仓位分配详情（仅显示值得交易的市场）</h4>
        <div v-for="alloc in executionResult.allocations" :key="alloc.id" class="allocation-item">
          <div class="alloc-info">
            <span class="market-id">市场 #{{ alloc.id }}</span>
            <span :class="['side-badge', alloc.side.toLowerCase()]">{{ alloc.side }}</span>
          </div>
          <div class="alloc-details">
            <span>投入: ${{ alloc.dollars.toFixed(2) }}</span>
            <span>份额: {{ alloc.shares.toFixed(2) }}</span>
            <span>成本: {{ (alloc.cost * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>
      <div v-else-if="executionResult.processed_count > 0" class="no-trades-message">
        <p>📊 所有市场均不符合Kelly准则，暂无值得交易的机会</p>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">{{ error }}</div>

    <!-- 待决策任务列表 -->
    <div class="tasks-section">
      <div class="section-header">
        <h3>待决策任务</h3>
        <span class="count-badge">{{ pendingTasks.length }}</span>
      </div>

      <div v-if="pendingTasks.length === 0 && !loading" class="empty-state">
        <div class="empty-icon">🎯</div>
        <p>暂无待决策任务</p>
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

          <!-- 核心信息网格 -->
          <div class="core-info-grid">
            <!-- 概率对比卡片 -->
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
                </div>
              </div>
            </div>

            <!-- 市场信息卡片 -->
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

    <!-- 已完成决策列表 -->
    <div class="tasks-section">
      <div class="section-header">
        <h3>已完成决策</h3>
        <span class="count-badge">{{ finishedTasks.length }}</span>
      </div>

      <div v-if="finishedTasks.length === 0 && !loading" class="empty-state">
        <div class="empty-icon">✅</div>
        <p>暂无已完成的决策</p>
      </div>

      <div v-else class="tasks-list compact">
        <div v-for="task in finishedTasks" :key="task.id" class="task-card finished-card">
          <div class="finished-header">
            <div class="finished-left">
              <span class="task-id">任务 #{{ task.id }}</span>
              <span v-if="task.result?.decision === 'trade'" :class="['side-badge', task.result?.allocation?.side?.toLowerCase()]">
                {{ task.result?.allocation?.side }}
              </span>
              <span v-else class="side-badge skip">SKIP</span>
              <span v-if="task.result?.decision === 'trade'" class="finished-amount">
                ${{ task.result?.allocation?.dollars?.toFixed(2) }}
              </span>
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
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { getPendingDecisionTasks, executeDecision, getTasks } from '@/api/tasks'

export default {
  name: 'Decision',
  setup() {
    const pendingTasks = ref([])
    const finishedTasksRaw = ref([])
    const loading = ref(false)
    const executing = ref(false)
    const error = ref('')
    const executionResult = ref(null)

    // 计算属性：过滤掉skip的已完成任务
    const finishedTasks = computed(() => {
      return finishedTasksRaw.value.filter(task => {
        return task.result && task.result.decision === 'trade'
      })
    })

    // 加载待决策任务
    const loadPendingTasks = async () => {
      loading.value = true
      error.value = ''
      try {
        const res = await getPendingDecisionTasks()
        if (res && res.success) {
          pendingTasks.value = res.data.tasks || []
        } else {
          error.value = res?.message || '加载失败'
        }
      } catch (e) {
        error.value = e.response?.data?.message || '加载待决策任务失败'
      } finally {
        loading.value = false
      }
    }

    // 加载已完成决策任务
    const loadFinishedTasks = async () => {
      try {
        const res = await getTasks({
          stage: 'decision',
          status: 'finished',
          limit: 50
        })
        if (res && res.success) {
          finishedTasksRaw.value = res.data.tasks || []
        }
      } catch (e) {
        console.error('加载已完成决策任务失败:', e)
      }
    }

    // 执行决策
    const executeDecisionHandler = async () => {
      executing.value = true
      error.value = ''
      executionResult.value = null
      try {
        const res = await executeDecision()
        if (res && res.success) {
          executionResult.value = res.data
          // 刷新列表
          await loadPendingTasks()
          await loadFinishedTasks()
        } else {
          error.value = res?.message || '执行失败'
        }
      } catch (e) {
        error.value = e.response?.data?.message || '决策执行失败'
      } finally {
        executing.value = false
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

    // 自动刷新定时器
    let autoRefreshTimer = null

    // 全局刷新事件处理
    const handleGlobalRefresh = () => {
      loadPendingTasks()
      loadFinishedTasks()
    }

    onMounted(() => {
      loadPendingTasks()
      loadFinishedTasks()
      // 每30秒自动刷新一次
      autoRefreshTimer = setInterval(() => {
        loadPendingTasks()
        loadFinishedTasks()
      }, 30000)
      // 监听全局刷新事件
      window.addEventListener('global-refresh', handleGlobalRefresh)
    })

    onBeforeUnmount(() => {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer)
      }
      // 移除全局刷新事件监听
      window.removeEventListener('global-refresh', handleGlobalRefresh)
    })

    return {
      pendingTasks,
      finishedTasks,
      loading,
      executing,
      error,
      executionResult,
      loadPendingTasks,
      loadFinishedTasks,
      executeDecisionHandler,
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
.decision-container { padding: 20px; max-width: 1400px; margin: 0 auto; }
.decision-header { margin-bottom: 12px; }
.decision-header h2 { font-size: 18px; color: #333; margin: 0; }

.action-panel { display: flex; gap: 10px; margin-bottom: 20px; }
.btn { height: 40px; padding: 0 20px; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; transition: background 0.2s; }
.btn-primary { background: #20a53a; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1a8c31; }
.btn-success { background: #2196f3; color: #fff; }
.btn-success:hover:not(:disabled) { background: #1976d2; }
.btn:disabled { background: #ccc; cursor: not-allowed; }

.result-panel { background: #e8f5e9; border: 1px solid #4caf50; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.result-header h3 { color: #2e7d32; font-size: 16px; }
.close-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #666; }
.result-summary { display: flex; gap: 20px; margin-bottom: 15px; }
.summary-item { display: flex; flex-direction: column; }
.summary-item .label { font-size: 12px; color: #666; }
.summary-item .value { font-size: 18px; font-weight: 600; color: #333; }

.allocations-list h4 { font-size: 14px; margin-bottom: 10px; color: #2e7d32; }
.allocation-item { background: #fff; border-radius: 4px; padding: 10px; margin-bottom: 8px; }
.alloc-info { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
.market-id { font-weight: 600; }
.side-badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.side-badge.yes { background: #4caf50; color: #fff; }
.side-badge.no { background: #f44336; color: #fff; }
.alloc-details { display: flex; gap: 15px; font-size: 13px; color: #666; }

.no-trades-message { text-align: center; padding: 20px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; margin-top: 15px; }
.no-trades-message p { color: #856404; font-size: 14px; margin: 0; }

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
.core-info-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 15px; margin-bottom: 20px; }

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

/* 市场信息卡片 */
.market-info-card { grid-column: span 1; }
.market-details { display: flex; flex-direction: column; gap: 8px; }
.detail-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
.detail-label { font-size: 11px; color: #888; text-transform: uppercase; }
.detail-value { font-size: 14px; font-weight: 600; color: #333; }
.detail-value.small { font-size: 11px; font-weight: 400; color: #666; word-break: break-all; }

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

/* 已完成决策卡片 */
.tasks-list.compact { gap: 10px; }
.finished-card { padding: 12px 15px; border-left: 4px solid #2196f3; background: #fafafa; }
.finished-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.finished-left { display: flex; align-items: center; gap: 10px; }
.side-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.side-badge.yes { background: #4caf50; color: #fff; }
.side-badge.no { background: #f44336; color: #fff; }
.side-badge.skip { background: #999; color: #fff; }
.finished-amount { font-size: 14px; font-weight: 700; color: #333; }
.finished-question { font-size: 13px; color: #666; line-height: 1.4; }

.tasks-section { margin-bottom: 40px; }

/* 响应式 */
@media (max-width: 1200px) {
  .core-info-grid { grid-template-columns: 1fr; }
  .analysis-reasons { grid-template-columns: 1fr; }
}
</style>

