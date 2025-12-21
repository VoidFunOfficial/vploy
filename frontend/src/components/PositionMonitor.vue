<template>
  <div class="page-container">
    <!-- 标题栏 -->
    <div class="header mb-4">
      <h2>持仓监控</h2>
    </div>

    <!-- 汇总信息卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="summary-card">
          <template #header><div class="card-header">持仓数量</div></template>
          <div class="card-value">{{ summary.total_positions || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="summary-card">
          <template #header><div class="card-header">总投资</div></template>
          <div class="card-value">${{ formatNumber(summary.total_invest) }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="summary-card" :class="getPnlClass(summary.total_pnl)">
          <template #header><div class="card-header">总盈亏</div></template>
          <div class="card-value" :class="getPnlTextClass(summary.total_pnl)">
            ${{ formatNumber(summary.total_pnl) }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" type="border-card" class="mb-4">
      <el-tab-pane label="持仓列表" name="positions">
        <div class="filter-bar mb-3">
          <el-select v-model="positionFilter" placeholder="状态筛选" @change="loadPositions" clearable style="width: 200px">
            <el-option label="全部持仓" value="" />
            <el-option label="未平仓" value="open" />
            <el-option label="已平仓" value="closed" />
          </el-select>
          <el-button type="primary" :icon="Refresh" circle class="ml-2" @click="loadPositions" :loading="loading" />
        </div>

        <el-table 
          v-loading="loading" 
          :data="positions" 
          style="width: 100%" 
          border 
          stripe
          row-key="id"
          @expand-change="handleExpandChange"
        >
          <el-table-column type="expand">
            <template #default="props">
              <div class="expanded-content p-3">
                <el-tabs type="card">
                  <el-tab-pane label="持仓详情">
                    <div class="metadata-container">
                      <!-- Market信息 -->
                      <div v-if="props.row.metadata?.market" class="metadata-section mb-3">
                        <h4 class="section-title"><el-icon class="mr-1"><Shop /></el-icon> 市场信息</h4>
                        <el-descriptions :column="2" border size="small">
                          <el-descriptions-item label="问题">{{ props.row.metadata.market.question }}</el-descriptions-item>
                          <el-descriptions-item label="市场ID">{{ props.row.metadata.market.id }}</el-descriptions-item>
                          <el-descriptions-item label="结算日期">{{ formatDate(props.row.metadata.market.end_date) }}</el-descriptions-item>
                          <el-descriptions-item label="Slug" v-if="props.row.metadata.market.slug">{{ props.row.metadata.market.slug }}</el-descriptions-item>
                        </el-descriptions>
                      </div>

                      <!-- Analysis信息 -->
                      <div v-if="props.row.metadata?.analysis" class="metadata-section mb-3">
                        <h4 class="section-title"><el-icon class="mr-1"><DataAnalysis /></el-icon> 分析结果</h4>
                        <el-descriptions :column="3" border size="small" class="mb-2">
                          <el-descriptions-item label="YES概率">
                            <span class="text-primary font-weight-bold">{{ formatPercent(props.row.metadata.analysis.p) }}</span>
                          </el-descriptions-item>
                          <el-descriptions-item label="NO概率">
                            <span class="text-primary font-weight-bold">{{ formatPercent(props.row.metadata.analysis.n) }}</span>
                          </el-descriptions-item>
                          <el-descriptions-item label="置信度">
                            <span class="text-primary font-weight-bold">{{ formatPercent(props.row.metadata.analysis.a) }}</span>
                          </el-descriptions-item>
                        </el-descriptions>

                        <el-row :gutter="20">
                          <el-col :span="12" v-if="props.row.metadata.analysis.reasons_y?.length">
                            <el-alert title="YES理由" type="success" :closable="false" show-icon>
                              <ul class="reasons-list">
                                <li v-for="(reason, idx) in props.row.metadata.analysis.reasons_y" :key="idx">{{ reason }}</li>
                              </ul>
                            </el-alert>
                          </el-col>
                          <el-col :span="12" v-if="props.row.metadata.analysis.reasons_n?.length">
                            <el-alert title="NO理由" type="error" :closable="false" show-icon>
                              <ul class="reasons-list">
                                <li v-for="(reason, idx) in props.row.metadata.analysis.reasons_n" :key="idx">{{ reason }}</li>
                              </ul>
                            </el-alert>
                          </el-col>
                        </el-row>
                      </div>

                      <!-- Marks标签 -->
                      <div v-if="props.row.metadata?.marks?.length" class="metadata-section mb-3">
                        <h4 class="section-title"><el-icon class="mr-1"><CollectionTag /></el-icon> 标签</h4>
                        <div class="marks-container">
                          <el-tag v-for="mark in props.row.metadata.marks" :key="mark" class="mr-2 mb-2" effect="plain">
                            {{ mark }}
                          </el-tag>
                        </div>
                      </div>

                      <!-- 交易参数 -->
                      <div class="metadata-section">
                        <h4 class="section-title"><el-icon class="mr-1"><Setting /></el-icon> 交易参数</h4>
                        <el-descriptions :column="3" border size="small">
                          <el-descriptions-item label="主观概率">{{ formatPercent(props.row.metadata.subjective_probability) }}</el-descriptions-item>
                          <el-descriptions-item label="赔率">{{ formatNumber(props.row.metadata.odds) }}</el-descriptions-item>
                          <el-descriptions-item label="仓位比例">{{ formatPercent(props.row.metadata.position_fraction) }}</el-descriptions-item>
                          <el-descriptions-item label="源任务ID" v-if="props.row.metadata.source_analysis_task_id">{{ props.row.metadata.source_analysis_task_id }}</el-descriptions-item>
                        </el-descriptions>
                      </div>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="价格曲线">
                    <div class="chart-container">
                      <div class="chart-header mb-3 flex-between">
                        <span class="font-weight-bold">价格曲线 - {{ formatMarketId(props.row.market_id) }}</span>
                        <el-select 
                          v-model="chartIntervals[props.row.id]" 
                          placeholder="时间范围" 
                          size="small" 
                          style="width: 120px"
                          @change="loadPositionChart(props.row)"
                        >
                          <el-option label="1小时" value="1h" />
                          <el-option label="6小时" value="6h" />
                          <el-option label="1天" value="1d" />
                          <el-option label="1周" value="1w" />
                          <el-option label="1个月" value="1m" />
                          <el-option label="最大" value="max" />
                        </el-select>
                      </div>

                      <div v-if="chartLoadingStates[props.row.id]" class="loading-container">
                        <el-skeleton :rows="5" animated />
                      </div>
                      <div v-else class="chart-wrapper">
                        <apexchart
                          v-if="chartOptions[props.row.id] && chartSeries[props.row.id]"
                          type="line"
                          height="350"
                          :options="chartOptions[props.row.id]"
                          :series="chartSeries[props.row.id]"
                        ></apexchart>
                        <el-empty v-else description="暂无图表数据" :image-size="100" />
                      </div>
                    </div>
                  </el-tab-pane>
                </el-tabs>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="id" label="ID" width="80" sortable />
          <el-table-column prop="market_id" label="市场ID" min-width="120">
            <template #default="scope">
              <el-tooltip :content="scope.row.market_id" placement="top">
                <span class="text-truncate d-block">{{ formatMarketId(scope.row.market_id) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="side" label="方向" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.side === 'YES' ? 'success' : 'danger'" effect="dark" size="small">
                {{ scope.row.side }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="entry_price" label="入场价" width="100">
            <template #default="scope">${{ formatPrice(scope.row.entry_price) }}</template>
          </el-table-column>
          <el-table-column prop="current_price" label="当前价" width="100">
            <template #default="scope">${{ formatPrice(scope.row.current_price) }}</template>
          </el-table-column>
          <el-table-column prop="shares" label="份额" width="100">
            <template #default="scope">{{ formatNumber(scope.row.shares) }}</template>
          </el-table-column>
          <el-table-column prop="invest_amount" label="投资" width="100">
            <template #default="scope">${{ formatNumber(scope.row.invest_amount) }}</template>
          </el-table-column>
          <el-table-column prop="pnl" label="盈亏" width="100" sortable>
            <template #default="scope">
              <span :class="getPnlTextClass(scope.row.pnl)">
                ${{ formatNumber(scope.row.pnl) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="create_time" label="创建时间" width="160" sortable>
            <template #default="scope">{{ formatTime(scope.row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" link size="small" @click="monitorPositionAction(scope.row.id)">
                监控
              </el-button>
              <el-button type="warning" link size="small" @click="editPosition(scope.row)">
                编辑
              </el-button>
              <el-button type="danger" link size="small" @click="deletePositionAction(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="订单列表" name="orders">
        <div class="filter-bar mb-3">
          <el-select v-model="orderFilter" placeholder="状态筛选" @change="loadOrders" clearable style="width: 200px">
            <el-option label="全部订单" value="" />
            <el-option label="待成交" value="pending" />
            <el-option label="已成交" value="filled" />
            <el-option label="已撤销" value="cancelled" />
          </el-select>
          <el-button type="primary" :icon="Refresh" circle class="ml-2" @click="loadOrders" :loading="loading" />
        </div>

        <el-table v-loading="loading" :data="orders" style="width: 100%" border stripe>
          <el-table-column prop="order_id" label="订单ID" min-width="120">
            <template #default="scope">
              <el-tooltip :content="scope.row.order_id" placement="top">
                <span class="text-truncate d-block">{{ formatOrderId(scope.row.order_id) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="market_id" label="市场ID" min-width="120">
            <template #default="scope">
              <el-tooltip :content="scope.row.market_id" placement="top">
                <span class="text-truncate d-block">{{ formatMarketId(scope.row.market_id) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="side" label="方向" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.side === 'BUY' ? 'success' : 'danger'" effect="dark" size="small">
                {{ scope.row.side }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" width="100">
            <template #default="scope">${{ formatPrice(scope.row.price) }}</template>
          </el-table-column>
          <el-table-column prop="size" label="数量" width="100">
            <template #default="scope">{{ formatNumber(scope.row.size) }}</template>
          </el-table-column>
          <el-table-column prop="filled_size" label="已成交" width="100">
            <template #default="scope">{{ formatNumber(scope.row.filled_size) }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getOrderStatusType(scope.row.status)" size="small">
                {{ getOrderStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="create_time" label="创建时间" width="160" sortable>
            <template #default="scope">{{ formatTime(scope.row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="scope">
              <el-button type="primary" link size="small" @click="monitorOrderAction(scope.row.order_id)">
                监控
              </el-button>
              <el-button type="warning" link size="small" @click="editOrder(scope.row)">
                编辑
              </el-button>
              <el-button type="danger" link size="small" @click="deleteOrderAction(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 编辑持仓对话框 -->
    <el-dialog v-model="editPositionDialog" title="编辑持仓" width="500px">
      <el-form :model="editPositionForm" label-width="120px">
        <el-form-item label="市场ID">
          <el-input v-model="editPositionForm.market_id" disabled />
        </el-form-item>
        <el-form-item label="方向">
          <el-tag :type="editPositionForm.side === 'YES' ? 'success' : 'danger'">
            {{ editPositionForm.side }}
          </el-tag>
        </el-form-item>
        <el-form-item label="入场价格">
          <el-input v-model="editPositionForm.entry_price" disabled />
        </el-form-item>
        <el-form-item label="当前价格">
          <el-input-number v-model="editPositionForm.current_price" :precision="4" :step="0.01" :min="0" :max="1" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editPositionForm.status">
            <el-option label="未平仓" value="open" />
            <el-option label="已平仓" value="closed" />
            <el-option label="监控中" value="monitoring" />
          </el-select>
        </el-form-item>
        <el-form-item label="结算结果" v-if="editPositionForm.status === 'closed'">
          <el-select v-model="editPositionForm.settlement_result">
            <el-option label="YES" value="YES" />
            <el-option label="NO" value="NO" />
          </el-select>
        </el-form-item>
        <el-form-item label="结算收益" v-if="editPositionForm.status === 'closed'">
          <el-input-number v-model="editPositionForm.settlement_payout" :precision="2" :step="1" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editPositionDialog = false">取消</el-button>
        <el-button type="primary" @click="savePosition" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑订单对话框 -->
    <el-dialog v-model="editOrderDialog" title="编辑订单" width="500px">
      <el-form :model="editOrderForm" label-width="120px">
        <el-form-item label="订单ID">
          <el-input v-model="editOrderForm.order_id" disabled />
        </el-form-item>
        <el-form-item label="市场ID">
          <el-input v-model="editOrderForm.market_id" disabled />
        </el-form-item>
        <el-form-item label="方向">
          <el-tag :type="editOrderForm.side === 'BUY' ? 'success' : 'danger'">
            {{ editOrderForm.side }}
          </el-tag>
        </el-form-item>
        <el-form-item label="价格">
          <el-input v-model="editOrderForm.price" disabled />
        </el-form-item>
        <el-form-item label="数量">
          <el-input v-model="editOrderForm.size" disabled />
        </el-form-item>
        <el-form-item label="已成交数量">
          <el-input-number v-model="editOrderForm.filled_size" :precision="2" :step="1" :min="0" :max="editOrderForm.size" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editOrderForm.status">
            <el-option label="待成交" value="pending" />
            <el-option label="已成交" value="filled" />
            <el-option label="已撤销" value="cancelled" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editOrderDialog = false">取消</el-button>
        <el-button type="primary" @click="saveOrder" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
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
  getPositionPriceCurve,
  updatePosition,
  deletePosition,
  updateOrder,
  deleteOrder
} from '@/api/positions'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Shop, DataAnalysis, CollectionTag, Setting } from '@element-plus/icons-vue'

export default {
  name: 'PositionMonitor',
  components: {
    apexchart: VueApexCharts,
    Refresh, Shop, DataAnalysis, CollectionTag, Setting
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

    // 编辑对话框状态
    const editPositionDialog = ref(false)
    const editOrderDialog = ref(false)
    const saving = ref(false)
    const editPositionForm = ref({
      id: null,
      market_id: '',
      side: '',
      entry_price: 0,
      current_price: 0,
      status: 'open',
      settlement_result: '',
      settlement_payout: 0
    })
    const editOrderForm = ref({
      order_id: '',
      market_id: '',
      side: '',
      price: 0,
      size: 0,
      filled_size: 0,
      status: 'pending'
    })

    // 图表相关 - 每个持仓独立的图表状态
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
        ElMessage.error('加载持仓列表失败')
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
        ElMessage.error('加载订单列表失败')
      } finally {
        loading.value = false
      }
    }

    // 监控持仓
    const monitorPositionAction = async (positionId) => {
      try {
        const response = await monitorPosition(positionId)
        if (response.success) {
          ElMessage.success('监控持仓成功')
          await loadPositions()
          await loadSummary()
        } else {
          ElMessage.error(response.message || '监控持仓失败')
        }
      } catch (error) {
        console.error('监控持仓失败:', error)
        ElMessage.error('监控持仓失败')
      }
    }

    // 监控订单
    const monitorOrderAction = async (orderId) => {
      try {
        const response = await monitorOrder(orderId)
        if (response.success) {
          ElMessage.success('监控订单成功')
          await loadOrders()
        } else {
          ElMessage.error(response.message || '监控订单失败')
        }
      } catch (error) {
        console.error('监控订单失败:', error)
        ElMessage.error('监控订单失败')
      }
    }

    // 编辑持仓
    const editPosition = (position) => {
      editPositionForm.value = {
        id: position.id,
        market_id: position.market_id,
        side: position.side,
        entry_price: position.entry_price,
        current_price: position.current_price || position.entry_price,
        status: position.status,
        settlement_result: position.settlement_result || '',
        settlement_payout: position.settlement_payout || 0
      }
      editPositionDialog.value = true
    }

    // 保存持仓
    const savePosition = async () => {
      saving.value = true
      try {
        const data = {
          current_price: editPositionForm.value.current_price,
          status: editPositionForm.value.status
        }

        if (editPositionForm.value.status === 'closed') {
          data.settlement_result = editPositionForm.value.settlement_result
          data.settlement_payout = editPositionForm.value.settlement_payout
        }

        const response = await updatePosition(editPositionForm.value.id, data)
        if (response.success) {
          ElMessage.success('更新持仓成功')
          editPositionDialog.value = false
          await loadPositions()
          await loadSummary()
        } else {
          ElMessage.error(response.message || '更新持仓失败')
        }
      } catch (error) {
        console.error('更新持仓失败:', error)
        ElMessage.error('更新持仓失败')
      } finally {
        saving.value = false
      }
    }

    // 删除持仓
    const deletePositionAction = async (position) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除持仓 ${position.market_id} 吗？此操作不可恢复！`,
          '删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        const response = await deletePosition(position.id)
        if (response.success) {
          ElMessage.success('删除持仓成功')
          await loadPositions()
          await loadSummary()
        } else {
          ElMessage.error(response.message || '删除持仓失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除持仓失败:', error)
          ElMessage.error('删除持仓失败')
        }
      }
    }

    // 编辑订单
    const editOrder = (order) => {
      editOrderForm.value = {
        order_id: order.order_id,
        market_id: order.market_id,
        side: order.side,
        price: order.price,
        size: order.size,
        filled_size: order.filled_size || 0,
        status: order.status
      }
      editOrderDialog.value = true
    }

    // 保存订单
    const saveOrder = async () => {
      saving.value = true
      try {
        const data = {
          status: editOrderForm.value.status,
          filled_size: editOrderForm.value.filled_size
        }

        const response = await updateOrder(editOrderForm.value.order_id, data)
        if (response.success) {
          ElMessage.success('更新订单成功')
          editOrderDialog.value = false
          await loadOrders()
        } else {
          ElMessage.error(response.message || '更新订单失败')
        }
      } catch (error) {
        console.error('更新订单失败:', error)
        ElMessage.error('更新订单失败')
      } finally {
        saving.value = false
      }
    }

    // 删除订单
    const deleteOrderAction = async (order) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除订单 ${order.order_id} 吗？此操作不可恢复！`,
          '删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        const response = await deleteOrder(order.order_id)
        if (response.success) {
          ElMessage.success('删除订单成功')
          await loadOrders()
        } else {
          ElMessage.error(response.message || '删除订单失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除订单失败:', error)
          ElMessage.error('删除订单失败')
        }
      }
    }

    // 处理行展开/收起
    const handleExpandChange = (row, expandedRows) => {
      const isExpanded = expandedRows.some(r => r.id === row.id)
      if (isExpanded) {
        // 如果是展开，且没有默认间隔，初始化为1d
        if (!chartIntervals.value[row.id]) {
          chartIntervals.value[row.id] = '1d'
        }
        // 自动加载图表
        loadPositionChart(row)
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
        ElMessage.error('加载价格曲线失败')
      } finally {
        chartLoadingStates.value[positionId] = false
      }
    }

    // 创建ApexCharts图表配置
    const createApexChart = (positionId, priceHistory, purchaseTime, position) => {
      // 处理数据
      const seriesData = priceHistory.map(item => ({
        x: new Date(item.timestamp).getTime(),
        y: item.price
      }))

      // 添加购买点
      const purchasePoint = {
        x: new Date(purchaseTime).getTime(),
        y: position.entry_price
      }

      chartSeries.value[positionId] = [{
        name: '市场价格',
        data: seriesData
      }]

      // 注解：购买点
      const annotations = {
        points: [{
          x: purchasePoint.x,
          y: purchasePoint.y,
          marker: {
            size: 6,
            fillColor: '#fff',
            strokeColor: '#2698FF',
            radius: 2,
            cssClass: 'apexcharts-custom-class'
          },
          label: {
            borderColor: '#2698FF',
            style: {
              color: '#fff',
              background: '#2698FF',
            },
            text: '买入点',
          }
        }],
        xaxis: [{
          x: purchasePoint.x,
          borderColor: '#999',
          yAxisIndex: 0,
          label: {
            show: true,
            text: '买入时间',
            style: {
              color: "#fff",
              background: '#775DD0'
            }
          }
        }]
      }

      chartOptions.value[positionId] = {
        chart: {
          type: 'line',
          height: 350,
          zoom: {
            enabled: true
          },
          toolbar: {
            show: true
          }
        },
        dataLabels: {
          enabled: false
        },
        stroke: {
          curve: 'smooth',
          width: 2
        },
        title: {
          text: undefined,
          align: 'left'
        },
        grid: {
          row: {
            colors: ['#f3f3f3', 'transparent'],
            opacity: 0.5
          },
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
          labels: {
            formatter: (value) => {
              return '$' + value.toFixed(3)
            }
          },
          title: {
            text: '价格'
          }
        },
        theme: {
          mode: 'light'
        },
        annotations: annotations,
        colors: ['#008FFB']
      }
    }

    // 格式化函数
    const formatDate = (dateStr) => {
      if (!dateStr) return '-'
      try {
        const date = new Date(dateStr)
        return date.toLocaleDateString('zh-CN')
      } catch {
        return dateStr
      }
    }

    const formatTime = (timeStr) => {
      if (!timeStr) return '-'
      try {
        const date = new Date(timeStr)
        return date.toLocaleString('zh-CN')
      } catch {
        return timeStr
      }
    }

    const formatNumber = (val) => {
      if (!val) return '0'
      const num = parseFloat(val)
      if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M'
      if (num >= 1000) return (num / 1000).toFixed(2) + 'K'
      return num.toFixed(2)
    }

    const formatPrice = (val) => {
      if (!val) return '0.00'
      return parseFloat(val).toFixed(3)
    }

    const formatPercent = (val) => {
      if (val === null || val === undefined) return '-'
      return (val * 100).toFixed(1) + '%'
    }

    const formatMarketId = (id) => {
      if (!id) return '-'
      return id.length > 8 ? id.substring(0, 8) + '...' : id
    }
    
    const formatOrderId = (id) => {
      if (!id) return '-'
      return id.length > 8 ? id.substring(0, 8) + '...' : id
    }

    // 状态辅助函数
    const getStatusType = (status) => {
      const map = {
        'open': 'success',
        'closed': 'info',
        'liquidated': 'danger'
      }
      return map[status] || 'info'
    }

    const getStatusText = (status) => {
      const map = {
        'open': '持仓中',
        'closed': '已平仓',
        'liquidated': '已清算'
      }
      return map[status] || status
    }

    const getOrderStatusType = (status) => {
      const map = {
        'pending': 'warning',
        'filled': 'success',
        'cancelled': 'info',
        'failed': 'danger'
      }
      return map[status] || 'info'
    }

    const getOrderStatusText = (status) => {
      const map = {
        'pending': '待成交',
        'filled': '已成交',
        'cancelled': '已撤销',
        'failed': '失败'
      }
      return map[status] || status
    }

    const getPnlClass = (pnl) => {
      if (!pnl) return ''
      return pnl > 0 ? 'pnl-positive' : (pnl < 0 ? 'pnl-negative' : '')
    }

    const getPnlTextClass = (pnl) => {
      if (!pnl) return ''
      return pnl > 0 ? 'text-success' : (pnl < 0 ? 'text-danger' : '')
    }

    onMounted(() => {
      loadSummary()
      loadPositions()
      // 监听全局刷新事件
      window.addEventListener('global-refresh', () => {
        loadSummary()
        loadPositions()
        loadOrders()
      })
    })

    return {
      summary,
      positions,
      orders,
      loading,
      activeTab,
      positionFilter,
      orderFilter,
      editPositionDialog,
      editOrderDialog,
      saving,
      editPositionForm,
      editOrderForm,
      chartOptions,
      chartSeries,
      chartIntervals,
      chartLoadingStates,
      loadSummary,
      loadPositions,
      loadOrders,
      monitorPositionAction,
      monitorOrderAction,
      editPosition,
      savePosition,
      deletePositionAction,
      editOrder,
      saveOrder,
      deleteOrderAction,
      handleExpandChange,
      loadPositionChart,
      formatDate,
      formatTime,
      formatNumber,
      formatPrice,
      formatPercent,
      formatMarketId,
      formatOrderId,
      getStatusType,
      getStatusText,
      getOrderStatusType,
      getOrderStatusText,
      getPnlClass,
      getPnlTextClass,
      Refresh,
      Shop,
      DataAnalysis,
      CollectionTag,
      Setting
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

.summary-card {
  height: 100%;
}

.card-header {
  font-weight: bold;
  color: var(--el-text-color-secondary);
}

.card-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--el-text-color-primary);
}

.pnl-positive .card-value { color: var(--el-color-success); }
.pnl-negative .card-value { color: var(--el-color-danger); }

.filter-bar {
  display: flex;
  align-items: center;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.d-block { display: block; }
.text-primary { color: var(--el-color-primary); }
.text-success { color: var(--el-color-success); }
.text-danger { color: var(--el-color-danger); }
.font-weight-bold { font-weight: bold; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
}

.reasons-list {
  margin: 0;
  padding-left: 15px;
}

.reasons-list li {
  font-size: 13px;
  margin-bottom: 4px;
}

.expanded-content {
  background-color: var(--el-fill-color-light);
}

/* Utility classes */
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.ml-2 { margin-left: 8px; }
.mr-1 { margin-right: 4px; }
.mr-2 { margin-right: 8px; }
.p-3 { padding: 12px; }
</style>