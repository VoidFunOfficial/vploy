<template>
  <MainLayout :active-menu="activeMenu" @menu-change="handleMenuChange">
    <!-- 根据激活的菜单显示不同内容 -->
    <SystemOverview v-if="activeMenu === 'overview'" />

    <!-- 日志管理 -->
    <LogManagement v-else-if="activeMenu === 'logs'" />

    <!-- 其他菜单项的占位内容 -->
    <div v-else class="placeholder-content">
      <div class="placeholder-card">
        <h2>{{ getMenuTitle(activeMenu) }}</h2>
        <p class="mt-20">此功能正在开发中...</p>
      </div>
    </div>
  </MainLayout>
</template>

<script>
import { ref } from 'vue'
import MainLayout from '@/components/Layout/MainLayout.vue'
import SystemOverview from '@/components/SystemOverview.vue'
import LogManagement from '@/components/LogManagement.vue'

export default {
  name: 'Dashboard',
  components: {
    MainLayout,
    SystemOverview,
    LogManagement
  },
  setup() {
    const activeMenu = ref('overview')

    // 菜单标题映射
    const menuTitles = {
      overview: '系统宏观信息',
      system: '系统信息',
      profit: '盈亏情况',
      filter: '过滤',
      analysis: '分析',
      trade: '交易',
      monitor: '监控',
      logs: '日志管理',
      api: 'API 刷新',
      settings: '设置'
    }

    // 处理菜单切换
    const handleMenuChange = (menuId) => {
      activeMenu.value = menuId
    }

    // 获取菜单标题
    const getMenuTitle = (menuId) => {
      return menuTitles[menuId] || '未知菜单'
    }

    return {
      activeMenu,
      handleMenuChange,
      getMenuTitle
    }
  }
}
</script>

<style scoped>
/* 占位内容 */
.placeholder-content {
  padding: 20px;
}

.placeholder-card {
  background-color: #fff;
  border: 1px solid #ddd;
  padding: 30px;
  text-align: center;
}

.placeholder-card h2 {
  font-size: 18px;
  color: #333;
  font-weight: 500;
}

.placeholder-card p {
  font-size: 14px;
  color: #666;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .placeholder-content {
    padding: 10px;
  }

  .placeholder-card {
    padding: 20px;
  }

  .placeholder-card h2 {
    font-size: 16px;
  }

  .placeholder-card p {
    font-size: 13px;
  }
}
</style>

