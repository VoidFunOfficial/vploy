<template>
  <div class="token-refresh-view">
    <TokenManagement />
  </div>
</template>

<script>
import TokenManagement from '@/components/TokenManagement.vue'

export default {
  name: 'TokenRefreshView',
  components: {
    TokenManagement
  }
}
</script>

<style scoped>
.token-refresh-view {
  padding: 20px;
  min-height: 100vh;
  background-color: var(--el-bg-color-page);
}
</style>
