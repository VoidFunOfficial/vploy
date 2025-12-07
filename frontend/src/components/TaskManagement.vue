<template>
  <div class="task-management">
    <!-- 标题栏 -->
    <div class="header">
      <h2>任务管理</h2>
      <div class="header-actions">
        <button
          v-if="selectedTasks.length > 0"
          class="btn-danger"
          @click="batchDelete"
        >
          🗑️ 批量删除 ({{ selectedTasks.length }})
        </button>
        <button class="btn-primary" @click="showCreateDialog">➕ 新建任务</button>
        <button class="btn-refresh" @click="refreshTasks">🔄 刷新</button>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item">
          <label>阶段:</label>
          <select v-model="filters.stage" @change="refreshTasks">
            <option value="">全部</option>
            <option value="mark">标记</option>
            <option value="analysis">分析</option>
            <option value="decision">决策</option>
            <option value="trade">交易</option>
            <option value="listen">监听</option>
          </select>
        </div>
        <div class="filter-item">
          <label>状态:</label>
          <select v-model="filters.status" @change="refreshTasks">
            <option value="">全部</option>
            <option value="waiting">等待中</option>
            <option value="processing">处理中</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
            <option value="cancelled">已取消</option>
          </select>
        </div>
        <div class="filter-item">
          <label>显示数量:</label>
          <select v-model="filters.limit" @change="refreshTasks">
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="200">200</option>
            <option :value="500">500</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="tasks-section">
      <div v-if="loading" class="loading">加载中...</div>
      
      <div v-else-if="tasks.length === 0" class="empty-state">
        <p>暂无任务</p>
      </div>

      <div v-else class="tasks-table">
        <table>
          <thead>
            <tr>
              <th style="width: 40px;">
                <input
                  type="checkbox"
                  @change="toggleSelectAll"
                  :checked="isAllSelected"
                />
              </th>
              <th>ID</th>
              <th>阶段</th>
              <th>状态</th>
              <th>详细状态</th>
              <th>元数据</th>
              <th>结果</th>
              <th>错误信息</th>
              <th>创建时间</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id">
              <td>
                <input
                  type="checkbox"
                  :value="task.id"
                  v-model="selectedTasks"
                />
              </td>
              <td>{{ task.id }}</td>
              <td>
                <span class="badge badge-stage">{{ getStageLabel(task.stage) }}</span>
              </td>
              <td>
                <span class="badge" :class="getStatusClass(task.status)">
                  {{ getStatusLabel(task.status) }}
                </span>
              </td>
              <td>
                <div v-if="task.extended_info" class="extended-info">
                  <span
                    v-if="task.extended_info.type === 'analysis'"
                    class="badge"
                    :class="getAnalysisStatusClass(task.extended_info.analysis_status)"
                  >
                    {{ getAnalysisStatusLabel(task.extended_info.analysis_status) }}
                  </span>
                  <div v-if="task.extended_info.conversation_id" class="info-detail">
                    <small>会话ID: {{ task.extended_info.conversation_id.substring(0, 8) }}...</small>
                  </div>
                  <div v-if="task.extended_info.market_count > 0" class="info-detail">
                    <small>市场数: {{ task.extended_info.market_count }}</small>
                  </div>
                </div>
                <span v-else>-</span>
              </td>
              <td>
                <button class="btn-sm btn-info" @click="showMetadata(task.metadata)">查看</button>
              </td>
              <td>
                <button
                  v-if="task.result"
                  class="btn-sm btn-info"
                  @click="showResult(task.result)"
                >
                  查看
                </button>
                <span v-else>-</span>
              </td>
              <td>
                <span v-if="task.error_msg" class="error-text">{{ task.error_msg }}</span>
                <span v-else>-</span>
              </td>
              <td>{{ formatTime(task.create_time) }}</td>
              <td>{{ formatTime(task.update_time) }}</td>
              <td class="actions">
                <button
                  v-if="task.status === 'waiting'"
                  class="btn-sm btn-success"
                  @click="approveTask(task)"
                  title="同意并开始处理"
                >
                  ✓ 同意
                </button>
                <button
                  v-if="task.stage === 'analysis' && task.extended_info && (task.extended_info.analysis_status === 'polling' || task.extended_info.analysis_status === 'requesting')"
                  class="btn-sm btn-poll"
                  @click="pollAnalysisOnceHandler(task)"
                  title="手动轮询一次"
                >
                  🔍 轮询
                </button>
                <button
                  v-if="task.stage === 'analysis' && task.extended_info && task.extended_info.analysis_status === 'success' && task.extended_info.market_count > 0"
                  class="btn-sm btn-split"
                  @click="splitAnalysisTaskHandler(task)"
                  title="拆分为decision任务"
                >
                  ✂️ 拆分
                </button>
                <button
                  v-if="task.status === 'waiting' || task.status === 'processing'"
                  class="btn-sm btn-warning"
                  @click="cancelTask(task)"
                >
                  取消
                </button>
                <button
                  v-if="task.status === 'failed' || task.status === 'finished'"
                  class="btn-sm btn-retry"
                  @click="retryTaskHandler(task)"
                  title="重新打回重试"
                >
                  🔄 重试
                </button>
                <button class="btn-sm btn-danger" @click="confirmDelete(task)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div v-if="tasks.length > 0" class="pagination">
        <button 
          class="btn-secondary" 
          :disabled="filters.offset === 0"
          @click="prevPage"
        >
          上一页
        </button>
        <span class="page-info">
          显示 {{ filters.offset + 1 }} - {{ filters.offset + tasks.length }} 条
        </span>
        <button 
          class="btn-secondary" 
          :disabled="tasks.length < filters.limit"
          @click="nextPage"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <Modal
      v-model:visible="createDialogVisible"
      title="新建任务"
      confirm-text="创建"
      @confirm="submitCreate"
    >
      <div class="form-group">
        <label>任务阶段 *</label>
        <select v-model="formData.stage">
          <option value="mark">标记</option>
          <option value="analysis">分析</option>
          <option value="decision">决策</option>
          <option value="trade">交易</option>
          <option value="listen">监听</option>
        </select>
      </div>
      <div class="form-group">
        <label>任务状态 *</label>
        <select v-model="formData.status">
          <option value="waiting">等待中</option>
          <option value="processing">处理中</option>
        </select>
      </div>
      <div class="form-group">
        <label>元数据 (JSON格式)</label>
        <textarea
          v-model="formData.metadata"
          rows="5"
          placeholder='{"key": "value"}'
        ></textarea>
      </div>
    </Modal>

    <!-- 查看详情对话框 -->
    <Modal
      v-model:visible="detailDialogVisible"
      :title="detailTitle"
      :show-footer="false"
      size="large"
    >
      <pre class="json-view">{{ detailContent }}</pre>
    </Modal>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { getTasks, createTask, updateTask, deleteTask, batchDeleteTasks, retryTask, pollAnalysisOnce, splitAnalysisTask } from '@/api/tasks'
import { toast, confirm, Modal } from '@/components/Notification'

export default {
  name: 'TaskManagement',
  components: {
    Modal
  },
  setup() {
    const loading = ref(false)
    const tasks = ref([])
    const selectedTasks = ref([])
    const createDialogVisible = ref(false)
    const detailDialogVisible = ref(false)
    const detailTitle = ref('')
    const detailContent = ref('')

    const filters = reactive({
      stage: '',
      status: '',
      limit: 100,
      offset: 0
    })

    const formData = reactive({
      stage: 'mark',
      status: 'waiting',
      metadata: '{}'
    })

    // 是否全选
    const isAllSelected = computed(() => {
      return tasks.value.length > 0 && selectedTasks.value.length === tasks.value.length
    })

    // 加载任务列表
    const loadTasks = async () => {
      loading.value = true
      try {
        const params = {
          limit: filters.limit,
          offset: filters.offset
        }
        if (filters.stage) params.stage = filters.stage
        if (filters.status) params.status = filters.status

        const response = await getTasks(params)
        console.log('任务列表响应:', response)
        if (response.success) {
          tasks.value = response.data.tasks || []
          console.log('加载的任务列表:', tasks.value)
        }
      } catch (error) {
        console.error('加载任务列表失败:', error)
        toast.error('加载任务列表失败: ' + (error.response?.data?.message || error.message))
      } finally {
        loading.value = false
      }
    }

    // 刷新任务列表
    const refreshTasks = () => {
      filters.offset = 0
      selectedTasks.value = []
      loadTasks()
    }

    // 上一页
    const prevPage = () => {
      if (filters.offset >= filters.limit) {
        filters.offset -= filters.limit
        selectedTasks.value = []
        loadTasks()
      }
    }

    // 下一页
    const nextPage = () => {
      filters.offset += filters.limit
      selectedTasks.value = []
      loadTasks()
    }

    // 全选/取消全选
    const toggleSelectAll = (event) => {
      if (event.target.checked) {
        selectedTasks.value = tasks.value.map(task => task.id)
      } else {
        selectedTasks.value = []
      }
    }

    // 批量删除
    const batchDelete = async () => {
      if (selectedTasks.value.length === 0) {
        toast.warning('请先选择要删除的任务')
        return
      }

      const result = await confirm({
        message: `确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`,
        type: 'danger'
      })
      if (!result) {
        return
      }

      try {
        const response = await batchDeleteTasks(selectedTasks.value)
        if (response.success) {
          const { deleted_count, failed_count } = response.data
          if (failed_count > 0) {
            toast.warning(`批量删除完成: 成功${deleted_count}个, 失败${failed_count}个`)
          } else {
            toast.success(`批量删除成功: 已删除${deleted_count}个任务`)
          }
          selectedTasks.value = []
          refreshTasks()
        }
      } catch (error) {
        console.error('批量删除任务失败:', error)
        toast.error('批量删除任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 同意任务(将waiting状态变为processing)
    const approveTask = async (task) => {
      const result = await confirm(`确定要同意并开始处理任务 #${task.id} 吗？`)
      if (!result) {
        return
      }

      try {
        const response = await updateTask(task.id, { status: 'processing' })
        if (response.success) {
          toast.success('任务已开始处理')
          refreshTasks()
        }
      } catch (error) {
        console.error('更新任务状态失败:', error)
        toast.error('更新任务状态失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 显示创建对话框
    const showCreateDialog = () => {
      formData.stage = 'mark'
      formData.status = 'waiting'
      formData.metadata = '{}'
      createDialogVisible.value = true
    }

    // 关闭创建对话框
    const closeCreateDialog = () => {
      createDialogVisible.value = false
    }

    // 提交创建
    const submitCreate = async () => {
      try {
        // 解析metadata
        let metadata = {}
        if (formData.metadata.trim()) {
          metadata = JSON.parse(formData.metadata)
        }

        const data = {
          stage: formData.stage,
          status: formData.status,
          metadata
        }

        const response = await createTask(data)
        if (response.success) {
          toast.success('创建任务成功')
          closeCreateDialog()
          refreshTasks()
        }
      } catch (error) {
        console.error('创建任务失败:', error)
        toast.error('创建任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 显示元数据
    const showMetadata = (metadata) => {
      detailTitle.value = '元数据'
      detailContent.value = JSON.stringify(metadata, null, 2)
      detailDialogVisible.value = true
    }

    // 显示结果
    const showResult = (result) => {
      detailTitle.value = '任务结果'
      detailContent.value = JSON.stringify(result, null, 2)
      detailDialogVisible.value = true
    }

    // 关闭详情对话框
    const closeDetailDialog = () => {
      detailDialogVisible.value = false
    }

    // 取消任务
    const cancelTask = async (task) => {
      const result = await confirm(`确定要取消任务 #${task.id} 吗？`)
      if (!result) {
        return
      }

      try {
        const response = await updateTask(task.id, {
          status: 'failed',
          error_msg: '用户手动取消'
        })
        if (response.success) {
          toast.success('取消任务成功')
          refreshTasks()
        }
      } catch (error) {
        console.error('取消任务失败:', error)
        toast.error('取消任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 确认删除
    const confirmDelete = async (task) => {
      const result = await confirm({
        message: `确定要删除任务 #${task.id} 吗？`,
        type: 'danger'
      })
      if (!result) {
        return
      }

      try {
        const response = await deleteTask(task.id)
        if (response.success) {
          toast.success('删除任务成功')
          refreshTasks()
        }
      } catch (error) {
        console.error('删除任务失败:', error)
        toast.error('删除任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 重试任务
    const retryTaskHandler = async (task) => {
      const result = await confirm({
        message: `确定要重试任务 #${task.id} 吗？\n任务将被重新打回到等待状态并重新执行。`
      })
      if (!result) {
        return
      }

      try {
        const response = await retryTask(task.id)
        if (response.success) {
          toast.success('任务已重新提交')
          refreshTasks()
        }
      } catch (error) {
        console.error('重试任务失败:', error)
        toast.error('重试任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 手动轮询一次分析任务
    const pollAnalysisOnceHandler = async (task) => {
      try {
        const response = await pollAnalysisOnce(task.id)
        if (response.success) {
          const data = response.data

          if (data.analysis_status === 'success') {
            // 分析成功
            toast.success(`✅ 分析完成！成功解析 ${data.market_count} 个市场`)
            refreshTasks()
          } else if (data.analysis_status === 'polling') {
            // 仍在思考
            toast.info('⏳ AI仍在思考中，请稍后再试')
          } else if (data.analysis_status === 'failed') {
            // 分析失败
            toast.error(`❌ 分析失败: ${data.error || '未知错误'}`)
            refreshTasks()
          }
        } else {
          toast.error(`轮询失败: ${response.message}`)
        }
      } catch (error) {
        console.error('手动轮询失败:', error)
        toast.error('手动轮询失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 拆分分析任务为多个decision任务
    const splitAnalysisTaskHandler = async (task) => {
      const marketCount = task.extended_info?.market_count || 0

      const result = await confirm({
        message: `确定要拆分任务 #${task.id} 吗？\n将创建 ${marketCount} 个decision任务，并删除原始analysis任务。`,
        type: 'warning'
      })
      if (!result) {
        return
      }

      try {
        const response = await splitAnalysisTask(task.id)

        if (response.success) {
          const data = response.data
          let message = `✅ 拆分成功！总市场数: ${data.total_markets}, 成功创建: ${data.success_count} 个decision任务`

          if (data.failed_count > 0) {
            message += `, 失败: ${data.failed_count} 个市场`
          }

          toast.success(message)
          refreshTasks()
        } else {
          toast.error(`❌ 拆分失败: ${response.message}`)
        }
      } catch (error) {
        console.error('拆分任务失败:', error)
        toast.error('拆分任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 获取阶段标签
    const getStageLabel = (stage) => {
      const labels = {
        mark: '标记',
        analysis: '分析',
        decision: '决策',
        trade: '交易',
        listen: '监听'
      }
      return labels[stage] || stage
    }

    // 获取状态标签
    const getStatusLabel = (status) => {
      const labels = {
        waiting: '等待中',
        processing: '处理中',
        finished: '已完成',
        failed: '失败'
      }
      return labels[status] || status
    }

    // 获取状态样式类
    const getStatusClass = (status) => {
      const classes = {
        waiting: 'badge-warning',
        processing: 'badge-info',
        finished: 'badge-success',
        failed: 'badge-danger'
      }
      return classes[status] || 'badge-gray'
    }

    // 获取分析状态标签
    const getAnalysisStatusLabel = (analysisStatus) => {
      const labels = {
        pending: '待处理',
        requesting: '请求中',
        polling: '轮询中',
        validating: '验证中',
        success: '成功',
        failed: '失败'
      }
      return labels[analysisStatus] || analysisStatus || '-'
    }

    // 获取分析状态样式类
    const getAnalysisStatusClass = (analysisStatus) => {
      const classes = {
        pending: 'badge-gray',
        requesting: 'badge-info',
        polling: 'badge-warning',
        validating: 'badge-info',
        success: 'badge-success',
        failed: 'badge-danger'
      }
      return classes[analysisStatus] || 'badge-gray'
    }

    // 格式化时间
    const formatTime = (timeStr) => {
      if (!timeStr) return '-'
      const date = new Date(timeStr)
      return date.toLocaleString('zh-CN')
    }

    onMounted(() => {
      loadTasks()
    })

    return {
      loading,
      tasks,
      selectedTasks,
      isAllSelected,
      filters,
      createDialogVisible,
      detailDialogVisible,
      detailTitle,
      detailContent,
      formData,
      refreshTasks,
      prevPage,
      nextPage,
      toggleSelectAll,
      batchDelete,
      approveTask,
      showCreateDialog,
      closeCreateDialog,
      submitCreate,
      showMetadata,
      showResult,
      closeDetailDialog,
      cancelTask,
      confirmDelete,
      retryTaskHandler,
      pollAnalysisOnceHandler,
      splitAnalysisTaskHandler,
      getStageLabel,
      getStatusLabel,
      getStatusClass,
      getAnalysisStatusLabel,
      getAnalysisStatusClass,
      formatTime
    }
  }
}
</script>

<style scoped>
/* 容器 */
.task-management {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

/* 标题栏 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  font-size: 20px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 过滤器 */
.filter-section {
  background: #fff;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.filter-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-item label {
  font-weight: 500;
  color: #666;
}

.filter-item select {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

/* 任务列表 */
.tasks-section {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.loading, .empty-state {
  padding: 40px;
  text-align: center;
  color: #999;
}

.tasks-table {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f5f5f5;
}

th {
  padding: 12px;
  text-align: left;
  font-weight: 500;
  color: #666;
  border-bottom: 2px solid #e0e0e0;
  white-space: nowrap;
}

td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

tr:hover {
  background: #fafafa;
}

.actions {
  display: flex;
  gap: 8px;
}

.error-text {
  color: #f44336;
  font-size: 12px;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  padding: 15px;
  border-top: 1px solid #e0e0e0;
}

.page-info {
  color: #666;
  font-size: 14px;
}

/* 徽章 */
.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-stage {
  background: #e3f2fd;
  color: #1976d2;
}

.badge-success {
  background: #e8f5e9;
  color: #2e7d32;
}

.badge-warning {
  background: #fff3e0;
  color: #f57c00;
}

.badge-info {
  background: #e1f5fe;
  color: #0277bd;
}

.badge-danger {
  background: #ffebee;
  color: #c62828;
}

.badge-gray {
  background: #f5f5f5;
  color: #757575;
}

/* 扩展信息 */
.extended-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-detail {
  color: #666;
  font-size: 11px;
  line-height: 1.4;
}

.info-detail small {
  display: block;
}

/* 按钮样式省略,与SchedulerManagement相同 */
.btn-primary, .btn-secondary, .btn-success, .btn-warning, .btn-danger, .btn-refresh, .btn-info {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-primary {
  background: #20a53a;
  color: white;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-success {
  background: #4caf50;
  color: white;
}

.btn-warning {
  background: #ff9800;
  color: white;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-refresh {
  background: #2196f3;
  color: white;
}

.btn-info {
  background: #00bcd4;
  color: white;
}

.btn-retry {
  background: #9c27b0;
  color: white;
}

.btn-retry:hover {
  background: #7b1fa2;
}

.btn-poll {
  background: #ff9800;
  color: white;
}

.btn-poll:hover {
  background: #f57c00;
}

.btn-split {
  background: #00bcd4;
  color: white;
}

.btn-split:hover {
  background: #0097a7;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}



.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #666;
}

.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.json-view {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}
</style>

