/**
 * 通知系统统一导出
 *
 * 使用方法:
 * import { toast, confirm, Modal } from '@/components/Notification'
 *
 * toast.success('操作成功')
 * toast.error('操作失败')
 * toast.warning('警告信息')
 * toast.info('提示信息')
 *
 * const result = await confirm('确定要删除吗？')
 * if (result) { ... }
 *
 * <Modal v-model:visible="showDialog" title="标题">
 *   内容
 * </Modal>
 */

import { toast } from './Toast.vue'
import { confirm } from './ConfirmDialog.vue'
import Modal from './Modal.vue'

export { toast, confirm, Modal }

export default {
  toast,
  confirm,
  Modal
}

