<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="header-actions">
          <div class="header-left">
            <h2 class="text-xl font-bold">任务管理</h2>
            <el-tag type="info" effect="plain" round>共 {{ tasks.length }} 条任务</el-tag>
          </div>
          <div class="header-right">
            <el-button
              v-if="selectedTasks.length > 0"
              type="danger"
              :icon="Delete"
              @click="batchDelete"
            >
              批量删除 ({{ selectedTasks.length }})
            </el-button>
            <el-button type="primary" :icon="Plus" @click="showCreateDialog">
              新建任务
            </el-button>
          </div>
        </div>
      </template>

      <!-- 过滤器 -->
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="阶段">
          <el-select v-model="filters.stage" placeholder="全部阶段" clearable @change="refreshTasks" style="width: 120px">
            <el-option label="标记" value="mark" />
            <el-option label="分析" value="analysis" />
            <el-option label="决策" value="decision" />
            <el-option label="交易" value="trade" />
            <el-option label="监听" value="listen" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable @change="refreshTasks" style="width: 120px">
            <el-option label="等待中" value="waiting" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="finished" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="显示数量">
          <el-select v-model="filters.limit" placeholder="50 条" @change="refreshTasks" style="width: 100px">
            <el-option label="50 条" :value="50" />
            <el-option label="100 条" :value="100" />
            <el-option label="200 条" :value="200" />
            <el-option label="500 条" :value="500" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 任务列表 -->
      <el-table
        v-loading="loading"
        :data="tasks"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        border
        stripe
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="ID" width="80" prop="id">
          <template #default="{ row }">
            <span class="task-id">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="阶段" width="100">
          <template #default="{ row }">
            <el-tag :type="getStageType(row.stage)">
              {{ getStageLabel(row.stage) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="详细状态" min-width="150">
          <template #default="{ row }">
            <div v-if="row.extended_info" class="extended-info">
              <el-tag
                v-if="row.extended_info.type === 'analysis'"
                size="small"
                :type="getAnalysisStatusType(row.extended_info.analysis_status)"
              >
                {{ getAnalysisStatusLabel(row.extended_info.analysis_status) }}
              </el-tag>
              <div v-if="row.extended_info.conversation_id" class="info-detail">
                <small>会话: {{ row.extended_info.conversation_id.substring(0, 8) }}...</small>
              </div>
              <div v-if="row.extended_info.market_count > 0" class="info-detail">
                <small>市场: {{ row.extended_info.market_count }}</small>
              </div>
              <div v-if="row.extended_info.analysis_status === 'waiting_quota' && row.result?.next_available" class="info-detail">
                <small style="color: var(--el-color-warning)">
                  预计恢复: {{ formatTime(row.result.next_available) }}
                </small>
              </div>
            </div>
            <span v-else style="color: var(--el-text-color-secondary)">-</span>
          </template>
        </el-table-column>
        <el-table-column label="元数据" width="140">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" :icon="View" @click="showMetadata(row.metadata)" title="查看" />
              <el-button size="small" :icon="Edit" @click="editMetadata(row)" title="编辑" />
            </el-button-group>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="140">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                size="small"
                :icon="View"
                :disabled="!row.result || Object.keys(row.result).length === 0"
                @click="showResult(row.result)"
                title="查看"
              />
              <el-button size="small" :icon="Edit" @click="editResult(row)" title="编辑" />
            </el-button-group>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error_msg" class="error-text">{{ row.error_msg }}</span>
            <span v-else style="color: var(--el-text-color-secondary)">-</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.update_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                v-if="row.status === 'waiting'"
                type="success"
                size="small"
                :icon="Check"
                circle
                @click="approveTask(row)"
                title="同意并开始处理"
              />
              <el-button
                v-if="row.stage === 'analysis' && row.extended_info && (row.extended_info.analysis_status === 'polling' || row.extended_info.analysis_status === 'requesting')"
                type="warning"
                size="small"
                :icon="Refresh"
                circle
                @click="pollAnalysisOnceHandler(row)"
                title="手动轮询一次"
              />
              <el-button
                v-if="row.stage === 'analysis' && row.extended_info && row.extended_info.analysis_status === 'success' && row.extended_info.market_count > 0"
                type="primary"
                size="small"
                :icon="Share"
                circle
                @click="splitAnalysisTaskHandler(row)"
                title="拆分为decision任务"
              />
              <el-button
                v-if="row.status === 'waiting' || row.status === 'processing'"
                type="warning"
                size="small"
                :icon="Close"
                circle
                @click="cancelTask(row)"
                title="取消任务"
              />
              <el-button
                v-if="row.status === 'failed' || row.status === 'finished'"
                type="info"
                size="small"
                :icon="RefreshLeft"
                circle
                @click="retryTaskHandler(row)"
                title="重新打回重试"
              />
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                circle
                @click="confirmDelete(row)"
                title="删除任务"
              />
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="filters.limit"
          :total="totalTasks" 
          layout="total, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="新建任务"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="任务阶段" required>
          <el-select v-model="formData.stage" style="width: 100%">
            <el-option label="标记" value="mark" />
            <el-option label="分析" value="analysis" />
            <el-option label="决策" value="decision" />
            <el-option label="交易" value="trade" />
            <el-option label="监听" value="listen" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务状态" required>
          <el-select v-model="formData.status" style="width: 100%">
            <el-option label="等待中" value="waiting" />
            <el-option label="处理中" value="processing" />
          </el-select>
        </el-form-item>
        <el-form-item label="元数据">
          <el-input
            v-model="formData.metadata"
            type="textarea"
            :rows="5"
            placeholder='{"key": "value"}'
          />
          <div class="form-tip">请输入有效的 JSON 格式</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitCreate">创建</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="detailTitle"
      width="600px"
    >
      <pre class="json-view">{{ detailContent }}</pre>
    </el-dialog>

    <!-- 编辑元数据对话框 -->
    <el-dialog
      v-model="editMetadataDialogVisible"
      title="编辑元数据"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="editFormData" label-width="80px">
        <el-form-item label="元数据" required>
          <el-input
            v-model="editFormData.metadata"
            type="textarea"
            :rows="15"
            placeholder='{"key": "value"}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editMetadataDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitMetadataEdit">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑结果对话框 -->
    <el-dialog
      v-model="editResultDialogVisible"
      title="编辑任务结果"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="editFormData" label-width="80px">
        <el-form-item label="任务结果" required>
          <el-input
            v-model="editFormData.result"
            type="textarea"
            :rows="15"
            placeholder='{"key": "value"}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editResultDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitResultEdit">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { getTasks, createTask, updateTask, deleteTask, batchDeleteTasks, retryTask, pollAnalysisOnce, splitAnalysisTask } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, Check, Refresh, Share, Close, RefreshLeft, View, Edit } from '@element-plus/icons-vue'

export default {
  name: 'TaskManagement',
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
    
    // Pagination state
    const currentPage = ref(1)
    // Note: Since API uses offset/limit, we need to manage total count if possible, 
    // but the current API might not return total count in a standard way or the previous code didn't use it.
    // Looking at previous code, it used offset/limit manual pagination.
    // If API doesn't return total, we might need to adjust or simulate.
    // Assuming API returns tasks list, let's look at previous code: 
    // response.data.tasks is the array.
    // We will assume for now we can fetch more. But el-pagination works best with total.
    // Let's use a large number for total if unknown, or just simple pagination.
    // Actually previous code: "显示 X - Y 条", and "下一页" disabled if tasks.length < limit.
    // So we don't know total. We can simulate "infinite" pages or just keep simple pagination logic.
    // However, el-pagination requires 'total' to show numbers properly.
    // Let's try to adapt to el-pagination by tracking current offset.
    const totalTasks = ref(1000) // Placeholder since we don't know total

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

    // Helper functions for labels and types
    const getStageLabel = (stage) => {
      const map = {
        mark: '标记',
        analysis: '分析',
        decision: '决策',
        trade: '交易',
        listen: '监听'
      }
      return map[stage] || stage
    }

    const getStageType = (stage) => {
      const map = {
        mark: 'info',
        analysis: 'primary',
        decision: 'warning',
        trade: 'success',
        listen: 'info'
      }
      return map[stage] || ''
    }

    const getStatusLabel = (status) => {
      const map = {
        waiting: '等待中',
        processing: '处理中',
        finished: '已完成',
        failed: '失败'
      }
      return map[status] || status
    }

    const getStatusType = (status) => {
      const map = {
        waiting: 'info',
        processing: 'primary',
        finished: 'success',
        failed: 'danger'
      }
      return map[status] || ''
    }

    const getAnalysisStatusLabel = (status) => {
      const map = {
        pending: '待处理',
        waiting_quota: '等待额度中',
        requesting: '请求中',
        polling: '轮询中',
        validating: '验证中',
        success: '成功',
        failed: '失败'
      }
      return map[status] || status
    }

    const getAnalysisStatusType = (status) => {
      const map = {
        pending: 'info',
        waiting_quota: 'warning',
        requesting: 'warning',
        polling: 'info',
        validating: 'primary',
        success: 'success',
        failed: 'danger'
      }
      return map[status] || ''
    }

    // Format time
    const formatTime = (timeStr) => {
      if (!timeStr) return '-'
      return new Date(timeStr).toLocaleString('zh-CN')
    }

    // Load tasks
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
        if (response.success) {
          tasks.value = response.data.tasks || []
          // If we got fewer tasks than limit, we reached the end (roughly)
          if (tasks.value.length < filters.limit) {
            totalTasks.value = filters.offset + tasks.value.length
          } else {
            // Assume there are more
            totalTasks.value = filters.offset + tasks.value.length + 100 // Approximation
          }
        }
      } catch (error) {
        console.error('加载任务列表失败:', error)
        ElMessage.error('加载任务列表失败: ' + (error.response?.data?.message || error.message))
      } finally {
        loading.value = false
      }
    }

    // Refresh
    const refreshTasks = () => {
      filters.offset = 0
      currentPage.value = 1
      selectedTasks.value = []
      loadTasks()
    }

    // Pagination handlers
    const handlePageChange = (page) => {
      filters.offset = (page - 1) * filters.limit
      loadTasks()
    }

    const handleSizeChange = (size) => {
      filters.limit = size
      filters.offset = 0
      currentPage.value = 1
      loadTasks()
    }

    // Selection handler
    const handleSelectionChange = (selection) => {
      selectedTasks.value = selection.map(item => item.id)
    }

    // Batch delete
    const batchDelete = async () => {
      if (selectedTasks.value.length === 0) {
        ElMessage.warning('请先选择要删除的任务')
        return
      }

      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`,
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        const response = await batchDeleteTasks(selectedTasks.value)
        if (response.success) {
          const { deleted_count, failed_count } = response.data
          if (failed_count > 0) {
            ElMessage.warning(`批量删除完成: 成功${deleted_count}个, 失败${failed_count}个`)
          } else {
            ElMessage.success(`批量删除成功: 已删除${deleted_count}个任务`)
          }
          selectedTasks.value = []
          refreshTasks()
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量删除任务失败:', error)
          ElMessage.error('批量删除任务失败: ' + (error.response?.data?.message || error.message))
        }
      }
    }

    // Approve task
    const approveTask = async (task) => {
      try {
        await ElMessageBox.confirm(
          `确定要同意并开始处理任务 #${task.id} 吗？`,
          '提示',
          { type: 'info' }
        )

        const response = await updateTask(task.id, { status: 'processing' })
        if (response.success) {
          ElMessage.success('任务已开始处理')
          refreshTasks()
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('更新任务状态失败:', error)
          ElMessage.error('更新任务状态失败')
        }
      }
    }

    // Poll Analysis Once
    const pollAnalysisOnceHandler = async (task) => {
      try {
         const response = await pollAnalysisOnce(task.id)
         if (response.success) {
            ElMessage.success('已触发轮询')
            refreshTasks()
         }
      } catch (error) {
         ElMessage.error('轮询失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // Split Analysis Task
    const splitAnalysisTaskHandler = async (task) => {
       try {
          await ElMessageBox.confirm(
             `确定要将任务 #${task.id} 拆分为决策任务吗？`,
             '提示',
             { type: 'info' }
          )
          const response = await splitAnalysisTask(task.id)
          if (response.success) {
             ElMessage.success(`拆分成功，创建了 ${response.data.created_count} 个新任务`)
             refreshTasks()
          }
       } catch (error) {
          if (error !== 'cancel') {
             ElMessage.error('拆分任务失败: ' + (error.response?.data?.message || error.message))
          }
       }
    }

    // Retry Task
    const retryTaskHandler = async (task) => {
       try {
          await ElMessageBox.confirm(
             `确定要重试任务 #${task.id} 吗？`,
             '提示',
             { type: 'warning' }
          )
          const response = await retryTask(task.id)
          if (response.success) {
             ElMessage.success('任务已重置为等待状态')
             refreshTasks()
          }
       } catch (error) {
          if (error !== 'cancel') {
             ElMessage.error('重试任务失败')
          }
       }
    }


    // Show create dialog
    const showCreateDialog = () => {
      formData.stage = 'mark'
      formData.status = 'waiting'
      formData.metadata = '{}'
      createDialogVisible.value = true
    }

    // Submit create
    const submitCreate = async () => {
      try {
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
          ElMessage.success('创建任务成功')
          createDialogVisible.value = false
          refreshTasks()
        }
      } catch (error) {
        if (error instanceof SyntaxError) {
          ElMessage.error('JSON格式错误: ' + error.message)
        } else {
          console.error('创建任务失败:', error)
          ElMessage.error('创建任务失败: ' + (error.response?.data?.message || error.message))
        }
      }
    }

    // Show metadata
    const showMetadata = (metadata) => {
      detailTitle.value = '元数据'
      detailContent.value = JSON.stringify(metadata, null, 2)
      detailDialogVisible.value = true
    }

    // Show result
    const showResult = (result) => {
      detailTitle.value = '任务结果'
      detailContent.value = JSON.stringify(result, null, 2)
      detailDialogVisible.value = true
    }

    // Edit metadata
    const editMetadata = (task) => {
      editFormData.taskId = task.id
      editFormData.metadata = JSON.stringify(task.metadata || {}, null, 2)
      editMetadataDialogVisible.value = true
    }

    // Submit metadata edit
    const submitMetadataEdit = async () => {
      try {
        const metadata = JSON.parse(editFormData.metadata)
        const response = await updateTask(editFormData.taskId, { metadata })
        if (response.success) {
          ElMessage.success('更新元数据成功')
          editMetadataDialogVisible.value = false
          refreshTasks()
        }
      } catch (error) {
        if (error instanceof SyntaxError) {
          ElMessage.error('JSON格式错误: ' + error.message)
        } else {
          ElMessage.error('更新元数据失败')
        }
      }
    }

    // Edit result
    const editResult = (task) => {
      editFormData.taskId = task.id
      editFormData.result = JSON.stringify(task.result || {}, null, 2)
      editResultDialogVisible.value = true
    }

    // Submit result edit
    const submitResultEdit = async () => {
      try {
        const result = JSON.parse(editFormData.result)
        const response = await updateTask(editFormData.taskId, { result })
        if (response.success) {
          ElMessage.success('更新任务结果成功')
          editResultDialogVisible.value = false
          refreshTasks()
        }
      } catch (error) {
        if (error instanceof SyntaxError) {
          ElMessage.error('JSON格式错误: ' + error.message)
        } else {
          ElMessage.error('更新任务结果失败')
        }
      }
    }

    // Cancel task
    const cancelTask = async (task) => {
      try {
        await ElMessageBox.confirm(
          `确定要取消任务 #${task.id} 吗？`,
          '警告',
          { type: 'warning' }
        )

        const response = await updateTask(task.id, {
          status: 'failed',
          error_msg: '用户手动取消'
        })
        if (response.success) {
          ElMessage.success('取消任务成功')
          refreshTasks()
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('取消任务失败:', error)
          ElMessage.error('取消任务失败')
        }
      }
    }

    // Confirm delete
    const confirmDelete = async (task) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除任务 #${task.id} 吗？`,
          '警告',
          { type: 'error' }
        )
        const response = await deleteTask(task.id)
        if (response.success) {
          ElMessage.success('删除成功')
          refreshTasks()
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    onMounted(() => {
      loadTasks()
    })

    return {
      loading,
      tasks,
      selectedTasks,
      createDialogVisible,
      detailDialogVisible,
      detailTitle,
      detailContent,
      editMetadataDialogVisible,
      editResultDialogVisible,
      currentPage,
      totalTasks,
      filters,
      formData,
      editFormData,
      getStageLabel,
      getStageType,
      getStatusLabel,
      getStatusType,
      getAnalysisStatusLabel,
      getAnalysisStatusType,
      formatTime,
      loadTasks,
      refreshTasks,
      handlePageChange,
      handleSizeChange,
      handleSelectionChange,
      batchDelete,
      approveTask,
      pollAnalysisOnceHandler,
      splitAnalysisTaskHandler,
      retryTaskHandler,
      showCreateDialog,
      submitCreate,
      showMetadata,
      showResult,
      editMetadata,
      submitMetadataEdit,
      editResult,
      submitResultEdit,
      cancelTask,
      confirmDelete,
      Delete, Plus, Check, Refresh, Share, Close, RefreshLeft, View, Edit
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

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-left h2 {
  margin: 0;
  color: var(--el-text-color-primary);
}

.filter-form {
  margin-bottom: 20px;
}

.extended-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-detail {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.error-text {
  color: var(--el-color-danger);
  font-size: 12px;
}

.action-buttons {
  display: flex;
  gap: 5px;
  justify-content: flex-start;
  flex-wrap: wrap;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.json-view {
  background-color: var(--el-fill-color-light);
  padding: 10px;
  border-radius: 4px;
  overflow: auto;
  max-height: 400px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
}

.form-tip {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-top: 5px;
}



/* 容器 */
/* .task-management removed */

/* 标题栏 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

/* .header-left duplicated above, removing/merging */

.header h2 {
  font-size: 18px;
  color: var(--el-text-color-primary);
  margin: 0;
}

.task-count {
  padding: 4px 10px;
  background: var(--el-fill-color);
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

/* .header-actions duplicated above */

/* 过滤器 */
.filter-section {
  background: var(--el-bg-color);
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: var(--el-box-shadow-light);
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
  font-size: 14px;
  color: var(--el-text-color-regular);
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

