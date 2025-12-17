<template>
  <div class="filter-management">
    <el-card shadow="never" class="stats-container">
      <template #header>
        <div class="header">
          <h2>过滤器管理</h2>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="4" :xs="12">
          <el-statistic title="总配置项" :value="summary.total" />
        </el-col>
        <el-col :span="4" :xs="12">
          <el-statistic title="已激活" :value="summary.active" value-style="color: var(--el-color-success)" />
        </el-col>
        <el-col :span="4" :xs="12">
          <el-statistic title="未激活" :value="summary.inactive" value-style="color: var(--el-color-info)" />
        </el-col>
        <el-col :span="4" :xs="12">
          <el-statistic title="Tag 黑名单" :value="summary.by_type.tag || 0" />
        </el-col>
        <el-col :span="4" :xs="12">
          <el-statistic title="标题关键词" :value="summary.by_type.title_keyword || 0" />
        </el-col>
        <el-col :span="4" :xs="12">
          <el-statistic title="描述关键词" :value="summary.by_type.description_keyword || 0" />
        </el-col>
      </el-row>
    </el-card>

    <div class="main-content">
      <!-- 黑名单管理 -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="section-header">
            <h3>黑名单配置</h3>
            <el-button type="primary" :icon="Plus" @click="showAddDialog = true">添加黑名单</el-button>
          </div>
        </template>

        <!-- 过滤器 -->
        <el-form :inline="true" class="filter-form">
          <el-form-item label="类型">
            <el-select v-model="filterType" placeholder="全部类型" clearable style="width: 150px">
              <el-option label="Tag 黑名单" value="tag" />
              <el-option label="标题关键词" value="title_keyword" />
              <el-option label="描述关键词" value="description_keyword" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 150px">
              <el-option label="已激活" value="active" />
              <el-option label="未激活" value="inactive" />
            </el-select>
          </el-form-item>
        </el-form>

        <!-- 黑名单列表 -->
        <el-table
          v-loading="loading"
          :data="filteredBlacklist"
          style="width: 100%"
          border
          stripe
        >
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column label="类型" width="150">
            <template #default="{ row }">
              <el-tag :type="getTypeTag(row.blacklist_type)">
                {{ getTypeLabel(row.blacklist_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="值" min-width="200" show-overflow-tooltip />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">
                {{ row.is_active ? '已激活' : '未激活' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button
                :type="row.is_active ? 'warning' : 'success'"
                size="small"
                circle
                :icon="row.is_active ? VideoPause : VideoPlay"
                @click="toggleBlacklist(row)"
                :title="row.is_active ? '禁用' : '启用'"
              />
              <el-button
                type="danger"
                size="small"
                circle
                :icon="Delete"
                @click="confirmDelete(row)"
                title="删除"
              />
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && filteredBlacklist.length === 0" description="暂无黑名单配置" />
      </el-card>

      <!-- 已处理事件管理 -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="section-header">
            <h3>已处理事件 ({{ processedTotal }})</h3>
            <el-button type="danger" :icon="Delete" @click="confirmClearProcessed">清空所有</el-button>
          </div>
        </template>

        <!-- 已处理事件列表 -->
        <el-table
          v-loading="loadingProcessed"
          :data="processedMarkets"
          style="width: 100%"
          border
          stripe
        >
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column label="Market ID" min-width="300">
             <template #default="{ row }">
                <span class="monospace-font">{{ row.market_id }}</span>
             </template>
          </el-table-column>
          <el-table-column label="处理时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.processed_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button
                type="danger"
                size="small"
                circle
                :icon="Delete"
                @click="deleteProcessedMarket(row.market_id)"
                title="删除"
              />
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="processedLimit"
            :total="processedTotal"
            layout="total, prev, pager, next"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 添加黑名单对话框 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加黑名单"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="newBlacklist" label-width="80px">
        <el-form-item label="类型">
          <el-select v-model="newBlacklist.type" style="width: 100%">
            <el-option label="Tag 黑名单" value="tag" />
            <el-option label="标题关键词" value="title_keyword" />
            <el-option label="描述关键词" value="description_keyword" />
          </el-select>
        </el-form-item>
        <el-form-item label="值">
          <el-input
            v-model="newBlacklist.value"
            placeholder="请输入黑名单值"
            @keyup.enter="addBlacklist"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="addBlacklist">确定</el-button>
        </span>
      </template>
    </el-dialog>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, VideoPlay, VideoPause } from '@element-plus/icons-vue'

export default {
  name: 'FilterManagement',
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
    const currentPage = ref(1)
    
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
        ElMessage.error('获取黑名单配置失败')
      } finally {
        loading.value = false
      }
    }

    // 获取已处理事件
    const loadProcessedMarkets = async (page = 1) => {
      loadingProcessed.value = true
      const offset = (page - 1) * processedLimit.value
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
    
    const handlePageChange = (page) => {
       currentPage.value = page
       loadProcessedMarkets(page)
    }

    // 刷新数据
    const refreshData = () => {
      loadBlacklist()
      loadProcessedMarkets(currentPage.value)
    }

    // 添加黑名单
    const addBlacklist = async () => {
      if (!newBlacklist.value.value.trim()) {
        ElMessage.warning('请输入黑名单值')
        return
      }

      try {
        const response = await addBlacklistApi({
          blacklist_type: newBlacklist.value.type,
          value: newBlacklist.value.value.trim()
        })

        if (response.success) {
          ElMessage.success('添加成功')
          showAddDialog.value = false
          newBlacklist.value.value = ''
          loadBlacklist()
        } else {
          ElMessage.error(response.message || '添加失败')
        }
      } catch (error) {
        console.error('添加黑名单失败:', error)
        ElMessage.error('添加黑名单失败')
      }
    }

    // 切换黑名单状态
    const toggleBlacklist = async (item) => {
      try {
        const response = await toggleBlacklistApi(item.id, !item.is_active)

        if (response.success) {
          loadBlacklist()
          ElMessage.success(item.is_active ? '已禁用' : '已激活')
        } else {
          ElMessage.error(response.message || '操作失败')
        }
      } catch (error) {
        console.error('切换黑名单状态失败:', error)
        ElMessage.error('操作失败')
      }
    }

    // 确认删除黑名单
    const confirmDelete = async (item) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除黑名单项 "${item.value}" 吗？`,
          '警告',
          { type: 'warning' }
        )
        deleteBlacklist(item.id)
      } catch (error) {
        if (error !== 'cancel') {
          console.error(error)
        }
      }
    }

    // 删除黑名单
    const deleteBlacklist = async (id) => {
      try {
        const response = await deleteBlacklistApi(id)

        if (response.success) {
          ElMessage.success('删除成功')
          loadBlacklist()
        } else {
          ElMessage.error(response.message || '删除失败')
        }
      } catch (error) {
        console.error('删除黑名单失败:', error)
        ElMessage.error('删除失败')
      }
    }

    // 删除已处理事件
    const deleteProcessedMarket = async (marketId) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除已处理事件 "${marketId}" 吗？`,
          '警告',
          { type: 'warning' }
        )
        
        const response = await deleteProcessedMarketApi(marketId)

        if (response.success) {
          ElMessage.success('删除成功')
          loadProcessedMarkets(currentPage.value)
        } else {
          ElMessage.error(response.message || '删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
           console.error('删除已处理事件失败:', error)
           ElMessage.error('删除失败')
        }
      }
    }

    // 确认清空已处理事件
    const confirmClearProcessed = async () => {
      try {
        await ElMessageBox.confirm(
          '确定要清空所有已处理事件吗？此操作不可恢复！',
          '危险',
          { 
             type: 'error',
             confirmButtonText: '清空',
             cancelButtonText: '取消'
          }
        )
        clearProcessedMarkets()
      } catch (error) {
         if (error !== 'cancel') {
            console.error(error)
         }
      }
    }

    // 清空已处理事件
    const clearProcessedMarkets = async () => {
      try {
        const response = await clearProcessedMarketsApi()

        if (response.success) {
          ElMessage.success(`已清空 ${response.data.cleared_count} 条记录`)
          loadProcessedMarkets(1)
          currentPage.value = 1
        } else {
          ElMessage.error(response.message || '清空失败')
        }
      } catch (error) {
        console.error('清空已处理事件失败:', error)
        ElMessage.error('清空失败')
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
    
    const getTypeTag = (type) => {
       const map = {
          'tag': '',
          'title_keyword': 'warning',
          'description_keyword': 'success'
       }
       return map[type] || 'info'
    }

    // 初始化
    onMounted(() => {
      loadBlacklist()
      loadProcessedMarkets(1)
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
      currentPage,
      showAddDialog,
      newBlacklist,
      refreshData,
      addBlacklist,
      toggleBlacklist,
      confirmDelete,
      deleteProcessedMarket,
      confirmClearProcessed,
      loadProcessedMarkets,
      handlePageChange,
      formatDate,
      getTypeLabel,
      getTypeTag,
      Plus, Delete, VideoPlay, VideoPause
    }
  }
}
</script>

<style scoped>
.filter-management {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.stats-container {
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-card {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.filter-form {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.monospace-font {
   font-family: monospace;
   color: #606266;
}
</style>

