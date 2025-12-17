<template>
  <div class="scheduler-management p-6 h-full flex flex-col gap-6 bg-gray-50">
    <el-card shadow="hover" class="flex-1 flex flex-col" :body-style="{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }">
      <template #header>
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <el-icon size="20" class="text-purple-500"><Timer /></el-icon>
            <h2 class="text-lg font-bold text-gray-800 m-0">定时任务管理</h2>
          </div>
          <div class="flex gap-2">
            <el-button type="primary" icon="Plus" @click="showCreateDialog">新建任务</el-button>
            <el-button icon="Refresh" @click="refreshTasks">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- Filters -->
      <div class="mb-4">
        <el-form :inline="true" :model="filters" class="demo-form-inline">
          <el-form-item label="状态">
            <el-select v-model="filters.enabled" placeholder="选择状态" @change="refreshTasks" style="width: 150px">
              <el-option label="全部" value="all" />
              <el-option label="已启用" value="true" />
              <el-option label="已禁用" value="false" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <!-- Task Table -->
      <div class="flex-1 overflow-hidden">
        <el-table
          v-loading="loading"
          :data="tasks"
          border
          stripe
          height="100%"
          style="width: 100%"
        >
          <el-table-column prop="id" label="ID" width="80" align="center" />
          
          <el-table-column label="任务名称" min-width="200">
            <template #default="scope">
              <div class="flex items-center gap-2">
                <span class="font-medium">{{ scope.row.name }}</span>
                <el-tag v-if="isHueyTask(scope.row)" size="small" type="info" effect="plain">Huey</el-tag>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="metadata.description" label="描述" show-overflow-tooltip min-width="200">
            <template #default="scope">
               {{ getTaskDescription(scope.row) }}
            </template>
          </el-table-column>
          
          <el-table-column label="类型" width="100" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.task_type === 'cron' ? 'success' : 'warning'" size="small">
                {{ scope.row.task_type === 'cron' ? 'Cron' : '间隔' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column label="调度配置" min-width="150">
            <template #default="scope">
              <code class="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-pink-600">{{ scope.row.schedule }}</code>
            </template>
          </el-table-column>
          
          <el-table-column label="状态" width="100" align="center">
            <template #default="scope">
              <el-switch
                v-model="scope.row.enabled"
                :active-value="true"
                :inactive-value="false"
                @change="(val) => handleStatusChange(scope.row, val)"
              />
            </template>
          </el-table-column>
          
          <el-table-column label="运行状态" width="120" align="center">
            <template #default="scope">
              <el-tag :type="getRunningStatusType(scope.row)" effect="light" size="small">
                {{ getRunningStatus(scope.row) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column label="时间" width="220">
            <template #default="scope">
              <div class="text-xs text-gray-500">
                <div>上次: {{ formatTime(scope.row.last_run) }}</div>
                <div :class="{ 'text-orange-500 font-bold': isNextRunSoon(scope.row) }">
                  下次: {{ formatTime(scope.row.next_run) }}
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="200" fixed="right" align="center">
            <template #default="scope">
              <el-button-group>
                <el-button 
                  type="success" 
                  size="small" 
                  icon="VideoPlay" 
                  circle 
                  @click="runTaskNow(scope.row)"
                  title="立即执行"
                ></el-button>
                <el-button 
                  type="primary" 
                  size="small" 
                  icon="Edit" 
                  circle 
                  @click="showEditDialog(scope.row)"
                  title="编辑"
                ></el-button>
                <el-button 
                  type="danger" 
                  size="small" 
                  icon="Delete" 
                  circle 
                  @click="confirmDelete(scope.row)"
                  title="删除"
                ></el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑任务' : '新建任务'"
      width="550px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form :model="formData" label-width="100px" ref="formRef">
        <el-form-item label="任务名称" required>
          <el-input v-model="formData.name" placeholder="请输入任务名称" :disabled="isEditing" />
        </el-form-item>
        
        <el-form-item label="任务类型" required>
          <el-radio-group v-model="formData.task_type">
            <el-radio-button label="interval">间隔时间</el-radio-button>
            <el-radio-button label="cron">Cron表达式</el-radio-button>
          </el-radio-group>
        </el-form-item>
        
        <!-- Interval Config -->
        <el-form-item v-if="formData.task_type === 'interval'" label="间隔配置" required>
          <div class="flex gap-2 w-full">
            <el-input-number v-model="intervalValue" :min="1" class="flex-1" />
            <el-select v-model="intervalUnit" style="width: 120px">
              <el-option label="秒" value="seconds" />
              <el-option label="分钟" value="minutes" />
              <el-option label="小时" value="hours" />
              <el-option label="天" value="days" />
            </el-select>
          </div>
          <div class="text-xs text-gray-400 mt-1">{{ getIntervalPreview() }}</div>
        </el-form-item>
        
        <!-- Cron Config -->
        <el-form-item v-else label="Cron配置" required>
          <div class="flex flex-col gap-2 w-full">
            <div class="flex flex-wrap gap-2 mb-2">
              <el-tag 
                v-for="preset in cronPresets" 
                :key="preset.value"
                class="cursor-pointer"
                :effect="formData.schedule === preset.value ? 'dark' : 'plain'"
                @click="selectCronPreset(preset.value)"
              >
                {{ preset.label }}
              </el-tag>
            </div>
            
            <el-checkbox v-model="showCustomCron">自定义Cron表达式</el-checkbox>
            
            <div v-if="showCustomCron">
              <el-input v-model="formData.schedule" placeholder="例如: 0 9 * * *">
                <template #append>
                  <el-tooltip content="格式: 分 时 日 月 周" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
              </el-input>
            </div>
            
            <div v-else-if="isDailyPreset()" class="flex items-center gap-2 bg-gray-50 p-2 rounded">
              <span class="text-sm">每天</span>
              <el-time-picker
                v-model="cronTime"
                format="HH:mm"
                placeholder="选择时间"
                style="width: 140px"
                @change="updateCronFromTime"
              />
              <span class="text-sm">执行</span>
            </div>
            
            <div class="text-xs text-gray-400 mt-1">{{ getCronPreview() }}</div>
          </div>
        </el-form-item>
        
        <el-form-item label="状态">
          <el-switch v-model="formData.enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            :rows="3" 
            placeholder="任务描述（可选）" 
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import {
  getScheduledTasks,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  runScheduledTaskNow
} from '@/api/scheduler'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Timer, Plus, Refresh, VideoPlay, Edit, Delete, QuestionFilled } from '@element-plus/icons-vue'

export default {
  name: 'SchedulerManagement',
  components: {
    Timer, Plus, Refresh, VideoPlay, Edit, Delete, QuestionFilled
  },
  setup() {
    const loading = ref(false)
    const tasks = ref([])
    const dialogVisible = ref(false)
    const isEditing = ref(false)
    const currentTask = ref(null)
    const formRef = ref(null)
    
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
    const cronTime = ref(new Date(2000, 0, 1, 9, 0)) // Default 9:00

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
        if (response.success) {
          tasks.value = response.data.tasks || []
        }
      } catch (error) {
        console.error('加载任务列表失败:', error)
        ElMessage.error('加载任务列表失败')
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
      cronTime.value = new Date(2000, 0, 1, 9, 0)
    }

    // 提交表单
    const submitForm = async () => {
      // 根据类型生成schedule
      if (formData.task_type === 'interval') {
        formData.schedule = calculateIntervalSeconds().toString()
      } else if (!showCustomCron.value) {
        // 如果不是自定义模式，从时间选择器生成cron
        if (isDailyPreset()) {
          const hours = cronTime.value.getHours()
          const minutes = cronTime.value.getMinutes()
          formData.schedule = `${minutes} ${hours} * * *`
        }
      }

      // 验证
      if (!formData.name || !formData.schedule) {
        ElMessage.warning('请填写必填字段')
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
          ElMessage.success('更新任务成功')
        } else {
          // 创建任务
          await createScheduledTask(data)
          ElMessage.success('创建任务成功')
        }

        dialogVisible.value = false
        refreshTasks()
      } catch (error) {
        console.error('提交失败:', error)
        ElMessage.error(isEditing.value ? '更新任务失败' : '创建任务失败')
      }
    }

    // Handle Switch Change for Status
    const handleStatusChange = async (task, val) => {
      try {
        // Optimistic update already happened via v-model, but if it fails we should revert
        // However, for better UX, we can just send the request
        const response = await updateScheduledTask(task.id, {
          enabled: val
        })
        if (response.success) {
          ElMessage.success(`${val ? '启用' : '禁用'}任务成功`)
          // refreshTasks() // Optional, but might be good to sync everything
        } else {
           // Revert on failure (if needed, but simple reload is easier)
           task.enabled = !val
           ElMessage.error('切换状态失败')
        }
      } catch (error) {
        console.error('切换任务状态失败:', error)
        task.enabled = !val // Revert
        ElMessage.error('切换任务状态失败: ' + (error.response?.data?.message || error.message))
      }
    }

    // 立即执行任务
    const runTaskNow = (task) => {
      ElMessageBox.confirm(
        `确定要立即执行任务 "${task.name}" 吗？`,
        '执行任务',
        {
          confirmButtonText: '执行',
          cancelButtonText: '取消',
          type: 'warning',
        }
      ).then(async () => {
        try {
          const response = await runScheduledTaskNow(task.id)
          if (response.success) {
            ElMessage.success(`任务 "${task.name}" 已开始执行`)
            // 刷新任务列表以更新最后运行时间
            setTimeout(() => {
              refreshTasks()
            }, 1000)
          }
        } catch (error) {
          console.error('执行任务失败:', error)
          ElMessage.error('执行任务失败: ' + (error.response?.data?.message || error.message))
        }
      }).catch(() => {})
    }

    // 确认删除
    const confirmDelete = (task) => {
      ElMessageBox.confirm(
        `确定要删除任务 "${task.name}" 吗？`,
        '确认删除',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        }
      ).then(async () => {
        try {
          const response = await deleteScheduledTask(task.id)
          if (response.success) {
            ElMessage.success('删除任务成功')
            refreshTasks()
          }
        } catch (error) {
          console.error('删除任务失败:', error)
          ElMessage.error('删除任务失败: ' + (error.response?.data?.message || error.message))
        }
      }).catch(() => {})
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
      if (!task.enabled) return '已停止'
      if (!task.next_run) return '等待中'
      
      const now = new Date()
      const nextRun = new Date(task.next_run)
      if (nextRun <= now) return '运行中'
      return '等待中'
    }

    // 获取运行状态样式类
    const getRunningStatusType = (task) => {
      const status = getRunningStatus(task)
      if (status === '运行中') return 'success'
      if (status === '等待中') return 'info'
      return 'danger'
    }

    // 判断下次运行是否即将到来 (1小时内)
    const isNextRunSoon = (task) => {
      if (!task.next_run) return false
      const now = new Date()
      const nextRun = new Date(task.next_run)
      const diff = nextRun - now
      return diff > 0 && diff < 3600000 // 1小时
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
      if (value === '0 9 * * *') {
        parseCronFromSchedule(value)
      }
    }

    // 判断是否为每天预设
    const isDailyPreset = () => {
      // Basic check for "min hour * * *" pattern
      return formData.schedule && formData.schedule.match(/^\d+ \d+ \* \* \*$/)
    }

    // 从时间选择器更新Cron
    const updateCronFromTime = () => {
      if (!showCustomCron.value && isDailyPreset()) {
        const hours = cronTime.value.getHours()
        const minutes = cronTime.value.getMinutes()
        formData.schedule = `${minutes} ${hours} * * *`
      }
    }

    // 获取Cron预览
    const getCronPreview = () => {
      if (!formData.schedule) return '请选择或输入Cron表达式'
      const preset = cronPresets.find(p => p.value === formData.schedule)
      if (preset) return preset.label
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
      const preset = cronPresets.find(p => p.value === schedule)
      if (preset) {
        showCustomCron.value = false
      } else {
        showCustomCron.value = true
      }

      const match = schedule.match(/^(\d+) (\d+) \* \* \*$/)
      if (match) {
        const date = new Date()
        date.setHours(parseInt(match[2]))
        date.setMinutes(parseInt(match[1]))
        cronTime.value = date
      }
    }

    onMounted(() => {
      loadTasks()
    })

    return {
      loading,
      tasks,
      dialogVisible,
      isEditing,
      formData,
      filters,
      intervalValue,
      intervalUnit,
      showCustomCron,
      cronTime,
      cronPresets,
      formRef,
      loadTasks,
      refreshTasks,
      showCreateDialog,
      showEditDialog,
      resetForm,
      submitForm,
      handleStatusChange,
      runTaskNow,
      confirmDelete,
      formatTime,
      isHueyTask,
      getTaskDescription,
      getRunningStatus,
      getRunningStatusType,
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
/* Scoped styles mostly replaced by utility classes */
</style>
