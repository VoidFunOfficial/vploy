<template>
  <div class="log-management">
    <!-- 标题栏 -->
    <div class="header">
      <h2>{{ traceMode ? `Trace 追踪: ${currentTraceId}` : '日志管理' }}</h2>
      <div class="header-actions">
        <button v-if="traceMode" class="btn-back" @click="exitTraceMode">← 返回</button>
        <button class="btn-refresh" @click="refreshLogs">🔄 刷新</button>
      </div>
    </div>

    <!-- 搜索过滤区域 -->
    <div class="filter-section" v-if="!traceMode">
      <div class="filter-row">
        <!-- 日志等级筛选 -->
        <div class="filter-item full-width">
          <label>日志等级:</label>
          <div class="checkbox-group">
            <label v-for="level in logLevels" :key="level.value" class="checkbox-label">
              <input
                type="checkbox"
                :value="level.value"
                v-model="filters.level"
              />
              <span :style="{ color: level.color }">{{ level.label }}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="filter-row">
        <!-- 关键词搜索 -->
        <div class="filter-item">
          <label>关键词:</label>
          <input
            type="text"
            v-model="filters.keyword"
            placeholder="在消息内容中搜索..."
            @keyup.enter="searchLogs"
          />
        </div>

        <!-- 事件类型 -->
        <div class="filter-item">
          <label>事件类型:</label>
          <input
            type="text"
            v-model="filters.event"
            placeholder="如: API.REQUEST.START"
            @keyup.enter="searchLogs"
          />
        </div>

        <!-- trace_id -->
        <div class="filter-item">
          <label>Trace ID:</label>
          <input
            type="text"
            v-model="filters.trace_id"
            placeholder="如: TRC-xxx"
            @keyup.enter="searchLogs"
          />
        </div>
      </div>

      <div class="filter-row">
        <!-- 时间范围 -->
        <div class="filter-item">
          <label>开始时间:</label>
          <input
            type="datetime-local"
            v-model="filters.start_time"
          />
        </div>

        <div class="filter-item">
          <label>结束时间:</label>
          <input
            type="datetime-local"
            v-model="filters.end_time"
          />
        </div>

        <!-- 每页显示数量 -->
        <div class="filter-item">
          <label>每页显示:</label>
          <select v-model.number="pageSize" @change="handlePageSizeChange">
            <option :value="20">20条</option>
            <option :value="50">50条</option>
            <option :value="100">100条</option>
          </select>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="filter-actions">
        <button class="btn-primary" @click="searchLogs">🔍 搜索</button>
        <button class="btn-secondary" @click="resetFilters">🔄 重置</button>
        <button class="btn-export" @click="showExportDialog = true">📥 导出</button>
      </div>
    </div>

    <!-- 日志列表 -->
    <div class="log-list">
      <div v-if="loading" class="loading">加载中...</div>

      <div v-else-if="paginatedLogs.length === 0" class="empty">
        暂无日志数据
      </div>

      <div v-else class="log-items">
        <div
          v-for="(log, index) in paginatedLogs"
          :key="getLogKey(log, index)"
          :class="['log-item', `level-${log.level.toLowerCase()}`]"
        >
          <!-- 日志头部 -->
          <div class="log-header">
            <span :class="['log-level', `level-${log.level.toLowerCase()}`]">
              {{ log.level }}
            </span>
            <span class="log-time">{{ formatTime(log.ts) }}</span>
            <span class="log-event">{{ truncateText(log.event, 30) }}</span>
            <span class="log-event-code">{{ log.event_code }}</span>
            <span class="log-message-preview">{{ truncateText(log.msg, 50) }}</span>
            <button
              class="btn-expand"
              @click="toggleExpand(getLogKey(log, index))"
            >
              {{ expandedLogs.has(getLogKey(log, index)) ? '收起 ▲' : '展开 ▼' }}
            </button>
          </div>

          <!-- 展开的详细信息 -->
          <div v-if="expandedLogs.has(getLogKey(log, index))" class="log-details">
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">时间戳</span>
                <span class="detail-value">{{ log.ts }}</span>
              </div>

              <div class="detail-item">
                <span class="detail-label">日志等级</span>
                <span :class="['detail-value', 'level-badge', `level-${log.level.toLowerCase()}`]">
                  {{ log.level }}
                </span>
              </div>

              <div class="detail-item">
                <span class="detail-label">事件类型</span>
                <span class="detail-value">{{ log.event }}</span>
              </div>

              <div class="detail-item">
                <span class="detail-label">事件码</span>
                <span class="detail-value event-code-badge">{{ log.event_code }}</span>
              </div>

              <div class="detail-item">
                <span class="detail-label">Trace ID</span>
                <span class="detail-value trace-id-link" @click="trackTrace(log.trace_id)">
                  {{ log.trace_id }}
                </span>
              </div>

              <div class="detail-item">
                <span class="detail-label">服务名称</span>
                <span class="detail-value">{{ log.service }}</span>
              </div>

              <div v-if="log.error_code" class="detail-item">
                <span class="detail-label">错误码</span>
                <span class="detail-value error-code">{{ log.error_code }}</span>
              </div>

              <div v-if="log.error_name" class="detail-item">
                <span class="detail-label">错误名称</span>
                <span class="detail-value error-name">{{ log.error_name }}</span>
              </div>
            </div>

            <div class="detail-item full-width">
              <span class="detail-label">消息内容</span>
              <div class="detail-value message-content">{{ log.msg }}</div>
            </div>

            <div v-if="log.extra && Object.keys(log.extra).length > 0" class="detail-item full-width">
              <span class="detail-label">额外信息</span>
              <pre class="detail-value json-content">{{ formatJSON(log.extra) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页控件 -->
    <div class="pagination" v-if="!loading && allLogs.length > 0">
      <div class="pagination-info">
        共 {{ allLogs.length }} 条日志，当前第 {{ currentPage }} / {{ totalPages }} 页
      </div>
      <div class="pagination-controls">
        <button
          class="btn-page"
          :disabled="currentPage === 1"
          @click="goToPage(1)"
        >
          首页
        </button>
        <button
          class="btn-page"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          上一页
        </button>

        <div class="page-numbers">
          <button
            v-for="page in visiblePages"
            :key="page"
            :class="['btn-page-number', { active: page === currentPage }]"
            @click="goToPage(page)"
          >
            {{ page }}
          </button>
        </div>

        <button
          class="btn-page"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          下一页
        </button>
        <button
          class="btn-page"
          :disabled="currentPage === totalPages"
          @click="goToPage(totalPages)"
        >
          末页
        </button>

        <div class="page-jump">
          <span>跳转到</span>
          <input
            type="number"
            v-model.number="jumpPage"
            @keyup.enter="handlePageJump"
            min="1"
            :max="totalPages"
          />
          <button class="btn-jump" @click="handlePageJump">GO</button>
        </div>
      </div>
    </div>

    <!-- 导出对话框 -->
    <div v-if="showExportDialog" class="modal-overlay" @click="showExportDialog = false">
      <div class="modal-content" @click.stop>
        <h3>导出日志</h3>
        <div class="export-options">
          <label>
            <input type="radio" v-model="exportFormat" value="json" />
            JSON 格式
          </label>
          <label>
            <input type="radio" v-model="exportFormat" value="csv" />
            CSV 格式
          </label>
          <label>
            <input type="radio" v-model="exportFormat" value="txt" />
            TXT 格式
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn-primary" @click="handleExport">确认导出</button>
          <button class="btn-secondary" @click="showExportDialog = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { queryLogs, exportLogs } from '@/api/logs'

export default {
  name: 'LogManagement',
  setup() {
    const loading = ref(false)
    const allLogs = ref([])
    const expandedLogs = ref(new Set())
    const showExportDialog = ref(false)
    const exportFormat = ref('json')

    // 分页相关
    const currentPage = ref(1)
    const pageSize = ref(50)
    const jumpPage = ref(1)

    // Trace追踪模式
    const traceMode = ref(false)
    const currentTraceId = ref('')

    // 日志等级配置
    const logLevels = [
      { value: 'INFO', label: 'INFO', color: '#2196f3' },
      { value: 'TRADE', label: 'TRADE', color: '#4caf50' },
      { value: 'WARN', label: 'WARN', color: '#ff9800' },
      { value: 'ERROR', label: 'ERROR', color: '#f44336' },
      { value: 'DEBUG', label: 'DEBUG', color: '#9e9e9e' },
      { value: 'AUDIT', label: 'AUDIT', color: '#9c27b0' }
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

    // 计算总页数
    const totalPages = computed(() => {
      return Math.ceil(allLogs.value.length / pageSize.value) || 1
    })

    // 计算当前页显示的日志
    const paginatedLogs = computed(() => {
      const start = (currentPage.value - 1) * pageSize.value
      const end = start + pageSize.value
      return allLogs.value.slice(start, end)
    })

    // 计算可见的页码
    const visiblePages = computed(() => {
      const pages = []
      const total = totalPages.value
      const current = currentPage.value

      // 显示当前页前后各2页
      let start = Math.max(1, current - 2)
      let end = Math.min(total, current + 2)

      // 确保至少显示5页
      if (end - start < 4) {
        if (start === 1) {
          end = Math.min(total, start + 4)
        } else if (end === total) {
          start = Math.max(1, end - 4)
        }
      }

      for (let i = start; i <= end; i++) {
        pages.push(i)
      }

      return pages
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

    // 截断文本
    const truncateText = (text, maxLength) => {
      if (!text) return ''
      if (text.length <= maxLength) return text
      return text.substring(0, maxLength) + '...'
    }

    // 格式化JSON
    const formatJSON = (obj) => {
      return JSON.stringify(obj, null, 2)
    }

    // 获取日志唯一键
    const getLogKey = (log, index) => {
      return `${log.ts}-${log.trace_id}-${index}`
    }

    // 切换展开/折叠
    const toggleExpand = (key) => {
      if (expandedLogs.value.has(key)) {
        expandedLogs.value.delete(key)
      } else {
        expandedLogs.value.add(key)
      }
      expandedLogs.value = new Set(expandedLogs.value)
    }

    // 跳转到指定页
    const goToPage = (page) => {
      if (page < 1 || page > totalPages.value) return
      currentPage.value = page
      jumpPage.value = page
    }

    // 处理页码跳转
    const handlePageJump = () => {
      const page = parseInt(jumpPage.value)
      if (page >= 1 && page <= totalPages.value) {
        goToPage(page)
      } else {
        jumpPage.value = currentPage.value
      }
    }

    // 处理每页显示数量变化
    const handlePageSizeChange = () => {
      currentPage.value = 1
      jumpPage.value = 1
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
          allLogs.value = response.data.logs
          currentPage.value = 1
          expandedLogs.value.clear()
        }
      } catch (error) {
        console.error('追踪Trace失败:', error)
        alert('追踪Trace失败')
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
      expandedLogs.value.clear()
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
          allLogs.value = response.data.logs
        }
      } catch (error) {
        console.error('查询日志失败:', error)
        alert('查询日志失败')
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
        alert('导出成功')
      } catch (error) {
        console.error('导出日志失败:', error)
        alert('导出日志失败')
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
      expandedLogs,
      showExportDialog,
      exportFormat,
      logLevels,
      filters,
      currentPage,
      pageSize,
      totalPages,
      visiblePages,
      jumpPage,
      traceMode,
      currentTraceId,
      formatTime,
      truncateText,
      formatJSON,
      getLogKey,
      toggleExpand,
      goToPage,
      handlePageJump,
      handlePageSizeChange,
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
/* 主容器 */
.log-management {
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
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn-refresh,
.btn-back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  background-color: #20a53a;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  transition: all 0.2s ease;
}

.btn-back {
  background-color: #666;
}

.btn-refresh:hover {
  background-color: #1a8c31;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(32, 165, 58, 0.3);
}

.btn-back:hover {
  background-color: #555;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 102, 102, 0.3);
}

/* 过滤区域 */
.filter-section {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.filter-item {
  flex: 1;
  min-width: 200px;
}

.filter-item.full-width {
  flex: 1 1 100%;
}

.filter-item > label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
  font-size: 14px;
}

.filter-item input[type="text"],
.filter-item input[type="datetime-local"],
.filter-item select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.filter-item input[type="text"]:focus,
.filter-item input[type="datetime-local"]:focus,
.filter-item select:focus {
  outline: none;
  border-color: #20a53a;
  box-shadow: 0 0 0 3px rgba(32, 165, 58, 0.1);
}

.checkbox-group {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: center;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: normal;
  padding: 6px 12px;
  border-radius: 6px;
  transition: background-color 0.2s ease;
  white-space: nowrap;
}

.checkbox-label:hover {
  background-color: #f5f5f5;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  accent-color: #20a53a;
  margin: 0;
  flex-shrink: 0;
}

.checkbox-label span {
  line-height: 1.2;
  vertical-align: middle;
}

.filter-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.btn-primary,
.btn-secondary,
.btn-export {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: #20a53a;
  color: #fff;
}

.btn-primary:hover {
  background-color: #1a8c31;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(32, 165, 58, 0.3);
}

.btn-secondary {
  background-color: #666;
  color: #fff;
}

.btn-secondary:hover {
  background-color: #555;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 102, 102, 0.3);
}

.btn-export {
  background-color: #2196f3;
  color: #fff;
}

.btn-export:hover {
  background-color: #1976d2;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

/* 日志列表 */
.log-list {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
}

.loading,
.empty {
  padding: 40px;
  text-align: center;
  color: #999;
  font-size: 16px;
}

.log-items {
  padding: 10px;
}

/* 日志条目 */
.log-item {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 10px;
  background-color: #fafafa;
  overflow: hidden;
  transition: all 0.2s ease;
}

.log-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.log-item.level-error {
  border-left: 4px solid #f44336;
}

.log-item.level-warn {
  border-left: 4px solid #ff9800;
}

.log-item.level-info {
  border-left: 4px solid #2196f3;
}

.log-item.level-trade {
  border-left: 4px solid #4caf50;
}

.log-item.level-debug {
  border-left: 4px solid #9e9e9e;
}

.log-item.level-audit {
  border-left: 4px solid #9c27b0;
}

.log-header {
  display: grid;
  grid-template-columns: 80px 140px 1fr 100px 2fr 100px;
  align-items: center;
  gap: 12px;
  padding: 12px 15px;
  background-color: #fff;
}

.log-level {
  padding: 4px 10px;
  font-size: 12px;
  font-weight: bold;
  border-radius: 12px;
  text-align: center;
  white-space: nowrap;
}

.log-level.level-error {
  background-color: #ffebee;
  color: #f44336;
}

.log-level.level-warn {
  background-color: #fff3e0;
  color: #ff9800;
}

.log-level.level-info {
  background-color: #e3f2fd;
  color: #2196f3;
}

.log-level.level-trade {
  background-color: #e8f5e9;
  color: #4caf50;
}

.log-level.level-debug {
  background-color: #f5f5f5;
  color: #9e9e9e;
}

.log-level.level-audit {
  background-color: #f3e5f5;
  color: #9c27b0;
}

.log-time {
  color: #666;
  font-size: 12px;
  white-space: nowrap;
}

.log-event {
  color: #333;
  font-weight: 500;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-event-code {
  color: #999;
  font-size: 11px;
  padding: 3px 8px;
  background-color: #f5f5f5;
  border-radius: 10px;
  text-align: center;
  white-space: nowrap;
}

.log-message-preview {
  color: #666;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-expand {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  color: #666;
  padding: 6px 12px;
  transition: all 0.2s ease;
  white-space: nowrap;
  justify-self: end;
}

.btn-expand:hover {
  background-color: #e0e0e0;
  color: #333;
}

.log-details {
  padding: 15px;
  background-color: #fafafa;
  border-top: 1px solid #e0e0e0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-label {
  color: #999;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  color: #333;
  font-size: 13px;
  word-break: break-word;
}

.level-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  text-align: center;
  width: fit-content;
}

.event-code-badge {
  display: inline-block;
  padding: 4px 10px;
  background-color: #f5f5f5;
  border-radius: 10px;
  font-size: 12px;
  width: fit-content;
}

.trace-id-link {
  color: #2196f3;
  cursor: pointer;
  text-decoration: underline;
  transition: color 0.2s ease;
}

.trace-id-link:hover {
  color: #1976d2;
}

.error-code {
  color: #f44336;
  font-weight: bold;
}

.error-name {
  color: #ff5722;
  font-weight: 500;
}

.message-content {
  padding: 10px;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  line-height: 1.6;
}

.json-content {
  margin: 0;
  padding: 12px;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.5;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

/* 分页控件 */
.pagination {
  margin-top: 15px;
  padding: 15px 20px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.pagination-info {
  color: #666;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-page,
.btn-page-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border: 1px solid #ddd;
  background-color: #fff;
  color: #333;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  transition: all 0.2s ease;
  min-width: 36px;
}

.btn-page:hover:not(:disabled),
.btn-page-number:hover {
  background-color: #f5f5f5;
  border-color: #20a53a;
}

.btn-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-page-number.active {
  background-color: #20a53a;
  color: #fff;
  border-color: #20a53a;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

.page-jump {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 10px;
  padding-left: 10px;
  border-left: 1px solid #ddd;
}

.page-jump span {
  color: #666;
  font-size: 13px;
}

.page-jump input {
  width: 60px;
  padding: 6px 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
  text-align: center;
  font-size: 13px;
}

.btn-jump {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  background-color: #20a53a;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  transition: all 0.2s ease;
}

.btn-jump:hover {
  background-color: #1a8c31;
}

/* 导出对话框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-content {
  background-color: #fff;
  padding: 30px;
  border: 1px solid #ddd;
  border-radius: 12px;
  min-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.modal-content h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #333;
}

.export-options {
  margin-bottom: 20px;
}

.export-options label {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 10px;
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.export-options label:hover {
  background-color: #f5f5f5;
}

.export-options input[type="radio"] {
  margin-right: 10px;
  cursor: pointer;
  width: 18px;
  height: 18px;
  accent-color: #20a53a;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .log-management {
    padding: 10px;
  }

  .filter-row {
    flex-direction: column;
  }

  .filter-item {
    min-width: 100%;
  }

  .log-header {
    grid-template-columns: 1fr;
    gap: 8px;
    font-size: 12px;
  }

  .log-level,
  .log-time,
  .log-event,
  .log-event-code,
  .log-message-preview {
    justify-self: start;
  }

  .btn-expand {
    justify-self: start;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .pagination {
    flex-direction: column;
    align-items: stretch;
  }

  .pagination-controls {
    justify-content: center;
  }

  .page-jump {
    margin-left: 0;
    padding-left: 0;
    border-left: none;
    border-top: 1px solid #ddd;
    padding-top: 10px;
    margin-top: 10px;
    justify-content: center;
  }

  .modal-content {
    min-width: 90%;
    padding: 20px;
  }
}
</style>

