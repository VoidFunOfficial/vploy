<template>
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <div class="top-navbar">
      <div class="navbar-left">
        <!-- 移动端菜单按钮 -->
        <button class="menu-toggle" @click="toggleSidebar">☰</button>
        <h1>VoidPoly 管理面板</h1>
      </div>
      <div class="navbar-right">
        <span class="user-info">{{ user?.username }}</span>
        <button class="btn-logout" @click="handleLogout">退出</button>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="main-body">
      <!-- 遮罩层（移动端） -->
      <div
        v-if="sidebarOpen"
        class="sidebar-overlay"
        @click="closeSidebar"
      ></div>

      <!-- 左侧导航栏 -->
      <div :class="['sidebar', { open: sidebarOpen }]">
        <div
          v-for="item in menuItems"
          :key="item.id"
          :class="['menu-item', { active: activeMenu === item.id }]"
          @click="handleMenuClick(item.id)"
        >
          <span class="menu-icon">{{ item.icon }}</span>
          <span class="menu-text">{{ item.name }}</span>
        </div>
      </div>

      <!-- 右侧内容区 -->
      <div class="content-area">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { logout } from '@/api/auth'
import { getUser, clearAuth } from '@/utils/auth'

export default {
  name: 'MainLayout',
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
    const sidebarOpen = ref(false)

    // 菜单项配置
    const menuItems = ref([
      { id: 'overview', name: '系统宏观信息', icon: '📊' },
      { id: 'system', name: '系统信息', icon: '💻' },
      { id: 'profit', name: '盈亏情况', icon: '💰' },
      { id: 'filter', name: '过滤', icon: '🔍' },
      { id: 'analysis', name: '分析', icon: '📈' },
      { id: 'trade', name: '交易', icon: '💱' },
      { id: 'monitor', name: '监控', icon: '👁️' },
      { id: 'logs', name: '日志管理', icon: '📝' },
      { id: 'api', name: 'API 刷新', icon: '🔄' },
      { id: 'database', name: '数据库管理', icon: '🗄️' },
      { id: 'settings', name: '设置', icon: '⚙️' }
    ])

    // 加载用户信息
    onMounted(() => {
      user.value = getUser()
    })

    // 切换侧边栏
    const toggleSidebar = () => {
      sidebarOpen.value = !sidebarOpen.value
    }

    // 关闭侧边栏
    const closeSidebar = () => {
      sidebarOpen.value = false
    }

    // 处理菜单点击
    const handleMenuClick = (menuId) => {
      emit('menu-change', menuId)
      // 移动端点击菜单后关闭侧边栏
      if (window.innerWidth <= 768) {
        closeSidebar()
      }
    }

    // 处理登出
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

    return {
      user,
      menuItems,
      sidebarOpen,
      toggleSidebar,
      closeSidebar,
      handleMenuClick,
      handleLogout
    }
  }
}
</script>

<style scoped>
/* 主布局容器 */
.main-layout {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
}

/* 顶部导航栏 */
.top-navbar {
  height: 50px;
  background-color: #20a53a;
  border-bottom: 1px solid #1a8c31;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.navbar-left h1 {
  font-size: 16px;
  color: #fff;
  font-weight: 500;
}

/* 移动端菜单按钮 */
.menu-toggle {
  display: none;
  width: 40px;
  height: 40px;
  border: none;
  background-color: transparent;
  color: #fff;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.user-info {
  color: #fff;
  font-size: 13px;
}

.btn-logout {
  height: 30px;
  padding: 0 15px;
  border: none;
  background-color: #fff;
  color: #20a53a;
  font-size: 12px;
  cursor: pointer;
  outline: none;
}

.btn-logout:hover {
  background-color: #f0f0f0;
}

/* 主体区域 */
.main-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 遮罩层（移动端） */
.sidebar-overlay {
  display: none;
}

/* 左侧导航栏 */
.sidebar {
  width: 200px;
  background-color: #2c3e50;
  overflow-y: auto;
  flex-shrink: 0;
  transition: transform 0.3s ease;
}

/* 菜单项 */
.menu-item {
  height: 45px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  border-bottom: 1px solid #34495e;
  color: #bdc3c7;
  font-size: 13px;
}

.menu-item:hover {
  background-color: #34495e;
  color: #fff;
}

.menu-item.active {
  background-color: #20a53a;
  color: #fff;
  border-left: 3px solid #1a8c31;
}

.menu-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
}

.menu-text {
  flex: 1;
}

/* 右侧内容区 */
.content-area {
  flex: 1;
  overflow-y: auto;
  background-color: #f5f5f5;
}

/* 滚动条样式 */
.sidebar::-webkit-scrollbar,
.content-area::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-thumb,
.content-area::-webkit-scrollbar-thumb {
  background-color: #555;
}

.sidebar::-webkit-scrollbar-track,
.content-area::-webkit-scrollbar-track {
  background-color: #2c3e50;
}

.content-area::-webkit-scrollbar-track {
  background-color: #e0e0e0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  /* 显示菜单按钮 */
  .menu-toggle {
    display: block;
  }

  /* 顶部导航栏 */
  .top-navbar {
    padding: 0 10px;
  }

  .navbar-left h1 {
    font-size: 14px;
  }

  .user-info {
    display: none;
  }

  .btn-logout {
    font-size: 11px;
    padding: 0 10px;
    height: 28px;
  }

  /* 侧边栏默认隐藏 */
  .sidebar {
    position: fixed;
    left: 0;
    top: 50px;
    bottom: 0;
    z-index: 1000;
    transform: translateX(-100%);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  /* 显示遮罩层 */
  .sidebar-overlay {
    display: block;
    position: fixed;
    top: 50px;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 999;
  }

  /* 内容区占满宽度 */
  .content-area {
    width: 100%;
  }
}

/* 小屏幕优化 */
@media (max-width: 480px) {
  .navbar-left h1 {
    font-size: 12px;
  }

  .btn-logout {
    font-size: 10px;
    padding: 0 8px;
    height: 26px;
  }
}
</style>

