<template>
  <div class="database-management h-full">
    <el-container class="h-full">
      <el-aside width="240px" class="bg-white border-r border-gray-200 flex flex-col">
        <div class="p-4 border-b border-gray-100 flex justify-between items-center">
          <h2 class="text-lg font-bold text-gray-800 m-0">数据库管理</h2>
          <el-button circle size="small" @click="loadTables">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
        <el-scrollbar>
          <el-menu
            :default-active="selectedTable"
            class="border-none"
            @select="selectTable"
          >
            <el-menu-item v-for="table in tables" :key="table.name" :index="table.name">
              <el-icon><DataBoard /></el-icon>
              <span class="truncate" :title="table.name">{{ table.name }}</span>
            </el-menu-item>
          </el-menu>
        </el-scrollbar>
      </el-aside>
      
      <el-main class="bg-gray-50 p-6">
        <el-card shadow="hover" class="h-full flex flex-col" :body-style="{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }">
          <template #header>
            <div class="flex justify-between items-center">
              <div class="flex items-center gap-2">
                <el-icon size="20" class="text-blue-500" v-if="selectedTable"><Grid /></el-icon>
                <h3 class="m-0 text-lg font-medium text-gray-800">{{ selectedTable || '请选择数据表' }}</h3>
              </div>
              <el-button 
                v-if="selectedTable" 
                type="primary" 
                icon="Plus" 
                @click="showCreateDialog = true"
              >
                新增记录
              </el-button>
            </div>
          </template>
          
          <div v-if="!selectedTable" class="flex flex-col items-center justify-center h-full text-gray-400">
            <el-empty description="请从左侧选择一个数据表查看数据" />
          </div>
          
          <template v-else>
            <div class="flex-1 overflow-hidden">
              <el-table
                v-loading="loading"
                :data="tableData.rows"
                border
                stripe
                height="100%"
                style="width: 100%"
              >
                <el-table-column
                  v-for="column in columns"
                  :key="column.name"
                  :prop="column.name"
                  :label="column.name"
                  min-width="150"
                  show-overflow-tooltip
                >
                  <template #header>
                    <div class="flex items-center gap-1">
                      <span>{{ column.name }}</span>
                      <el-tag v-if="column.pk" size="small" type="warning" effect="plain" round>PK</el-tag>
                    </div>
                  </template>
                  <template #default="scope">
                    {{ formatValue(scope.row[column.name]) }}
                  </template>
                </el-table-column>
                
                <el-table-column label="操作" width="120" fixed="right" align="center">
                  <template #default="scope">
                    <el-button-group>
                      <el-button type="primary" link icon="Edit" @click="editRow(scope.row)"></el-button>
                      <el-button type="danger" link icon="Delete" @click="confirmDelete(scope.row)"></el-button>
                    </el-button-group>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div class="mt-4 flex justify-end pt-4 border-t border-gray-100">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[20, 50, 100, 200]"
                layout="total, sizes, prev, pager, next, jumper"
                :total="tableData.total"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
              />
            </div>
          </template>
        </el-card>
      </el-main>
    </el-container>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="showCreateDialog ? '新增记录' : '编辑记录'"
      width="600px"
      destroy-on-close
      :close-on-click-modal="false"
      @closed="closeDialogs"
    >
      <el-form 
        ref="formRef"
        :model="formData" 
        label-width="120px" 
        label-position="top"
        class="max-h-[60vh] overflow-y-auto px-2"
      >
        <el-form-item
          v-for="column in editableColumns"
          :key="column.name"
          :label="column.name"
          :required="column.notnull"
        >
          <template #label>
            <div class="flex items-center gap-2">
              <span>{{ column.name }}</span>
              <el-tag size="small" type="info" effect="light">{{ column.type }}</el-tag>
            </div>
          </template>
          
          <el-input-number
            v-if="getInputType(column.type) === 'number'"
            v-model="formData[column.name]"
            class="w-full"
            :controls="false"
            :placeholder="column.dflt_value ? `默认: ${column.dflt_value}` : ''"
          />
          <el-switch
            v-else-if="getInputType(column.type) === 'checkbox'"
            v-model="formData[column.name]"
          />
          <el-input
            v-else
            v-model="formData[column.name]"
            :placeholder="column.dflt_value ? `默认: ${column.dflt_value}` : ''"
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeDialogs">取消</el-button>
          <el-button type="primary" @click="saveRow">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { getTables, getTableSchema, getTableData, createRow, updateRow, deleteRow as deleteRowAPI } from '@/api/database'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, DataBoard, Plus, Edit, Delete, Grid } from '@element-plus/icons-vue'

export default {
  name: 'DatabaseManagement',
  components: {
    Refresh, DataBoard, Plus, Edit, Delete, Grid
  },
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
    const formData = ref({})
    const editingRow = ref(null)

    // Dialog visibility computed
    const dialogVisible = computed({
      get: () => showCreateDialog.value || showEditDialog.value,
      set: (val) => {
        if (!val) closeDialogs()
      }
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
        ElMessage.error('加载表列表失败')
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
        ElMessage.error('加载表数据失败')
      } finally {
        loading.value = false
      }
    }

    // Handle pagination
    const handleSizeChange = (val) => {
      pageSize.value = val
      currentPage.value = 1 // Reset to first page when size changes
      loadTableData()
    }

    const handleCurrentChange = (val) => {
      currentPage.value = val
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
      ElMessageBox.confirm(
        '确定要删除这条记录吗？此操作不可恢复。',
        '确认删除',
        {
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
          type: 'warning',
        }
      ).then(async () => {
        try {
          const response = await deleteRowAPI(selectedTable.value, row.id)
          if (response.success) {
            ElMessage.success('删除成功')
            await loadTableData()
          }
        } catch (error) {
          console.error('删除失败:', error)
          ElMessage.error('删除失败: ' + error.message)
        }
      }).catch(() => {
        // Cancelled
      })
    }

    // 保存行
    const saveRow = async () => {
      try {
        if (showCreateDialog.value) {
          const response = await createRow(selectedTable.value, formData.value)
          if (response.success) {
            ElMessage.success('创建成功')
            closeDialogs()
            await loadTableData()
          }
        } else if (showEditDialog.value) {
          const response = await updateRow(selectedTable.value, editingRow.value.id, formData.value)
          if (response.success) {
            ElMessage.success('更新成功')
            closeDialogs()
            await loadTableData()
          }
        }
      } catch (error) {
        console.error('保存失败:', error)
        ElMessage.error('保存失败: ' + error.message)
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
      pageSize,
      showCreateDialog,
      showEditDialog,
      dialogVisible,
      formData,
      editableColumns,
      selectTable,
      handleSizeChange,
      handleCurrentChange,
      loadTables,
      formatValue,
      getInputType,
      editRow,
      confirmDelete,
      saveRow,
      closeDialogs
    }
  }
}
</script>

<style scoped>
/* Element Plus 样式覆盖或补充 */
.el-menu {
  border-right: none;
}
.el-menu-item {
  height: 40px;
  line-height: 40px;
  margin-bottom: 4px;
  border-radius: 4px;
}
.el-menu-item.is-active {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 500;
}
.el-menu-item:hover {
  background-color: var(--el-color-primary-light-9);
}
</style>
