<template>
  <div class="position-monitor">
    <!-- 标题栏 -->
    <div class="header">
      <h2>持仓监控</h2>
    </div>

    <!-- 汇总信息卡片 -->
    <div class="summary-cards">
      <div class="summary-card">
        <div class="card-content">
          <div class="card-label">持仓数量</div>
          <div class="card-value">{{ summary.total_positions || 0 }}</div>
        </div>
      </div>
      <div class="summary-card">
        <div class="card-content">
          <div class="card-label">总投资</div>
          <div class="card-value">${{ formatNumber(summary.total_invest) }}</div>
        </div>
      </div>
      <div class="summary-card" :class="getPnlClass(summary.total_pnl)">
        <div class="card-content">
          <div class="card-label">总盈亏</div>
          <div class="card-value">${{ formatNumber(summary.total_pnl) }}</div>
        </div>
      </div>
    </div>

    <!-- 标签页 -->
    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'positions' }"
        @click="activeTab = 'positions'"
      >
        持仓列表
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'orders' }"
        @click="activeTab = 'orders'"
      >
        订单列表
      </button>
    </div>

    <!-- 持仓列表 -->
    <div v-if="activeTab === 'positions'" class="positions-list">
      <div class="filter-bar">
        <select v-model="positionFilter" @change="loadPositions">
          <option value="">全部持仓</option>
          <option value="open">未平仓</option>
          <option value="closed">已平仓</option>
        </select>
      </div>

      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="positions.length === 0" class="empty">暂无持仓数据</div>
      <div v-else class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th width="80">展开</th>
              <th>ID</th>
              <th>市场ID</th>
              <th>方向</th>
              <th>入场价</th>
              <th>当前价</th>
              <th>份额</th>
              <th>投资</th>
              <th>盈亏</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="position in positions" :key="position.id">
              <!-- 持仓行 -->
              <tr>
                <td>
                  <div class="expand-buttons">
                    <button
                      class="btn-expand"
                      @click="toggleMetadata(position.id)"
                      :title="expandedMetadata[position.id] ? '收起详情' : '展开详情'"
                    >
                      <span class="arrow" :class="{ expanded: expandedMetadata[position.id] }">ℹ️</span>
                    </button>
                    <button
                      class="btn-expand"
                      @click="toggleChart(position.id)"
                      :title="expandedCharts[position.id] ? '收起图表' : '展开图表'"
                    >
                      <span class="arrow" :class="{ expanded: expandedCharts[position.id] }">📊</span>
                    </button>
                  </div>
                </td>
                <td>{{ position.id }}</td>
                <td class="market-id">
                  {{ formatMarketId(position.market_id) }}
                </td>
                <td>
                  <span class="badge" :class="position.side === 'YES' ? 'badge-yes' : 'badge-no'">
                    {{ position.side }}
                  </span>
                </td>
                <td>${{ formatPrice(position.entry_price) }}</td>
                <td>${{ formatPrice(position.current_price) }}</td>
                <td>{{ formatNumber(position.shares) }}</td>
                <td>${{ formatNumber(position.invest_amount) }}</td>
                <td :class="getPnlClass(position.pnl)">
                  ${{ formatNumber(position.pnl) }}
                </td>
                <td>
                  <span class="badge" :class="getStatusClass(position.status)">
                    {{ getStatusText(position.status) }}
                  </span>
                </td>
                <td>{{ formatTime(position.create_time) }}</td>
                <td>
                  <button class="btn-small" @click="monitorPositionAction(position.id)">
                    监控
                  </button>
                </td>
              </tr>

              <!-- Metadata详情展开行 -->
              <tr v-if="expandedMetadata[position.id]" class="metadata-row">
                <td colspan="12">
                  <div class="metadata-container">
                    <h4>📋 持仓详情</h4>

                    <!-- Market信息 -->
                    <div v-if="position.metadata?.market" class="metadata-section">
                      <h5>🎯 市场信息</h5>
                      <div class="metadata-grid">
                        <div class="metadata-item">
                          <span class="label">问题:</span>
                          <span class="value">{{ position.metadata.market.question }}</span>
                        </div>
                        <div class="metadata-item">
                          <span class="label">市场ID:</span>
                          <span class="value">{{ position.metadata.market.id }}</span>
                        </div>
                        <div class="metadata-item">
                          <span class="label">结算日期:</span>
                          <span class="value">{{ formatDate(position.metadata.market.end_date) }}</span>
                        </div>
                        <div class="metadata-item" v-if="position.metadata.market.slug">
                          <span class="label">Slug:</span>
                          <span class="value">{{ position.metadata.market.slug }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Analysis信息 -->
                    <div v-if="position.metadata?.analysis" class="metadata-section">
                      <h5>🧠 分析结果</h5>
                      <div class="metadata-grid">
                        <div class="metadata-item">
                          <span class="label">YES概率:</span>
                          <span class="value probability">{{ formatPercent(position.metadata.analysis.p) }}</span>
                        </div>
                        <div class="metadata-item">
                          <span class="label">NO概率:</span>
                          <span class="value probability">{{ formatPercent(position.metadata.analysis.n) }}</span>
                        </div>
                        <div class="metadata-item">
                          <span class="label">置信度:</span>
                          <span class="value probability">{{ formatPercent(position.metadata.analysis.a) }}</span>
                        </div>
                      </div>

                      <!-- YES理由 -->
                      <div v-if="position.metadata.analysis.reasons_y?.length" class="reasons-section">
                        <h6>✅ YES理由:</h6>
                        <ul class="reasons-list">
                          <li v-for="(reason, idx) in position.metadata.analysis.reasons_y" :key="idx">
                            {{ reason }}
                          </li>
                        </ul>
                      </div>

                      <!-- NO理由 -->
                      <div v-if="position.metadata.analysis.reasons_n?.length" class="reasons-section">
                        <h6>❌ NO理由:</h6>
                        <ul class="reasons-list">
                          <li v-for="(reason, idx) in position.metadata.analysis.reasons_n" :key="idx">
                            {{ reason }}
                          </li>
                        </ul>
                      </div>
                    </div>

                    <!-- Marks标签 -->
                    <div v-if="position.metadata?.marks?.length" class="metadata-section">
                      <h5>🏷️ 标签</h5>
                      <div class="marks-container">
                        <span
                          v-for="mark in position.metadata.marks"
                          :key="mark"
                          class="mark-badge"
                        >
                          {{ mark }}
                        </span>
                      </div>
                    </div>

                    <!-- 其他元信息 -->
                    <div class="metadata-section">
                      <h5>📊 交易参数</h5>
                      <div class="metadata-grid">
                        <div class="metadata-item">
                          <span class="label">主观概率:</span>
                          <span class="value">{{ formatPercent(position.metadata.subjective_probability) }}</span>
                        </div>
                        <div class="metadata-item">
                          <span class="label">赔率:</span>
                          <span class="value">{{ formatNumber(position.metadata.odds) }}</span>
                        </div>
                        <div class="metadata-item">
                          <span class="label">仓位比例:</span>
                          <span class="value">{{ formatPercent(position.metadata.position_fraction) }}</span>
                        </div>
                        <div class="metadata-item" v-if="position.metadata.source_analysis_task_id">
                          <span class="label">源任务ID:</span>
                          <span class="value">{{ position.metadata.source_analysis_task_id }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>

              <!-- 价格曲线展开行 -->
              <tr v-if="expandedCharts[position.id]" class="chart-row">
                <td colspan="12">
                  <div class="inline-chart-container">
                    <div class="chart-header">
                      <h4>📈 价格曲线 - {{ formatMarketId(position.market_id) }}</h4>
                      <div class="chart-controls-inline">
                        <select
                          v-model="chartIntervals[position.id]"
                          @change="loadPositionChart(position)"
                          class="interval-select"
                        >
                          <option value="1h">1小时</option>
                          <option value="6h">6小时</option>
                          <option value="1d">1天</option>
                          <option value="1w">1周</option>
                          <option value="1m">1个月</option>
                          <option value="max">最大</option>
                        </select>
                      </div>
                    </div>

                    <div v-if="chartLoadingStates[position.id]" class="loading-inline">
                      加载图表数据中...
                    </div>
                    <div v-else class="chart-wrapper">
                      <apexchart
                        v-if="chartOptions[position.id] && chartSeries[position.id]"
                        type="line"
                        height="350"
                        :options="chartOptions[position.id]"
                        :series="chartSeries[position.id]"
                      ></apexchart>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 订单列表 -->
    <div v-if="activeTab === 'orders'" class="orders-list">
      <div class="filter-bar">
        <select v-model="orderFilter" @change="loadOrders">
          <option value="">全部订单</option>
          <option value="pending">待成交</option>
          <option value="filled">已成交</option>
          <option value="cancelled">已撤销</option>
        </select>
      </div>

      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="orders.length === 0" class="empty">暂无订单数据</div>
      <div v-else class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>订单ID</th>
              <th>市场ID</th>
              <th>方向</th>
              <th>价格</th>
              <th>数量</th>
              <th>已成交</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in orders" :key="order.order_id">
              <td class="order-id">{{ formatOrderId(order.order_id) }}</td>
              <td class="market-id">{{ formatMarketId(order.market_id) }}</td>
              <td>
                <span class="badge" :class="order.side === 'BUY' ? 'badge-buy' : 'badge-sell'">
                  {{ order.side }}
                </span>
              </td>
              <td>${{ formatPrice(order.price) }}</td>
              <td>{{ formatNumber(order.size) }}</td>
              <td>{{ formatNumber(order.filled_size) }}</td>
              <td>
                <span class="badge" :class="getOrderStatusClass(order.status)">
                  {{ getOrderStatusText(order.status) }}
                </span>
              </td>
              <td>{{ formatTime(order.create_time) }}</td>
              <td>
                <button class="btn-small" @click="monitorOrderAction(order.order_id)">
                  监控
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>


  </div>
</template>

<script>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import VueApexCharts from 'vue3-apexcharts'
import {
  getPositionSummary,
  getPositions,
  getOrders,
  monitorPosition,
  monitorOrder,
  getMarketPositions,
  getPositionPriceCurve
} from '@/api/positions'
import { toast } from '@/components/Notification'

export default {
  name: 'PositionMonitor',
  components: {
    apexchart: VueApexCharts
  },
  setup() {
    // 数据状态
    const summary = ref({})
    const positions = ref([])
    const orders = ref([])
    const loading = ref(false)

    // UI状态
    const activeTab = ref('positions')
    const positionFilter = ref('')
    const orderFilter = ref('')

    // 图表相关 - 每个持仓独立的图表状态
    const expandedCharts = ref({}) // 记录哪些持仓的图表是展开的
    const expandedMetadata = ref({}) // 记录哪些持仓的metadata是展开的
    const chartOptions = ref({}) // 存储每个持仓的图表配置
    const chartSeries = ref({}) // 存储每个持仓的图表数据系列
    const chartIntervals = ref({}) // 每个持仓的时间间隔选择
    const chartLoadingStates = ref({}) // 每个持仓的加载状态
    const chartDataCache = ref({}) // 缓存图表数据

    // 加载汇总数据
    const loadSummary = async () => {
      try {
        const response = await getPositionSummary()
        if (response.success) {
          summary.value = response.data
        }
      } catch (error) {
        console.error('加载汇总数据失败:', error)
      }
    }

    // 加载持仓列表
    const loadPositions = async () => {
      loading.value = true
      try {
        const params = {}
        if (positionFilter.value) {
          params.status = positionFilter.value
        }

        const response = await getPositions(params)
        if (response.success) {
          positions.value = response.data.positions || []
        }
      } catch (error) {
        console.error('加载持仓列表失败:', error)
        toast.error('加载持仓列表失败')
      } finally {
        loading.value = false
      }
    }

    // 加载订单列表
    const loadOrders = async () => {
      loading.value = true
      try {
        const params = {}
        if (orderFilter.value) {
          params.status = orderFilter.value
        }

        const response = await getOrders(params)
        if (response.success) {
          orders.value = response.data.orders || []
        }
      } catch (error) {
        console.error('加载订单列表失败:', error)
        toast.error('加载订单列表失败')
      } finally {
        loading.value = false
      }
    }

    // 监控持仓
    const monitorPositionAction = async (positionId) => {
      try {
        const response = await monitorPosition(positionId)
        if (response.success) {
          toast.success('监控持仓成功')
          await loadPositions()
          await loadSummary()
        } else {
          toast.error(response.message || '监控持仓失败')
        }
      } catch (error) {
        console.error('监控持仓失败:', error)
        toast.error('监控持仓失败')
      }
    }

    // 监控订单
    const monitorOrderAction = async (orderId) => {
      try {
        const response = await monitorOrder(orderId)
        if (response.success) {
          toast.success('监控订单成功')
          await loadOrders()
        } else {
          toast.error(response.message || '监控订单失败')
        }
      } catch (error) {
        console.error('监控订单失败:', error)
        toast.error('监控订单失败')
      }
    }

    // 切换metadata展开/收起
    const toggleMetadata = (positionId) => {
      expandedMetadata.value[positionId] = !expandedMetadata.value[positionId]
    }

    // 切换图表展开/收起
    const toggleChart = async (positionId) => {
      const isExpanded = expandedCharts.value[positionId]

      if (isExpanded) {
        // 收起图表
        expandedCharts.value[positionId] = false
        // 清除图表数据
        delete chartOptions.value[positionId]
        delete chartSeries.value[positionId]
      } else {
        // 展开图表
        expandedCharts.value[positionId] = true
        // 初始化默认时间间隔
        if (!chartIntervals.value[positionId]) {
          chartIntervals.value[positionId] = '1d'
        }

        // 等待DOM更新后加载图表
        await nextTick()
        const position = positions.value.find(p => p.id === positionId)
        if (position) {
          await loadPositionChart(position)
        }
      }
    }

    // 加载单个持仓的图表数据
    const loadPositionChart = async (position) => {
      const positionId = position.id
      const interval = chartIntervals.value[positionId] || '1d'

      // 设置加载状态
      chartLoadingStates.value[positionId] = true

      try {
        // 根据interval计算before_hours和after_hours
        const intervalHours = {
          '1h': 1,
          '6h': 6,
          '1d': 24,
          '1w': 168,
          '1m': 720,
          'max': 8760  // 1年
        }
        const hours = intervalHours[interval] || 24

        const params = {
          before_hours: hours,
          after_hours: hours,
          fidelity: 60
        }

        // 使用新的API端点获取以购买时刻为基准的价格曲线
        const response = await getPositionPriceCurve(positionId, params)
        if (response.success) {
          const priceHistory = response.data.price_history || []
          const purchaseTime = response.data.purchase_time
          const positionData = response.data.position

          // 缓存数据
          chartDataCache.value[positionId] = {
            priceHistory,
            purchaseTime,
            position: positionData
          }

          // 等待DOM更新
          await nextTick()

          // 创建ApexCharts配置和数据
          createApexChart(positionId, priceHistory, purchaseTime, positionData)
        }
      } catch (error) {
        console.error('加载持仓图表失败:', error)
        toast.error('加载价格曲线失败')
      } finally {
        chartLoadingStates.value[positionId] = false
      }
    }

    // 创建ApexCharts图表配置
    const createApexChart = (positionId, priceHistory, purchaseTime, position) => {
      // 准备价格曲线数据
      const priceData = priceHistory.map(item => ({
        x: item.t * 1000, // 转换为毫秒时间戳
        y: parseFloat(item.p)
      }))

      // 准备买入点数据（单个点）
      const buyPointData = [{
        x: purchaseTime * 1000,
        y: parseFloat(position.entry_price)
      }]

      // 设置图表系列数据
      chartSeries.value[positionId] = [
        {
          name: '价格曲线',
          type: 'line',
          data: priceData
        },
        {
          name: '买入点',
          type: 'scatter',
          data: buyPointData
        }
      ]

      // 设置图表配置选项
      chartOptions.value[positionId] = {
        chart: {
          type: 'line',
          height: 350,
          toolbar: {
            show: true,
            tools: {
              download: true,
              selection: true,
              zoom: true,
              zoomin: true,
              zoomout: true,
              pan: true,
              reset: true
            }
          },
          animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 300
          },
          zoom: {
            enabled: true,
            type: 'x',
            autoScaleYaxis: true
          }
        },
        colors: ['#5470c6', '#ee6666'],
        stroke: {
          width: [2, 0],
          curve: 'smooth'
        },
        markers: {
          size: [0, 10],
          colors: ['#5470c6', '#ee6666'],
          strokeColors: '#fff',
          strokeWidth: 2,
          hover: {
            size: 12
          }
        },
        // 添加购买时刻的垂直标记线
        annotations: {
          xaxis: [
            {
              x: purchaseTime * 1000,
              borderColor: '#ee6666',
              strokeDashArray: 4,
              label: {
                borderColor: '#ee6666',
                style: {
                  color: '#fff',
                  background: '#ee6666',
                  fontSize: '12px',
                  fontWeight: 'bold'
                },
                text: '购买时刻',
                orientation: 'horizontal',
                position: 'top'
              }
            }
          ]
        },
        xaxis: {
          type: 'datetime',
          labels: {
            datetimeFormatter: {
              year: 'yyyy',
              month: 'MM/dd',
              day: 'MM/dd',
              hour: 'HH:mm'
            }
          }
        },
        yaxis: {
          title: {
            text: '价格 ($)'
          },
          min: 0,
          max: 1,
          labels: {
            formatter: function(value) {
              return '$' + value.toFixed(4)
            }
          }
        },
        tooltip: {
          shared: false,
          intersect: true,
          x: {
            format: 'yyyy-MM-dd HH:mm'
          },
          y: {
            formatter: function(value) {
              return '$' + value.toFixed(4)
            }
          }
        },
        legend: {
          show: true,
          position: 'top',
          horizontalAlign: 'left',
          offsetY: 0
        },
        grid: {
          borderColor: '#e7e7e7',
          row: {
            colors: ['#f3f3f3', 'transparent'],
            opacity: 0.5
          }
        },
        dataLabels: {
          enabled: false
        }
      }
    }

    // 刷新所有数据
    const refreshData = async () => {
      await loadSummary()
      if (activeTab.value === 'positions') {
        await loadPositions()
        // 刷新已展开的图表
        for (const positionId in expandedCharts.value) {
          if (expandedCharts.value[positionId]) {
            const position = positions.value.find(p => p.id === parseInt(positionId))
            if (position) {
              await loadPositionChart(position)
            }
          }
        }
      } else if (activeTab.value === 'orders') {
        await loadOrders()
      }
      toast.success('数据已刷新')
    }

    // 格式化函数
    const formatNumber = (num) => {
      if (num === null || num === undefined) return '0.00'
      return parseFloat(num).toFixed(2)
    }

    const formatPrice = (price) => {
      if (price === null || price === undefined) return '0.0000'
      return parseFloat(price).toFixed(4)
    }

    const formatMarketId = (id) => {
      if (!id) return '-'
      return id.length > 12 ? id.substring(0, 12) + '...' : id
    }

    const formatOrderId = (id) => {
      if (!id) return '-'
      return id.length > 16 ? id.substring(0, 16) + '...' : id
    }

    const formatTime = (time) => {
      if (!time) return '-'
      return new Date(time).toLocaleString('zh-CN')
    }

    const formatDate = (dateStr) => {
      if (!dateStr) return '-'
      return new Date(dateStr).toLocaleDateString('zh-CN')
    }

    const formatPercent = (value) => {
      if (value === null || value === undefined) return '-'
      return (parseFloat(value) * 100).toFixed(2) + '%'
    }

    const getPnlClass = (pnl) => {
      if (!pnl) return ''
      return pnl > 0 ? 'positive' : pnl < 0 ? 'negative' : ''
    }

    const getStatusClass = (status) => {
      const classMap = {
        'open': 'badge-success',
        'closed': 'badge-info',
        'monitoring': 'badge-warning'
      }
      return classMap[status] || ''
    }

    const getStatusText = (status) => {
      const textMap = {
        'open': '持仓中',
        'closed': '已平仓',
        'monitoring': '监控中'
      }
      return textMap[status] || status
    }

    const getOrderStatusClass = (status) => {
      const classMap = {
        'pending': 'badge-warning',
        'filled': 'badge-success',
        'cancelled': 'badge-info',
        'failed': 'badge-danger'
      }
      return classMap[status] || ''
    }

    const getOrderStatusText = (status) => {
      const textMap = {
        'pending': '待成交',
        'filled': '已成交',
        'cancelled': '已撤销',
        'failed': '失败'
      }
      return textMap[status] || status
    }

    // 自动刷新定时器
    let autoRefreshTimer = null

    // 全局刷新事件处理
    const handleGlobalRefresh = async () => {
      await loadSummary()
      if (activeTab.value === 'positions') {
        await loadPositions()
      } else if (activeTab.value === 'orders') {
        await loadOrders()
      }
    }

    // 组件挂载
    onMounted(async () => {
      await loadSummary()
      await loadPositions()
      // 每60秒自动刷新一次
      autoRefreshTimer = setInterval(async () => {
        await loadSummary()
        if (activeTab.value === 'positions') {
          await loadPositions()
        } else if (activeTab.value === 'orders') {
          await loadOrders()
        }
      }, 60000)
      // 监听全局刷新事件
      window.addEventListener('global-refresh', handleGlobalRefresh)
    })

    // 组件卸载前清理
    onBeforeUnmount(() => {
      // 清理定时器
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer)
      }
      // 移除全局刷新事件监听
      window.removeEventListener('global-refresh', handleGlobalRefresh)
      // 清理图表数据
      chartOptions.value = {}
      chartSeries.value = {}
      chartDataCache.value = {}
    })

    return {
      summary,
      positions,
      orders,
      loading,
      activeTab,
      positionFilter,
      orderFilter,
      expandedCharts,
      expandedMetadata,
      chartOptions,
      chartSeries,
      chartIntervals,
      chartLoadingStates,
      loadPositions,
      loadOrders,
      monitorPositionAction,
      monitorOrderAction,
      toggleMetadata,
      toggleChart,
      loadPositionChart,
      refreshData,
      formatNumber,
      formatPrice,
      formatMarketId,
      formatOrderId,
      formatTime,
      formatDate,
      formatPercent,
      getPnlClass,
      getStatusClass,
      getStatusText,
      getOrderStatusClass,
      getOrderStatusText
    }
  }
}
</script>

<style scoped>
.position-monitor {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header h2 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn-refresh {
  padding: 8px 16px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-refresh:hover {
  background: #66b1ff;
}

/* 汇总卡片 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.summary-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 15px;
}

.summary-card.positive {
  border-left: 4px solid #67c23a;
}

.summary-card.negative {
  border-left: 4px solid #f56c6c;
}

.card-icon {
  font-size: 36px;
}

.card-content {
  flex: 1;
}

.card-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.card-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

/* 标签页 */
.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e4e7ed;
}

.tab-btn {
  padding: 10px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 16px;
  color: #606266;
  transition: all 0.3s;
}

.tab-btn:hover {
  color: #409eff;
}

.tab-btn.active {
  color: #409eff;
  border-bottom-color: #409eff;
  font-weight: bold;
}

/* 过滤栏 */
.filter-bar {
  margin-bottom: 20px;
}

.filter-bar select {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
}

/* 表格 */
.table-container {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  background: #f5f7fa;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #606266;
  border-bottom: 1px solid #ebeef5;
}

.data-table td {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  color: #606266;
}

.data-table tr:hover {
  background: #f5f7fa;
}

.market-id,
.order-id {
  cursor: pointer;
  color: #409eff;
  text-decoration: underline;
}

.market-id:hover,
.order-id:hover {
  color: #66b1ff;
}

/* 徽章 */
.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-yes {
  background: #e1f3d8;
  color: #67c23a;
}

.badge-no {
  background: #fde2e2;
  color: #f56c6c;
}

.badge-buy {
  background: #e1f3d8;
  color: #67c23a;
}

.badge-sell {
  background: #fde2e2;
  color: #f56c6c;
}

.badge-success {
  background: #e1f3d8;
  color: #67c23a;
}

.badge-warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.badge-info {
  background: #e9ecef;
  color: #909399;
}

.badge-danger {
  background: #fde2e2;
  color: #f56c6c;
}

/* 盈亏颜色 */
.positive {
  color: #67c23a;
  font-weight: bold;
}

.negative {
  color: #f56c6c;
  font-weight: bold;
}

/* 按钮 */
.btn-small {
  padding: 4px 12px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-small:hover {
  background: #66b1ff;
}

/* 展开按钮容器 */
.expand-buttons {
  display: flex;
  gap: 4px;
  align-items: center;
}

/* 展开/收起按钮 */
.btn-expand {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  font-size: 16px;
}

.btn-expand:hover {
  background: #f5f7fa;
  border-radius: 4px;
}

.arrow {
  display: inline-block;
  font-size: 12px;
  color: #606266;
  transition: transform 0.3s;
}

.arrow.expanded {
  transform: rotate(90deg);
}

/* 图表行样式 */
.chart-row {
  background: #f9fafb;
}

.chart-row td {
  padding: 0 !important;
}

/* 内联图表容器 */
.inline-chart-container {
  padding: 20px;
  background: white;
  border-top: 2px solid #e4e7ed;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.chart-header h4 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.chart-controls-inline {
  display: flex;
  gap: 10px;
  align-items: center;
}

.interval-select {
  padding: 6px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
  background: white;
  cursor: pointer;
}

.interval-select:hover {
  border-color: #409eff;
}

/* 图表包装器 */
.chart-wrapper {
  width: 100%;
  background: white;
  padding: 10px 0;
}

/* 内联加载状态 */
.loading-inline {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
  font-size: 14px;
}

/* ApexCharts 样式覆盖 */
.chart-wrapper :deep(.apexcharts-canvas) {
  margin: 0 auto;
}

.chart-wrapper :deep(.apexcharts-tooltip) {
  background: rgba(0, 0, 0, 0.85);
  color: white;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.chart-wrapper :deep(.apexcharts-tooltip-title) {
  background: rgba(0, 0, 0, 0.9);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.chart-wrapper :deep(.apexcharts-legend) {
  padding: 5px 10px;
}

.chart-wrapper :deep(.apexcharts-toolbar) {
  z-index: 10;
}

/* 加载和空状态 */
.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #909399;
  font-size: 14px;
}

/* Metadata展开行样式 */
.metadata-row {
  background: #f9fafb;
}

.metadata-row td {
  padding: 0 !important;
}

.metadata-container {
  padding: 20px;
  background: white;
  border-top: 2px solid #e4e7ed;
  animation: slideDown 0.3s ease-out;
}

.metadata-container h4 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #303133;
  border-bottom: 2px solid #409eff;
  padding-bottom: 10px;
}

.metadata-section {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.metadata-section h5 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #409eff;
  font-weight: 600;
}

.metadata-section h6 {
  margin: 10px 0 8px 0;
  font-size: 14px;
  color: #606266;
  font-weight: 600;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}

.metadata-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.metadata-item .label {
  font-weight: 600;
  color: #606266;
  margin-right: 8px;
  min-width: 80px;
}

.metadata-item .value {
  color: #303133;
  flex: 1;
  word-break: break-all;
}

.metadata-item .value.probability {
  font-weight: 600;
  color: #409eff;
}

.reasons-section {
  margin-top: 15px;
}

.reasons-list {
  margin: 8px 0;
  padding-left: 20px;
  list-style: none;
}

.reasons-list li {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #67c23a;
  line-height: 1.6;
  color: #606266;
}

.reasons-section:last-child .reasons-list li {
  border-left-color: #f56c6c;
}

.marks-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mark-badge {
  display: inline-block;
  padding: 6px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}
</style>

