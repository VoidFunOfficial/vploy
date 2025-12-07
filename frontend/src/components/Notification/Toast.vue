<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', `toast-${toast.type}`]"
        >
          <div class="toast-icon">{{ getIcon(toast.type) }}</div>
          <div class="toast-content">
            <div v-if="toast.title" class="toast-title">{{ toast.title }}</div>
            <div class="toast-message">{{ toast.message }}</div>
          </div>
          <button class="toast-close" @click="removeToast(toast.id)">&times;</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script>
import { ref, reactive } from 'vue'

// 全局 toast 列表
const toasts = reactive([])
let toastId = 0

// 添加 toast
const addToast = (options) => {
  const id = ++toastId
  const toast = {
    id,
    type: options.type || 'info',
    title: options.title || '',
    message: options.message || '',
    duration: options.duration !== undefined ? options.duration : 3000
  }
  
  // 新 toast 添加到数组末尾（显示在最下方）
  toasts.push(toast)
  
  // 自动消失
  if (toast.duration > 0) {
    setTimeout(() => {
      removeToast(id)
    }, toast.duration)
  }
  
  // 记录日志到后端
  logNotification(toast)
  
  return id
}

// 移除 toast
const removeToast = (id) => {
  const index = toasts.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.splice(index, 1)
  }
}

// 记录通知日志到后端
const logNotification = async (toast) => {
  try {
    await fetch('/api/logs/notification', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        type: toast.type,
        title: toast.title,
        message: toast.message,
        action: 'show',
        timestamp: new Date().toISOString()
      })
    })
  } catch (error) {
    // 静默失败，不影响用户体验
    console.debug('通知日志记录失败:', error)
  }
}

// 快捷方法
const toast = {
  success: (message, title = '') => addToast({ type: 'success', message, title }),
  error: (message, title = '') => addToast({ type: 'error', message, title }),
  warning: (message, title = '') => addToast({ type: 'warning', message, title }),
  info: (message, title = '') => addToast({ type: 'info', message, title }),
  show: addToast
}

export { toast, toasts, removeToast }

export default {
  name: 'Toast',
  setup() {
    const getIcon = (type) => {
      const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
      }
      return icons[type] || icons.info
    }

    return {
      toasts,
      removeToast,
      getIcon
    }
  }
}
</script>

<style scoped>
/* Toast 容器 - 右下角定位 */
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 360px;
  pointer-events: none;
}

/* 单个 Toast */
.toast {
  display: flex;
  align-items: flex-start;
  padding: 12px 16px;
  border-radius: 6px;
  background-color: #fff;
  border: 1px solid #ddd;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  pointer-events: auto;
  min-width: 280px;
}

/* Toast 图标 */
.toast-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin-right: 12px;
  font-size: 12px;
  font-weight: bold;
  color: #fff;
}

/* Toast 内容 */
.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-weight: 600;
  font-size: 14px;
  color: #333;
  margin-bottom: 4px;
}

.toast-message {
  font-size: 13px;
  color: #666;
  word-break: break-word;
}

/* 关闭按钮 */
.toast-close {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  padding: 0;
  margin-left: 8px;
  border-radius: 4px;
}

.toast-close:hover {
  background-color: #f5f5f5;
  color: #666;
  transform: none;
  box-shadow: none;
}

/* 成功类型 */
.toast-success {
  border-left: 4px solid #20a53a;
}
.toast-success .toast-icon {
  background-color: #20a53a;
}

/* 错误类型 */
.toast-error {
  border-left: 4px solid #ff5722;
}
.toast-error .toast-icon {
  background-color: #ff5722;
}

/* 警告类型 */
.toast-warning {
  border-left: 4px solid #ff9800;
}
.toast-warning .toast-icon {
  background-color: #ff9800;
}

/* 信息类型 */
.toast-info {
  border-left: 4px solid #2196f3;
}
.toast-info .toast-icon {
  background-color: #2196f3;
}

/* 动画 */
.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.2s ease-in;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* 移动端适配 */
@media (max-width: 480px) {
  .toast-container {
    left: 10px;
    right: 10px;
    bottom: 10px;
    max-width: none;
  }
  
  .toast {
    min-width: auto;
  }
}
</style>

