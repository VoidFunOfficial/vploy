<template>
  <div class="trade-container">
    <div class="header-actions mb-4">
      <div class="left">
        <h2>交易管理</h2>
      </div>
      <div class="right">
        <el-button type="primary" :loading="loading" :icon="Refresh" @click="loadPendingTasks">
          刷新列表
        </el-button>
      </div>
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-if="error"
      title="错误"
      type="error"
      :description="error"
      show-icon
      class="mb-4"
    />

    <!-- 待交易任务列表 -->
    <div class="tasks-section">
      <div class="section-header mb-3">
        <h3>待交易任务</h3>
        <el-tag type="success" effect="dark" round class="ml-2">{{ pendingTasks.length }}</el-tag>
      </div>

      <el-empty v-if="pendingTasks.length === 0 && !loading" description="暂无待交易任务" />

      <div v-else class="tasks-list">
        <el-card v-for="task in pendingTasks" :key="task.id" class="task-card mb-4" shadow="hover">
          <template #header>
            <div class="task-header">
              <div class="task-header-left">
                <span class="task-id">任务 #{{ task.id }}</span>
                <div v-if="task.metadata?.marks?.length" class="marks-inline ml-2">
                  <el-tag 
                    v-for="mark in task.metadata.marks" 
                    :key="mark" 
                    size="small" 
                    effect="plain"
                    class="mr-1"
                  >
                    {{ mark }}
                  </el-tag>
                </div>
              </div>
              <span class="task-time text-secondary">{{ formatTime(task.create_time) }}</span>
            </div>
          </template>

          <!-- 市场问题 -->
          <div class="market-question mb-4" v-if="task.metadata?.market">
            <h3>{{ task.metadata.market.question }}</h3>
          </div>

          <!-- 核心信息卡片 -->
          <el-row :gutter="20" class="mb-4">
            <!-- 市场概率 vs AI预测 -->
            <el-col :xs="24" :lg="12" class="mb-3">
              <el-card shadow="never" class="h-100">
                <template #header><div class="card-title">概率对比</div></template>
                <div class="probability-comparison">
                  <el-row :gutter="20">
                    <el-col :span="12" class="prob-column">
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
                      <div v-if="task.result?.decision === 'trade' && task.result?.allocation?.side === 'YES'" class="trade-action mt-3">
                        <el-tag type="success" effect="dark" class="mb-1">买入 YES</el-tag>
                        <div class="action-amount">${{ task.result.allocation.dollars?.toFixed(2) }}</div>
                      </div>
                      <div v-else-if="task.result?.decision === 'skip'" class="trade-action mt-3">
                        <el-tag type="info" effect="dark">不交易</el-tag>
                      </div>
                    </el-col>

                    <el-col :span="12" class="prob-column">
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
                      <div v-if="task.result?.decision === 'trade' && task.result?.allocation?.side === 'NO'" class="trade-action mt-3">
                        <el-tag type="danger" effect="dark" class="mb-1">买入 NO</el-tag>
                        <div class="action-amount">${{ task.result.allocation.dollars?.toFixed(2) }}</div>
                      </div>
                      <div v-else-if="task.result?.decision === 'skip'" class="trade-action mt-3">
                        <el-tag type="info" effect="dark">不交易</el-tag>
                      </div>
                    </el-col>
                  </el-row>
                </div>
              </el-card>
            </el-col>

            <!-- 交易详情 -->
            <el-col :xs="24" :sm="12" :lg="6" class="mb-3" v-if="task.result?.decision === 'trade'">
              <el-card shadow="never" class="h-100">
                <template #header><div class="card-title">交易详情</div></template>
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="方向">
                    <el-tag :type="task.result.allocation.side === 'YES' ? 'success' : 'danger'" size="small">
                      {{ task.result.allocation.side }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="投入">${{ task.result.allocation.dollars?.toFixed(2) }}</el-descriptions-item>
                  <el-descriptions-item label="份额">{{ task.result.allocation.shares?.toFixed(2) }}</el-descriptions-item>
                  <el-descriptions-item label="成本">{{ (task.result.allocation.cost * 100)?.toFixed(1) }}%</el-descriptions-item>
                  <el-descriptions-item label="仓位">{{ (task.result.allocation.fraction_of_gross * 100)?.toFixed(2) }}%</el-descriptions-item>
                  <el-descriptions-item label="评分">{{ task.result.allocation.score?.toFixed(4) }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>

            <!-- 市场信息 -->
            <el-col :xs="24" :sm="12" :lg="6" class="mb-3">
              <el-card shadow="never" class="h-100">
                <template #header><div class="card-title">市场信息</div></template>
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="ID">
                    <el-tooltip :content="task.metadata?.market?.id" placement="top">
                      <span class="text-truncate d-block" style="max-width: 100px;">{{ task.metadata?.market?.id }}</span>
                    </el-tooltip>
                  </el-descriptions-item>
                  <el-descriptions-item label="流动性">${{ formatNumber(task.metadata?.market?.liquidity) }}</el-descriptions-item>
                  <el-descriptions-item label="交易量">${{ formatNumber(task.metadata?.market?.volume) }}</el-descriptions-item>
                  <el-descriptions-item label="风险因子">{{ formatPercent(task.metadata?.analysis?.a) }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
          </el-row>

          <!-- AI分析理由 -->
          <div class="analysis-reasons" v-if="task.metadata?.analysis">
            <el-row :gutter="20">
              <el-col :span="12" v-if="task.metadata.analysis.reasons_y?.length">
                <el-alert title="支持理由" type="success" :closable="false" show-icon>
                  <ul class="reasons-list">
                    <li v-for="(reason, idx) in task.metadata.analysis.reasons_y" :key="idx">{{ reason }}</li>
                  </ul>
                </el-alert>
              </el-col>
              <el-col :span="12" v-if="task.metadata.analysis.reasons_n?.length">
                <el-alert title="反对理由" type="error" :closable="false" show-icon>
                  <ul class="reasons-list">
                    <li v-for="(reason, idx) in task.metadata.analysis.reasons_n" :key="idx">{{ reason }}</li>
                  </ul>
                </el-alert>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 已完成交易列表 -->
    <div class="tasks-section">
      <div class="section-header mb-3">
        <h3>已完成交易</h3>
        <el-tag type="primary" effect="dark" round class="ml-2">{{ finishedTasks.length }}</el-tag>
      </div>

      <el-empty v-if="finishedTasks.length === 0 && !loading" description="暂无已完成的交易" />

      <el-row v-else :gutter="20">
        <el-col :xs="24" :sm="12" :lg="8" v-for="task in finishedTasks" :key="task.id" class="mb-3">
          <el-card class="finished-card" shadow="hover" :body-style="{ padding: '15px' }">
            <div class="finished-header">
              <div class="finished-left">
                <span class="task-id">#{{ task.id }}</span>
                <el-tag 
                  :type="task.result?.allocation?.side === 'YES' ? 'success' : 'danger'" 
                  size="small" 
                  effect="dark"
                >
                  {{ task.result?.allocation?.side }}
                </el-tag>
                <span class="finished-amount">${{ task.result?.allocation?.dollars?.toFixed(2) }}</span>
              </div>
              <span class="task-time text-secondary" style="font-size: 12px;">{{ formatTime(task.update_time) }}</span>
            </div>
            <div class="finished-question mt-2">{{ task.metadata?.market?.question }}</div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { getPendingTradeTasks, getTasks } from '@/api/tasks'
import { Refresh } from '@element-plus/icons-vue'

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
      error,
      loadPendingTasks,
      formatTime,
      formatNumber,
      formatPricePercent,
      formatPercent,
      calculateDiff,
      formatDiff,
      getDiffClass,
      Refresh
    }
  }
}
</script>

<style scoped>
.trade-container { 
  padding: 20px; 
  max-width: 1400px; 
  margin: 0 auto; 
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions h2 {
  font-size: 20px;
  color: var(--text-color);
  margin: 0;
}

.section-header {
  display: flex;
  align-items: center;
}

.section-header h3 {
  font-size: 18px;
  color: var(--text-color);
  margin: 0;
}

/* 任务头部 */
.task-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
}

.task-header-left { 
  display: flex; 
  align-items: center; 
}

.task-id { 
  font-weight: bold; 
  font-size: 16px; 
}

.market-question h3 {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
  margin: 0;
  line-height: 1.5;
}

.card-title {
  font-size: 14px;
  font-weight: bold;
  color: var(--el-text-color-secondary);
}

/* 概率对比 */
.prob-column {
  text-align: center;
}

.prob-header {
  font-weight: bold;
  margin-bottom: 10px;
  border-bottom: 2px solid var(--el-border-color-lighter);
  padding-bottom: 5px;
}

.prob-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
  font-size: 14px;
}

.prob-row.diff {
  border-top: 1px dashed var(--el-border-color-lighter);
  padding-top: 5px;
  margin-top: 5px;
}

.prob-label {
  color: var(--el-text-color-secondary);
}

.prob-value {
  font-weight: 500;
}

.prob-value.market { color: var(--el-text-color-regular); }
.prob-value.predict { color: var(--el-color-primary); }
.prob-value.positive { color: var(--el-color-success); }
.prob-value.positive-high { color: var(--el-color-success); font-weight: bold; }
.prob-value.negative { color: var(--el-color-danger); }
.prob-value.negative-high { color: var(--el-color-danger); font-weight: bold; }
.prob-value.neutral { color: var(--el-text-color-secondary); }

.trade-action {
  text-align: center;
  padding-top: 10px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.action-amount {
  font-weight: bold;
  font-size: 16px;
}

.reasons-list {
  margin: 0;
  padding-left: 15px;
}

.reasons-list li {
  font-size: 13px;
  margin-bottom: 4px;
}

/* 已完成交易 */
.finished-card {
  border-left: 4px solid var(--el-color-primary);
}

.finished-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.finished-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.finished-amount {
  font-weight: bold;
}

.finished-question {
  font-size: 13px;
  color: var(--el-text-color-regular);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Utility classes */
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.ml-2 { margin-left: 8px; }
.mr-1 { margin-right: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.h-100 { height: 100%; }
.text-secondary { color: var(--el-text-color-secondary); }
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.d-block { display: block; }
</style>

