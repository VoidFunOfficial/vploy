<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="visible" class="modal-overlay" @click.self="handleOverlayClick">
        <div class="modal-dialog" :class="sizeClass">
          <!-- 头部 -->
          <div v-if="showHeader" class="modal-header">
            <slot name="header">
              <h3 class="modal-title">{{ title }}</h3>
            </slot>
            <button v-if="showClose" class="modal-close" @click="handleClose">×</button>
          </div>

          <!-- 内容 -->
          <div class="modal-body">
            <slot></slot>
          </div>

          <!-- 底部 -->
          <div v-if="showFooter" class="modal-footer">
            <slot name="footer">
              <button class="btn-secondary" @click="handleCancel">{{ cancelText }}</button>
              <button class="btn-primary" @click="handleConfirm">{{ confirmText }}</button>
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'Modal',
  props: {
    // 是否显示
    visible: {
      type: Boolean,
      default: false
    },
    // 标题
    title: {
      type: String,
      default: ''
    },
    // 尺寸: small, medium, large
    size: {
      type: String,
      default: 'medium',
      validator: (value) => ['small', 'medium', 'large'].includes(value)
    },
    // 是否显示头部
    showHeader: {
      type: Boolean,
      default: true
    },
    // 是否显示关闭按钮
    showClose: {
      type: Boolean,
      default: true
    },
    // 是否显示底部
    showFooter: {
      type: Boolean,
      default: true
    },
    // 确认按钮文本
    confirmText: {
      type: String,
      default: '确定'
    },
    // 取消按钮文本
    cancelText: {
      type: String,
      default: '取消'
    },
    // 点击遮罩层是否关闭
    closeOnClickOverlay: {
      type: Boolean,
      default: true
    }
  },
  emits: ['update:visible', 'confirm', 'cancel', 'close'],
  setup(props, { emit }) {
    // 尺寸类名
    const sizeClass = computed(() => {
      return `modal-${props.size}`
    })

    // 处理遮罩层点击
    const handleOverlayClick = () => {
      if (props.closeOnClickOverlay) {
        handleClose()
      }
    }

    // 处理关闭
    const handleClose = () => {
      emit('update:visible', false)
      emit('close')
    }

    // 处理确认
    const handleConfirm = () => {
      emit('confirm')
    }

    // 处理取消
    const handleCancel = () => {
      emit('cancel')
      handleClose()
    }

    return {
      sizeClass,
      handleOverlayClick,
      handleClose,
      handleConfirm,
      handleCancel
    }
  }
}
</script>

<style scoped>
/* 遮罩层 */
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
  backdrop-filter: blur(2px);
}

/* 对话框 */
.modal-dialog {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* 尺寸 */
.modal-small {
  width: 90%;
  max-width: 400px;
}

.modal-medium {
  width: 90%;
  max-width: 600px;
}

.modal-large {
  width: 90%;
  max-width: 800px;
}

/* 头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-title {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #333;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.modal-close:hover {
  color: #333;
}

/* 内容 */
.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

/* 底部 */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #e0e0e0;
}

/* 按钮 */
.btn-primary,
.btn-secondary {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-primary {
  background-color: #1890ff;
  color: white;
}

.btn-primary:hover {
  background-color: #40a9ff;
}

.btn-secondary {
  background-color: #fff;
  color: #333;
  border: 1px solid #d9d9d9;
}

.btn-secondary:hover {
  color: #1890ff;
  border-color: #1890ff;
}

/* 过渡动画 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-active .modal-dialog,
.modal-fade-leave-active .modal-dialog {
  transition: transform 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-dialog,
.modal-fade-leave-to .modal-dialog {
  transform: scale(0.9);
}
</style>

