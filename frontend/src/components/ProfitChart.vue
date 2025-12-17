<template>
  <div class="profit-chart">
    <!-- 标题栏 -->
    <div class="header-actions mb-4">
      <div class="left">
        <h2>收益曲线</h2>
      </div>
      <div class="right">
        <el-button-group>
          <el-button type="primary" :icon="Wallet" @click="openConfigDialog">钱包配置</el-button>
          <el-button type="success" :icon="Plus" @click="showAddDialog = true">添加记录</el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 筛选区域 -->
    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="filters.startDate"
            type="date"
            placeholder="选择开始日期"
            value-format="YYYY-MM-DD"
            @change="loadData"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="filters.endDate"
            type="date"
            placeholder="选择结束日期"
            value-format="YYYY-MM-DD"
            @change="loadData"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters" :icon="Refresh">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 图表区域 -->
    <el-card shadow="hover" class="mb-4 chart-card">
      <div ref="chartRef" class="chart"></div>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="hover" class="data-table-card">
      <template #header>
        <div class="card-header">
          <span>收益记录</span>
        </div>
      </template>
      <el-table :data="records" style="width: 100%" border stripe v-loading="loading">
        <el-table-column prop="record_date" label="日期" width="120" sortable />
        <el-table-column prop="expect_profit" label="预期收益" width="120">
          <template #default="scope">
            <span :class="getProfitClass(scope.row.expect_profit)">
              {{ formatNumber(scope.row.expect_profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="real_profit" label="实际收益" width="120">
          <template #default="scope">
            <span :class="getProfitClass(scope.row.real_profit)">
              {{ formatNumber(scope.row.real_profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="total_fund" label="总资金" width="120">
          <template #default="scope">{{ formatNumber(scope.row.total_fund) }}</template>
        </el-table-column>
        <el-table-column prop="success_market" label="成功市场" width="100" align="center" />
        <el-table-column prop="lost_market" label="失败市场" width="100" align="center" />
        <el-table-column prop="notes" label="备注" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="scope">
            <el-button link type="primary" size="small" :icon="Edit" @click="editRecord(scope.row)">编辑</el-button>
            <el-popconfirm title="确定要删除此记录吗？" @confirm="deleteRecord(scope.row.record_date)">
              <template #reference>
                <el-button link type="danger" size="small" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingRecord ? '编辑记录' : '添加记录'"
      width="500px"
      @closed="handleDialogClose"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="日期" required>
          <el-date-picker
            v-model="formData.record_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            :disabled="!!editingRecord"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="预期收益" required>
          <el-input-number v-model="formData.expect_profit" :precision="2" :step="0.1" style="width: 100%" controls-position="right" />
        </el-form-item>
        <el-form-item label="实际收益" required>
          <el-input-number v-model="formData.real_profit" :precision="2" :step="0.1" style="width: 100%" controls-position="right" />
        </el-form-item>
        <el-form-item label="总资金">
          <el-input-number v-model="formData.total_fund" :precision="2" :step="100" placeholder="留空则使用当前总资金" style="width: 100%" controls-position="right" />
        </el-form-item>
        <el-form-item label="成功市场数">
          <el-input-number v-model="formData.success_market" :step="1" placeholder="留空则使用当前值" style="width: 100%" controls-position="right" />
        </el-form-item>
        <el-form-item label="失败市场数">
          <el-input-number v-model="formData.lost_market" :step="1" placeholder="留空则使用当前值" style="width: 100%" controls-position="right" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input type="textarea" v-model="formData.notes" rows="3" placeholder="请输入备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 钱包配置对话框 -->
    <el-dialog
      v-model="showConfigDialog"
      title="钱包参数配置"
      width="600px"
    >
      <el-alert
        title="提示：修改这些参数会直接更新钱包状态，请谨慎操作！"
        type="warning"
        show-icon
        :closable="false"
        class="mb-4"
      />
      
      <el-form :model="configData" label-width="100px">
        <div class="section-title">资金状态</div>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="总资金">
              <el-input-number v-model="configData.total_fund" :precision="2" :step="100" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="锁定资金">
              <el-input-number v-model="configData.locked_fund" :precision="2" :step="100" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="可用现金">
              <el-input-number v-model="configData.available_cash" :precision="2" :step="100" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider />
        
        <div class="section-title">盈亏数据</div>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="总亏损">
              <el-input-number v-model="configData.loss" :precision="2" :step="10" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预期盈利">
              <el-input-number v-model="configData.expect_profit" :precision="2" :step="10" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="实际盈利">
              <el-input-number v-model="configData.real_profit" :precision="2" :step="10" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider />

        <div class="section-title">市场统计</div>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="成功市场数">
              <el-input-number v-model="configData.success_market" :step="1" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="失败市场数">
              <el-input-number v-model="configData.lost_market" :step="1" style="width: 100%" controls-position="right" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showConfigDialog = false">取消</el-button>
          <el-button type="primary" @click="handleConfigSave" :loading="configSaving">更新配置</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDailyRecords, addDailyRecord, updateDailyRecord, deleteDailyRecord, getPurseStatus, updatePurseStatus } from '@/api/purse'
import { ElMessage } from 'element-plus'
import { Wallet, Plus, Refresh, Edit, Delete } from '@element-plus/icons-vue'

export default {
  name: 'ProfitChart',
  setup() {
    const chartRef = ref(null)
    let chartInstance = null
    const records = ref([])
    const showAddDialog = ref(false)
    const editingRecord = ref(null)
    const loading = ref(false)
    const saving = ref(false)
    const configSaving = ref(false)

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
      loading.value = true
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
          ElMessage.error(response.message || '加载数据失败')
        }
      } catch (error) {
        console.error('加载数据失败:', error)
        ElMessage.error('加载数据失败')
      } finally {
        loading.value = false
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
          ElMessage.error(response.message || '加载钱包状态失败')
        }
      } catch (error) {
        console.error('加载钱包状态失败:', error)
        ElMessage.error('加载钱包状态失败')
      }
    }

    // 保存钱包配置
    const handleConfigSave = async () => {
      configSaving.value = true
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
          ElMessage.success('钱包配置更新成功')
          showConfigDialog.value = false
          // 刷新数据
          loadData()
        } else {
          ElMessage.error(response.message || '更新失败')
        }
      } catch (error) {
        console.error('更新钱包配置失败:', error)
        ElMessage.error('更新钱包配置失败')
      } finally {
        configSaving.value = false
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
        ElMessage.warning('请选择日期')
        return
      }
      if (formData.expect_profit === null || formData.expect_profit === undefined) {
        ElMessage.warning('请输入预期收益')
        return
      }
      if (formData.real_profit === null || formData.real_profit === undefined) {
        ElMessage.warning('请输入实际收益')
        return
      }

      saving.value = true
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
          ElMessage.success(response.message || '保存成功')
          showAddDialog.value = false
          editingRecord.value = null
          resetForm()
          loadData()
        } else {
          ElMessage.error(response.message || '保存失败')
        }
      } catch (error) {
        console.error('保存失败:', error)
        ElMessage.error('保存失败')
      } finally {
        saving.value = false
      }
    }

    // 删除记录
    const deleteRecord = async (recordDate) => {
      try {
        const response = await deleteDailyRecord(recordDate)
        if (response.success) {
          ElMessage.success(response.message || '删除成功')
          loadData()
        } else {
          ElMessage.error(response.message || '删除失败')
        }
      } catch (error) {
        console.error('删除失败:', error)
        ElMessage.error('删除失败')
      }
    }

    // 格式化数字
    const formatNumber = (num) => {
      if (num === null || num === undefined) return '-'
      return num.toFixed(2)
    }

    // 获取收益样式类
    const getProfitClass = (value) => {
      if (value > 0) return 'text-success font-weight-bold'
      if (value < 0) return 'text-danger font-weight-bold'
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
      loading,
      saving,
      configSaving,
      loadData,
      resetFilters,
      editRecord,
      handleSave,
      deleteRecord,
      formatNumber,
      getProfitClass,
      handleDialogClose,
      openConfigDialog,
      handleConfigSave,
      Wallet,
      Plus,
      Refresh,
      Edit,
      Delete
    }
  }
}
</script>

<style scoped>
.profit-chart {
  /* 使用 page-container 替代 */
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions h2 {
  font-size: 20px;
  color: var(--el-text-color-primary);
  margin: 0;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.chart {
  width: 100%;
  height: 400px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 15px;
  margin-top: 10px;
}

.text-success { color: var(--el-color-success); }
.text-danger { color: var(--el-color-danger); }
.font-weight-bold { font-weight: bold; }
</style>