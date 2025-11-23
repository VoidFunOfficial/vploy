<template>
  <div class="system-overview">
    <h2 class="page-title">系统宏观信息</h2>

    <!-- 状态卡片区域 -->
    <div class="status-cards">
      <!-- CPU 占用率 -->
      <div class="status-card">
        <div class="card-header">
          <span class="card-icon">💻</span>
          <span class="card-title">CPU 占用率</span>
        </div>
        <div class="card-body">
          <div class="progress-circle">
            <svg width="120" height="120">
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke="#e0e0e0"
                stroke-width="10"
              />
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                :stroke="getColorByValue(systemData.cpu_percent)"
                stroke-width="10"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="getCpuOffset"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="progress-text">
              <span class="progress-value">{{ systemData.cpu_percent }}%</span>
            </div>
          </div>
          <div class="card-info">{{ systemData.cpu_count }} 核心</div>
        </div>
      </div>

      <!-- 内存占用率 -->
      <div class="status-card">
        <div class="card-header">
          <span class="card-icon">🧠</span>
          <span class="card-title">内存占用率</span>
        </div>
        <div class="card-body">
          <div class="progress-circle">
            <svg width="120" height="120">
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke="#e0e0e0"
                stroke-width="10"
              />
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                :stroke="getColorByValue(systemData.memory_percent)"
                stroke-width="10"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="getMemoryOffset"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="progress-text">
              <span class="progress-value">{{ systemData.memory_percent }}%</span>
            </div>
          </div>
          <div class="card-info">
            {{ formatBytes(systemData.memory_used) }} / {{ formatBytes(systemData.memory_total) }}
          </div>
        </div>
      </div>

      <!-- 磁盘占用率 -->
      <div class="status-card">
        <div class="card-header">
          <span class="card-icon">💾</span>
          <span class="card-title">磁盘占用率</span>
        </div>
        <div class="card-body">
          <div class="progress-circle">
            <svg width="120" height="120">
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke="#e0e0e0"
                stroke-width="10"
              />
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                :stroke="getColorByValue(systemData.disk_percent)"
                stroke-width="10"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="getDiskOffset"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="progress-text">
              <span class="progress-value">{{ systemData.disk_percent }}%</span>
            </div>
          </div>
          <div class="card-info">
            {{ formatBytes(systemData.disk_used) }} / {{ formatBytes(systemData.disk_total) }}
          </div>
        </div>
      </div>

      <!-- 累计运行时间 -->
      <div class="status-card">
        <div class="card-header">
          <span class="card-icon">⏱️</span>
          <span class="card-title">累计运行时间</span>
        </div>
        <div class="card-body">
          <div class="uptime-display">
            <div class="uptime-value">{{ formatUptime(systemData.uptime) }}</div>
          </div>
          <div class="card-info">启动时间: {{ systemData.boot_time }}</div>
        </div>
      </div>
    </div>

    <!-- TPS 统计区域 -->
    <div class="tps-section">
      <div class="section-card">
        <div class="section-header">
          <span class="section-icon">📊</span>
          <span class="section-title">TPS 统计（近 3 小时）</span>
          <span class="refresh-btn" @click="refreshData">🔄 刷新</span>
        </div>
        <div class="section-body">
          <div class="tps-stats">
            <div class="stat-item">
              <div class="stat-label">当前 TPS</div>
              <div class="stat-value">{{ systemData.current_tps }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">平均 TPS</div>
              <div class="stat-value">{{ systemData.avg_tps }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">峰值 TPS</div>
              <div class="stat-value">{{ systemData.max_tps }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">总事务数</div>
              <div class="stat-value">{{ systemData.total_transactions }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 首次加载状态 -->
    <div v-if="isFirstLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <div class="loading-text">加载中...</div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getSystemMonitor } from '@/api/monitor'

export default {
  name: 'SystemOverview',
  setup() {
    const isFirstLoading = ref(true)  // 首次加载标志
    const circumference = 2 * Math.PI * 50 // 圆周长

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

    // 计算 CPU 进度条偏移
    const getCpuOffset = computed(() => {
      const percent = systemData.value.cpu_percent
      return circumference - (percent / 100) * circumference
    })

    // 计算内存进度条偏移
    const getMemoryOffset = computed(() => {
      const percent = systemData.value.memory_percent
      return circumference - (percent / 100) * circumference
    })

    // 计算磁盘进度条偏移
    const getDiskOffset = computed(() => {
      const percent = systemData.value.disk_percent
      return circumference - (percent / 100) * circumference
    })

    // 根据数值获取颜色
    const getColorByValue = (value) => {
      if (value < 50) return '#20a53a'
      if (value < 80) return '#ff9800'
      return '#ff5722'
    }

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
        // 首次加载完成后，关闭加载遮罩
        if (isFirstLoading.value) {
          isFirstLoading.value = false
        }
      }
    }

    // 刷新数据
    const refreshData = () => {
      fetchSystemData()
    }

    // 定时刷新
    let refreshTimer = null

    onMounted(() => {
      fetchSystemData()
      // 每 5 秒刷新一次
      refreshTimer = setInterval(fetchSystemData, 5000)
    })

    onUnmounted(() => {
      if (refreshTimer) {
        clearInterval(refreshTimer)
      }
    })

    return {
      isFirstLoading,
      systemData,
      circumference,
      getCpuOffset,
      getMemoryOffset,
      getDiskOffset,
      getColorByValue,
      formatBytes,
      formatUptime,
      refreshData
    }
  }
}
</script>

<style scoped>
/* 系统概览容器 */
.system-overview {
  padding: 20px;
  position: relative;
}

/* 页面标题 */
.page-title {
  font-size: 18px;
  color: #333;
  margin-bottom: 20px;
  font-weight: 500;
}

/* 状态卡片区域 */
.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .system-overview {
    padding: 10px;
  }

  .page-title {
    font-size: 16px;
    margin-bottom: 15px;
  }

  .status-cards {
    grid-template-columns: 1fr;
    gap: 10px;
    margin-bottom: 15px;
  }
}

/* 状态卡片 */
.status-card {
  background-color: #fff;
  border: 1px solid #ddd;
  padding: 20px;
}

/* 移动端卡片样式 */
@media (max-width: 768px) {
  .status-card {
    padding: 15px;
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.card-icon {
  font-size: 18px;
}

.card-title {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.card-body {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 进度圆环 */
.progress-circle {
  position: relative;
  width: 120px;
  height: 120px;
  margin-bottom: 10px;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.progress-value {
  font-size: 24px;
  color: #333;
  font-weight: 500;
}

.card-info {
  font-size: 12px;
  color: #666;
  text-align: center;
}

/* 移动端进度圆环 */
@media (max-width: 768px) {
  .progress-circle {
    width: 100px;
    height: 100px;
  }

  .progress-value {
    font-size: 20px;
  }

  .card-info {
    font-size: 11px;
  }
}

/* 运行时间显示 */
.uptime-display {
  width: 100%;
  padding: 30px 0;
  text-align: center;
}

.uptime-value {
  font-size: 18px;
  color: #20a53a;
  font-weight: 500;
}

/* TPS 统计区域 */
.tps-section {
  margin-bottom: 20px;
}

.section-card {
  background-color: #fff;
  border: 1px solid #ddd;
}

/* 移动端 TPS 区域 */
@media (max-width: 768px) {
  .tps-section {
    margin-bottom: 15px;
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 15px 20px;
  border-bottom: 1px solid #ddd;
}

.section-icon {
  font-size: 18px;
}

.section-title {
  flex: 1;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.refresh-btn {
  font-size: 12px;
  color: #20a53a;
  cursor: pointer;
}

.refresh-btn:hover {
  color: #1a8c31;
}

.section-body {
  padding: 20px;
}

/* 移动端区域头部 */
@media (max-width: 768px) {
  .section-header {
    padding: 12px 15px;
  }

  .section-icon {
    font-size: 16px;
  }

  .section-title {
    font-size: 13px;
  }

  .section-body {
    padding: 15px;
  }
}

/* TPS 统计 */
.tps-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background-color: #f9f9f9;
  border: 1px solid #e0e0e0;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  color: #20a53a;
  font-weight: 500;
}

/* 移动端 TPS 统计 */
@media (max-width: 768px) {
  .tps-stats {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .stat-item {
    padding: 12px;
  }

  .stat-label {
    font-size: 11px;
  }

  .stat-value {
    font-size: 20px;
  }
}

/* 加载状态 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 15px;
  z-index: 1000;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e0e0e0;
  border-top-color: #20a53a;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-size: 14px;
  color: #666;
}

/* 数据更新平滑过渡 */
.progress-value,
.uptime-value,
.stat-value,
.card-info {
  transition: opacity 0.3s ease;
}

/* 圆环进度条平滑过渡 */
.progress-circle circle {
  transition: stroke-dashoffset 0.5s ease, stroke 0.3s ease;
}
</style>

