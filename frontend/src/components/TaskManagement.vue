<template>
  <div class="task-management">
    <!-- 标题栏 -->
    <div class="header">
      <h2>任务管理</h2>
      <div class="header-actions">
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
              <th>ID</th>
              <th>阶段</th>
              <th>状态</th>
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
                  v-if="task.status === 'waiting' || task.status === 'processing'"
                  class="btn-sm btn-warning" 
                  @click="cancelTask(task)"
                >
                  取消
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
    <div v-if="createDialogVisible" class="dialog-overlay" @click.self="closeCreateDialog">
      <div class="dialog">
        <div class="dialog-header">
          <h3>新建任务</h3>
          <button class="btn-close" @click="closeCreateDialog">×</button>
        </div>
        <div class="dialog-body">
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
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="closeCreateDialog">取消</button>
          <button class="btn-primary" @click="submitCreate">创建</button>
        </div>
      </div>
    </div>

    <!-- 查看详情对话框 -->
    <div v-if="detailDialogVisible" class="dialog-overlay" @click.self="closeDetailDialog">
      <div class="dialog">
        <div class="dialog-header">
          <h3>{{ detailTitle }}</h3>
          <button class="btn-close" @click="closeDetailDialog">×</button>
        </div>
        <div class="dialog-body">
          <pre class="json-view">{{ detailContent }}</pre>
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="closeDetailDialog">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { getTasks, createTask, updateTask, deleteTask } from '@/api/tasks'

export default {
  name: 'TaskManagement',
  setup() {
    const loading = ref(false)
    const tasks = ref([])
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
        alert('加载任务列表失败: ' + (error.response?.data?.message || error.message))
      } finally {
        loading.value = false
      }
    }

    // 刷新任务列表
    const refreshTasks = () => {
      filters.offset = 0
      loadTasks()
    }

    // 上一页
    const prevPage = () => {
      if (filters.offset >= filters.limit) {
        filters.offset -= filters.limit
        loadTasks()
      }
    }

    // 下一页
    const nextPage = () => {
      filters.offset += filters.limit
      loadTasks()
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
          alert('创建任务成功')
          closeCreateDialog()
          refreshTasks()
        }
      } catch (error) {
        console.error('创建任务失败:', error)
        alert('创建任务失败: ' + (error.response?.data?.message || error.message))
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
      if (!confirm(`确定要取消任务 #${task.id} 吗？`)) {
        return
      }

      try {
        const response = await updateTask(task.id, { status: 'cancelled' })
        if (response.success) {
          alert('取消任务成功')
          refreshTasks()
        }
      } catch (error) {
        console.error('取消任务失败:', error)
        alert('取消任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 确认删除
    const confirmDelete = async (task) => {
      if (!confirm(`确定要删除任务 #${task.id} 吗？`)) {
        return
      }

      try {
        const response = await deleteTask(task.id)
        if (response.success) {
          alert('删除任务成功')
          refreshTasks()
        }
      } catch (error) {
        console.error('删除任务失败:', error)
        alert('删除任务失败: ' + (error.response?.data?.message || error.message))
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
        success: '成功',
        failed: '失败',
        cancelled: '已取消'
      }
      return labels[status] || status
    }

    // 获取状态样式类
    const getStatusClass = (status) => {
      const classes = {
        waiting: 'badge-warning',
        processing: 'badge-info',
        success: 'badge-success',
        failed: 'badge-danger',
        cancelled: 'badge-gray'
      }
      return classes[status] || 'badge-gray'
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
      filters,
      createDialogVisible,
      detailDialogVisible,
      detailTitle,
      detailContent,
      formData,
      refreshTasks,
      prevPage,
      nextPage,
      showCreateDialog,
      closeCreateDialog,
      submitCreate,
      showMetadata,
      showResult,
      closeDetailDialog,
      cancelTask,
      confirmDelete,
      getStageLabel,
      getStatusLabel,
      getStatusClass,
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

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* 对话框样式省略,与SchedulerManagement相同 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.dialog-header h3 {
  margin: 0;
  font-size: 18px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.dialog-body {
  padding: 20px;
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

.dialog-footer {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

