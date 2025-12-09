<template>
  <div class="decision-container">
    <div class="decision-header">
      <h2>决策管理</h2>
      <p class="header-desc">审核待决策任务，执行仓位分配</p>
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
            <span class="task-id">任务 #{{ task.id }}</span>
            <span class="task-time">{{ formatTime(task.create_time) }}</span>
          </div>

          <!-- 市场信息 -->
          <div class="market-info" v-if="task.metadata?.market">
            <h4 class="market-question">{{ task.metadata.market.question }}</h4>
            <div class="market-meta">
              <span class="meta-item">
                <span class="meta-label">市场ID:</span>
                {{ task.metadata.market.id }}
              </span>
              <span class="meta-item">
                <span class="meta-label">流动性:</span>
                ${{ formatNumber(task.metadata.market.liquidity) }}
              </span>
              <span class="meta-item">
                <span class="meta-label">交易量:</span>
                ${{ formatNumber(task.metadata.market.volume) }}
              </span>
            </div>
            <!-- 当前价格 -->
            <div class="price-info">
              <span class="price-label">当前价格:</span>
              <span class="price-yes">YES {{ formatPrice(task.metadata.market.outcome_prices, 0) }}</span>
              <span class="price-no">NO {{ formatPrice(task.metadata.market.outcome_prices, 1) }}</span>
            </div>
          </div>

          <!-- 分析结果 -->
          <div class="analysis-info" v-if="task.metadata?.analysis">
            <h5>AI分析结果</h5>
            <div class="analysis-probs">
              <div class="prob-item">
                <span class="prob-label">预测概率 (p)</span>
                <span class="prob-value">{{ (task.metadata.analysis.p * 100).toFixed(1) }}%</span>
              </div>
              <div class="prob-item">
                <span class="prob-label">风险因子 (a)</span>
                <span class="prob-value">{{ (task.metadata.analysis.a * 100).toFixed(1) }}%</span>
              </div>
              <div class="prob-item" v-if="task.metadata.analysis.n">
                <span class="prob-label">否定概率 (n)</span>
                <span class="prob-value">{{ (task.metadata.analysis.n * 100).toFixed(1) }}%</span>
              </div>
            </div>
            <!-- 支持理由 -->
            <div v-if="task.metadata.analysis.reasons_y?.length" class="reasons">
              <span class="reasons-label">支持理由:</span>
              <ul>
                <li v-for="(reason, idx) in task.metadata.analysis.reasons_y" :key="idx">{{ reason }}</li>
              </ul>
            </div>
            <!-- 反对理由 -->
            <div v-if="task.metadata.analysis.reasons_n?.length" class="reasons">
              <span class="reasons-label">反对理由:</span>
              <ul>
                <li v-for="(reason, idx) in task.metadata.analysis.reasons_n" :key="idx">{{ reason }}</li>
              </ul>
            </div>
          </div>

          <!-- 标签 -->
          <div class="marks" v-if="task.metadata?.marks?.length">
            <span v-for="mark in task.metadata.marks" :key="mark" class="mark-tag">{{ mark }}</span>
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

      <div v-else class="tasks-list">
        <div v-for="task in finishedTasks" :key="task.id" class="task-card finished-card">
          <!-- 任务头部 -->
          <div class="task-header">
            <span class="task-id">任务 #{{ task.id }}</span>
            <span class="task-time">{{ formatTime(task.update_time) }}</span>
          </div>

          <!-- 市场信息 -->
          <div class="market-info" v-if="task.metadata?.market">
            <h4 class="market-question">{{ task.metadata.market.question }}</h4>
            <div class="market-meta">
              <span class="meta-item">
                <span class="meta-label">市场ID:</span>
                {{ task.metadata.market.id }}
              </span>
              <span class="meta-item">
                <span class="meta-label">流动性:</span>
                ${{ formatNumber(task.metadata.market.liquidity) }}
              </span>
              <span class="meta-item">
                <span class="meta-label">交易量:</span>
                ${{ formatNumber(task.metadata.market.volume) }}
              </span>
            </div>
            <!-- 当前价格 -->
            <div class="price-info">
              <span class="price-label">当前价格:</span>
              <span class="price-yes">YES {{ formatPrice(task.metadata.market.outcome_prices, 0) }}</span>
              <span class="price-no">NO {{ formatPrice(task.metadata.market.outcome_prices, 1) }}</span>
            </div>
          </div>

          <!-- 分析结果 -->
          <div class="analysis-info" v-if="task.metadata?.analysis">
            <h5>AI分析结果</h5>
            <div class="analysis-probs">
              <div class="prob-item">
                <span class="prob-label">预测概率 (p)</span>
                <span class="prob-value">{{ (task.metadata.analysis.p * 100).toFixed(1) }}%</span>
              </div>
              <div class="prob-item">
                <span class="prob-label">风险因子 (a)</span>
                <span class="prob-value">{{ (task.metadata.analysis.a * 100).toFixed(1) }}%</span>
              </div>
              <div class="prob-item" v-if="task.metadata.analysis.n">
                <span class="prob-label">否定概率 (n)</span>
                <span class="prob-value">{{ (task.metadata.analysis.n * 100).toFixed(1) }}%</span>
              </div>
            </div>
            <!-- 支持理由 -->
            <div v-if="task.metadata.analysis.reasons_y?.length" class="reasons">
              <span class="reasons-label">支持理由:</span>
              <ul>
                <li v-for="(reason, idx) in task.metadata.analysis.reasons_y" :key="idx">{{ reason }}</li>
              </ul>
            </div>
            <!-- 反对理由 -->
            <div v-if="task.metadata.analysis.reasons_n?.length" class="reasons">
              <span class="reasons-label">反对理由:</span>
              <ul>
                <li v-for="(reason, idx) in task.metadata.analysis.reasons_n" :key="idx">{{ reason }}</li>
              </ul>
            </div>
          </div>

          <!-- 决策结果 -->
          <div class="decision-result" v-if="task.result">
            <h5>决策结果</h5>
            <div v-if="task.result.decision === 'trade'" class="trade-decision">
              <div class="decision-header-info">
                <span :class="['decision-badge', task.result.allocation.side.toLowerCase()]">
                  {{ task.result.allocation.side }}
                </span>
                <span class="decision-score">评分: {{ task.result.allocation.score?.toFixed(4) || 'N/A' }}</span>
              </div>
              <div class="allocation-details-grid">
                <div class="detail-item">
                  <span class="detail-label">投入金额</span>
                  <span class="detail-value">${{ task.result.allocation.dollars?.toFixed(2) || '0.00' }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">份额</span>
                  <span class="detail-value">{{ task.result.allocation.shares?.toFixed(2) || '0.00' }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">成本</span>
                  <span class="detail-value">{{ (task.result.allocation.cost * 100)?.toFixed(1) || '0.0' }}%</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">仓位占比</span>
                  <span class="detail-value">{{ (task.result.allocation.fraction_of_gross * 100)?.toFixed(2) || '0.00' }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 标签 -->
          <div class="marks" v-if="task.metadata?.marks?.length">
            <span v-for="mark in task.metadata.marks" :key="mark" class="mark-tag">{{ mark }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
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

    // 格式化价格
    const formatPrice = (pricesStr, index) => {
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

    onMounted(() => {
      loadPendingTasks()
      loadFinishedTasks()
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
      formatPrice
    }
  }
}
</script>

<style scoped>
.decision-container { padding: 20px; }
.decision-header { margin-bottom: 20px; }
.decision-header h2 { font-size: 20px; color: #333; margin-bottom: 5px; }
.header-desc { color: #666; font-size: 13px; }

.action-panel { display: flex; gap: 10px; margin-bottom: 20px; }
.btn { height: 40px; padding: 0 20px; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
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
.section-header h3 { font-size: 16px; color: #333; }
.count-badge { padding: 2px 8px; background: #20a53a; color: #fff; border-radius: 12px; font-size: 12px; }

.empty-state { text-align: center; padding: 60px 20px; background: #fff; border: 1px solid #ddd; border-radius: 8px; }
.empty-icon { font-size: 48px; margin-bottom: 15px; }
.empty-state p { color: #666; }

.tasks-list { display: flex; flex-direction: column; gap: 15px; }
.task-card { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 15px; }
.task-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
.task-id { font-weight: 600; color: #333; }
.task-time { font-size: 12px; color: #999; }

.market-info { margin-bottom: 15px; }
.market-question { font-size: 15px; color: #333; margin-bottom: 10px; line-height: 1.4; }
.market-meta { display: flex; gap: 15px; font-size: 13px; margin-bottom: 8px; }
.meta-item { color: #666; }
.meta-label { color: #999; }
.price-info { display: flex; gap: 15px; font-size: 13px; }
.price-label { color: #999; }
.price-yes { color: #4caf50; font-weight: 600; }
.price-no { color: #f44336; font-weight: 600; }

.analysis-info { background: #f5f5f5; border-radius: 6px; padding: 12px; margin-bottom: 10px; }
.analysis-info h5 { font-size: 13px; margin-bottom: 8px; color: #666; }
.analysis-probs { display: flex; gap: 20px; margin-bottom: 10px; }
.prob-item { display: flex; flex-direction: column; }
.prob-label { font-size: 11px; color: #999; }
.prob-value { font-size: 16px; font-weight: 600; color: #333; }

.reasons { margin-top: 8px; }
.reasons-label { font-size: 12px; color: #666; }
.reasons ul { margin: 5px 0 0 20px; padding: 0; }
.reasons li { font-size: 12px; color: #555; margin-bottom: 3px; }

.marks { display: flex; gap: 6px; flex-wrap: wrap; }
.mark-tag { padding: 2px 8px; background: #e3f2fd; color: #1976d2; border-radius: 4px; font-size: 12px; }

/* 已完成决策卡片样式 */
.finished-card { border-left: 4px solid #4caf50; background: #fafafa; }

.decision-result { background: #e8f5e9; border-radius: 6px; padding: 12px; margin-bottom: 10px; }
.decision-result h5 { font-size: 13px; margin-bottom: 10px; color: #2e7d32; }

.trade-decision { }
.decision-header-info { display: flex; align-items: center; gap: 15px; margin-bottom: 12px; }
.decision-badge { padding: 4px 12px; border-radius: 4px; font-size: 13px; font-weight: 600; }
.decision-badge.yes { background: #4caf50; color: #fff; }
.decision-badge.no { background: #f44336; color: #fff; }
.decision-score { font-size: 13px; color: #666; }

.allocation-details-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.detail-item { display: flex; flex-direction: column; }
.detail-label { font-size: 11px; color: #666; margin-bottom: 2px; }
.detail-value { font-size: 15px; font-weight: 600; color: #2e7d32; }

.tasks-section { margin-bottom: 30px; }
</style>

