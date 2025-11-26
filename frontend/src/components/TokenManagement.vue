<template>
  <div class="token-management">
    <div class="header">
      <h2>API Token 管理</h2>
      <div class="header-actions">
        <button class="btn-quick-import" @click="showQuickImportDialog = true">
          快捷导入
        </button>
        <button class="btn-refresh" @click="refreshStatus" :disabled="loading">
          {{ loading ? '刷新中...' : '刷新状态' }}
        </button>
        <button class="btn-check" @click="checkAllTokens" :disabled="loading">
          立即检查
        </button>
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="system-status">
      <div class="status-item">
        <span class="label">后台检查状态:</span>
        <span :class="['value', systemStatus.is_running ? 'running' : 'stopped']">
          {{ systemStatus.is_running ? '运行中' : '已停止' }}
        </span>
      </div>
      <div class="status-item">
        <span class="label">检查间隔:</span>
        <span class="value">{{ systemStatus.check_interval_minutes }} 分钟</span>
        <button class="btn-edit" @click="showIntervalDialog = true">修改</button>
      </div>
    </div>

    <!-- Token 列表 -->
    <div class="token-list">
      <div
        v-for="(token, tokenType) in tokens"
        :key="tokenType"
        :class="['token-card', { expired: token.is_expired }]"
      >
        <div class="token-header">
          <div class="token-title">
            <h3>{{ token.description }}</h3>
            <span class="token-type">{{ tokenType }}</span>
          </div>
          <div class="token-status">
            <span :class="['status-badge', token.is_expired ? 'expired' : 'valid']">
              {{ token.is_expired ? '已过期' : '有效' }}
            </span>
          </div>
        </div>

        <div class="token-info">
          <div class="info-row">
            <span class="info-label">有效期:</span>
            <span class="info-value">{{ token.validity_days }} 天</span>
          </div>
          <div class="info-row">
            <span class="info-label">过期时间:</span>
            <span class="info-value">{{ formatDateTime(token.expires_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">最后检查:</span>
            <span class="info-value">
              {{ token.last_checked_at ? formatDateTime(token.last_checked_at) : '未检查' }}
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">Token 值:</span>
            <span class="info-value token-value">
              {{ token.token_value ? maskToken(token.token_value) : '未设置' }}
            </span>
          </div>
        </div>

        <div class="token-actions">
          <button class="btn-update" @click="openUpdateDialog(tokenType, token)">
            更新 Token
          </button>
          <button
            class="btn-expire"
            @click="expireToken(tokenType)"
            :disabled="token.is_expired"
          >
            标记过期
          </button>
        </div>
      </div>
    </div>

    <!-- 更新 Token 对话框 -->
    <div v-if="showUpdateDialog" class="dialog-overlay" @click="closeUpdateDialog">
      <div class="dialog" @click.stop>
        <div class="dialog-header">
          <h3>更新 Token</h3>
          <button class="btn-close" @click="closeUpdateDialog">×</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>Token 类型</label>
            <input type="text" :value="updateForm.token_type" disabled />
          </div>
          <div class="form-group">
            <label>Token 值</label>
            <textarea
              v-model="updateForm.token_value"
              rows="3"
              placeholder="输入新的 Token 值"
            ></textarea>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="updateForm.custom_expiry" />
              自定义过期时间
            </label>
          </div>
          <div v-if="updateForm.custom_expiry" class="form-group">
            <label>过期时间</label>
            <input type="datetime-local" v-model="updateForm.expires_at" />
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="closeUpdateDialog">取消</button>
          <button class="btn-submit" @click="submitUpdate" :disabled="updating">
            {{ updating ? '更新中...' : '确认更新' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 修改检查间隔对话框 -->
    <div v-if="showIntervalDialog" class="dialog-overlay" @click="closeIntervalDialog">
      <div class="dialog" @click.stop>
        <div class="dialog-header">
          <h3>修改检查间隔</h3>
          <button class="btn-close" @click="closeIntervalDialog">×</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>检查间隔（分钟）</label>
            <input
              type="number"
              v-model.number="intervalForm.minutes"
              min="1"
              placeholder="输入检查间隔"
            />
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="closeIntervalDialog">取消</button>
          <button class="btn-submit" @click="submitInterval" :disabled="updating">
            {{ updating ? '更新中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 快捷导入对话框 -->
    <div v-if="showQuickImportDialog" class="dialog-overlay" @click="closeQuickImportDialog">
      <div class="dialog dialog-large" @click.stop>
        <div class="dialog-header">
          <h3>快捷导入 Token</h3>
          <button class="btn-close" @click="closeQuickImportDialog">×</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>粘贴 HTTP Header 或 Cookie 字符串</label>
            <textarea
              v-model="quickImportForm.headerString"
              rows="8"
              placeholder="支持多种格式，例如：&#10;&#10;Cookie 格式：&#10;__Secure-auth_token=xxx;__Secure-access_token=yyy;&#10;&#10;Header 格式：&#10;Authorization: Bearer eyJhbGc...&#10;Access-Token: abc123...&#10;&#10;或直接粘贴 cURL 命令"
              @input="parseHeaderString"
            ></textarea>
            <div class="hint">
              支持格式：Cookie 字符串、HTTP Header、cURL 命令、或直接粘贴 token 值
            </div>
          </div>

          <!-- 解析结果预览 -->
          <div v-if="quickImportForm.parsedTokens.length > 0" class="parsed-tokens">
            <h4>检测到的 Token:</h4>
            <div
              v-for="(item, index) in quickImportForm.parsedTokens"
              :key="index"
              class="parsed-token-item"
            >
              <div class="parsed-token-header">
                <label>
                  <input
                    type="checkbox"
                    v-model="item.selected"
                  />
                  <strong>{{ item.type }}</strong> - {{ item.description }}
                </label>
              </div>
              <div class="parsed-token-value">
                {{ maskToken(item.value) }}
              </div>
            </div>
          </div>

          <div v-else-if="quickImportForm.headerString.trim()" class="no-tokens-found">
            未检测到有效的 Token，请检查输入格式
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="closeQuickImportDialog">取消</button>
          <button
            class="btn-submit"
            @click="submitQuickImport"
            :disabled="updating || quickImportForm.parsedTokens.filter(t => t.selected).length === 0"
          >
            {{ updating ? '导入中...' : '确认导入' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
    <div v-if="message.show" :class="['message', message.type]">
      {{ message.text }}
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import {
  getAllTokenStatus,
  updateToken,
  checkAllTokens as checkAllTokensApi,
  expireToken as expireTokenApi,
  setCheckInterval
} from '@/api/token'

export default {
  name: 'TokenManagement',
  setup() {
    // 状态管理
    const loading = ref(false)
    const updating = ref(false)
    const tokens = ref({})
    const systemStatus = reactive({
      is_running: false,
      check_interval_minutes: 10
    })

    // 对话框状态
    const showUpdateDialog = ref(false)
    const showIntervalDialog = ref(false)
    const showQuickImportDialog = ref(false)

    // 表单数据
    const updateForm = reactive({
      token_type: '',
      token_value: '',
      custom_expiry: false,
      expires_at: ''
    })

    const intervalForm = reactive({
      minutes: 10
    })

    const quickImportForm = reactive({
      headerString: '',
      parsedTokens: []
    })

    // 消息提示
    const message = reactive({
      show: false,
      type: 'success',
      text: ''
    })

    // 显示消息
    const showMessage = (text, type = 'success') => {
      message.text = text
      message.type = type
      message.show = true
      setTimeout(() => {
        message.show = false
      }, 3000)
    }

    // 格式化日期时间
    const formatDateTime = (dateStr) => {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    // 遮蔽 Token 值
    const maskToken = (token) => {
      if (!token || token.length < 10) return token
      return token.substring(0, 10) + '...' + token.substring(token.length - 10)
    }

    // 刷新状态
    const refreshStatus = async () => {
      loading.value = true
      try {
        const res = await getAllTokenStatus()
        if (res.success) {
          tokens.value = res.data.tokens
          systemStatus.is_running = res.data.is_running
          systemStatus.check_interval_minutes = res.data.check_interval_minutes
        } else {
          showMessage(res.message || '获取状态失败', 'error')
        }
      } catch (error) {
        showMessage('获取状态失败: ' + error.message, 'error')
      } finally {
        loading.value = false
      }
    }

    // 检查所有 Token
    const checkAllTokens = async () => {
      loading.value = true
      try {
        const res = await checkAllTokensApi()
        if (res.success) {
          showMessage('检查完成')
          await refreshStatus()
        } else {
          showMessage(res.message || '检查失败', 'error')
        }
      } catch (error) {
        showMessage('检查失败: ' + error.message, 'error')
      } finally {
        loading.value = false
      }
    }

    // 打开更新对话框
    const openUpdateDialog = (tokenType, token) => {
      updateForm.token_type = tokenType
      updateForm.token_value = token.token_value || ''
      updateForm.custom_expiry = false
      updateForm.expires_at = ''
      showUpdateDialog.value = true
    }

    // 关闭更新对话框
    const closeUpdateDialog = () => {
      showUpdateDialog.value = false
    }

    // 提交更新
    const submitUpdate = async () => {
      if (!updateForm.token_value.trim()) {
        showMessage('请输入 Token 值', 'error')
        return
      }

      updating.value = true
      try {
        const data = {
          token_type: updateForm.token_type,
          token_value: updateForm.token_value
        }

        if (updateForm.custom_expiry && updateForm.expires_at) {
          data.expires_at = new Date(updateForm.expires_at).toISOString()
        }

        const res = await updateToken(data)
        if (res.success) {
          showMessage('更新成功')
          closeUpdateDialog()
          await refreshStatus()
        } else {
          showMessage(res.message || '更新失败', 'error')
        }
      } catch (error) {
        showMessage('更新失败: ' + error.message, 'error')
      } finally {
        updating.value = false
      }
    }

    // 标记过期
    const expireToken = async (tokenType) => {
      if (!confirm('确定要将此 Token 标记为过期吗？这将立即发送告警邮件。')) {
        return
      }

      loading.value = true
      try {
        const res = await expireTokenApi(tokenType)
        if (res.success) {
          showMessage(res.message || '已标记为过期')
          await refreshStatus()
        } else {
          showMessage(res.message || '标记失败', 'error')
        }
      } catch (error) {
        showMessage('标记失败: ' + error.message, 'error')
      } finally {
        loading.value = false
      }
    }

    // 打开间隔对话框
    const openIntervalDialog = () => {
      intervalForm.minutes = systemStatus.check_interval_minutes
      showIntervalDialog.value = true
    }

    // 关闭间隔对话框
    const closeIntervalDialog = () => {
      showIntervalDialog.value = false
    }

    // 提交间隔修改
    const submitInterval = async () => {
      if (!intervalForm.minutes || intervalForm.minutes <= 0) {
        showMessage('请输入有效的检查间隔', 'error')
        return
      }

      updating.value = true
      try {
        const res = await setCheckInterval(intervalForm.minutes)
        if (res.success) {
          showMessage(res.message || '修改成功')
          closeIntervalDialog()
          await refreshStatus()
        } else {
          showMessage(res.message || '修改失败', 'error')
        }
      } catch (error) {
        showMessage('修改失败: ' + error.message, 'error')
      } finally {
        updating.value = false
      }
    }

    // 解析 Header 字符串
    const parseHeaderString = () => {
      const input = quickImportForm.headerString.trim()
      if (!input) {
        quickImportForm.parsedTokens = []
        return
      }

      const parsedTokens = []

      // Token 类型映射配置
      const tokenMapping = {
        'auth_token': {
          patterns: [
            // Cookie 格式: __Secure-auth_token=xxx
            /__Secure-auth[-_]token=([^;]+)/i,
            /auth[-_]token=([^;]+)/i,
            // Header 格式
            /Authorization:\s*Bearer\s+([^\s\n]+)/i,
            /Authorization:\s*([^\s\n]+)/i,
            /-H\s+['"]Authorization:\s*Bearer\s+([^\s'"]+)['"]/i,
            /-H\s+['"]Authorization:\s*([^\s'"]+)['"]/i,
            // Cookie Header 格式
            /Cookie:.*?auth[-_]token=([^;]+)/i,
            /-H\s+['"]Cookie:.*?auth[-_]token=([^;'"]+)['"]/i
          ],
          description: '认证 Token'
        },
        'access_token': {
          patterns: [
            // Cookie 格式: __Secure-access_token=xxx
            /__Secure-access[-_]token=([^;]+)/i,
            /access[-_]token=([^;]+)/i,
            // Header 格式
            /Access-Token:\s*([^\s\n]+)/i,
            /-H\s+['"]Access-Token:\s*([^\s'"]+)['"]/i,
            // Cookie Header 格式
            /Cookie:.*?access[-_]token=([^;]+)/i,
            /-H\s+['"]Cookie:.*?access[-_]token=([^;'"]+)['"]/i
          ],
          description: '访问 Token'
        },
        'coze_token': {
          patterns: [
            // Cookie 格式
            /__Secure-coze[-_]token=([^;]+)/i,
            /coze[-_]token=([^;]+)/i,
            // Header 格式
            /Coze-Token:\s*([^\s\n]+)/i,
            /-H\s+['"]Coze-Token:\s*([^\s'"]+)['"]/i,
            // Cookie Header 格式
            /Cookie:.*?coze[-_]token=([^;]+)/i,
            /-H\s+['"]Cookie:.*?coze[-_]token=([^;'"]+)['"]/i
          ],
          description: 'Coze API Token'
        }
      }

      // 尝试匹配各种 token
      for (const [tokenType, config] of Object.entries(tokenMapping)) {
        for (const pattern of config.patterns) {
          const match = input.match(pattern)
          if (match && match[1]) {
            let value = match[1].trim()
            // 移除可能的引号
            value = value.replace(/^["']|["']$/g, '')

            // 检查是否已经添加过这个 token
            if (!parsedTokens.find(t => t.type === tokenType) && value.length > 0) {
              parsedTokens.push({
                type: tokenType,
                value: value,
                description: config.description,
                selected: true
              })
            }
            break
          }
        }
      }

      // 如果没有匹配到任何格式，尝试直接作为 token 值
      if (parsedTokens.length === 0 && input.length > 20 && !input.includes('\n') && !input.includes(';')) {
        // 假设是直接粘贴的 token 值，默认作为 auth_token
        parsedTokens.push({
          type: 'auth_token',
          value: input,
          description: '认证 Token (自动识别)',
          selected: true
        })
      }

      quickImportForm.parsedTokens = parsedTokens
    }

    // 打开快捷导入对话框
    const openQuickImportDialog = () => {
      quickImportForm.headerString = ''
      quickImportForm.parsedTokens = []
      showQuickImportDialog.value = true
    }

    // 关闭快捷导入对话框
    const closeQuickImportDialog = () => {
      showQuickImportDialog.value = false
    }

    // 提交快捷导入
    const submitQuickImport = async () => {
      const selectedTokens = quickImportForm.parsedTokens.filter(t => t.selected)

      if (selectedTokens.length === 0) {
        showMessage('请至少选择一个 Token', 'error')
        return
      }

      updating.value = true
      let successCount = 0
      let failCount = 0

      try {
        for (const token of selectedTokens) {
          try {
            const res = await updateToken({
              token_type: token.type,
              token_value: token.value
            })
            if (res.success) {
              successCount++
            } else {
              failCount++
            }
          } catch (error) {
            failCount++
          }
        }

        if (successCount > 0) {
          showMessage(`成功导入 ${successCount} 个 Token${failCount > 0 ? `，失败 ${failCount} 个` : ''}`)
          closeQuickImportDialog()
          await refreshStatus()
        } else {
          showMessage('导入失败', 'error')
        }
      } catch (error) {
        showMessage('导入失败: ' + error.message, 'error')
      } finally {
        updating.value = false
      }
    }

    // 初始化
    onMounted(() => {
      refreshStatus()
    })

    return {
      loading,
      updating,
      tokens,
      systemStatus,
      showUpdateDialog,
      showIntervalDialog,
      showQuickImportDialog,
      updateForm,
      intervalForm,
      quickImportForm,
      message,
      formatDateTime,
      maskToken,
      refreshStatus,
      checkAllTokens,
      openUpdateDialog,
      closeUpdateDialog,
      submitUpdate,
      expireToken,
      openIntervalDialog,
      closeIntervalDialog,
      submitInterval,
      parseHeaderString,
      openQuickImportDialog,
      closeQuickImportDialog,
      submitQuickImport,
      showMessage
    }
  }
}
</script>

<style scoped>
/* 容器 */
.token-management {
  padding: 20px;
}

/* 头部 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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

.btn-refresh,
.btn-check,
.btn-quick-import {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  color: #333;
  cursor: pointer;
  font-size: 13px;
}

.btn-quick-import {
  background: #1890ff;
  color: white;
  border-color: #1890ff;
}

.btn-quick-import:hover {
  background: #40a9ff;
}

.btn-refresh:hover,
.btn-check:hover {
  background: #f5f5f5;
}

.btn-refresh:disabled,
.btn-check:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 系统状态 */
.system-status {
  background: white;
  border: 1px solid #ddd;
  padding: 15px;
  margin-bottom: 20px;
  display: flex;
  gap: 30px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-item .label {
  color: #666;
  font-size: 13px;
}

.status-item .value {
  font-weight: 500;
  font-size: 13px;
}

.status-item .value.running {
  color: #52c41a;
}

.status-item .value.stopped {
  color: #ff4d4f;
}

.btn-edit {
  padding: 4px 12px;
  border: 1px solid #ddd;
  background: white;
  color: #333;
  cursor: pointer;
  font-size: 12px;
}

.btn-edit:hover {
  background: #f5f5f5;
}

/* Token 列表 */
.token-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

/* Token 卡片 */
.token-card {
  background: white;
  border: 1px solid #ddd;
  padding: 20px;
}

.token-card.expired {
  border-color: #ff4d4f;
  background: #fff1f0;
}

.token-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.token-title h3 {
  margin: 0 0 5px 0;
  font-size: 16px;
  color: #333;
}

.token-type {
  font-size: 12px;
  color: #999;
  font-family: monospace;
}

.status-badge {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.valid {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.status-badge.expired {
  background: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

/* Token 信息 */
.token-info {
  margin-bottom: 15px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 13px;
}

.info-label {
  color: #666;
}

.info-value {
  color: #333;
  font-weight: 500;
}

.info-value.token-value {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

/* Token 操作 */
.token-actions {
  display: flex;
  gap: 10px;
}

.btn-update,
.btn-expire {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  color: #333;
  cursor: pointer;
  font-size: 13px;
}

.btn-update:hover {
  background: #f5f5f5;
}

.btn-expire {
  color: #ff4d4f;
  border-color: #ff4d4f;
}

.btn-expire:hover {
  background: #fff1f0;
}

.btn-expire:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: white;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.dialog-large {
  max-width: 700px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.dialog-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.btn-close {
  border: none;
  background: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  line-height: 1;
}

.btn-close:hover {
  color: #333;
}

.dialog-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 13px;
  color: #666;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="datetime-local"],
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  font-size: 13px;
  box-sizing: border-box;
}

.form-group input[type="checkbox"] {
  margin-right: 5px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #f0f0f0;
}

.btn-cancel,
.btn-submit {
  padding: 8px 20px;
  border: 1px solid #ddd;
  background: white;
  color: #333;
  cursor: pointer;
  font-size: 13px;
}

.btn-cancel:hover {
  background: #f5f5f5;
}

.btn-submit {
  background: #1890ff;
  color: white;
  border-color: #1890ff;
}

.btn-submit:hover {
  background: #40a9ff;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 消息提示 */
.message {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 20px;
  background: white;
  border: 1px solid #ddd;
  font-size: 13px;
  z-index: 2000;
  min-width: 200px;
}

.message.success {
  border-color: #52c41a;
  background: #f6ffed;
  color: #52c41a;
}

.message.error {
  border-color: #ff4d4f;
  background: #fff1f0;
  color: #ff4d4f;
}

/* 快捷导入相关样式 */
.hint {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}

.parsed-tokens {
  margin-top: 20px;
  padding: 15px;
  background: #f5f5f5;
  border: 1px solid #ddd;
}

.parsed-tokens h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
}

.parsed-token-item {
  background: white;
  border: 1px solid #ddd;
  padding: 10px;
  margin-bottom: 10px;
}

.parsed-token-item:last-child {
  margin-bottom: 0;
}

.parsed-token-header {
  margin-bottom: 5px;
}

.parsed-token-header label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
}

.parsed-token-header input[type="checkbox"] {
  margin: 0;
}

.parsed-token-value {
  font-family: monospace;
  font-size: 12px;
  color: #666;
  padding: 5px 10px;
  background: #f9f9f9;
  border: 1px solid #eee;
  word-break: break-all;
}

.no-tokens-found {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
  background: #f5f5f5;
  border: 1px solid #ddd;
}

/* 响应式 */
@media (max-width: 768px) {
  .token-list {
    grid-template-columns: 1fr;
  }

  .system-status {
    flex-direction: column;
    gap: 10px;
  }

  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .dialog-large {
    max-width: 95%;
  }
}
</style>

