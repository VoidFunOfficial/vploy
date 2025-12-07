<template>
  <div class="system-settings">
    <!-- 标题栏 -->
    <div class="header">
      <h2>系统设置</h2>
      <div class="header-actions">
        <button class="btn-primary" @click="openAddDialog">➕ 新增设置</button>
        <button class="btn-refresh" @click="loadSettings">🔄 刷新</button>
      </div>
    </div>

    <!-- 命名空间标签页 -->
    <div class="tabs-container">
      <div class="tabs">
        <button
          v-for="ns in namespaces"
          :key="ns"
          :class="['tab', { active: activeNamespace === ns }]"
          @click="activeNamespace = ns"
        >
          {{ getNamespaceLabel(ns) }}
        </button>
      </div>
    </div>

    <!-- 设置列表 -->
    <div class="main-content">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="filteredSettings.length === 0" class="empty">
        {{ activeNamespace === 'all' ? '暂无设置项' : `暂无 ${activeNamespace} 配置项` }}
      </div>
      <div v-else class="settings-table">
        <table>
          <thead>
            <tr>
              <th>设置键</th>
              <th>设置值</th>
              <th>类型</th>
              <th>描述</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="setting in filteredSettings" :key="setting.key">
              <td class="key-cell">
                <span class="namespace-prefix">{{ getNamespaceFromKey(setting.key) }}.</span>{{ getKeyWithoutNamespace(setting.key) }}
              </td>
              <td class="value-cell">{{ formatValue(setting.value, setting.value_type) }}</td>
              <td>
                <span :class="['type-badge', setting.value_type]">
                  {{ setting.value_type }}
                </span>
              </td>
              <td class="desc-cell">{{ setting.description || '-' }}</td>
              <td>{{ formatDate(setting.updated_at) }}</td>
              <td class="actions-cell">
                <button class="btn-edit" @click="openEditDialog(setting)" title="编辑">✏️</button>
                <button class="btn-delete" @click="confirmDelete(setting)" title="删除">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <Modal
      v-model:visible="showDialog"
      :title="isEditing ? '编辑设置' : '新增设置'"
      :confirm-text="isEditing ? '保存' : '新增'"
      @confirm="handleSubmit"
    >
          <div class="form-group">
            <label>设置键 *</label>
            <input 
              v-model="formData.key" 
              type="text" 
              placeholder="例如: app.version"
              :disabled="isEditing"
            />
          </div>
          <div class="form-group">
            <label>值类型 *</label>
            <select v-model="formData.value_type" @change="handleTypeChange">
              <option value="string">字符串 (string)</option>
              <option value="int">整数 (int)</option>
              <option value="float">浮点数 (float)</option>
              <option value="bool">布尔值 (bool)</option>
              <option value="json">JSON对象 (json)</option>
            </select>
          </div>
          <div class="form-group">
            <label>设置值 *</label>
            <!-- 布尔值使用开关 -->
            <div v-if="formData.value_type === 'bool'" class="bool-switch">
              <label class="switch">
                <input type="checkbox" v-model="formData.boolValue" />
                <span class="slider"></span>
              </label>
              <span class="bool-label">{{ formData.boolValue ? '是 (true)' : '否 (false)' }}</span>
            </div>
            <!-- 数字类型使用数字输入框 -->
            <input 
              v-else-if="formData.value_type === 'int' || formData.value_type === 'float'"
              v-model="formData.value" 
              type="number"
              :step="formData.value_type === 'float' ? '0.01' : '1'"
              placeholder="请输入数字"
            />
            <!-- JSON类型使用文本域 -->
            <textarea 
              v-else-if="formData.value_type === 'json'"
              v-model="formData.value"
              rows="6"
              placeholder='例如: {"key": "value"}'
            ></textarea>
            <!-- 字符串使用文本输入框 -->
            <input 
              v-else
              v-model="formData.value" 
              type="text"
              placeholder="请输入设置值"
            />
          </div>
          <div class="form-group">
            <label>描述</label>
            <input 
              v-model="formData.description" 
              type="text"
              placeholder="设置项的描述信息（可选）"
            />
          </div>
    </Modal>

    <!-- 删除确认对话框 -->
    <Modal
      v-model:visible="showDeleteDialog"
      title="确认删除"
      size="small"
      confirm-text="确认删除"
      @confirm="handleDelete"
    >
      <p>确定要删除设置项 <strong>{{ deletingKey }}</strong> 吗？</p>
      <p class="warning-text">此操作不可恢复！</p>
    </Modal>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { getAllSettings, createSetting, updateSetting, deleteSetting } from '@/api/sys_settings'
import { toast, Modal } from '@/components/Notification'

export default {
  name: 'SystemSettings',
  components: {
    Modal
  },
  setup() {
    const loading = ref(false)
    const settings = ref([])
    const showDialog = ref(false)
    const showDeleteDialog = ref(false)
    const isEditing = ref(false)
    const deletingKey = ref('')
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

    // 获取命名空间的配置项数量
    const getNamespaceCount = (ns) => {
      if (ns === 'all') {
        return settings.value.length
      }
      return settings.value.filter(s => getNamespaceFromKey(s.key) === ns).length
    }

    // 过滤当前命名空间的配置项
    const filteredSettings = computed(() => {
      if (activeNamespace.value === 'all') {
        return settings.value
      }
      return settings.value.filter(s => getNamespaceFromKey(s.key) === activeNamespace.value)
    })

    // 统计各类型数量
    const getTypeCount = (type) => {
      return settings.value.filter(s => s.value_type === type).length
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
          toast.error('加载失败: ' + response.message)
        }
      } catch (error) {
        console.error('加载设置失败:', error)
        toast.error('加载设置失败')
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
      formData.value = {
        key: setting.key,
        value: setting.value_type === 'json' ? JSON.stringify(setting.value, null, 2) : String(setting.value),
        value_type: setting.value_type,
        description: setting.description || '',
        boolValue: setting.value_type === 'bool' ? setting.value : false
      }
      showDialog.value = true
    }

    // 关闭对话框
    const closeDialog = () => {
      showDialog.value = false
    }

    // 类型改变处理
    const handleTypeChange = () => {
      formData.value.value = ''
      formData.value.boolValue = false
    }

    // 提交表单
    const handleSubmit = async () => {
      if (!formData.value.key.trim()) {
        toast.warning('请输入设置键')
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
          toast.error('JSON格式错误，请检查')
          return
        }
      }
      // 处理数字
      else if (formData.value.value_type === 'int') {
        finalValue = parseInt(formData.value.value)
        if (isNaN(finalValue)) {
          toast.warning('请输入有效的整数')
          return
        }
      }
      else if (formData.value.value_type === 'float') {
        finalValue = parseFloat(formData.value.value)
        if (isNaN(finalValue)) {
          toast.warning('请输入有效的浮点数')
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
          toast.success(isEditing.value ? '更新成功' : '新增成功')
          closeDialog()
          loadSettings()
        } else {
          toast.error(response.message || '操作失败')
        }
      } catch (error) {
        console.error('提交失败:', error)
        toast.error('操作失败')
      }
    }

    // 确认删除
    const confirmDelete = (setting) => {
      deletingKey.value = setting.key
      showDeleteDialog.value = true
    }

    // 执行删除
    const handleDelete = async () => {
      try {
        const response = await deleteSetting(deletingKey.value)
        if (response.success) {
          toast.success('删除成功')
          showDeleteDialog.value = false
          loadSettings()
        } else {
          toast.error(response.message || '删除失败')
        }
      } catch (error) {
        console.error('删除失败:', error)
        toast.error('删除失败')
      }
    }

    // 初始加载
    loadSettings()

    return {
      loading,
      settings,
      showDialog,
      showDeleteDialog,
      isEditing,
      deletingKey,
      formData,
      activeNamespace,
      namespaces,
      filteredSettings,
      getNamespaceFromKey,
      getKeyWithoutNamespace,
      getNamespaceLabel,
      getNamespaceCount,
      getTypeCount,
      formatValue,
      formatDate,
      loadSettings,
      openAddDialog,
      openEditDialog,
      closeDialog,
      handleTypeChange,
      handleSubmit,
      confirmDelete,
      handleDelete
    }
  }
}
</script>

<style scoped>
.system-settings {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100%;
}

/* 标题栏 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px 20px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.header h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 标签页容器 */
.tabs-container {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  padding: 15px;
}

.tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tab {
  padding: 10px 20px;
  border: 1px solid #ddd;
  background-color: #fff;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.tab:hover {
  background-color: #f5f5f5;
  border-color: #999;
  color: #333;
}

.tab.active {
  background-color: #2196f3;
  color: white;
  border-color: #2196f3;
}

/* 主体内容 */
.main-content {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  padding: 20px;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 14px;
}

/* 表格样式 */
.settings-table {
  overflow-x: auto;
}

.settings-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.settings-table th {
  background-color: #f8f8f8;
  padding: 12px 8px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e0e0e0;
  white-space: nowrap;
}

.settings-table td {
  padding: 12px 8px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}

.settings-table tr:hover {
  background-color: #f9f9f9;
}

.key-cell {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #333;
  max-width: 200px;
  word-break: break-all;
}

.namespace-prefix {
  color: #667eea;
  font-weight: 700;
}

.value-cell {
  font-family: 'Courier New', monospace;
  max-width: 300px;
  word-break: break-all;
  color: #555;
}

.desc-cell {
  color: #666;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.type-badge.string {
  background-color: #e3f2fd;
  color: #1976d2;
}

.type-badge.int, .type-badge.float {
  background-color: #fff3e0;
  color: #f57c00;
}

.type-badge.bool {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

.type-badge.json {
  background-color: #e8f5e9;
  color: #388e3c;
}

.actions-cell {
  white-space: nowrap;
}

/* 按钮样式 */
.btn-primary, .btn-refresh, .btn-edit, .btn-delete, .btn-cancel, .btn-confirm, .btn-danger, .btn-close {
  padding: 8px 16px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.btn-primary {
  background-color: #20a53a;
  color: #fff;
}

.btn-primary:hover {
  background-color: #1a8c31;
}

.btn-refresh {
  background-color: #2196f3;
  color: #fff;
}

.btn-refresh:hover {
  background-color: #1976d2;
}

.btn-edit {
  background-color: transparent;
  padding: 4px 8px;
  font-size: 16px;
}

.btn-edit:hover {
  background-color: #e3f2fd;
}

.btn-delete {
  background-color: transparent;
  padding: 4px 8px;
  font-size: 16px;
}

.btn-delete:hover {
  background-color: #ffebee;
}

.btn-cancel {
  background-color: #e0e0e0;
  color: #333;
}

.btn-cancel:hover {
  background-color: #d0d0d0;
}

.btn-confirm {
  background-color: #20a53a;
  color: #fff;
}

.btn-confirm:hover {
  background-color: #1a8c31;
}

.btn-danger {
  background-color: #f44336;
  color: #fff;
}

.btn-danger:hover {
  background-color: #d32f2f;
}

.btn-close {
  background-color: transparent;
  color: #999;
  padding: 4px 8px;
  font-size: 20px;
}

.btn-close:hover {
  color: #333;
}

/* 对话框样式 */

/* 表单样式 */
.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 3px;
  font-size: 13px;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #20a53a;
}

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.form-group textarea {
  font-family: 'Courier New', monospace;
  resize: vertical;
}

/* 布尔值开关 */
.bool-switch {
  display: flex;
  align-items: center;
  gap: 10px;
}

.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #20a53a;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

.bool-label {
  font-size: 13px;
  color: #666;
}

.warning-text {
  color: #f44336;
  font-size: 13px;
  margin-top: 10px;
}

/* 响应式 */
@media (max-width: 768px) {
  .system-settings {
    padding: 10px;
  }

  .header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .tabs {
    gap: 5px;
  }

  .tab {
    padding: 8px 15px;
    font-size: 13px;
  }

  .settings-table {
    font-size: 12px;
  }

  .settings-table th,
  .settings-table td {
    padding: 8px 4px;
  }

  .dialog {
    width: 95%;
  }
}
</style>

