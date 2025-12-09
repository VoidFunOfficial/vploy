<template>
  <div class="profit-chart">
    <!-- 标题栏 -->
    <div class="header">
      <h2>收益曲线</h2>
      <div class="header-actions">
        <button class="btn-config" @click="openConfigDialog">⚙️ 钱包配置</button>
        <button class="btn-primary" @click="showAddDialog = true">➕ 添加记录</button>
        <button class="btn-refresh" @click="loadData">🔄 刷新</button>
      </div>
    </div>

    <!-- 筛选区域 -->
    <div class="filter-section">
      <div class="filter-item">
        <label>开始日期:</label>
        <input type="date" v-model="filters.startDate" @change="loadData" />
      </div>
      <div class="filter-item">
        <label>结束日期:</label>
        <input type="date" v-model="filters.endDate" @change="loadData" />
      </div>
      <div class="filter-item">
        <button class="btn-secondary" @click="resetFilters">重置</button>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-container">
      <div ref="chartRef" class="chart"></div>
    </div>

    <!-- 数据表格 -->
    <div class="data-table">
      <h3>收益记录</h3>
      <table>
        <thead>
          <tr>
            <th>日期</th>
            <th>预期收益</th>
            <th>实际收益</th>
            <th>总资金</th>
            <th>成功市场</th>
            <th>失败市场</th>
            <th>备注</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.record_date">
            <td>{{ record.record_date }}</td>
            <td :class="getProfitClass(record.expect_profit)">
              {{ formatNumber(record.expect_profit) }}
            </td>
            <td :class="getProfitClass(record.real_profit)">
              {{ formatNumber(record.real_profit) }}
            </td>
            <td>{{ formatNumber(record.total_fund) }}</td>
            <td>{{ record.success_market }}</td>
            <td>{{ record.lost_market }}</td>
            <td>{{ record.notes || '-' }}</td>
            <td>
              <button class="btn-edit" @click="editRecord(record)">编辑</button>
              <button class="btn-delete" @click="deleteRecord(record.record_date)">删除</button>
            </td>
          </tr>
          <tr v-if="records.length === 0">
            <td colspan="8" style="text-align: center; color: #999;">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加/编辑对话框 -->
    <Modal
      v-model:visible="showAddDialog"
      :title="editingRecord ? '编辑记录' : '添加记录'"
      @confirm="handleSave"
    >
      <div class="form-group">
        <label>日期 *</label>
        <input
          type="date"
          v-model="formData.record_date"
          :disabled="!!editingRecord"
        />
      </div>
      <div class="form-group">
        <label>预期收益 *</label>
        <input
          type="number"
          step="0.01"
          v-model.number="formData.expect_profit"
          placeholder="请输入预期收益"
        />
      </div>
      <div class="form-group">
        <label>实际收益 *</label>
        <input
          type="number"
          step="0.01"
          v-model.number="formData.real_profit"
          placeholder="请输入实际收益"
        />
      </div>
      <div class="form-group">
        <label>总资金</label>
        <input
          type="number"
          step="0.01"
          v-model.number="formData.total_fund"
          placeholder="留空则使用当前总资金"
        />
      </div>
      <div class="form-group">
        <label>成功市场数</label>
        <input
          type="number"
          v-model.number="formData.success_market"
          placeholder="留空则使用当前值"
        />
      </div>
      <div class="form-group">
        <label>失败市场数</label>
        <input
          type="number"
          v-model.number="formData.lost_market"
          placeholder="留空则使用当前值"
        />
      </div>
      <div class="form-group">
        <label>备注</label>
        <textarea
          v-model="formData.notes"
          placeholder="请输入备注信息"
          rows="3"
        ></textarea>
      </div>
    </Modal>

    <!-- 钱包配置对话框 -->
    <Modal
      v-model:visible="showConfigDialog"
      title="钱包参数配置"
      @confirm="handleConfigSave"
      width="600px"
    >
      <div class="config-form">
        <div class="config-section">
          <h4>资金状态</h4>
          <div class="form-row">
            <div class="form-group">
              <label>总资金</label>
              <input
                type="number"
                step="0.01"
                v-model.number="configData.total_fund"
                placeholder="总资金"
              />
            </div>
            <div class="form-group">
              <label>锁定资金</label>
              <input
                type="number"
                step="0.01"
                v-model.number="configData.locked_fund"
                placeholder="锁定资金"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>可用现金</label>
              <input
                type="number"
                step="0.01"
                v-model.number="configData.available_cash"
                placeholder="可用现金"
              />
            </div>
          </div>
        </div>

        <div class="config-section">
          <h4>盈亏数据</h4>
          <div class="form-row">
            <div class="form-group">
              <label>总亏损</label>
              <input
                type="number"
                step="0.01"
                v-model.number="configData.loss"
                placeholder="总亏损"
              />
            </div>
            <div class="form-group">
              <label>预期盈利</label>
              <input
                type="number"
                step="0.01"
                v-model.number="configData.expect_profit"
                placeholder="预期盈利"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>实际盈利</label>
              <input
                type="number"
                step="0.01"
                v-model.number="configData.real_profit"
                placeholder="实际盈利"
              />
            </div>
          </div>
        </div>

        <div class="config-section">
          <h4>市场统计</h4>
          <div class="form-row">
            <div class="form-group">
              <label>成功市场数</label>
              <input
                type="number"
                v-model.number="configData.success_market"
                placeholder="成功市场数"
              />
            </div>
            <div class="form-group">
              <label>失败市场数</label>
              <input
                type="number"
                v-model.number="configData.lost_market"
                placeholder="失败市场数"
              />
            </div>
          </div>
        </div>

        <div class="config-tip">
          <p>💡 提示：修改这些参数会直接更新钱包状态，请谨慎操作！</p>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDailyRecords, addDailyRecord, updateDailyRecord, deleteDailyRecord, getPurseStatus, updatePurseStatus } from '@/api/purse'
import { toast, confirm, Modal } from '@/components/Notification'

export default {
  name: 'ProfitChart',
  components: {
    Modal
  },
  setup() {
    const chartRef = ref(null)
    let chartInstance = null
    const records = ref([])
    const showAddDialog = ref(false)
    const editingRecord = ref(null)

    // 钱包配置对话框
    const showConfigDialog = ref(false)
    const configData = reactive({
      total_fund: 0,
      locked_fund: 0,
      available_cash: 0,
      loss: 0,
      expect_profit: 0,
      real_profit: 0,
      success_market: 0,
      lost_market: 0
    })

    // 筛选条件
    const filters = reactive({
      startDate: '',
      endDate: ''
    })

    // 表单数据
    const formData = reactive({
      record_date: '',
      expect_profit: 0,
      real_profit: 0,
      total_fund: null,
      success_market: null,
      lost_market: null,
      notes: ''
    })

    // 初始化图表
    const initChart = () => {
      if (!chartRef.value) return

      chartInstance = echarts.init(chartRef.value)

      const option = {
        title: {
          text: '收益趋势图',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        legend: {
          data: ['预期收益', '实际收益'],
          top: 30
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: []
        },
        yAxis: {
          type: 'value',
          name: '收益'
        },
        series: [
          {
            name: '预期收益',
            type: 'line',
            data: [],
            smooth: true,
            itemStyle: {
              color: '#5470c6'
            }
          },
          {
            name: '实际收益',
            type: 'line',
            data: [],
            smooth: true,
            itemStyle: {
              color: '#91cc75'
            }
          }
        ]
      }

      chartInstance.setOption(option)
    }

    // 更新图表数据
    const updateChart = () => {
      if (!chartInstance || records.value.length === 0) return

      // 按日期升序排序
      const sortedRecords = [...records.value].reverse()

      const dates = sortedRecords.map(r => r.record_date)
      const expectProfits = sortedRecords.map(r => r.expect_profit)
      const realProfits = sortedRecords.map(r => r.real_profit)

      chartInstance.setOption({
        xAxis: {
          data: dates
        },
        series: [
          {
            data: expectProfits
          },
          {
            data: realProfits
          }
        ]
      })
    }

    // 加载数据
    const loadData = async () => {
      try {
        const params = {}
        if (filters.startDate) params.start_date = filters.startDate
        if (filters.endDate) params.end_date = filters.endDate

        const response = await getDailyRecords(params)
        if (response.success) {
          records.value = response.data
          await nextTick()
          updateChart()
        } else {
          toast.error(response.message || '加载数据失败')
        }
      } catch (error) {
        console.error('加载数据失败:', error)
        toast.error('加载数据失败')
      }
    }

    // 重置筛选条件
    const resetFilters = () => {
      filters.startDate = ''
      filters.endDate = ''
      loadData()
    }

    // 重置表单
    const resetForm = () => {
      formData.record_date = new Date().toISOString().split('T')[0]
      formData.expect_profit = 0
      formData.real_profit = 0
      formData.total_fund = null
      formData.success_market = null
      formData.lost_market = null
      formData.notes = ''
    }

    // 打开钱包配置对话框
    const openConfigDialog = async () => {
      try {
        // 加载当前钱包状态
        const response = await getPurseStatus()
        if (response.success) {
          const status = response.data
          configData.total_fund = status.total_fund || 0
          configData.locked_fund = status.locked_fund || 0
          configData.available_cash = status.available_cash || 0
          configData.loss = status.loss || 0
          configData.expect_profit = status.expect_profit || 0
          configData.real_profit = status.real_profit || 0
          configData.success_market = status.success_market || 0
          configData.lost_market = status.lost_market || 0
          showConfigDialog.value = true
        } else {
          toast.error(response.message || '加载钱包状态失败')
        }
      } catch (error) {
        console.error('加载钱包状态失败:', error)
        toast.error('加载钱包状态失败')
      }
    }

    // 保存钱包配置
    const handleConfigSave = async () => {
      try {
        // 构建更新数据
        const updateData = {
          total_fund: configData.total_fund,
          locked_fund: configData.locked_fund,
          available_cash: configData.available_cash,
          loss: configData.loss,
          expect_profit: configData.expect_profit,
          real_profit: configData.real_profit,
          success_market: configData.success_market,
          lost_market: configData.lost_market
        }

        const response = await updatePurseStatus(updateData)
        if (response.success) {
          toast.success('钱包配置更新成功')
          showConfigDialog.value = false
          // 刷新数据
          loadData()
        } else {
          toast.error(response.message || '更新失败')
        }
      } catch (error) {
        console.error('更新钱包配置失败:', error)
        toast.error('更新钱包配置失败')
      }
    }

    // 编辑记录
    const editRecord = (record) => {
      editingRecord.value = record
      formData.record_date = record.record_date
      formData.expect_profit = record.expect_profit
      formData.real_profit = record.real_profit
      formData.total_fund = record.total_fund
      formData.success_market = record.success_market
      formData.lost_market = record.lost_market
      formData.notes = record.notes || ''
      showAddDialog.value = true
    }

    // 保存记录
    const handleSave = async () => {
      // 验证必填字段
      if (!formData.record_date) {
        toast.error('请选择日期')
        return
      }
      if (formData.expect_profit === null || formData.expect_profit === undefined) {
        toast.error('请输入预期收益')
        return
      }
      if (formData.real_profit === null || formData.real_profit === undefined) {
        toast.error('请输入实际收益')
        return
      }

      try {
        const data = {
          record_date: formData.record_date,
          expect_profit: formData.expect_profit,
          real_profit: formData.real_profit
        }

        // 只在有值时添加可选字段
        if (formData.total_fund !== null && formData.total_fund !== undefined) {
          data.total_fund = formData.total_fund
        }
        if (formData.success_market !== null && formData.success_market !== undefined) {
          data.success_market = formData.success_market
        }
        if (formData.lost_market !== null && formData.lost_market !== undefined) {
          data.lost_market = formData.lost_market
        }
        if (formData.notes) {
          data.notes = formData.notes
        }

        let response
        if (editingRecord.value) {
          // 更新记录
          response = await updateDailyRecord(formData.record_date, data)
        } else {
          // 添加记录
          response = await addDailyRecord(data)
        }

        if (response.success) {
          toast.success(response.message || '保存成功')
          showAddDialog.value = false
          editingRecord.value = null
          resetForm()
          loadData()
        } else {
          toast.error(response.message || '保存失败')
        }
      } catch (error) {
        console.error('保存失败:', error)
        toast.error('保存失败')
      }
    }

    // 删除记录
    const deleteRecord = async (recordDate) => {
      const confirmed = await confirm(`确定要删除 ${recordDate} 的记录吗？`)
      if (!confirmed) return

      try {
        const response = await deleteDailyRecord(recordDate)
        if (response.success) {
          toast.success(response.message || '删除成功')
          loadData()
        } else {
          toast.error(response.message || '删除失败')
        }
      } catch (error) {
        console.error('删除失败:', error)
        toast.error('删除失败')
      }
    }

    // 格式化数字
    const formatNumber = (num) => {
      if (num === null || num === undefined) return '-'
      return num.toFixed(2)
    }

    // 获取收益样式类
    const getProfitClass = (value) => {
      if (value > 0) return 'profit-positive'
      if (value < 0) return 'profit-negative'
      return ''
    }

    // 监听对话框关闭
    const handleDialogClose = () => {
      editingRecord.value = null
      resetForm()
    }

    // 组件挂载时初始化
    onMounted(async () => {
      resetForm()
      await nextTick()
      initChart()
      loadData()

      // 监听窗口大小变化
      window.addEventListener('resize', () => {
        if (chartInstance) {
          chartInstance.resize()
        }
      })
    })

    return {
      chartRef,
      records,
      showAddDialog,
      showConfigDialog,
      editingRecord,
      filters,
      formData,
      configData,
      loadData,
      resetFilters,
      editRecord,
      handleSave,
      deleteRecord,
      formatNumber,
      getProfitClass,
      handleDialogClose,
      openConfigDialog,
      handleConfigSave
    }
  }
}
</script>

<style scoped>
/* 主容器 */
.profit-chart {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100%;
}

/* 标题栏 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px 20px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.header h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 筛选区域 */
.filter-section {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px 20px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-item label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
}

.filter-item input[type="date"] {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

/* 图表容器 */
.chart-container {
  margin-bottom: 20px;
  padding: 20px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.chart {
  width: 100%;
  height: 400px;
}

/* 数据表格 */
.data-table {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
}

.data-table h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.data-table table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.data-table th {
  background-color: #f8f8f8;
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.data-table td {
  font-size: 14px;
  color: #666;
}

.data-table tbody tr:hover {
  background-color: #f9f9f9;
}

/* 收益样式 */
.profit-positive {
  color: #52c41a;
  font-weight: 600;
}

.profit-negative {
  color: #f5222d;
  font-weight: 600;
}

/* 按钮样式 */
.btn-primary,
.btn-secondary,
.btn-refresh,
.btn-config,
.btn-edit,
.btn-delete {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: opacity 0.2s;
}

.btn-primary {
  background-color: #1890ff;
  color: white;
}

.btn-primary:hover {
  opacity: 0.8;
}

.btn-config {
  background-color: #722ed1;
  color: white;
}

.btn-config:hover {
  opacity: 0.8;
}

.btn-secondary {
  background-color: #d9d9d9;
  color: #333;
}

.btn-secondary:hover {
  opacity: 0.8;
}

.btn-refresh {
  background-color: #52c41a;
  color: white;
}

.btn-refresh:hover {
  opacity: 0.8;
}

.btn-edit {
  padding: 4px 12px;
  background-color: #1890ff;
  color: white;
  margin-right: 5px;
}

.btn-edit:hover {
  opacity: 0.8;
}

.btn-delete {
  padding: 4px 12px;
  background-color: #ff4d4f;
  color: white;
}

.btn-delete:hover {
  opacity: 0.8;
}

/* 表单样式 */
.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #1890ff;
}

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

/* 配置表单样式 */
.config-form {
  max-height: 600px;
  overflow-y: auto;
}

.config-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.config-section:last-of-type {
  border-bottom: none;
}

.config-section h4 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: #333;
  font-weight: 600;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.form-row:last-child {
  margin-bottom: 0;
}

.form-row .form-group {
  margin-bottom: 0;
}

.config-tip {
  margin-top: 20px;
  padding: 12px 16px;
  background-color: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 4px;
}

.config-tip p {
  margin: 0;
  font-size: 13px;
  color: #0050b3;
  line-height: 1.5;
}
</style>
