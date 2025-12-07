<template>
  <div id="app">
    <router-view />
    <!-- 全局通知组件 -->
    <Toast />
    <ConfirmDialog />
  </div>
</template>

<script>
import Toast from '@/components/Notification/Toast.vue'
import ConfirmDialog from '@/components/Notification/ConfirmDialog.vue'

export default {
  name: 'App',
  components: {
    Toast,
    ConfirmDialog
  }
}
</script>

<style>
#app {
  width: 100%;
  height: 100%;
}
</style>

