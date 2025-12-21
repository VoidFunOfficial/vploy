<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '260px'" class="aside">
      <div class="logo-container" :class="{ 'collapsed': isCollapse }">
        <div class="logo-box" @click="toggleCollapse">
          <el-icon :size="24" class="logo-icon" v-if="isCollapse"><ElementPlus /></el-icon>
          <div v-else class="logo-full">
             <el-icon :size="24" class="logo-icon"><ElementPlus /></el-icon>
             <span class="logo-text">VoidPoly</span>
          </div>
        </div>
      </div>
      
      <el-scrollbar>
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
          :collapse="isCollapse"
          @select="handleMenuSelect"
          background-color="transparent"
          text-color="#475569"
          active-text-color="#3B82F6"
        >
          <el-menu-item v-for="item in menuItems" :key="item.id" :index="item.id">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.name }}</template>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="main-wrapper">
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-button link @click="toggleCollapse" class="collapse-btn">
            <el-icon :size="20"><component :is="isCollapse ? 'Expand' : 'Fold'" /></el-icon>
          </el-button>
          <h2 class="page-title">{{ currentPageTitle }}</h2>
        </div>
        <div class="header-right">
          <el-tooltip content="全局刷新" placement="bottom">
            <el-button circle text @click="handleGlobalRefresh" :loading="isRefreshing" class="icon-btn">
              <el-icon :size="18"><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
          
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-profile">
              <el-avatar :size="32" class="user-avatar">{{ userInitial }}</el-avatar>
              <span class="username">{{ user?.username || 'Admin' }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">个人设置</el-dropdown-item>
                <el-dropdown-item divided command="logout" style="color: var(--el-color-danger)">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主要内容 -->
      <el-main class="main-content">
        <slot></slot>
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { logout } from '@/api/auth'
import { getUser, clearAuth } from '@/utils/auth'
import { 
  Odometer, Monitor, Money, List, Filter, TrendCharts, Cpu, 
  Switch, PieChart, Document, Link, DataLine, Timer, Setting,
  Expand, Fold, Refresh, ArrowDown, ElementPlus
} from '@element-plus/icons-vue'

export default {
  name: 'MainLayout',
  components: {
    Odometer, Monitor, Money, List, Filter, TrendCharts, Cpu,
    Switch, PieChart, Document, Link, DataLine, Timer, Setting,
    Expand, Fold, Refresh, ArrowDown, ElementPlus
  },
  props: {
    activeMenu: {
      type: String,
      default: 'overview'
    }
  },
  emits: ['menu-change'],
  setup(props, { emit }) {
    const router = useRouter()
    const user = ref(null)
    const isCollapse = ref(false)
    const isRefreshing = ref(false)

    // 菜单项配置 - 映射到 Element Plus 图标
    const menuItems = ref([
      { id: 'overview', name: '系统宏观信息', icon: 'Odometer' },
      { id: 'system', name: '系统信息', icon: 'Monitor' },
      { id: 'profit', name: '盈亏情况', icon: 'Money' },
      { id: 'tasks', name: '任务管理', icon: 'List' },
      { id: 'filter', name: '过滤', icon: 'Filter' },
      { id: 'analysis', name: '分析', icon: 'TrendCharts' },
      { id: 'decision', name: '决策', icon: 'Cpu' },
      { id: 'trade', name: '交易', icon: 'Switch' },
      { id: 'positions', name: '持仓监控', icon: 'PieChart' },
      { id: 'logs', name: '日志管理', icon: 'Document' },
      { id: 'api', name: 'API 刷新', icon: 'Link' },
      { id: 'database', name: '数据库管理', icon: 'DataLine' },
      { id: 'scheduler', name: '定时任务管理', icon: 'Timer' },
      { id: 'settings', name: '设置', icon: 'Setting' }
    ])

    const currentPageTitle = computed(() => {
      const item = menuItems.value.find(i => i.id === props.activeMenu)
      return item ? item.name : 'Dashboard'
    })

    const userInitial = computed(() => {
      const name = user.value?.username || 'A'
      return name.charAt(0).toUpperCase()
    })

    onMounted(() => {
      user.value = getUser()
      // 读取侧边栏状态
      const savedCollapse = localStorage.getItem('sidebarCollapse')
      if (savedCollapse !== null) {
        isCollapse.value = savedCollapse === 'true'
      }
      
      // 响应式处理
      checkScreenSize()
      window.addEventListener('resize', checkScreenSize)
    })

    const checkScreenSize = () => {
      if (window.innerWidth <= 768) {
        isCollapse.value = true
      }
    }

    const toggleCollapse = () => {
      isCollapse.value = !isCollapse.value
      localStorage.setItem('sidebarCollapse', isCollapse.value)
    }

    const handleMenuSelect = (index) => {
      emit('menu-change', index)
    }

    const handleCommand = (command) => {
      if (command === 'logout') {
        handleLogout()
      } else if (command === 'settings') {
        emit('menu-change', 'settings')
      }
    }

    const handleLogout = async () => {
      try {
        await logout()
      } catch (error) {
        console.error('登出失败:', error)
      } finally {
        clearAuth()
        router.push('/login')
      }
    }

    const handleGlobalRefresh = () => {
      if (isRefreshing.value) return
      isRefreshing.value = true
      emit('global-refresh')
      setTimeout(() => {
        isRefreshing.value = false
      }, 1000)
    }

    return {
      user,
      menuItems,
      isCollapse,
      isRefreshing,
      currentPageTitle,
      userInitial,
      toggleCollapse,
      handleMenuSelect,
      handleCommand,
      handleGlobalRefresh
    }
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  background-color: var(--el-bg-color-page);
}

.aside {
  background-color: #fff;
  border-right: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
  overflow: hidden;
}

.logo-container {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color-light);
  cursor: pointer;
}

.logo-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.logo-full {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  color: var(--el-color-primary);
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: -0.5px;
  font-family: 'Inter', sans-serif;
}

.sidebar-menu {
  border-right: none;
  padding: 8px 0;
}

.header {
  background-color: #fff;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--el-border-color-light);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 18px;
  color: var(--el-text-color-regular);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 20px;
  transition: background-color 0.2s;
  border: 1px solid transparent;
}

.user-profile:hover {
  background-color: var(--el-bg-color-page);
  border-color: var(--el-border-color-light);
}

.user-avatar {
  background-color: var(--el-color-primary);
  color: #fff;
  font-weight: 600;
  font-size: 14px;
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.main-content {
  padding: 0;
  background-color: var(--el-bg-color-page);
  overflow-y: auto;
}

/* 覆盖 Element Plus 样式 */
:deep(.el-menu-item) {
  margin: 4px 12px;
  width: auto;
  border-radius: 8px;
  height: 48px;
  line-height: 48px;
}

:deep(.el-menu-item.is-active) {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 600;
}

:deep(.el-menu-item:hover) {
  background-color: var(--el-bg-color-page);
}

/* 折叠时的微调 */
:deep(.el-menu--collapse .el-menu-item) {
  margin: 4px 0;
  padding: 0 !important;
  display: flex;
  justify-content: center;
  width: 100%;
}

:deep(.el-menu--collapse .el-menu-item .el-icon) {
  margin: 0;
}
</style>
