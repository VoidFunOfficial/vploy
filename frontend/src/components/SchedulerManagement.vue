<template>
  <div class="scheduler-management">
    <!-- 标题栏 -->
    <div class="header">
      <h2>定时任务管理</h2>
      <div class="header-actions">
        <button class="btn-primary" @click="showCreateDialog">➕ 新建任务</button>
        <button class="btn-refresh" @click="refreshTasks">🔄 刷新</button>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="filter-section">
      <div class="filter-item">
        <label>状态:</label>
        <select v-model="filters.enabled" @change="refreshTasks">
          <option value="all">全部</option>
          <option value="true">已启用</option>
          <option value="false">已禁用</option>
        </select>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="tasks-section">
      <div v-if="loading" class="loading">加载中...</div>
      
      <div v-else-if="tasks.length === 0" class="empty-state">
        <p>暂无定时任务</p>
      </div>

      <div v-else class="tasks-table">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>任务名称</th>
              <th>描述</th>
              <th>类型</th>
              <th>调度配置</th>
              <th>状态</th>
              <th>运行状态</th>
              <th>上次运行</th>
              <th>下次运行</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id" :class="{ 'huey-task': isHueyTask(task) }">
              <td>{{ task.id }}</td>
              <td>
                <div class="task-name">
                  {{ task.name }}
                  <span v-if="isHueyTask(task)" class="huey-badge" title="Huey自动任务">🤖</span>
                </div>
              </td>
              <td>
                <span class="task-description">{{ getTaskDescription(task) }}</span>
              </td>
              <td>
                <span class="badge" :class="task.task_type === 'cron' ? 'badge-info' : 'badge-warning'">
                  {{ task.task_type === 'cron' ? 'Cron' : '间隔' }}
                </span>
              </td>
              <td>
                <code class="schedule-code">{{ task.schedule }}</code>
              </td>
              <td>
                <span class="badge" :class="task.enabled ? 'badge-success' : 'badge-gray'">
                  {{ task.enabled ? '✓ 已启用' : '✗ 已禁用' }}
                </span>
              </td>
              <td>
                <span class="badge" :class="getRunningStatusClass(task)">
                  {{ getRunningStatus(task) }}
                </span>
              </td>
              <td>{{ formatTime(task.last_run) }}</td>
              <td>
                <span :class="{ 'next-run-soon': isNextRunSoon(task) }">
                  {{ formatTime(task.next_run) }}
                </span>
              </td>
              <td class="actions">
                <button
                  class="btn-sm"
                  :class="task.enabled ? 'btn-warning' : 'btn-success'"
                  @click="toggleTask(task)"
                >
                  {{ task.enabled ? '禁用' : '启用' }}
                </button>
                <button
                  class="btn-sm btn-primary"
                  @click="showEditDialog(task)"
                >
                  编辑
                </button>
                <button
                  class="btn-sm btn-danger"
                  @click="confirmDelete(task)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <div v-if="dialogVisible" class="dialog-overlay" @click.self="closeDialog">
      <div class="dialog">
        <div class="dialog-header">
          <h3>{{ isEditing ? '编辑任务' : '新建任务' }}</h3>
          <button class="btn-close" @click="closeDialog">×</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>任务名称 *</label>
            <input
              v-model="formData.name"
              type="text"
              placeholder="请输入任务名称"
              :disabled="isEditing"
            />
          </div>
          <div class="form-group">
            <label>任务类型 *</label>
            <select v-model="formData.task_type">
              <option value="interval">间隔时间</option>
              <option value="cron">Cron表达式</option>
            </select>
          </div>
          <!-- 间隔时间配置 -->
          <div v-if="formData.task_type === 'interval'" class="form-group">
            <label>调度配置 *</label>
            <div class="interval-config">
              <input
                v-model.number="intervalValue"
                type="number"
                min="1"
                placeholder="输入数值"
                class="interval-input"
              />
              <select v-model="intervalUnit" class="interval-unit">
                <option value="seconds">秒</option>
                <option value="minutes">分钟</option>
                <option value="hours">小时</option>
                <option value="days">天</option>
              </select>
            </div>
            <small class="interval-preview">
              {{ getIntervalPreview() }}
            </small>
          </div>

          <!-- Cron表达式配置 -->
          <div v-else class="form-group">
            <label>调度配置 *</label>

            <!-- 预设选项 -->
            <div class="cron-presets">
              <button
                type="button"
                v-for="preset in cronPresets"
                :key="preset.value"
                @click="selectCronPreset(preset.value)"
                class="preset-btn"
                :class="{ 'active': formData.schedule === preset.value }"
              >
                {{ preset.label }}
              </button>
            </div>

            <!-- 自定义模式 -->
            <div class="cron-custom">
              <label class="custom-toggle">
                <input type="checkbox" v-model="showCustomCron" />
                自定义Cron表达式
              </label>

              <div v-if="showCustomCron" class="custom-cron-input">
                <input
                  v-model="formData.schedule"
                  type="text"
                  placeholder="例如: 0 9 * * * (每天9点)"
                  class="cron-input"
                />
                <small>
                  格式: 分 时 日 月 周 (例如: 0 9 * * * 表示每天9点)
                </small>
              </div>

              <!-- 可视化时间选择器 (仅用于每天定时) -->
              <div v-if="!showCustomCron && isDailyPreset()" class="time-picker">
                <label>执行时间:</label>
                <div class="time-inputs">
                  <input
                    v-model.number="cronHour"
                    type="number"
                    min="0"
                    max="23"
                    placeholder="时"
                    @input="updateCronFromTime"
                  />
                  <span>:</span>
                  <input
                    v-model.number="cronMinute"
                    type="number"
                    min="0"
                    max="59"
                    placeholder="分"
                    @input="updateCronFromTime"
                  />
                </div>
              </div>
            </div>

            <small class="cron-preview">
              {{ getCronPreview() }}
            </small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.enabled" />
              启用任务
            </label>
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea 
              v-model="formData.description" 
              rows="3" 
              placeholder="任务描述（可选）"
            ></textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="closeDialog">取消</button>
          <button class="btn-primary" @click="submitForm">{{ isEditing ? '保存' : '创建' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  getScheduledTasks,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask
} from '@/api/scheduler'

export default {
  name: 'SchedulerManagement',
  setup() {
    const loading = ref(false)
    const tasks = ref([])
    const dialogVisible = ref(false)
    const isEditing = ref(false)
    const currentTask = ref(null)
    
    const filters = reactive({
      enabled: 'all'
    })
    
    const formData = reactive({
      name: '',
      task_type: 'interval',
      schedule: '',
      enabled: true,
      description: ''
    })

    // 间隔时间配置
    const intervalValue = ref(1)
    const intervalUnit = ref('hours')

    // Cron配置
    const showCustomCron = ref(false)
    const cronHour = ref(9)
    const cronMinute = ref(0)

    // Cron预设选项
    const cronPresets = [
      { label: '每分钟', value: '* * * * *' },
      { label: '每5分钟', value: '*/5 * * * *' },
      { label: '每15分钟', value: '*/15 * * * *' },
      { label: '每30分钟', value: '*/30 * * * *' },
      { label: '每小时', value: '0 * * * *' },
      { label: '每天', value: '0 9 * * *' },
      { label: '每周一', value: '0 9 * * 1' },
      { label: '每月1号', value: '0 9 1 * *' }
    ]

    // 加载任务列表
    const loadTasks = async () => {
      loading.value = true
      try {
        // 只传递有效的参数
        const params = {}
        if (filters.enabled && filters.enabled !== 'all') {
          params.enabled = filters.enabled
        }

        const response = await getScheduledTasks(params)
        console.log('定时任务响应:', response)
        if (response.success) {
          tasks.value = response.data.tasks || []
          console.log('加载的任务列表:', tasks.value)
        }
      } catch (error) {
        console.error('加载任务列表失败:', error)
        alert('加载任务列表失败')
      } finally {
        loading.value = false
      }
    }

    // 刷新任务列表
    const refreshTasks = () => {
      loadTasks()
    }

    // 显示创建对话框
    const showCreateDialog = () => {
      isEditing.value = false
      currentTask.value = null
      resetForm()
      dialogVisible.value = true
    }

    // 显示编辑对话框
    const showEditDialog = (task) => {
      isEditing.value = true
      currentTask.value = task
      formData.name = task.name
      formData.task_type = task.task_type
      formData.schedule = task.schedule
      formData.enabled = task.enabled
      formData.description = task.metadata?.description || ''

      // 解析现有配置
      if (task.task_type === 'interval') {
        parseIntervalFromSchedule(task.schedule)
      } else {
        parseCronFromSchedule(task.schedule)
      }

      dialogVisible.value = true
    }

    // 关闭对话框
    const closeDialog = () => {
      dialogVisible.value = false
      resetForm()
    }

    // 重置表单
    const resetForm = () => {
      formData.name = ''
      formData.task_type = 'interval'
      formData.schedule = ''
      formData.enabled = true
      formData.description = ''

      // 重置间隔时间配置
      intervalValue.value = 1
      intervalUnit.value = 'hours'

      // 重置Cron配置
      showCustomCron.value = false
      cronHour.value = 9
      cronMinute.value = 0
    }

    // 提交表单
    const submitForm = async () => {
      // 根据类型生成schedule
      if (formData.task_type === 'interval') {
        formData.schedule = calculateIntervalSeconds().toString()
      } else if (!showCustomCron.value) {
        // 如果不是自定义模式，从时间选择器生成cron
        if (isDailyPreset()) {
          formData.schedule = `${cronMinute.value} ${cronHour.value} * * *`
        }
      }

      // 验证
      if (!formData.name || !formData.schedule) {
        alert('请填写必填字段')
        return
      }

      try {
        const data = {
          name: formData.name,
          task_type: formData.task_type,
          schedule: formData.schedule,
          enabled: formData.enabled,
          metadata: {
            description: formData.description
          }
        }

        if (isEditing.value) {
          // 更新任务
          await updateScheduledTask(currentTask.value.id, data)
          alert('更新任务成功')
        } else {
          // 创建任务
          await createScheduledTask(data)
          alert('创建任务成功')
        }

        closeDialog()
        refreshTasks()
      } catch (error) {
        console.error('提交失败:', error)
        alert(isEditing.value ? '更新任务失败' : '创建任务失败')
      }
    }

    // 切换任务状态
    const toggleTask = async (task) => {
      try {
        const response = await updateScheduledTask(task.id, {
          enabled: !task.enabled
        })
        if (response.success) {
          alert(`${task.enabled ? '禁用' : '启用'}任务成功`)
          refreshTasks()
        }
      } catch (error) {
        console.error('切换任务状态失败:', error)
        alert('切换任务状态失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 确认删除
    const confirmDelete = async (task) => {
      if (!confirm(`确定要删除任务 "${task.name}" 吗？`)) {
        return
      }

      try {
        const response = await deleteScheduledTask(task.id)
        if (response.success) {
          alert('删除任务成功')
          refreshTasks()
        }
      } catch (error) {
        console.error('删除任务失败:', error)
        alert('删除任务失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 格式化时间
    const formatTime = (timeStr) => {
      if (!timeStr) return '-'
      const date = new Date(timeStr)
      return date.toLocaleString('zh-CN')
    }

    // 判断是否为Huey自动任务
    const isHueyTask = (task) => {
      return task.metadata?.huey_task === true
    }

    // 获取任务描述
    const getTaskDescription = (task) => {
      return task.metadata?.description || '-'
    }

    // 获取运行状态
    const getRunningStatus = (task) => {
      if (!task.enabled) {
        return '已停止'
      }

      if (!task.next_run) {
        return '等待中'
      }

      const now = new Date()
      const nextRun = new Date(task.next_run)

      if (nextRun <= now) {
        return '运行中'
      }

      return '等待中'
    }

    // 获取运行状态样式类
    const getRunningStatusClass = (task) => {
      const status = getRunningStatus(task)
      if (status === '运行中') return 'badge-running'
      if (status === '等待中') return 'badge-waiting'
      return 'badge-stopped'
    }

    // 判断下次运行是否即将到来 (1小时内)
    const isNextRunSoon = (task) => {
      if (!task.next_run) return false
      const now = new Date()
      const nextRun = new Date(task.next_run)
      const diff = nextRun - now
      return diff > 0 && diff < 3600000 // 1小时 = 3600000毫秒
    }

    // 计算间隔秒数
    const calculateIntervalSeconds = () => {
      const unitMultipliers = {
        seconds: 1,
        minutes: 60,
        hours: 3600,
        days: 86400
      }
      return intervalValue.value * unitMultipliers[intervalUnit.value]
    }

    // 获取间隔预览
    const getIntervalPreview = () => {
      if (!intervalValue.value || intervalValue.value <= 0) {
        return '请输入有效的数值'
      }
      const seconds = calculateIntervalSeconds()
      const unitNames = {
        seconds: '秒',
        minutes: '分钟',
        hours: '小时',
        days: '天'
      }
      return `每 ${intervalValue.value} ${unitNames[intervalUnit.value]}执行一次 (${seconds}秒)`
    }

    // 选择Cron预设
    const selectCronPreset = (value) => {
      formData.schedule = value
      showCustomCron.value = false

      // 如果是每天的预设，解析时间
      if (value === '0 9 * * *') {
        parseCronFromSchedule(value)
      }
    }

    // 判断是否为每天预设
    const isDailyPreset = () => {
      return formData.schedule && formData.schedule.match(/^\d+ \d+ \* \* \*$/)
    }

    // 从时间选择器更新Cron
    const updateCronFromTime = () => {
      if (!showCustomCron.value && isDailyPreset()) {
        formData.schedule = `${cronMinute.value} ${cronHour.value} * * *`
      }
    }

    // 获取Cron预览
    const getCronPreview = () => {
      if (!formData.schedule) {
        return '请选择或输入Cron表达式'
      }

      // 查找预设
      const preset = cronPresets.find(p => p.value === formData.schedule)
      if (preset) {
        return preset.label
      }

      // 尝试解析常见格式
      const parts = formData.schedule.split(' ')
      if (parts.length === 5) {
        const [min, hour, day, month, week] = parts

        if (day === '*' && month === '*' && week === '*') {
          if (min === '*' && hour === '*') return '每分钟执行'
          if (min.startsWith('*/')) return `每${min.slice(2)}分钟执行`
          if (hour === '*') return `每小时的第${min}分钟执行`
          return `每天${hour}:${min.padStart(2, '0')}执行`
        }

        if (day === '*' && month === '*' && week !== '*') {
          return `每周${week}的${hour}:${min.padStart(2, '0')}执行`
        }

        if (day !== '*' && month === '*') {
          return `每月${day}号${hour}:${min.padStart(2, '0')}执行`
        }
      }

      return `Cron: ${formData.schedule}`
    }

    // 从schedule解析间隔时间
    const parseIntervalFromSchedule = (schedule) => {
      const seconds = parseInt(schedule)
      if (isNaN(seconds)) {
        intervalValue.value = 1
        intervalUnit.value = 'hours'
        return
      }

      // 尝试转换为最合适的单位
      if (seconds % 86400 === 0) {
        intervalValue.value = seconds / 86400
        intervalUnit.value = 'days'
      } else if (seconds % 3600 === 0) {
        intervalValue.value = seconds / 3600
        intervalUnit.value = 'hours'
      } else if (seconds % 60 === 0) {
        intervalValue.value = seconds / 60
        intervalUnit.value = 'minutes'
      } else {
        intervalValue.value = seconds
        intervalUnit.value = 'seconds'
      }
    }

    // 从schedule解析Cron表达式
    const parseCronFromSchedule = (schedule) => {
      // 检查是否为预设
      const preset = cronPresets.find(p => p.value === schedule)
      if (preset) {
        showCustomCron.value = false
      } else {
        showCustomCron.value = true
      }

      // 尝试解析每天的时间
      const match = schedule.match(/^(\d+) (\d+) \* \* \*$/)
      if (match) {
        cronMinute.value = parseInt(match[1])
        cronHour.value = parseInt(match[2])
      }
    }

    // 定时刷新定时器
    let refreshTimer = null

    onMounted(() => {
      loadTasks()
      // 每30秒刷新一次任务列表,更新运行状态
      refreshTimer = setInterval(() => {
        loadTasks()
      }, 30000)
    })

    // 组件卸载时清除定时器
    onUnmounted(() => {
      if (refreshTimer) {
        clearInterval(refreshTimer)
        refreshTimer = null
      }
    })

    return {
      loading,
      tasks,
      filters,
      dialogVisible,
      isEditing,
      formData,
      intervalValue,
      intervalUnit,
      showCustomCron,
      cronHour,
      cronMinute,
      cronPresets,
      refreshTasks,
      showCreateDialog,
      showEditDialog,
      closeDialog,
      submitForm,
      toggleTask,
      confirmDelete,
      formatTime,
      isHueyTask,
      getTaskDescription,
      getRunningStatus,
      getRunningStatusClass,
      isNextRunSoon,
      getIntervalPreview,
      selectCronPreset,
      isDailyPreset,
      updateCronFromTime,
      getCronPreview
    }
  }
}
</script>

<style scoped>
/* 容器 */
.scheduler-management {
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
}

td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

tr:hover {
  background: #fafafa;
}

/* Huey任务高亮 */
tr.huey-task {
  background: #f0f8ff;
}

tr.huey-task:hover {
  background: #e6f3ff;
}

.actions {
  display: flex;
  gap: 8px;
}

/* 任务名称 */
.task-name {
  display: flex;
  align-items: center;
  gap: 5px;
}

.huey-badge {
  font-size: 14px;
  cursor: help;
}

/* 任务描述 */
.task-description {
  font-size: 12px;
  color: #666;
  max-width: 200px;
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 调度配置代码 */
.schedule-code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #d63384;
}

/* 下次运行即将到来 */
.next-run-soon {
  color: #ff9800;
  font-weight: 500;
}

/* 徽章 */
.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
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
  background: #e3f2fd;
  color: #1976d2;
}

.badge-gray {
  background: #f5f5f5;
  color: #757575;
}

.badge-running {
  background: #e8f5e9;
  color: #2e7d32;
  animation: pulse 2s infinite;
}

.badge-waiting {
  background: #fff3e0;
  color: #f57c00;
}

.badge-stopped {
  background: #ffebee;
  color: #c62828;
}

/* 运行中动画 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* 按钮 */
.btn-primary, .btn-secondary, .btn-success, .btn-warning, .btn-danger, .btn-refresh {
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

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 对话框 */
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
  max-width: 500px;
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

.form-group input[type="text"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group small {
  display: block;
  margin-top: 5px;
  color: #999;
  font-size: 12px;
}

.form-group small.huey-warning {
  color: #ff9800;
  font-weight: 500;
  background: #fff3e0;
  padding: 8px 12px;
  border-radius: 4px;
  border-left: 3px solid #ff9800;
}

.dialog-footer {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 间隔时间配置 */
.interval-config {
  display: flex;
  gap: 10px;
  align-items: center;
}

.interval-input {
  flex: 1;
  min-width: 0;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.interval-unit {
  width: 120px;
  flex-shrink: 0;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
  background: white;
  color: #333;
}

.interval-preview {
  display: block;
  margin-top: 8px;
  padding: 10px 12px;
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  color: #0d47a1;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
}

/* Cron配置 */
.cron-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 15px;
}

.preset-btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  color: #333;
}

.preset-btn:hover {
  border-color: #20a53a;
  color: #20a53a;
  background: #f0f8f0;
}

.preset-btn.active {
  background: #20a53a;
  color: white !important;
  border-color: #20a53a;
}

.cron-custom {
  margin-top: 15px;
}

.custom-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 10px;
  color: #333;
}

.custom-toggle input[type="checkbox"] {
  cursor: pointer;
  width: auto;
}

.custom-cron-input {
  margin-top: 10px;
}

.custom-cron-input small {
  color: #666;
  font-size: 12px;
}

.cron-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  box-sizing: border-box;
  background: white;
  color: #333;
}

.time-picker {
  margin-top: 15px;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 4px;
}

.time-picker > label {
  display: block;
  margin-bottom: 10px;
  font-weight: 500;
  color: #333;
}

.time-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-inputs input {
  width: 70px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  text-align: center;
  font-size: 16px;
  box-sizing: border-box;
  background: white;
  color: #333;
}

.time-inputs span {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

.cron-preview {
  display: block;
  margin-top: 8px;
  padding: 10px 12px;
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  color: #e65100;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
}
</style>

