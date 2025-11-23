import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/auth'

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 检查认证状态
router.beforeEach((to, from, next) => {
  const token = getToken()
  
  // 如果路由需要认证
  if (to.meta.requiresAuth) {
    if (token) {
      next()
    } else {
      // 未登录，跳转到登录页
      next('/login')
    }
  } else {
    // 如果已登录且访问登录页，跳转到首页
    if (to.path === '/login' && token) {
      next('/')
    } else {
      next()
    }
  }
})

export default router

