<template>
  <div class="page-container">
    <!-- 标题栏 -->
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-bold">
        {{ traceMode ? `Trace 追踪: ${currentTraceId}` : '日志管理' }}
      </h2>
      <div class="flex gap-2">
        <el-button v-if="traceMode" @click="exitTraceMode" icon="Back">返回</el-button>
        <el-button type="success" @click="refreshLogs" icon="Refresh" :loading="loading">刷新</el-button>
      </div>
    </div>

    <!-- 搜索过滤区域 -->
    <el-card v-if="!traceMode" class="mb-4" shadow="hover">
      <el-form :model="filters" label-position="top" size="default">
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="日志等级">
              <el-checkbox-group v-model="filters.level">
                <el-checkbox-button
                  v-for="level in logLevels"
                  :key="level.value"
                  :label="level.value"
                >
                  <span :style="{ color: level.color }">{{ level.label }}</span>
                </el-checkbox-button>
              </el-checkbox-group>
            </el-form-item>
          </el-col>
          
          <el-col :xs="24" :sm="8" :md="6">
            <el-form-item label="关键词">
              <el-input 
                v-model="filters.keyword" 
                placeholder="在消息内容中搜索..." 
                clearable
                @keyup.enter="searchLogs"
                prefix-icon="Search"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="8" :md="6">
            <el-form-item label="事件类型">
              <el-input 
                v-model="filters.event" 
                placeholder="如: API.REQUEST.START" 
                clearable
                @keyup.enter="searchLogs"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="8" :md="6">
            <el-form-item label="Trace ID">
              <el-input 
                v-model="filters.trace_id" 
                placeholder="如: TRC-xxx" 
                clearable
                @keyup.enter="searchLogs"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                value-format="YYYY-MM-DDTHH:mm:ss"
                style="width: 100%"
                @change="handleDateRangeChange"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="flex justify-end gap-2 mt-2">
          <el-button type="primary" @click="searchLogs" icon="Search" :loading="loading">搜索</el-button>
          <el-button @click="resetFilters" icon="RefreshLeft">重置</el-button>
          <el-button type="info" @click="showExportDialog = true" icon="Download">导出</el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 日志列表 -->
    <el-card shadow="never" class="table-card">
      <el-table
        v-loading="loading"
        :data="paginatedLogs"
        style="width: 100%"
        row-key="_ui_id"
        border
        stripe
      >
        <el-table-column type="expand">
          <template #default="props">
            <div class="p-4" style="background-color: var(--el-fill-color-lighter)">
               <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="时间戳">{{ props.row.ts }}</el-descriptions-item>
                  <el-descriptions-item label="事件码">
                    <el-tag size="small" effect="plain">{{ props.row.event_code }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="Trace ID">
                    <el-link type="primary" @click="trackTrace(props.row.trace_id)">{{ props.row.trace_id }}</el-link>
                  </el-descriptions-item>
                  <el-descriptions-item label="服务">{{ props.row.service }}</el-descriptions-item>
                  <el-descriptions-item label="错误码" v-if="props.row.error_code">
                    <span class="text-danger font-mono">{{ props.row.error_code }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="错误名称" v-if="props.row.error_name">
                    <span class="text-danger">{{ props.row.error_name }}</span>
                  </el-descriptions-item>
               </el-descriptions>
               
               <div class="mt-4">
                 <div class="font-bold mb-2" style="color: var(--el-text-color-regular)">消息内容:</div>
                 <div class="p-3 border rounded text-sm break-words" style="background-color: var(--el-bg-color); color: var(--el-text-color-secondary)">{{ props.row.msg }}</div>
               </div>

               <div v-if="props.row.extra && Object.keys(props.row.extra).length > 0" class="mt-4">
                 <div class="font-bold mb-2" style="color: var(--el-text-color-regular)">额外信息:</div>
                 <pre class="p-3 rounded overflow-auto text-xs font-mono" style="background-color: #1a1a1a; color: #67c23a">{{ formatJSON(props.row.extra) }}</pre>
               </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="等级" width="100" align="center">
          <template #default="scope">
            <el-tag :type="getLogLevelType(scope.row.level)" effect="dark">{{ scope.row.level }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.ts) }}
          </template>
        </el-table-column>

        <el-table-column prop="event" label="事件类型" width="200" show-overflow-tooltip />
        
        <el-table-column prop="msg" label="消息预览" show-overflow-tooltip />

      </el-table>

      <!-- 分页控件 -->
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="allLogs.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 导出对话框 -->
    <el-dialog
      v-model="showExportDialog"
      title="导出日志"
      width="400px"
    >
      <el-form label-position="top">
        <el-form-item label="选择导出格式">
          <el-radio-group v-model="exportFormat">
            <el-radio label="json" border>JSON 格式</el-radio>
            <el-radio label="csv" border>CSV 格式</el-radio>
            <el-radio label="txt" border>TXT 格式</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showExportDialog = false">取消</el-button>
          <el-button type="primary" @click="handleExport">确认导出</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { queryLogs, exportLogs } from '@/api/logs'
import { ElMessage } from 'element-plus'
import { Search, Refresh, RefreshLeft, Download, Back } from '@element-plus/icons-vue'

export default {
  name: 'LogManagement',
  setup() {
    const loading = ref(false)
    const allLogs = ref([])
    const showExportDialog = ref(false)
    const exportFormat = ref('json')
    const dateRange = ref([])

    // 分页相关
    const currentPage = ref(1)
    const pageSize = ref(50)

    // Trace追踪模式
    const traceMode = ref(false)
    const currentTraceId = ref('')

    // 日志等级配置
    const logLevels = [
      { value: 'INFO', label: 'INFO', color: '#409EFF' },
      { value: 'TRADE', label: 'TRADE', color: '#67C23A' },
      { value: 'WARN', label: 'WARN', color: '#E6A23C' },
      { value: 'ERROR', label: 'ERROR', color: '#F56C6C' },
      { value: 'DEBUG', label: 'DEBUG', color: '#909399' },
      { value: 'AUDIT', label: 'AUDIT', color: '#9C27B0' }
    ]

    // 过滤条件
    const filters = reactive({
      limit: 1000,
      level: [],
      event: '',
      keyword: '',
      trace_id: '',
      start_time: '',
      end_time: ''
    })

    // 监听日期范围变化
    const handleDateRangeChange = (val) => {
      if (val && val.length === 2) {
        filters.start_time = val[0]
        filters.end_time = val[1]
      } else {
        filters.start_time = ''
        filters.end_time = ''
      }
    }

    // 计算当前页显示的日志
    const paginatedLogs = computed(() => {
      const start = (currentPage.value - 1) * pageSize.value
      const end = start + pageSize.value
      return allLogs.value.slice(start, end)
    })

    // 格式化时间
    const formatTime = (isoTime) => {
      if (!isoTime) return ''
      const date = new Date(isoTime)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    // 获取日志等级对应的Element Plus type
    const getLogLevelType = (level) => {
      const map = {
        'INFO': 'primary',
        'TRADE': 'success',
        'WARN': 'warning',
        'ERROR': 'danger',
        'DEBUG': 'info',
        'AUDIT': ''
      }
      return map[level] || 'info'
    }

    // 格式化JSON
    const formatJSON = (obj) => {
      return JSON.stringify(obj, null, 2)
    }

    // 处理每页显示数量变化
    const handlePageSizeChange = (val) => {
      pageSize.value = val
      currentPage.value = 1
    }
    
    // 处理页码变化
    const handleCurrentChange = (val) => {
      currentPage.value = val
    }

    // 处理日志数据，确保每条日志都有唯一的ID
    const processLogs = (logs) => {
      return logs.map((log, index) => ({
        ...log,
        _ui_id: log.id || `log_${Date.now()}_${index}_${Math.random().toString(36).substr(2, 9)}`
      }))
    }

    // Trace追踪
    const trackTrace = async (traceId) => {
      traceMode.value = true
      currentTraceId.value = traceId

      // 使用trace_id过滤日志
      loading.value = true
      try {
        const params = {
          limit: 1000,
          trace_id: traceId
        }

        const response = await queryLogs(params)
        if (response.success) {
          allLogs.value = processLogs(response.data.logs)
          currentPage.value = 1
        }
      } catch (error) {
        console.error('追踪Trace失败:', error)
        ElMessage.error('追踪Trace失败')
      } finally {
        loading.value = false
      }
    }

    // 退出Trace追踪模式
    const exitTraceMode = () => {
      traceMode.value = false
      currentTraceId.value = ''
      filters.trace_id = ''
      searchLogs()
    }

    // 搜索日志
    const searchLogs = async () => {
      loading.value = true
      currentPage.value = 1

      try {
        const params = { ...filters }
        if (params.start_time) {
          params.start_time = new Date(params.start_time).toISOString()
        }
        if (params.end_time) {
          params.end_time = new Date(params.end_time).toISOString()
        }

        const response = await queryLogs(params)
        if (response.success) {
          allLogs.value = processLogs(response.data.logs)
        }
      } catch (error) {
        console.error('查询日志失败:', error)
        ElMessage.error('查询日志失败')
      } finally {
        loading.value = false
      }
    }

    // 刷新日志
    const refreshLogs = () => {
      if (traceMode.value) {
        trackTrace(currentTraceId.value)
      } else {
        searchLogs()
      }
    }

    // 重置过滤条件
    const resetFilters = () => {
      filters.limit = 1000
      filters.level = []
      filters.event = ''
      filters.keyword = ''
      filters.trace_id = ''
      filters.start_time = ''
      filters.end_time = ''
      dateRange.value = []
      currentPage.value = 1
      searchLogs()
    }

    // 导出日志
    const handleExport = async () => {
      try {
        // 转换时间格式
        const exportFilters = { ...filters }
        if (exportFilters.start_time) {
          exportFilters.start_time = new Date(exportFilters.start_time).toISOString()
        }
        if (exportFilters.end_time) {
          exportFilters.end_time = new Date(exportFilters.end_time).toISOString()
        }

        const response = await exportLogs({
          format: exportFormat.value,
          filters: exportFilters
        })

        // 处理下载
        if (exportFormat.value === 'json') {
          // JSON格式直接下载
          const blob = new Blob([JSON.stringify(response.data, null, 2)], {
            type: 'application/json'
          })
          downloadFile(blob, `logs_${Date.now()}.json`)
        } else {
          // CSV和TXT格式（已经是blob）
          const extension = exportFormat.value === 'csv' ? 'csv' : 'txt'
          downloadFile(response, `logs_${Date.now()}.${extension}`)
        }

        showExportDialog.value = false
        ElMessage.success('导出成功')
      } catch (error) {
        console.error('导出日志失败:', error)
        ElMessage.error('导出日志失败')
      }
    }

    // 下载文件
    const downloadFile = (blob, filename) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    }

    // 初始加载
    onMounted(() => {
      searchLogs()
    })

    return {
      loading,
      allLogs,
      paginatedLogs,
      showExportDialog,
      exportFormat,
      logLevels,
      filters,
      dateRange,
      currentPage,
      pageSize,
      traceMode,
      currentTraceId,
      formatTime,
      formatJSON,
      getLogLevelType,
      handleDateRangeChange,
      handlePageSizeChange,
      handleCurrentChange,
      trackTrace,
      exitTraceMode,
      searchLogs,
      refreshLogs,
      resetFilters,
      handleExport
    }
  }
}
</script>

<style scoped>
/* .log-management styles removed as we use .page-container */
</style>
