<template>
  <div class="filter-management">
    <!-- 标题栏 -->
    <div class="header">
      <h2>过滤器管理</h2>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-label">总配置项</div>
        <div class="stat-value">{{ summary.total }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已激活</div>
        <div class="stat-value active">{{ summary.active }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">未激活</div>
        <div class="stat-value inactive">{{ summary.inactive }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tag 黑名单</div>
        <div class="stat-value">{{ summary.by_type.tag || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">标题关键词</div>
        <div class="stat-value">{{ summary.by_type.title_keyword || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">描述关键词</div>
        <div class="stat-value">{{ summary.by_type.description_keyword || 0 }}</div>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="main-content">
      <!-- 黑名单管理 -->
      <div class="section">
        <div class="section-header">
          <h3>黑名单配置</h3>
          <button class="btn-primary" @click="showAddDialog = true">➕ 添加黑名单</button>
        </div>

        <!-- 过滤器 -->
        <div class="filters">
          <select v-model="filterType" class="filter-select">
            <option value="">全部类型</option>
            <option value="tag">Tag 黑名单</option>
            <option value="title_keyword">标题关键词</option>
            <option value="description_keyword">描述关键词</option>
          </select>
          <select v-model="filterStatus" class="filter-select">
            <option value="">全部状态</option>
            <option value="active">已激活</option>
            <option value="inactive">未激活</option>
          </select>
        </div>

        <!-- 黑名单列表 -->
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="filteredBlacklist.length === 0" class="empty">暂无黑名单配置</div>
        <div v-else class="blacklist-table">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>类型</th>
                <th>值</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredBlacklist" :key="item.id">
                <td>{{ item.id }}</td>
                <td>
                  <span :class="['type-badge', item.blacklist_type]">
                    {{ getTypeLabel(item.blacklist_type) }}
                  </span>
                </td>
                <td class="value-cell">{{ item.value }}</td>
                <td>
                  <span :class="['status-badge', item.is_active ? 'active' : 'inactive']">
                    {{ item.is_active ? '已激活' : '未激活' }}
                  </span>
                </td>
                <td>{{ formatDate(item.created_at) }}</td>
                <td class="actions-cell">
                  <button 
                    class="btn-toggle" 
                    @click="toggleBlacklist(item)"
                    :title="item.is_active ? '禁用' : '启用'"
                  >
                    {{ item.is_active ? '🔴' : '🟢' }}
                  </button>
                  <button class="btn-delete" @click="confirmDelete(item)" title="删除">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 已处理事件管理 -->
      <div class="section">
        <div class="section-header">
          <h3>已处理事件 ({{ processedTotal }})</h3>
          <button class="btn-danger" @click="confirmClearProcessed">🗑️ 清空所有</button>
        </div>

        <!-- 已处理事件列表 -->
        <div v-if="loadingProcessed" class="loading">加载中...</div>
        <div v-else-if="processedMarkets.length === 0" class="empty">暂无已处理事件</div>
        <div v-else class="processed-table">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Market ID</th>
                <th>处理时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in processedMarkets" :key="item.id">
                <td>{{ item.id }}</td>
                <td class="market-id-cell">{{ item.market_id }}</td>
                <td>{{ formatDate(item.processed_at) }}</td>
                <td class="actions-cell">
                  <button class="btn-delete" @click="deleteProcessedMarket(item.market_id)" title="删除">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 分页 -->
          <div class="pagination">
            <button :disabled="processedOffset === 0" @click="loadProcessedMarkets(processedOffset - processedLimit)">
              上一页
            </button>
            <span class="page-info">
              显示 {{ processedOffset + 1 }} - {{ Math.min(processedOffset + processedLimit, processedTotal) }} / {{ processedTotal }}
            </span>
            <button :disabled="processedOffset + processedLimit >= processedTotal" @click="loadProcessedMarkets(processedOffset + processedLimit)">
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加黑名单对话框 -->
    <Modal
      v-model:visible="showAddDialog"
      title="添加黑名单"
      size="small"
      @confirm="addBlacklist"
    >
      <div class="form-group">
        <label>类型</label>
        <select v-model="newBlacklist.type" class="form-control">
          <option value="tag">Tag 黑名单</option>
          <option value="title_keyword">标题关键词</option>
          <option value="description_keyword">描述关键词</option>
        </select>
      </div>
      <div class="form-group">
        <label>值</label>
        <input
          v-model="newBlacklist.value"
          type="text"
          class="form-control"
          placeholder="请输入黑名单值"
          @keyup.enter="addBlacklist"
        />
      </div>
    </Modal>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import {
  getBlacklist,
  addBlacklist as addBlacklistApi,
  deleteBlacklist as deleteBlacklistApi,
  toggleBlacklist as toggleBlacklistApi,
  getProcessedMarkets,
  deleteProcessedMarket as deleteProcessedMarketApi,
  clearProcessedMarkets as clearProcessedMarketsApi
} from '@/api/filter'
import { toast, confirm, Modal } from '@/components/Notification'

export default {
  name: 'FilterManagement',
  components: {
    Modal
  },
  setup() {
    // 数据状态
    const loading = ref(false)
    const loadingProcessed = ref(false)
    const blacklistItems = ref([])
    const summary = ref({
      total: 0,
      active: 0,
      inactive: 0,
      by_type: {}
    })
    
    // 过滤器
    const filterType = ref('')
    const filterStatus = ref('')
    
    // 已处理事件
    const processedMarkets = ref([])
    const processedTotal = ref(0)
    const processedLimit = ref(50)
    const processedOffset = ref(0)
    
    // 对话框
    const showAddDialog = ref(false)
    const newBlacklist = ref({
      type: 'tag',
      value: ''
    })

    // 计算过滤后的黑名单列表
    const filteredBlacklist = computed(() => {
      let items = blacklistItems.value
      
      if (filterType.value) {
        items = items.filter(item => item.blacklist_type === filterType.value)
      }
      
      if (filterStatus.value === 'active') {
        items = items.filter(item => item.is_active)
      } else if (filterStatus.value === 'inactive') {
        items = items.filter(item => !item.is_active)
      }
      
      return items
    })

    // 获取黑名单配置
    const loadBlacklist = async () => {
      loading.value = true
      try {
        const response = await getBlacklist()
        if (response.success) {
          blacklistItems.value = response.data.items
          summary.value = response.data.summary
        }
      } catch (error) {
        console.error('获取黑名单配置失败:', error)
        toast.error('获取黑名单配置失败')
      } finally {
        loading.value = false
      }
    }

    // 获取已处理事件
    const loadProcessedMarkets = async (offset = 0) => {
      loadingProcessed.value = true
      processedOffset.value = offset
      try {
        const response = await getProcessedMarkets({
          limit: processedLimit.value,
          offset: offset
        })
        if (response.success) {
          processedMarkets.value = response.data.items
          processedTotal.value = response.data.total
        }
      } catch (error) {
        console.error('获取已处理事件失败:', error)
      } finally {
        loadingProcessed.value = false
      }
    }

    // 刷新数据
    const refreshData = () => {
      loadBlacklist()
      loadProcessedMarkets(processedOffset.value)
    }

    // 添加黑名单
    const addBlacklist = async () => {
      if (!newBlacklist.value.value.trim()) {
        toast.warning('请输入黑名单值')
        return
      }

      try {
        const response = await addBlacklistApi({
          blacklist_type: newBlacklist.value.type,
          value: newBlacklist.value.value.trim()
        })

        if (response.success) {
          toast.success('添加成功')
          showAddDialog.value = false
          newBlacklist.value.value = ''
          loadBlacklist()
        } else {
          toast.error(response.message || '添加失败')
        }
      } catch (error) {
        console.error('添加黑名单失败:', error)
        toast.error('添加黑名单失败')
      }
    }

    // 切换黑名单状态
    const toggleBlacklist = async (item) => {
      try {
        const response = await toggleBlacklistApi(item.id, !item.is_active)

        if (response.success) {
          loadBlacklist()
        } else {
          toast.error(response.message || '操作失败')
        }
      } catch (error) {
        console.error('切换黑名单状态失败:', error)
        toast.error('操作失败')
      }
    }

    // 确认删除黑名单
    const confirmDelete = async (item) => {
      const result = await confirm(`确定要删除黑名单项 "${item.value}" 吗？`)
      if (result) {
        deleteBlacklist(item.id)
      }
    }

    // 删除黑名单
    const deleteBlacklist = async (id) => {
      try {
        const response = await deleteBlacklistApi(id)

        if (response.success) {
          toast.success('删除成功')
          loadBlacklist()
        } else {
          toast.error(response.message || '删除失败')
        }
      } catch (error) {
        console.error('删除黑名单失败:', error)
        toast.error('删除失败')
      }
    }

    // 删除已处理事件
    const deleteProcessedMarket = async (marketId) => {
      const result = await confirm(`确定要删除已处理事件 "${marketId}" 吗？`)
      if (!result) {
        return
      }

      try {
        const response = await deleteProcessedMarketApi(marketId)

        if (response.success) {
          loadProcessedMarkets(processedOffset.value)
        } else {
          toast.error(response.message || '删除失败')
        }
      } catch (error) {
        console.error('删除已处理事件失败:', error)
        toast.error('删除失败')
      }
    }

    // 确认清空已处理事件
    const confirmClearProcessed = async () => {
      const result = await confirm({
        message: '确定要清空所有已处理事件吗？此操作不可恢复！',
        type: 'danger'
      })
      if (result) {
        clearProcessedMarkets()
      }
    }

    // 清空已处理事件
    const clearProcessedMarkets = async () => {
      try {
        const response = await clearProcessedMarketsApi()

        if (response.success) {
          toast.success(`已清空 ${response.data.cleared_count} 条记录`)
          loadProcessedMarkets(0)
        } else {
          toast.error(response.message || '清空失败')
        }
      } catch (error) {
        console.error('清空已处理事件失败:', error)
        toast.error('清空失败')
      }
    }

    // 格式化日期
    const formatDate = (dateStr) => {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN')
    }

    // 获取类型标签
    const getTypeLabel = (type) => {
      const labels = {
        'tag': 'Tag',
        'title_keyword': '标题',
        'description_keyword': '描述'
      }
      return labels[type] || type
    }

    // 初始化
    onMounted(() => {
      loadBlacklist()
      loadProcessedMarkets(0)
    })

    return {
      loading,
      loadingProcessed,
      blacklistItems,
      summary,
      filterType,
      filterStatus,
      filteredBlacklist,
      processedMarkets,
      processedTotal,
      processedLimit,
      processedOffset,
      showAddDialog,
      newBlacklist,
      refreshData,
      addBlacklist,
      toggleBlacklist,
      confirmDelete,
      deleteProcessedMarket,
      confirmClearProcessed,
      loadProcessedMarkets,
      formatDate,
      getTypeLabel
    }
  }
}
</script>

<style scoped>
.filter-management {
  padding: 20px;
}

/* 标题栏 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

.stat-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  padding: 15px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.stat-value.active {
  color: #52c41a;
}

.stat-value.inactive {
  color: #999;
}

/* 主体区域 */
.main-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

/* 区块 */
.section {
  background: #fff;
  border: 1px solid #e0e0e0;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

/* 过滤器 */
.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
  color: #333;
}

/* 表格 */
.blacklist-table table,
.processed-table table {
  width: 100%;
  border-collapse: collapse;
}

.blacklist-table th,
.blacklist-table td,
.processed-table th,
.processed-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
  color: #333;
}

.blacklist-table th,
.processed-table th {
  background: #fafafa;
  font-weight: 600;
  color: #333;
}

.blacklist-table tbody tr:hover,
.processed-table tbody tr:hover {
  background: #fafafa;
}

/* 类型标签 */
.type-badge {
  display: inline-block;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 2px;
  background: #e6f7ff;
  color: #1890ff;
}

.type-badge.title_keyword {
  background: #fff7e6;
  color: #fa8c16;
}

.type-badge.description_keyword {
  background: #f6ffed;
  color: #52c41a;
}

/* 状态标签 */
.status-badge {
  display: inline-block;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 2px;
}

.status-badge.active {
  background: #f6ffed;
  color: #52c41a;
}

.status-badge.inactive {
  background: #f5f5f5;
  color: #999;
}

/* 单元格 */
.value-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.market-id-cell {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

.actions-cell {
  white-space: nowrap;
}

/* 按钮 */
.btn-refresh,
.btn-primary,
.btn-secondary,
.btn-danger,
.btn-toggle,
.btn-delete,
.btn-close {
  padding: 8px 16px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  background: #fff;
  border: 1px solid #d9d9d9;
  color: #333;
}

.btn-refresh:hover,
.btn-toggle:hover,
.btn-delete:hover {
  background: #f5f5f5;
}

.btn-primary {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.btn-primary:hover {
  background: #40a9ff;
  border-color: #40a9ff;
}

.btn-danger {
  background: #ff4d4f;
  color: #fff;
  border-color: #ff4d4f;
}

.btn-danger:hover {
  background: #ff7875;
  border-color: #ff7875;
}

.btn-toggle {
  padding: 4px 8px;
  font-size: 16px;
}

.btn-delete {
  padding: 4px 8px;
  font-size: 16px;
  margin-left: 5px;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  background: #fff;
  cursor: pointer;
  color: #333;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination button:not(:disabled):hover {
  background: #f5f5f5;
}

.page-info {
  color: #666;
  font-size: 14px;
}

/* 加载和空状态 */
.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #999;
}



/* 表单 */
.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  font-size: 14px;
  box-sizing: border-box;
  color: #333;
  background: #fff;
}

.form-control:focus {
  outline: none;
  border-color: #1890ff;
}
</style>

