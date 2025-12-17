<template>
  <MainLayout :active-menu="activeMenu" @menu-change="handleMenuChange">
    <!-- 根据激活的菜单显示不同内容 -->
    <SystemOverview v-if="activeMenu === 'overview'" />

    <!-- 日志管理 -->
    <LogManagement v-else-if="activeMenu === 'logs'" />

    <!-- 数据库管理 -->
    <DatabaseManagement v-else-if="activeMenu === 'database'" />

    <!-- 定时任务管理 -->
    <SchedulerManagement v-else-if="activeMenu === 'scheduler'" />

    <!-- 任务管理 -->
    <TaskManagement v-else-if="activeMenu === 'tasks'" />

    <!-- 分析界面 -->
    <Analysis v-else-if="activeMenu === 'analysis'" />

    <!-- 决策界面 -->
    <Decision v-else-if="activeMenu === 'decision'" />

    <!-- 交易界面 -->
    <Trade v-else-if="activeMenu === 'trade'" />

    <!-- 持仓监控 -->
    <PositionMonitor v-else-if="activeMenu === 'positions'" />

    <!-- Token 管理 -->
    <TokenManagement v-else-if="activeMenu === 'api'" />

    <!-- 过滤器管理 -->
    <FilterManagement v-else-if="activeMenu === 'filter'" />

    <!-- 盈亏情况 -->
    <ProfitChart v-else-if="activeMenu === 'profit'" />

    <!-- 系统设置 -->
    <SystemSettings v-else-if="activeMenu === 'settings'" />

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
import DatabaseManagement from '@/components/DatabaseManagement.vue'
import SchedulerManagement from '@/components/SchedulerManagement.vue'
import TaskManagement from '@/components/TaskManagement.vue'
import Analysis from '@/components/Analysis.vue'
import Decision from '@/components/Decision.vue'
import Trade from '@/components/Trade.vue'
import TokenManagement from '@/components/TokenManagement.vue'
import FilterManagement from '@/components/FilterManagement.vue'
import ProfitChart from '@/components/ProfitChart.vue'
import SystemSettings from '@/components/SystemSettings.vue'
import PositionMonitor from '@/components/PositionMonitor.vue'

export default {
  name: 'Dashboard',
  components: {
    MainLayout,
    SystemOverview,
    LogManagement,
    DatabaseManagement,
    SchedulerManagement,
    TaskManagement,
    Analysis,
    Decision,
    Trade,
    PositionMonitor,
    TokenManagement,
    FilterManagement,
    ProfitChart,
    SystemSettings
  },
  setup() {
    const activeMenu = ref('overview')

    // 菜单标题映射
    const menuTitles = {
      overview: '系统宏观信息',
      system: '系统信息',
      profit: '盈亏情况',
      tasks: '任务管理',
      filter: '过滤',
      analysis: '分析',
      decision: '决策',
      trade: '交易',
      positions: '持仓监控',
      logs: '日志管理',
      api: 'API 刷新',
      database: '数据库管理',
      scheduler: '定时任务管理',
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

