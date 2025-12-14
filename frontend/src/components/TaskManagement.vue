<template>
  <div class="task-management">
    <!-- 标题栏 -->
    <div class="header">
      <div class="header-left">
        <h2>📋 任务管理</h2>
        <span class="task-count">共 {{ tasks.length }} 条任务</span>
      </div>
      <div class="header-actions">
        <button
          v-if="selectedTasks.length > 0"
          class="btn btn-danger"
          @click="batchDelete"
        >
          <span class="btn-icon">🗑️</span>
          批量删除 ({{ selectedTasks.length }})
        </button>
        <button class="btn btn-primary" @click="showCreateDialog">
          <span class="btn-icon">➕</span>
          新建任务
        </button>
        <button class="btn btn-refresh" @click="refreshTasks">
          <span class="btn-icon">🔄</span>
          刷新
        </button>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item">
          <label>阶段</label>
          <select v-model="filters.stage" @change="refreshTasks">
            <option value="">全部阶段</option>
            <option value="mark">📌 标记</option>
            <option value="analysis">🔍 分析</option>
            <option value="decision">🎯 决策</option>
            <option value="trade">💱 交易</option>
            <option value="listen">👂 监听</option>
          </select>
        </div>
        <div class="filter-item">
          <label>状态</label>
          <select v-model="filters.status" @change="refreshTasks">
            <option value="">全部状态</option>
            <option value="waiting">⏳ 等待中</option>
            <option value="processing">⚙️ 处理中</option>
            <option value="finished">✅ 已完成</option>
            <option value="failed">❌ 失败</option>
          </select>
        </div>
        <div class="filter-item">
          <label>显示数量</label>
          <select v-model="filters.limit" @change="refreshTasks">
            <option :value="50">50 条</option>
            <option :value="100">100 条</option>
            <option :value="200">200 条</option>
            <option :value="500">500 条</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="tasks-section">
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="tasks.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <p>暂无任务数据</p>
        <button class="btn btn-primary" @click="showCreateDialog">创建第一个任务</button>
      </div>

      <div v-else class="tasks-table-wrapper">
        <table class="tasks-table">
          <thead>
            <tr>
              <th class="th-checkbox">
                <input
                  type="checkbox"
                  @change="toggleSelectAll"
                  :checked="isAllSelected"
                />
              </th>
              <th class="th-id">ID</th>
              <th class="th-stage">阶段</th>
              <th class="th-status">状态</th>
              <th class="th-extended">详细状态</th>
              <th class="th-data">元数据</th>
              <th class="th-data">结果</th>
              <th class="th-error">错误信息</th>
              <th class="th-time">创建时间</th>
              <th class="th-time">更新时间</th>
              <th class="th-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id" class="task-row">
              <td class="td-checkbox">
                <input
                  type="checkbox"
                  :value="task.id"
                  v-model="selectedTasks"
                />
              </td>
              <td class="td-id">
                <span class="task-id">#{{ task.id }}</span>
              </td>
              <td class="td-stage">
                <span class="badge badge-stage" :class="'badge-stage-' + task.stage">
                  {{ getStageLabel(task.stage) }}
                </span>
              </td>
              <td class="td-status">
                <span class="badge" :class="getStatusClass(task.status)">
                  {{ getStatusLabel(task.status) }}
                </span>
              </td>
              <td class="td-extended">
                <div v-if="task.extended_info" class="extended-info">
                  <span
                    v-if="task.extended_info.type === 'analysis'"
                    class="badge badge-sm"
                    :class="getAnalysisStatusClass(task.extended_info.analysis_status)"
                  >
                    {{ getAnalysisStatusLabel(task.extended_info.analysis_status) }}
                  </span>
                  <div v-if="task.extended_info.conversation_id" class="info-detail">
                    <small>会话: {{ task.extended_info.conversation_id.substring(0, 8) }}...</small>
                  </div>
                  <div v-if="task.extended_info.market_count > 0" class="info-detail">
                    <small>市场: {{ task.extended_info.market_count }}</small>
                  </div>
                </div>
                <span v-else class="text-muted">-</span>
              </td>
              <td class="td-data">
                <div class="btn-group">
                  <button class="btn-sm btn-view" @click="showMetadata(task.metadata)" title="查看元数据">
                    👁️
                  </button>
                  <button class="btn-sm btn-edit" @click="editMetadata(task)" title="编辑元数据">
                    ✏️
                  </button>
                </div>
              </td>
              <td class="td-data">
                <div class="btn-group">
                  <button
                    v-if="task.result && Object.keys(task.result).length > 0"
                    class="btn-sm btn-view"
                    @click="showResult(task.result)"
                    title="查看结果"
                  >
                    👁️
                  </button>
                  <span v-else class="text-muted">-</span>
                  <button class="btn-sm btn-edit" @click="editResult(task)" title="编辑结果">
                    ✏️
                  </button>
                </div>
              </td>
              <td class="td-error">
                <span v-if="task.error_msg" class="error-text" :title="task.error_msg">
                  {{ task.error_msg.length > 30 ? task.error_msg.substring(0, 30) + '...' : task.error_msg }}
                </span>
                <span v-else class="text-muted">-</span>
              </td>
              <td class="td-time">
                <span class="time-text">{{ formatTime(task.create_time) }}</span>
              </td>
              <td class="td-time">
                <span class="time-text">{{ formatTime(task.update_time) }}</span>
              </td>
              <td class="td-actions">
                <div class="action-buttons">
                  <button
                    v-if="task.status === 'waiting'"
                    class="btn-sm btn-success"
                    @click="approveTask(task)"
                    title="同意并开始处理"
                  >
                    ✓
                  </button>
                  <button
                    v-if="task.stage === 'analysis' && task.extended_info && (task.extended_info.analysis_status === 'polling' || task.extended_info.analysis_status === 'requesting')"
                    class="btn-sm btn-poll"
                    @click="pollAnalysisOnceHandler(task)"
                    title="手动轮询一次"
                  >
                    🔍
                  </button>
                  <button
                    v-if="task.stage === 'analysis' && task.extended_info && task.extended_info.analysis_status === 'success' && task.extended_info.market_count > 0"
                    class="btn-sm btn-split"
                    @click="splitAnalysisTaskHandler(task)"
                    title="拆分为decision任务"
                  >
                    ✂️
                  </button>
                  <button
                    v-if="task.status === 'waiting' || task.status === 'processing'"
                    class="btn-sm btn-cancel"
                    @click="cancelTask(task)"
                    title="取消任务"
                  >
                    ⏸️
                  </button>
                  <button
                    v-if="task.status === 'failed' || task.status === 'finished'"
                    class="btn-sm btn-retry"
                    @click="retryTaskHandler(task)"
                    title="重新打回重试"
                  >
                    🔄
                  </button>
                  <button class="btn-sm btn-delete" @click="confirmDelete(task)" title="删除任务">
                    🗑️
                  </button>
                </div>
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

    <!-- 编辑元数据对话框 -->
    <Modal
      v-model:visible="editMetadataDialogVisible"
      title="编辑元数据"
      confirm-text="保存"
      @confirm="submitMetadataEdit"
    >
      <div class="form-group">
        <label>元数据 (JSON格式) *</label>
        <textarea
          v-model="editFormData.metadata"
          rows="15"
          placeholder='{"key": "value"}'
          class="json-editor"
        ></textarea>
      </div>
    </Modal>

    <!-- 编辑结果对话框 -->
    <Modal
      v-model:visible="editResultDialogVisible"
      title="编辑任务结果"
      confirm-text="保存"
      @confirm="submitResultEdit"
    >
      <div class="form-group">
        <label>任务结果 (JSON格式) *</label>
        <textarea
          v-model="editFormData.result"
          rows="15"
          placeholder='{"key": "value"}'
          class="json-editor"
        ></textarea>
      </div>
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
    const editMetadataDialogVisible = ref(false)
    const editResultDialogVisible = ref(false)

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

    const editFormData = reactive({
      taskId: null,
      metadata: '{}',
      result: '{}'
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

    // 编辑元数据
    const editMetadata = (task) => {
      editFormData.taskId = task.id
      editFormData.metadata = JSON.stringify(task.metadata || {}, null, 2)
      editMetadataDialogVisible.value = true
    }

    // 提交元数据编辑
    const submitMetadataEdit = async () => {
      try {
        // 解析JSON
        const metadata = JSON.parse(editFormData.metadata)

        const response = await updateTask(editFormData.taskId, { metadata })
        if (response.success) {
          toast.success('更新元数据成功')
          editMetadataDialogVisible.value = false
          refreshTasks()
        }
      } catch (error) {
        if (error instanceof SyntaxError) {
          toast.error('JSON格式错误: ' + error.message)
        } else {
          console.error('更新元数据失败:', error)
          toast.error('更新元数据失败: ' + (error.response?.data?.message || error.message))
        }
      }
    }

    // 编辑结果
    const editResult = (task) => {
      editFormData.taskId = task.id
      editFormData.result = JSON.stringify(task.result || {}, null, 2)
      editResultDialogVisible.value = true
    }

    // 提交结果编辑
    const submitResultEdit = async () => {
      try {
        // 解析JSON
        const result = JSON.parse(editFormData.result)

        const response = await updateTask(editFormData.taskId, { result })
        if (response.success) {
          toast.success('更新任务结果成功')
          editResultDialogVisible.value = false
          refreshTasks()
        }
      } catch (error) {
        if (error instanceof SyntaxError) {
          toast.error('JSON格式错误: ' + error.message)
        } else {
          console.error('更新任务结果失败:', error)
          toast.error('更新任务结果失败: ' + (error.response?.data?.message || error.message))
        }
      }
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
      editMetadataDialogVisible,
      editResultDialogVisible,
      formData,
      editFormData,
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
      editMetadata,
      submitMetadataEdit,
      editResult,
      submitResultEdit,
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

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header h2 {
  font-size: 20px;
  color: #333;
  margin: 0;
}

.task-count {
  padding: 4px 10px;
  background: #f0f0f0;
  border-radius: 12px;
  font-size: 12px;
  color: #666;
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

/* 加载状态 */
.loading {
  padding: 40px;
  text-align: center;
  color: #999;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 16px;
  border: 4px solid #f0f0f0;
  border-top-color: #2196f3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 空状态 */
.empty-state {
  padding: 40px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  color: #999;
  font-size: 16px;
  margin-bottom: 20px;
}

/* 表格 */
.tasks-table-wrapper {
  overflow-x: auto;
}

.tasks-table {
  width: 100%;
  border-collapse: collapse;
}

.tasks-table thead {
  background: #f5f5f5;
}

.tasks-table th {
  padding: 12px;
  text-align: left;
  font-weight: 500;
  color: #666;
  border-bottom: 2px solid #e0e0e0;
  white-space: nowrap;
}

.tasks-table td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.task-row:hover {
  background: #fafafa;
}

/* 列宽度 */
.th-checkbox, .td-checkbox { width: 40px; text-align: center; }
.th-id, .td-id { width: 60px; }
.th-stage, .td-stage { width: 80px; }
.th-status, .td-status { width: 90px; }
.th-extended, .td-extended { width: 140px; }
.th-data, .td-data { width: 100px; }
.th-error, .td-error { max-width: 200px; }
.th-time, .td-time { width: 140px; }
.th-actions, .td-actions { width: 180px; }

/* 任务ID */
.task-id {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #2196f3;
}

/* 文本样式 */
.text-muted {
  color: #999;
}

.time-text {
  font-size: 13px;
  color: #666;
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

.badge-sm {
  padding: 3px 6px;
  font-size: 11px;
}

/* 阶段徽章 */
.badge-stage {
  background: #e3f2fd;
  color: #1976d2;
}

.badge-stage-mark {
  background: #fce4ec;
  color: #c2185b;
}

.badge-stage-analysis {
  background: #e1f5fe;
  color: #0277bd;
}

.badge-stage-decision {
  background: #e8f5e9;
  color: #388e3c;
}

.badge-stage-trade {
  background: #fff3e0;
  color: #f57c00;
}

.badge-stage-listen {
  background: #f3e5f5;
  color: #7b1fa2;
}

/* 状态徽章 */
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

/* 按钮基础样式 */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-icon {
  margin-right: 4px;
}

.btn-primary {
  background: #20a53a;
  color: white;
}

.btn-primary:hover {
  background: #1a8c31;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover {
  background: #d32f2f;
}

.btn-refresh {
  background: #2196f3;
  color: white;
}

.btn-refresh:hover {
  background: #1976d2;
}

/* 小按钮 */
.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-sm:hover {
  opacity: 0.8;
}

/* 按钮组 */
.btn-group {
  display: flex;
  gap: 5px;
  align-items: center;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.btn-view {
  background: #e1f5fe;
  color: #0277bd;
}

.btn-edit {
  background: #fff3e0;
  color: #f57c00;
}

.btn-success {
  background: #4caf50;
  color: white;
}

.btn-cancel {
  background: #ff9800;
  color: white;
}

.btn-retry {
  background: #9c27b0;
  color: white;
}

.btn-poll {
  background: #ff9800;
  color: white;
}

.btn-split {
  background: #00bcd4;
  color: white;
}

.btn-delete {
  background: #f44336;
  color: white;
}

.btn-info {
  background: #00bcd4;
  color: white;
}



/* 表单样式 */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  font-size: 13px;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-group select,
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
  transition: all 0.2s;
  background: white;
}

.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* JSON查看器 */
.json-view {
  background: #1e293b;
  color: #e2e8f0;
  padding: 20px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'Courier New', monospace;
  max-height: 500px;
  overflow-y: auto;
}

/* JSON编辑器 */
.json-editor {
  font-family: 'Courier New', 'Monaco', monospace;
  background: #1e293b;
  color: #e2e8f0;
  border: 2px solid #334155;
  border-radius: 8px;
  padding: 16px;
  font-size: 13px;
  line-height: 1.8;
  resize: vertical;
  min-height: 300px;
}

.json-editor:focus {
  outline: none;
  border-color: #3b82f6;
  background: #0f172a;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 滚动条美化 */
.json-view::-webkit-scrollbar,
.json-editor::-webkit-scrollbar,
.tasks-table-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.json-view::-webkit-scrollbar-track,
.json-editor::-webkit-scrollbar-track,
.tasks-table-wrapper::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 4px;
}

.json-view::-webkit-scrollbar-thumb,
.json-editor::-webkit-scrollbar-thumb,
.tasks-table-wrapper::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.json-view::-webkit-scrollbar-thumb:hover,
.json-editor::-webkit-scrollbar-thumb:hover,
.tasks-table-wrapper::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>

