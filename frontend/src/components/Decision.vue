<template>
  <div class="page-container">
    <div class="header-actions mb-4">
      <div class="left">
        <h2 class="text-xl font-bold">决策管理</h2>
      </div>
      <div class="right">
        <el-button-group>
          <el-button type="primary" :loading="loading" :icon="Refresh" @click="loadPendingTasks">
            刷新列表
          </el-button>
          <el-button 
            type="success" 
            :icon="Check"
            @click="executeDecisionHandler" 
            :loading="executing"
            :disabled="loading || pendingTasks.length === 0"
          >
            {{ executing ? '处理中...' : '同意并执行决策' }}
          </el-button>
        </el-button-group>
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
      @close="error = ''"
    />

    <!-- 执行结果展示 -->
    <div v-if="executionResult" class="result-panel mb-4">
      <el-card shadow="hover" class="execution-result-card">
        <template #header>
          <div class="card-header">
            <span class="text-success font-weight-bold">
              <el-icon class="mr-1"><Check /></el-icon>决策执行成功
            </span>
            <el-button link :icon="Close" @click="executionResult = null"></el-button>
          </div>
        </template>
        
        <el-row :gutter="20" class="mb-4">
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">处理任务数</div>
              <div class="stat-value">{{ executionResult.processed_count }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">可交易市场</div>
              <div class="stat-value">{{ executionResult.summary?.tradable_markets || 0 }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">账户资金</div>
              <div class="stat-value">${{ (executionResult.summary?.gross_wealth || 0).toFixed(2) }}</div>
            </div>
          </el-col>
        </el-row>

        <div v-if="executionResult.allocations?.length > 0">
          <div class="section-title mb-2">
            <el-icon class="mr-1"><TrendCharts /></el-icon>
            <span>仓位分配详情（仅显示值得交易的市场）</span>
          </div>
          <el-table :data="executionResult.allocations" style="width: 100%" size="small" border stripe>
            <el-table-column prop="id" label="市场 ID" width="120">
              <template #default="scope">
                <span class="font-monospace">#{{ scope.row.id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="side" label="方向" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.side === 'YES' ? 'success' : 'danger'" effect="dark" size="small">
                  {{ scope.row.side }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="dollars" label="投入金额">
              <template #default="scope">${{ scope.row.dollars.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="shares" label="份额">
              <template #default="scope">{{ scope.row.shares.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="cost" label="成本">
              <template #default="scope">{{ (scope.row.cost * 100).toFixed(1) }}%</template>
            </el-table-column>
          </el-table>
        </div>
        
        <el-empty v-else-if="executionResult.processed_count > 0" description="所有市场均不符合Kelly准则，暂无值得交易的机会" :image-size="100" />
      </el-card>
    </div>

    <!-- 待决策任务列表 -->
    <div class="tasks-section mb-5">
      <div class="section-header mb-3">
        <h3>待决策任务</h3>
        <el-tag type="success" effect="dark" round class="ml-2">{{ pendingTasks.length }}</el-tag>
      </div>

      <el-empty v-if="pendingTasks.length === 0 && !loading" description="暂无待决策任务">
        <template #extra>
          <div class="empty-hint">任务列表会自动刷新</div>
        </template>
      </el-empty>

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
            <!-- 概率对比 -->
            <el-col :xs="24" :lg="16" class="mb-3">
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
                    </el-col>
                  </el-row>
                </div>
              </el-card>
            </el-col>

            <!-- 市场信息 -->
            <el-col :xs="24" :lg="8" class="mb-3">
              <el-card shadow="never" class="h-100">
                <template #header><div class="card-title">市场信息</div></template>
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="ID">
                    <el-tooltip :content="task.metadata?.market?.id" placement="top">
                      <span class="text-truncate d-block" style="max-width: 150px;">{{ task.metadata?.market?.id }}</span>
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

    <!-- 已完成决策列表 -->
    <div class="tasks-section">
      <div class="section-header mb-3">
        <h3>已完成决策</h3>
        <el-tag type="primary" effect="dark" round class="ml-2">{{ finishedTasks.length }}</el-tag>
      </div>

      <el-empty v-if="finishedTasks.length === 0 && !loading" description="暂无已完成的决策" />

      <el-row v-else :gutter="20">
        <el-col :xs="24" :sm="12" :lg="8" v-for="task in finishedTasks" :key="task.id" class="mb-3">
          <el-card class="finished-card" shadow="hover" :body-style="{ padding: '15px' }">
            <div class="finished-header">
              <div class="finished-left">
                <span class="task-id">#{{ task.id }}</span>
                <template v-if="task.result?.decision === 'trade'">
                  <el-tag 
                    :type="task.result?.allocation?.side === 'YES' ? 'success' : 'danger'" 
                    size="small" 
                    effect="dark"
                  >
                    {{ task.result?.allocation?.side }}
                  </el-tag>
                  <span class="finished-amount ml-2">${{ task.result?.allocation?.dollars?.toFixed(2) }}</span>
                </template>
                <el-tag v-else type="info" size="small" effect="dark">SKIP</el-tag>
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
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { getPendingDecisionTasks, executeDecision, getTasks } from '@/api/tasks'
import { Refresh, Check, Close, TrendCharts } from '@element-plus/icons-vue'

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
      getDiffClass,
      Refresh,
      Check,
      Close,
      TrendCharts
    }
  }
}
</script>

<style scoped>
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions h2 {
  margin: 0;
  color: var(--el-text-color-primary);
}

.section-header {
  display: flex;
  align-items: center;
}

.section-header h3 {
  font-size: 18px;
  color: var(--el-text-color-primary);
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
  color: var(--el-text-color-primary);
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

.reasons-list {
  margin: 0;
  padding-left: 15px;
}

.reasons-list li {
  font-size: 13px;
  margin-bottom: 4px;
}

/* 结果卡片 */
.execution-result-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-item {
  text-align: center;
  padding: 10px;
  background-color: var(--el-fill-color-light);
  border-radius: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
  color: var(--el-text-color-primary);
}

/* 已完成交易 */
.finished-card {
  border-left: 4px solid var(--el-color-success);
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
  color: var(--el-color-success);
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
.mb-5 { margin-bottom: 24px; }
.ml-2 { margin-left: 8px; }
.mr-1 { margin-right: 4px; }
.mt-2 { margin-top: 8px; }
.h-100 { height: 100%; }
.text-secondary { color: var(--el-text-color-secondary); }
.text-success { color: var(--el-color-success); }
.font-weight-bold { font-weight: bold; }
.font-monospace { font-family: monospace; }
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.d-block { display: block; }
</style>