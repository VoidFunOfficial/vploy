<template>
  <div class="page-container p-4">
    <div class="page-header mb-4 flex justify-between items-center">
      <h2 class="text-xl font-bold" style="font-size: 1.25rem; font-weight: 700; color: var(--el-text-color-primary);">系统信息</h2>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="12" :lg="8">
        <el-card shadow="hover" class="h-full">
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-medium">GPT 额度状态</span>
              <el-button 
                type="primary" 
                link 
                @click="handleCleanup"
                :loading="cleaning"
              >
                清理记录
              </el-button>
            </div>
          </template>
          
          <div v-loading="loading" class="quota-content">
            <div class="status-row mb-4 flex items-center" style="margin-bottom: 1rem; gap: 10px;">
              <span class="label">当前状态:</span>
              <el-tag :type="quotaData.allowed ? 'success' : 'danger'" effect="dark">
                {{ quotaData.allowed ? '允许请求' : '限制请求' }}
              </el-tag>
            </div>

            <div v-if="!quotaData.allowed" class="error-info mb-4" style="margin-bottom: 1rem;">
              <el-alert
                :title="quotaData.reason"
                type="error"
                :description="quotaData.next_available ? `预计恢复时间: ${formatDate(quotaData.next_available)}` : ''"
                show-icon
                :closable="false"
              />
            </div>

            <div class="usage-list">
              <div v-for="(info, key) in quotaData.usage" :key="key" class="usage-item mb-3" style="margin-bottom: 0.75rem;">
                <div class="flex justify-between mb-1" style="margin-bottom: 0.25rem;">
                  <span class="text-sm" style="font-size: 0.875rem;">{{ formatDuration(key) }}</span>
                  <span class="text-sm text-secondary" style="font-size: 0.875rem; color: var(--el-text-color-secondary);">
                    {{ info.current }} / {{ info.limit }}
                  </span>
                </div>
                <el-progress 
                  :percentage="calculatePercentage(info.current, info.limit)"
                  :status="getProgressStatus(info.current, info.limit)"
                  :format="() => `${info.remaining} 剩余`"
                />
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { getGptQuotaStatus, cleanupGptQuotaRecords } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'SystemInfo',
  setup() {
    const loading = ref(false)
    const cleaning = ref(false)
    const quotaData = ref({
      allowed: true,
      reason: '',
      usage: {},
      next_available: null
    })

    const fetchData = async () => {
      loading.value = true
      try {
        const res = await getGptQuotaStatus()
        if (res.success) {
          quotaData.value = res.data
        }
      } catch (error) {
        console.error('获取GPT额度失败:', error)
        ElMessage.error('获取GPT额度失败')
      } finally {
        loading.value = false
      }
    }

    const handleCleanup = async () => {
      try {
        await ElMessageBox.confirm(
          '确定要清理30天前的GPT请求记录吗？',
          '清理确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        cleaning.value = true
        const res = await cleanupGptQuotaRecords(30)
        if (res.success) {
          ElMessage.success(res.message || '清理成功')
          fetchData()
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('清理失败:', error)
          ElMessage.error('清理失败')
        }
      } finally {
        cleaning.value = false
      }
    }

    const calculatePercentage = (current, limit) => {
      if (!limit) return 0
      const p = (current / limit) * 100
      return Math.min(Math.max(p, 0), 100)
    }

    const getProgressStatus = (current, limit) => {
      const p = current / limit
      if (p >= 1) return 'exception'
      if (p >= 0.8) return 'warning'
      return 'success'
    }

    const formatDuration = (key) => {
        return key.replace('h', '小时') + '内限制'
    }

    const formatDate = (dateStr) => {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleString()
    }

    onMounted(() => {
      fetchData()
    })

    return {
      loading,
      cleaning,
      quotaData,
      handleCleanup,
      calculatePercentage,
      getProgressStatus,
      formatDuration,
      formatDate
    }
  }
}
</script>

<style scoped>
.page-container {
  min-height: 100%;
}
</style>
