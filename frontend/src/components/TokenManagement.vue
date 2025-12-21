<template>
  <div class="page-container">
    <div class="header mb-4">
      <h2 class="text-xl font-bold">API Token 管理</h2>
      <div class="header-actions">
        <el-button type="primary" :icon="Download" @click="showQuickImportDialog = true">
          快捷导入
        </el-button>
        <el-button :loading="loading" :icon="Refresh" @click="refreshStatus">
          刷新状态
        </el-button>
        <el-button type="success" :loading="loading" :icon="Check" @click="checkAllTokens">
          立即检查
        </el-button>
      </div>
    </div>

    <!-- 系统状态 -->
    <el-card class="box-card mb-4" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>系统状态</span>
          <el-button type="primary" link :icon="Edit" @click="showIntervalDialog = true">
            修改设置
          </el-button>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="后台检查状态">
          <el-tag :type="systemStatus.is_running ? 'success' : 'danger'">
            {{ systemStatus.is_running ? '运行中' : '已停止' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="检查间隔">
          {{ systemStatus.check_interval_minutes }} 分钟
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Token 列表 -->
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="12" :lg="8" v-for="(token, tokenType) in tokens" :key="tokenType" class="mb-4">
        <el-card :class="['token-card', { 'is-expired': token.is_expired }]" shadow="hover">
          <template #header>
            <div class="card-header">
              <div class="token-title-group">
                <span class="token-title">{{ token.description }}</span>
                <el-tag size="small" type="info" effect="plain">{{ tokenType }}</el-tag>
              </div>
              <el-tag :type="token.is_expired ? 'danger' : 'success'">
                {{ token.is_expired ? '已过期' : '有效' }}
              </el-tag>
            </div>
          </template>
          
          <div class="token-info">
            <div class="info-item">
              <span class="label">有效期:</span>
              <span class="value">{{ token.validity_days }} 天</span>
            </div>
            <div class="info-item">
              <span class="label">过期时间:</span>
              <span class="value">{{ formatDateTime(token.expires_at) }}</span>
            </div>
            <div class="info-item">
              <span class="label">最后检查:</span>
              <span class="value">{{ token.last_checked_at ? formatDateTime(token.last_checked_at) : '未检查' }}</span>
            </div>
            <div class="info-item">
              <span class="label">Token 值:</span>
              <el-tooltip :content="token.token_value || '未设置'" placement="top" :disabled="!token.token_value">
                <span class="value token-value">{{ token.token_value ? maskToken(token.token_value) : '未设置' }}</span>
              </el-tooltip>
            </div>
          </div>

          <div class="card-actions">
            <el-button type="primary" size="small" :icon="Edit" @click="openUpdateDialog(tokenType, token)">
              更新
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              :icon="Warning" 
              :disabled="token.is_expired"
              @click="expireToken(tokenType)"
            >
              标记过期
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 更新 Token 对话框 -->
    <el-dialog
      v-model="showUpdateDialog"
      title="更新 Token"
      width="500px"
      @close="closeUpdateDialog"
    >
      <el-form :model="updateForm" label-width="100px">
        <el-form-item label="Token 类型">
          <el-input v-model="updateForm.token_type" disabled />
        </el-form-item>
        <el-form-item label="Token 值">
          <el-input
            v-model="updateForm.token_value"
            type="textarea"
            :rows="4"
            placeholder="输入新的 Token 值"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="updateForm.custom_expiry">自定义过期时间</el-checkbox>
        </el-form-item>
        <el-form-item label="过期时间" v-if="updateForm.custom_expiry">
          <el-date-picker
            v-model="updateForm.expires_at"
            type="datetime"
            placeholder="选择过期时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showUpdateDialog = false">取消</el-button>
          <el-button type="primary" :loading="updating" @click="submitUpdate">
            确认更新
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 修改检查间隔对话框 -->
    <el-dialog
      v-model="showIntervalDialog"
      title="修改检查间隔"
      width="400px"
    >
      <el-form :model="intervalForm" label-width="120px">
        <el-form-item label="检查间隔(分)">
          <el-input-number v-model="intervalForm.minutes" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showIntervalDialog = false">取消</el-button>
          <el-button type="primary" :loading="updating" @click="submitInterval">
            确认修改
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 快捷导入对话框 -->
    <el-dialog
      v-model="showQuickImportDialog"
      title="快捷导入 Token"
      width="800px"
      @close="closeQuickImportDialog"
    >
      <el-form :model="quickImportForm" label-position="top">
        <el-form-item label="粘贴 HTTP Header 或 Cookie 字符串">
          <el-input
            v-model="quickImportForm.headerString"
            type="textarea"
            :rows="6"
            placeholder="支持多种格式，例如：&#10;Cookie 格式：__Secure-auth_token=xxx;__Secure-access_token=yyy;&#10;Header 格式：Authorization: Bearer eyJhbGc...&#10;或直接粘贴 cURL 命令"
            @input="parseHeaderString"
          />
          <div class="form-hint">支持格式：Cookie 字符串、HTTP Header、cURL 命令、或直接粘贴 token 值</div>
        </el-form-item>
      </el-form>

      <!-- 解析结果预览 -->
      <div v-if="quickImportForm.parsedTokens.length > 0" class="parsed-tokens-area">
        <h4>检测到的 Token:</h4>
        <div
          v-for="(item, index) in quickImportForm.parsedTokens"
          :key="index"
          class="parsed-token-item"
        >
          <div class="parsed-token-header">
            <el-checkbox v-model="item.selected">
              <strong>{{ item.type }}</strong> - {{ item.description }}
            </el-checkbox>
          </div>
          <div class="parsed-token-value">
            {{ maskToken(item.value) }}
          </div>
        </div>
      </div>
      <el-empty 
        v-else-if="quickImportForm.headerString.trim()" 
        description="未检测到有效的 Token，请检查输入格式" 
        :image-size="60"
      />

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showQuickImportDialog = false">取消</el-button>
          <el-button type="primary" :loading="updating" @click="submitQuickImport">
            确认导入
          </el-button>
        </span>
      </template>
    </el-dialog>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Check, Edit, Warning, Download } from '@element-plus/icons-vue'

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
          ElMessage.error(res.message || '获取状态失败')
        }
      } catch (error) {
        ElMessage.error('获取状态失败: ' + error.message)
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
          ElMessage.success('检查完成')
          await refreshStatus()
        } else {
          ElMessage.error(res.message || '检查失败')
        }
      } catch (error) {
        ElMessage.error('检查失败: ' + error.message)
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
        ElMessage.warning('请输入 Token 值')
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
          ElMessage.success('更新成功')
          closeUpdateDialog()
          await refreshStatus()
        } else {
          ElMessage.error(res.message || '更新失败')
        }
      } catch (error) {
        ElMessage.error('更新失败: ' + error.message)
      } finally {
        updating.value = false
      }
    }

    // 标记过期
    const expireToken = async (tokenType) => {
      try {
        await ElMessageBox.confirm(
          '确定要将此 Token 标记为过期吗？这将立即发送告警邮件。',
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        loading.value = true
        try {
          const res = await expireTokenApi(tokenType)
          if (res.success) {
            ElMessage.success(res.message || '已标记为过期')
            await refreshStatus()
          } else {
            ElMessage.error(res.message || '标记失败')
          }
        } catch (error) {
          ElMessage.error('标记失败: ' + error.message)
        } finally {
          loading.value = false
        }
      } catch {
        // 取消操作
      }
    }

    // 提交间隔修改
    const submitInterval = async () => {
      if (!intervalForm.minutes || intervalForm.minutes <= 0) {
        ElMessage.warning('请输入有效的检查间隔')
        return
      }

      updating.value = true
      try {
        const res = await setCheckInterval(intervalForm.minutes)
        if (res.success) {
          ElMessage.success(res.message || '修改成功')
          showIntervalDialog.value = false
          await refreshStatus()
        } else {
          ElMessage.error(res.message || '修改失败')
        }
      } catch (error) {
        ElMessage.error('修改失败: ' + error.message)
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

    // 关闭快捷导入对话框
    const closeQuickImportDialog = () => {
      showQuickImportDialog.value = false
    }

    // 提交快捷导入
    const submitQuickImport = async () => {
      const selectedTokens = quickImportForm.parsedTokens.filter(t => t.selected)

      if (selectedTokens.length === 0) {
        ElMessage.warning('请至少选择一个 Token')
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
          ElMessage.success(`成功导入 ${successCount} 个 Token${failCount > 0 ? `，失败 ${failCount} 个` : ''}`)
          closeQuickImportDialog()
          await refreshStatus()
        } else {
          ElMessage.error('导入失败')
        }
      } catch (error) {
        ElMessage.error('导入失败: ' + error.message)
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
      formatDateTime,
      maskToken,
      refreshStatus,
      checkAllTokens,
      openUpdateDialog,
      closeUpdateDialog,
      submitUpdate,
      expireToken,
      submitInterval,
      parseHeaderString,
      closeQuickImportDialog,
      submitQuickImport,
      Refresh, Check, Edit, Warning, Download
    }
  }
}
</script>

<style scoped>
/* Removed .token-management since we use .page-container */

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h2 {
  margin: 0;
  color: var(--el-text-color-primary);
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* Removed .mb-4 since it is global */

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.token-title-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.token-title {
  font-weight: bold;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.token-info {
  margin-bottom: 15px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.info-item .label {
  color: var(--el-text-color-secondary);
}

.info-item .value {
  color: var(--el-text-color-primary);
}

.token-value {
  font-family: monospace;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 15px;
}

.form-hint {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-top: 5px;
}

.parsed-tokens-area {
  margin-top: 20px;
  padding: 15px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.parsed-tokens-area h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: var(--text-color-secondary);
}

.parsed-token-item {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 4px;
}

.parsed-token-header {
  margin-bottom: 5px;
.parsed-token-value {
  font-family: monospace;
  font-size: 12px;
  color: var(--el-text-color-regular);
  padding: 5px;
  background: var(--el-fill-color-light);
  border-radius: 2px;
} word-break: break-all;
}

/* Expired card styling */
.token-card.is-expired :deep(.el-card__body) {
  background-color: #fef0f0;
}
</style>

