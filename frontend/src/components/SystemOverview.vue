<template>
  <div class="page-container">
    <div class="page-header mb-4">
      <h2 class="text-xl font-bold text-gray-800">系统宏观信息</h2>
    </div>

    <!-- 首次加载状态 -->
    <div v-if="isFirstLoading" class="loading-container" v-loading="true" element-loading-text="加载系统数据中...">
    </div>
    
    <template v-else>
      <el-row :gutter="20">
        <!-- CPU -->
        <el-col :xs="24" :sm="12" :md="6" class="mb-4">
          <el-card shadow="hover" class="monitor-card h-full">
            <template #header>
              <div class="flex justify-between items-center">
                <span class="font-medium">CPU 占用率</span>
                <el-tag size="small" effect="plain">{{ systemData.cpu_count }} 核心</el-tag>
              </div>
            </template>
            <div class="flex flex-col items-center justify-center p-4">
              <el-progress type="dashboard" :percentage="systemData.cpu_percent" :color="colors" :width="120" />
            </div>
          </el-card>
        </el-col>

        <!-- 内存 -->
        <el-col :xs="24" :sm="12" :md="6" class="mb-4">
          <el-card shadow="hover" class="monitor-card h-full">
            <template #header>
              <div class="flex justify-between items-center">
                <span class="font-medium">内存占用率</span>
              </div>
            </template>
            <div class="flex flex-col items-center justify-center p-4">
              <el-progress type="dashboard" :percentage="systemData.memory_percent" :color="colors" :width="120" />
              <div class="mt-4 text-gray-500 text-sm font-medium">
                {{ formatBytes(systemData.memory_used) }} / {{ formatBytes(systemData.memory_total) }}
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 磁盘 -->
        <el-col :xs="24" :sm="12" :md="6" class="mb-4">
          <el-card shadow="hover" class="monitor-card h-full">
            <template #header>
              <div class="flex justify-between items-center">
                <span class="font-medium">磁盘占用率</span>
              </div>
            </template>
            <div class="flex flex-col items-center justify-center p-4">
              <el-progress type="dashboard" :percentage="systemData.disk_percent" :color="colors" :width="120" />
              <div class="mt-4 text-gray-500 text-sm font-medium">
                {{ formatBytes(systemData.disk_used) }} / {{ formatBytes(systemData.disk_total) }}
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 运行时间 -->
        <el-col :xs="24" :sm="12" :md="6" class="mb-4">
          <el-card shadow="hover" class="monitor-card h-full flex flex-col">
            <template #header>
              <div class="flex justify-between items-center">
                <span class="font-medium">系统运行时间</span>
              </div>
            </template>
            <div class="flex flex-col items-center justify-center flex-grow p-4">
              <div class="text-2xl font-bold text-primary mb-2">{{ formatUptime(systemData.uptime) }}</div>
              <div class="text-gray-500 text-sm">启动时间: {{ systemData.boot_time }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- TPS 统计 -->
      <el-card shadow="hover" class="mt-4">
        <template #header>
          <div class="flex justify-between items-center">
            <span class="font-medium">TPS 统计（近 3 小时）</span>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :xs="12" :sm="6">
            <el-statistic title="当前 TPS" :value="systemData.current_tps" value-style="color: var(--el-color-primary)" />
          </el-col>
          <el-col :xs="12" :sm="6">
            <el-statistic title="平均 TPS" :value="systemData.avg_tps" />
          </el-col>
          <el-col :xs="12" :sm="6">
            <el-statistic title="峰值 TPS" :value="systemData.max_tps" value-style="color: var(--el-color-warning)" />
          </el-col>
          <el-col :xs="12" :sm="6">
            <el-statistic title="总事务数" :value="systemData.total_transactions" />
          </el-col>
        </el-row>
      </el-card>
    </template>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { getSystemMonitor } from '@/api/monitor'

export default {
  name: 'SystemOverview',
  setup() {
    const isFirstLoading = ref(true)
    
    // 进度条颜色配置
    const colors = [
      { color: '#10B981', percentage: 50 },
      { color: '#F59E0B', percentage: 80 },
      { color: '#EF4444', percentage: 100 },
    ]

    // 系统数据
    const systemData = ref({
      cpu_percent: 0,
      cpu_count: 0,
      memory_percent: 0,
      memory_used: 0,
      memory_total: 0,
      disk_percent: 0,
      disk_used: 0,
      disk_total: 0,
      uptime: 0,
      boot_time: '',
      current_tps: 0,
      avg_tps: 0,
      max_tps: 0,
      total_transactions: 0
    })

    // 格式化字节数
    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    // 格式化运行时间
    const formatUptime = (seconds) => {
      const days = Math.floor(seconds / 86400)
      const hours = Math.floor((seconds % 86400) / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      return `${days}天 ${hours}小时 ${minutes}分钟`
    }

    // 获取系统监控数据
    const fetchSystemData = async () => {
      try {
        const response = await getSystemMonitor()
        if (response.success) {
          systemData.value = response.data
        }
      } catch (error) {
        console.error('获取系统监控数据失败:', error)
      } finally {
        if (isFirstLoading.value) {
          isFirstLoading.value = false
        }
      }
    }

    let refreshTimer = null

    const handleGlobalRefresh = () => {
      fetchSystemData()
    }

    onMounted(() => {
      fetchSystemData()
      refreshTimer = setInterval(fetchSystemData, 5000)
      window.addEventListener('global-refresh', handleGlobalRefresh)
    })

    onUnmounted(() => {
      if (refreshTimer) {
        clearInterval(refreshTimer)
      }
      window.removeEventListener('global-refresh', handleGlobalRefresh)
    })

    return {
      isFirstLoading,
      systemData,
      colors,
      formatBytes,
      formatUptime
    }
  }
}
</script>

<style scoped>
.loading-container {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.text-primary {
  color: var(--el-color-primary);
}

.h-full {
  height: 100%;
}

.monitor-card {
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  flex-grow: 1;
}
</style>
