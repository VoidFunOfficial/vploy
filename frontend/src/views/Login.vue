<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="login-header">
          <div class="logo-box">
             <el-icon :size="40" color="var(--el-color-primary)"><ElementPlus /></el-icon>
          </div>
          <h1>VoidPoly</h1>
          <p class="subtitle">自动化交易系统管理面板</p>
        </div>
      </template>

      <el-form
        ref="loginFormRef"
        :model="formData"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
        size="large"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="formData.username" 
            placeholder="请输入用户名" 
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="formData.password" 
            type="password" 
            placeholder="请输入密码" 
            :prefix-icon="Lock" 
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-alert
          v-if="errors.general"
          :title="errors.general"
          type="error"
          show-icon
          :closable="false"
          class="mb-4"
        />

        <el-button 
          type="primary" 
          class="w-full mt-4" 
          :loading="loading" 
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>

      <div class="login-footer">
        <p>默认账号：admin / admin123</p>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/auth'
import { setToken, setUser } from '@/utils/auth'
import { User, Lock, ElementPlus } from '@element-plus/icons-vue'

export default {
  name: 'Login',
  components: {
    ElementPlus
  },
  setup() {
    const router = useRouter()
    const loginFormRef = ref(null)
    const loading = ref(false)
    
    const formData = reactive({
      username: '',
      password: ''
    })
    
    const rules = {
      username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
      password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
    }
    
    const errors = reactive({
      general: ''
    })
    
    const handleLogin = async () => {
      if (!loginFormRef.value) return
      
      await loginFormRef.value.validate(async (valid) => {
        if (valid) {
          loading.value = true
          errors.general = ''
          
          try {
            const response = await login(formData.username, formData.password)
            
            if (response.success) {
              setToken(response.data.token)
              setUser(response.data.user)
              router.push('/')
            } else {
              errors.general = response.message || '登录失败'
            }
          } catch (error) {
             if (error.response && error.response.data) {
              errors.general = error.response.data.message || '登录失败，请检查用户名和密码'
            } else {
              errors.general = '网络错误，请稍后重试'
            }
          } finally {
            loading.value = false
          }
        }
      })
    }
    
    return {
      loginFormRef,
      formData,
      rules,
      errors,
      loading,
      handleLogin,
      User,
      Lock
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-color-page);
  background-image: radial-gradient(var(--el-color-primary-light-9) 1px, transparent 1px);
  background-size: 20px 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  border-radius: 16px !important;
  padding: 20px;
}

.login-header {
  text-align: center;
  padding: 10px 0 20px;
}

.logo-box {
  margin-bottom: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background-color: var(--el-color-primary-light-9);
  border-radius: 16px;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color-primary);
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.subtitle {
  color: var(--text-color-secondary);
  font-size: 14px;
  margin: 0;
}

.w-full {
  width: 100%;
}

.mt-4 {
  margin-top: 1rem;
}

.mb-4 {
  margin-bottom: 1rem;
}

.login-footer {
  margin-top: 32px;
  text-align: center;
  color: var(--text-color-placeholder);
  font-size: 13px;
}

:deep(.el-card__header) {
  border-bottom: none;
  padding-bottom: 0;
}

:deep(.el-input__wrapper) {
  padding: 8px 12px;
}
</style>
