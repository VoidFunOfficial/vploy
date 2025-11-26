<template>
  <div class="database-management">
    <!-- 标题栏 -->
    <div class="header">
      <h2>数据库管理</h2>
      <div class="header-actions">
        <button class="btn-refresh" @click="refreshData">🔄 刷新</button>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="main-content">
      <!-- 左侧表列表 -->
      <div class="table-list">
        <h3>数据表</h3>
        <div class="table-items">
          <div
            v-for="table in tables"
            :key="table.name"
            :class="['table-item', { active: selectedTable === table.name }]"
            @click="selectTable(table.name)"
          >
            <span class="table-icon">📋</span>
            <span class="table-name">{{ table.name }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧数据区域 -->
      <div class="data-area">
        <div v-if="!selectedTable" class="empty-state">
          <p>请从左侧选择一个数据表</p>
        </div>

        <div v-else class="table-data">
          <!-- 表信息 -->
          <div class="table-info">
            <h3>{{ selectedTable }}</h3>
            <button class="btn-primary" @click="showCreateDialog = true">➕ 新增记录</button>
          </div>

          <!-- 数据表格 -->
          <div v-if="loading" class="loading">加载中...</div>
          
          <div v-else-if="tableData.rows.length === 0" class="empty">
            暂无数据
          </div>

          <div v-else class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="column in columns" :key="column.name">
                    {{ column.name }}
                    <span v-if="column.pk" class="pk-badge">PK</span>
                  </th>
                  <th class="actions-column">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in tableData.rows" :key="row.id">
                  <td v-for="column in columns" :key="column.name">
                    {{ formatValue(row[column.name]) }}
                  </td>
                  <td class="actions-column">
                    <button class="btn-edit" @click="editRow(row)">✏️</button>
                    <button class="btn-delete" @click="confirmDelete(row)">🗑️</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 分页 -->
          <div v-if="tableData.total > 0" class="pagination">
            <button 
              :disabled="currentPage === 1" 
              @click="changePage(currentPage - 1)"
            >
              上一页
            </button>
            <span class="page-info">
              第 {{ currentPage }} / {{ totalPages }} 页 (共 {{ tableData.total }} 条)
            </span>
            <button 
              :disabled="currentPage === totalPages" 
              @click="changePage(currentPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <div v-if="showCreateDialog || showEditDialog" class="modal-overlay" @click="closeDialogs">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ showCreateDialog ? '新增记录' : '编辑记录' }}</h3>
          <button class="btn-close" @click="closeDialogs">✕</button>
        </div>
        <div class="modal-body">
          <div v-for="column in editableColumns" :key="column.name" class="form-group">
            <label>
              {{ column.name }}
              <span v-if="column.notnull" class="required">*</span>
              <span class="type-hint">({{ column.type }})</span>
            </label>
            <input
              v-model="formData[column.name]"
              :type="getInputType(column.type)"
              :required="column.notnull"
              :placeholder="column.dflt_value ? `默认: ${column.dflt_value}` : ''"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeDialogs">取消</button>
          <button class="btn-primary" @click="saveRow">保存</button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteDialog" class="modal-overlay" @click="showDeleteDialog = false">
      <div class="modal-content small" @click.stop>
        <div class="modal-header">
          <h3>确认删除</h3>
          <button class="btn-close" @click="showDeleteDialog = false">✕</button>
        </div>
        <div class="modal-body">
          <p>确定要删除这条记录吗？此操作不可恢复。</p>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showDeleteDialog = false">取消</button>
          <button class="btn-danger" @click="deleteRow">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { getTables, getTableSchema, getTableData, createRow, updateRow, deleteRow as deleteRowAPI } from '@/api/database'

export default {
  name: 'DatabaseManagement',
  setup() {
    const tables = ref([])
    const selectedTable = ref('')
    const columns = ref([])
    const tableData = ref({ rows: [], total: 0, page: 1, page_size: 50 })
    const loading = ref(false)
    const currentPage = ref(1)
    const pageSize = ref(50)

    const showCreateDialog = ref(false)
    const showEditDialog = ref(false)
    const showDeleteDialog = ref(false)
    const formData = ref({})
    const editingRow = ref(null)
    const deletingRow = ref(null)

    // 计算总页数
    const totalPages = computed(() => {
      return Math.ceil(tableData.value.total / pageSize.value)
    })

    // 可编辑的列（排除主键和自动生成的列）
    const editableColumns = computed(() => {
      return columns.value.filter(col => {
        // 编辑时允许修改所有非主键列
        if (showEditDialog.value) {
          return !col.pk && col.name !== 'created_at' && col.name !== 'updated_at'
        }
        // 创建时排除主键和时间戳列
        return !col.pk && col.name !== 'created_at' && col.name !== 'updated_at'
      })
    })

    // 加载表列表
    const loadTables = async () => {
      try {
        const response = await getTables()
        if (response.success) {
          tables.value = response.data.tables
        }
      } catch (error) {
        console.error('加载表列表失败:', error)
      }
    }

    // 选择表
    const selectTable = async (tableName) => {
      selectedTable.value = tableName
      currentPage.value = 1
      await loadTableSchema()
      await loadTableData()
    }

    // 加载表结构
    const loadTableSchema = async () => {
      try {
        const response = await getTableSchema(selectedTable.value)
        if (response.success) {
          columns.value = response.data.columns
        }
      } catch (error) {
        console.error('加载表结构失败:', error)
      }
    }

    // 加载表数据
    const loadTableData = async () => {
      loading.value = true
      try {
        const response = await getTableData(selectedTable.value, {
          page: currentPage.value,
          page_size: pageSize.value
        })
        if (response.success) {
          tableData.value = response.data
        }
      } catch (error) {
        console.error('加载表数据失败:', error)
      } finally {
        loading.value = false
      }
    }

    // 刷新数据
    const refreshData = async () => {
      await loadTables()
      if (selectedTable.value) {
        await loadTableData()
      }
    }

    // 切换页码
    const changePage = (page) => {
      currentPage.value = page
      loadTableData()
    }

    // 格式化值显示
    const formatValue = (value) => {
      if (value === null || value === undefined) {
        return '-'
      }
      if (typeof value === 'string' && value.length > 100) {
        return value.substring(0, 100) + '...'
      }
      return value
    }

    // 获取输入框类型
    const getInputType = (columnType) => {
      const type = columnType.toUpperCase()
      if (type.includes('INT')) return 'number'
      if (type.includes('REAL') || type.includes('FLOAT')) return 'number'
      if (type.includes('BOOL')) return 'checkbox'
      return 'text'
    }

    // 编辑行
    const editRow = (row) => {
      editingRow.value = row
      formData.value = { ...row }
      showEditDialog.value = true
    }

    // 确认删除
    const confirmDelete = (row) => {
      deletingRow.value = row
      showDeleteDialog.value = true
    }

    // 删除行
    const deleteRow = async () => {
      try {
        const response = await deleteRowAPI(selectedTable.value, deletingRow.value.id)
        if (response.success) {
          showDeleteDialog.value = false
          await loadTableData()
        }
      } catch (error) {
        console.error('删除失败:', error)
        alert('删除失败: ' + error.message)
      }
    }

    // 保存行
    const saveRow = async () => {
      try {
        if (showCreateDialog.value) {
          const response = await createRow(selectedTable.value, formData.value)
          if (response.success) {
            closeDialogs()
            await loadTableData()
          }
        } else if (showEditDialog.value) {
          const response = await updateRow(selectedTable.value, editingRow.value.id, formData.value)
          if (response.success) {
            closeDialogs()
            await loadTableData()
          }
        }
      } catch (error) {
        console.error('保存失败:', error)
        alert('保存失败: ' + error.message)
      }
    }

    // 关闭对话框
    const closeDialogs = () => {
      showCreateDialog.value = false
      showEditDialog.value = false
      formData.value = {}
      editingRow.value = null
    }

    onMounted(() => {
      loadTables()
    })

    return {
      tables,
      selectedTable,
      columns,
      tableData,
      loading,
      currentPage,
      totalPages,
      showCreateDialog,
      showEditDialog,
      showDeleteDialog,
      formData,
      editableColumns,
      selectTable,
      refreshData,
      changePage,
      formatValue,
      getInputType,
      editRow,
      confirmDelete,
      deleteRow,
      saveRow,
      closeDialogs
    }
  }
}
</script>

<style scoped>
.database-management {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e0e0e0;
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

.btn-refresh {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-refresh:hover {
  background-color: #45a049;
}

.main-content {
  display: flex;
  gap: 20px;
  flex: 1;
  overflow: hidden;
}

.table-list {
  width: 250px;
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
}

.table-list h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.table-items {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.table-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.table-item:hover {
  background-color: #f5f5f5;
}

.table-item.active {
  background-color: #e3f2fd;
  color: #1976d2;
}

.table-icon {
  font-size: 16px;
}

.table-name {
  font-size: 14px;
  word-break: break-all;
}

.data-area {
  flex: 1;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-size: 16px;
}

.table-data {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.table-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e0e0e0;
}

.table-info h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.btn-primary {
  padding: 8px 16px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary:hover {
  background-color: #1976D2;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #666;
}

.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #999;
}

.table-container {
  flex: 1;
  overflow: auto;
  margin-bottom: 15px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table th {
  background-color: #f5f5f5;
  padding: 12px 8px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table td {
  padding: 10px 8px;
  border-bottom: 1px solid #e0e0e0;
  color: #666;
}

.data-table tbody tr:hover {
  background-color: #f9f9f9;
}

.pk-badge {
  display: inline-block;
  margin-left: 5px;
  padding: 2px 6px;
  background-color: #ff9800;
  color: white;
  font-size: 10px;
  border-radius: 3px;
}

.actions-column {
  width: 100px;
  text-align: center;
}

.btn-edit,
.btn-delete {
  padding: 4px 8px;
  margin: 0 2px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 16px;
}

.btn-edit:hover {
  opacity: 0.7;
}

.btn-delete:hover {
  opacity: 0.7;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  padding: 15px 0;
  border-top: 1px solid #e0e0e0;
}

.pagination button {
  padding: 6px 12px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.pagination button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.pagination button:not(:disabled):hover {
  background-color: #1976D2;
}

.page-info {
  color: #666;
  font-size: 14px;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-content.small {
  max-width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.required {
  color: #f44336;
  margin-left: 2px;
}

.type-hint {
  color: #999;
  font-size: 12px;
  font-weight: normal;
  margin-left: 5px;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #2196F3;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #e0e0e0;
}

.btn-secondary {
  padding: 8px 16px;
  background-color: #9e9e9e;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary:hover {
  background-color: #757575;
}

.btn-danger {
  padding: 8px 16px;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-danger:hover {
  background-color: #d32f2f;
}
</style>

