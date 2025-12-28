<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div v-if="visible" class="confirm-overlay" @click.self="handleCancel">
        <div class="confirm-dialog">
          <div class="confirm-header">
            <span class="confirm-icon">{{ getIcon() }}</span>
            <span class="confirm-title">{{ title || '确认' }}</span>
          </div>
          <div class="confirm-body">
            <div class="confirm-message" v-html="formattedMessage"></div>
          </div>
          <div class="confirm-footer">
            <button class="btn-cancel" @click="handleCancel">{{ cancelText }}</button>
            <button class="btn-confirm" @click="handleConfirm">{{ confirmText }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { ref, reactive, computed } from 'vue'
import request from '@/api/request'

// 全局状态
const state = reactive({
  visible: false,
  title: '',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  type: 'info', // info, warning, danger
  resolve: null,
  reject: null
})

// 显示确认对话框
const showConfirm = (options) => {
  return new Promise((resolve, reject) => {
    state.visible = true
    state.title = options.title || ''
    state.message = options.message || ''
    state.confirmText = options.confirmText || '确定'
    state.cancelText = options.cancelText || '取消'
    state.type = options.type || 'info'
    state.resolve = resolve
    state.reject = reject
    
    // 记录日志
    logConfirmAction('show', options.message)
  })
}

// 隐藏对话框
const hideConfirm = () => {
  state.visible = false
}

// 记录确认框操作日志
const logConfirmAction = async (action, message) => {
  try {
    await request({
      url: '/logs/notification',
      method: 'post',
      data: {
        type: 'confirm',
        title: state.title,
        message: message,
        action: action,
        timestamp: new Date().toISOString()
      }
    })
  } catch (error) {}
}

// confirm 函数 - 替代原生 confirm
const confirm = async (message, options = {}) => {
  if (typeof message === 'object') {
    options = message
    message = options.message
  }
  return showConfirm({
    message,
    ...options
  })
}

export { confirm, showConfirm }

export default {
  name: 'ConfirmDialog',
  setup() {
    const visible = computed(() => state.visible)
    const title = computed(() => state.title)
    const message = computed(() => state.message)
    const confirmText = computed(() => state.confirmText)
    const cancelText = computed(() => state.cancelText)
    const type = computed(() => state.type)
    
    // 处理消息中的换行符
    const formattedMessage = computed(() => {
      return state.message.replace(/\n/g, '<br>')
    })

    const getIcon = () => {
      const icons = {
        info: '?',
        warning: '⚠',
        danger: '!'
      }
      return icons[state.type] || icons.info
    }

    const handleConfirm = () => {
      logConfirmAction('confirm', state.message)
      hideConfirm()
      if (state.resolve) {
        state.resolve(true)
      }
    }

    const handleCancel = () => {
      logConfirmAction('cancel', state.message)
      hideConfirm()
      if (state.resolve) {
        state.resolve(false)
      }
    }

    return {
      visible,
      title,
      message,
      confirmText,
      cancelText,
      type,
      formattedMessage,
      getIcon,
      handleConfirm,
      handleCancel
    }
  }
}
</script>

<style scoped>
/* 遮罩层 */
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
}

/* 对话框 */
.confirm-dialog {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  min-width: 320px;
  max-width: 480px;
  max-height: 80vh;
  overflow: hidden;
}

/* 头部 */
.confirm-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.confirm-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: #2196f3;
  color: #fff;
  font-weight: bold;
  margin-right: 12px;
  font-size: 16px;
}

.confirm-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

/* 内容 */
.confirm-body {
  padding: 20px;
}

.confirm-message {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

/* 底部按钮 */
.confirm-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #eee;
  background-color: #fafafa;
}

.btn-cancel,
.btn-confirm {
  min-width: 80px;
  height: 36px;
  padding: 0 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.btn-cancel {
  background-color: #fff;
  border: 1px solid #ddd;
  color: #666;
}

.btn-cancel:hover {
  background-color: #f5f5f5;
  transform: none;
  box-shadow: none;
}

.btn-confirm {
  background-color: #20a53a;
  border: none;
  color: #fff;
}

.btn-confirm:hover {
  background-color: #1a8c31;
}

/* 动画 */
.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 0.2s ease;
}

.confirm-fade-enter-active .confirm-dialog,
.confirm-fade-leave-active .confirm-dialog {
  transition: transform 0.2s ease;
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}

.confirm-fade-enter-from .confirm-dialog,
.confirm-fade-leave-to .confirm-dialog {
  transform: scale(0.9);
}

/* 移动端适配 */
@media (max-width: 480px) {
  .confirm-dialog {
    min-width: auto;
    margin: 20px;
    width: calc(100% - 40px);
  }
}
</style>
