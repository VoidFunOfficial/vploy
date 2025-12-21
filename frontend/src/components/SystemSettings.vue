<template>
  <div class="page-container">
    <!-- 标题栏 -->
    <div class="page-header">
      <h2 class="page-title">系统设置</h2>
      <div class="header-actions">
        <el-button type="primary" @click="openAddDialog" :icon="Plus">新增设置</el-button>
        <el-button type="success" @click="loadSettings" :icon="Refresh" :loading="loading">刷新</el-button>
      </div>
    </div>

    <!-- 主要内容 -->
    <el-card shadow="never">
      <!-- 标签页 -->
      <el-tabs v-model="activeNamespace">
        <el-tab-pane
          v-for="ns in namespaces"
          :key="ns"
          :label="getNamespaceLabel(ns)"
          :name="ns"
        />
      </el-tabs>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="filteredSettings"
        style="width: 100%"
        border
        stripe
      >
        <el-table-column label="设置键" prop="key" min-width="200" show-overflow-tooltip>
          <template #default="scope">
            <span class="namespace-text">{{ getNamespaceFromKey(scope.row.key) }}.</span>
            <span class="key-text">{{ getKeyWithoutNamespace(scope.row.key) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="设置值" prop="value" min-width="200" show-overflow-tooltip>
          <template #default="scope">
            <div class="value-text">{{ formatValue(scope.row.value, scope.row.value_type) }}</div>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="100" align="center">
          <template #default="scope">
            <el-tag size="small" :type="getTypeTagType(scope.row.value_type)">
              {{ scope.row.value_type }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="描述" prop="description" min-width="150" show-overflow-tooltip>
          <template #default="scope">{{ scope.row.description || '-' }}</template>
        </el-table-column>

        <el-table-column label="更新时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="scope">
            <el-button link type="primary" size="small" @click="openEditDialog(scope.row)" :icon="Edit">编辑</el-button>
            <el-popconfirm title="确定要删除此设置项吗？" @confirm="handleDelete(scope.row)">
              <template #reference>
                <el-button link type="danger" size="small" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑/新增对话框 -->
    <el-dialog
      v-model="showDialog"
      :title="isEditing ? '编辑设置' : '新增设置'"
      width="500px"
    >
      <el-form :model="formData" label-width="80px">
        <el-form-item label="设置键" required>
          <el-input 
            v-model="formData.key" 
            placeholder="例如: app.version" 
            :disabled="isEditing"
          />
        </el-form-item>
        
        <el-form-item label="值类型" required>
          <el-select v-model="formData.value_type" @change="handleTypeChange" style="width: 100%">
            <el-option value="string" label="字符串 (string)" />
            <el-option value="int" label="整数 (int)" />
            <el-option value="float" label="浮点数 (float)" />
            <el-option value="bool" label="布尔值 (bool)" />
            <el-option value="json" label="JSON对象 (json)" />
          </el-select>
        </el-form-item>

        <el-form-item label="设置值" required>
          <el-switch
            v-if="formData.value_type === 'bool'"
            v-model="formData.boolValue"
            active-text="是 (true)"
            inactive-text="否 (false)"
          />
          
          <el-input-number
            v-else-if="formData.value_type === 'int'"
            v-model="formData.value"
            :step="1"
            style="width: 100%"
            controls-position="right"
          />

          <el-input-number
            v-else-if="formData.value_type === 'float'"
            v-model="formData.value"
            :step="0.01"
            style="width: 100%"
            controls-position="right"
          />

          <el-input
            v-else-if="formData.value_type === 'json'"
            v-model="formData.value"
            type="textarea"
            :rows="6"
            placeholder='例如: {"key": "value"}'
          />

          <el-input
            v-else
            v-model="formData.value"
            placeholder="请输入设置值"
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="formData.description" placeholder="可选描述" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDialog = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { getAllSettings, createSetting, updateSetting, deleteSetting } from '@/api/sys_settings'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Edit, Delete } from '@element-plus/icons-vue'

export default {
  name: 'SystemSettings',
  setup() {
    const loading = ref(false)
    const settings = ref([])
    const showDialog = ref(false)
    const isEditing = ref(false)
    const activeNamespace = ref('all')

    const formData = ref({
      key: '',
      value: '',
      value_type: 'string',
      description: '',
      boolValue: false
    })

    // 提取命名空间列表
    const namespaces = computed(() => {
      const nsSet = new Set(['all'])
      settings.value.forEach(setting => {
        const ns = getNamespaceFromKey(setting.key)
        if (ns) {
          nsSet.add(ns)
        }
      })
      return Array.from(nsSet).sort()
    })

    // 从配置键中提取命名空间
    const getNamespaceFromKey = (key) => {
      const dotIndex = key.indexOf('.')
      if (dotIndex > 0) {
        return key.substring(0, dotIndex)
      }
      return 'other'
    }

    // 获取不带命名空间的键名
    const getKeyWithoutNamespace = (key) => {
      const dotIndex = key.indexOf('.')
      if (dotIndex > 0) {
        return key.substring(dotIndex + 1)
      }
      return key
    }

    // 获取命名空间的显示标签
    const getNamespaceLabel = (ns) => {
      const labels = {
        'all': '全部',
        'logging': '日志配置',
        'mail': '邮件配置',
        'api': 'API配置',
        'database': '数据库配置',
        'other': '其他'
      }
      return labels[ns] || ns
    }

    // 过滤当前命名空间的配置项
    const filteredSettings = computed(() => {
      if (activeNamespace.value === 'all') {
        return settings.value
      }
      return settings.value.filter(s => getNamespaceFromKey(s.key) === activeNamespace.value)
    })

    // 获取类型对应的标签类型
    const getTypeTagType = (type) => {
      const map = {
        string: '',
        int: 'success',
        float: 'warning',
        bool: 'danger',
        json: 'info'
      }
      return map[type] || ''
    }

    // 格式化值显示
    const formatValue = (value, type) => {
      if (type === 'json') {
        return JSON.stringify(value)
      }
      if (type === 'bool') {
        return value ? '是 (true)' : '否 (false)'
      }
      return String(value)
    }

    // 格式化日期
    const formatDate = (dateStr) => {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN')
    }

    // 加载设置列表
    const loadSettings = async () => {
      loading.value = true
      try {
        const response = await getAllSettings()
        if (response.success) {
          settings.value = response.data.settings || []
        } else {
          ElMessage.error('加载失败: ' + response.message)
        }
      } catch (error) {
        console.error('加载设置失败:', error)
        ElMessage.error('加载设置失败')
      } finally {
        loading.value = false
      }
    }

    // 打开新增对话框
    const openAddDialog = () => {
      isEditing.value = false
      formData.value = {
        key: '',
        value: '',
        value_type: 'string',
        description: '',
        boolValue: false
      }
      showDialog.value = true
    }

    // 打开编辑对话框
    const openEditDialog = (setting) => {
      isEditing.value = true
      
      let val = setting.value
      let boolVal = false
      
      if (setting.value_type === 'json') {
        val = JSON.stringify(setting.value, null, 2)
      } else if (setting.value_type === 'bool') {
        boolVal = setting.value
      } else if (setting.value_type === 'int' || setting.value_type === 'float') {
        val = Number(setting.value)
      } else {
        val = String(setting.value)
      }

      formData.value = {
        key: setting.key,
        value: val,
        value_type: setting.value_type,
        description: setting.description || '',
        boolValue: boolVal
      }
      showDialog.value = true
    }

    // 类型改变处理
    const handleTypeChange = () => {
      formData.value.value = ''
      formData.value.boolValue = false
    }

    // 提交表单
    const handleSubmit = async () => {
      if (!formData.value.key.trim()) {
        ElMessage.warning('请输入设置键')
        return
      }

      let finalValue = formData.value.value

      // 处理布尔值
      if (formData.value.value_type === 'bool') {
        finalValue = formData.value.boolValue
      }
      // 处理JSON
      else if (formData.value.value_type === 'json') {
        try {
          finalValue = JSON.parse(formData.value.value)
        } catch (e) {
          ElMessage.error('JSON格式错误，请检查')
          return
        }
      }
      // 处理数字
      else if (formData.value.value_type === 'int') {
        finalValue = parseInt(formData.value.value)
        if (isNaN(finalValue)) {
          ElMessage.warning('请输入有效的整数')
          return
        }
      }
      else if (formData.value.value_type === 'float') {
        finalValue = parseFloat(formData.value.value)
        if (isNaN(finalValue)) {
          ElMessage.warning('请输入有效的浮点数')
          return
        }
      }

      try {
        const data = {
          value: finalValue,
          value_type: formData.value.value_type,
          description: formData.value.description
        }

        let response
        if (isEditing.value) {
          response = await updateSetting(formData.value.key, data)
        } else {
          data.key = formData.value.key
          response = await createSetting(data)
        }

        if (response.success) {
          ElMessage.success(isEditing.value ? '更新成功' : '新增成功')
          showDialog.value = false
          loadSettings()
        } else {
          ElMessage.error(response.message || '操作失败')
        }
      } catch (error) {
        console.error('提交失败:', error)
        ElMessage.error('操作失败')
      }
    }

    // 执行删除
    const handleDelete = async (setting) => {
      try {
        const response = await deleteSetting(setting.key)
        if (response.success) {
          ElMessage.success('删除成功')
          loadSettings()
        } else {
          ElMessage.error(response.message || '删除失败')
        }
      } catch (error) {
        console.error('删除失败:', error)
        ElMessage.error('删除失败')
      }
    }

    // 初始加载
    loadSettings()

    return {
      loading,
      settings,
      showDialog,
      isEditing,
      formData,
      activeNamespace,
      namespaces,
      filteredSettings,
      getNamespaceFromKey,
      getKeyWithoutNamespace,
      getNamespaceLabel,
      getTypeTagType,
      formatValue,
      formatDate,
      loadSettings,
      openAddDialog,
      openEditDialog,
      handleTypeChange,
      handleSubmit,
      handleDelete,
      Plus,
      Refresh,
      Edit,
      Delete
    }
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: bold;
  color: var(--el-text-color-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.namespace-text {
  color: var(--el-text-color-secondary);
  margin-right: 4px;
}

.key-text {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.value-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
