<template>
  <div class="login-container">
    <div class="login-box">
      <!-- 标题 -->
      <div class="login-header">
        <h1>VoidPoly 管理面板</h1>
        <p>Polymarket 自动化交易系统</p>
      </div>

      <!-- 登录表单 -->
      <div class="login-form">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input
            type="text"
            v-model="formData.username"
            placeholder="请输入用户名"
            @keyup.enter="handleLogin"
          />
          <div class="form-error" v-if="errors.username">{{ errors.username }}</div>
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            type="password"
            v-model="formData.password"
            placeholder="请输入密码"
            @keyup.enter="handleLogin"
          />
          <div class="form-error" v-if="errors.password">{{ errors.password }}</div>
        </div>

        <div class="form-error" v-if="errors.general">{{ errors.general }}</div>

        <button
          class="btn btn-block mt-20"
          @click="handleLogin"
          :disabled="loading"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </div>

      <!-- 底部信息 -->
      <div class="login-footer">
        <p>默认账号：admin / admin123</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/auth'
import { setToken, setUser } from '@/utils/auth'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const loading = ref(false)
    
    // 表单数据
    const formData = reactive({
      username: '',
      password: ''
    })
    
    // 错误信息
    const errors = reactive({
      username: '',
      password: '',
      general: ''
    })
    
    // 清除错误信息
    const clearErrors = () => {
      errors.username = ''
      errors.password = ''
      errors.general = ''
    }
    
    // 表单验证
    const validateForm = () => {
      clearErrors()
      let isValid = true
      
      if (!formData.username.trim()) {
        errors.username = '请输入用户名'
        isValid = false
      }
      
      if (!formData.password.trim()) {
        errors.password = '请输入密码'
        isValid = false
      }
      
      return isValid
    }
    
    // 处理登录
    const handleLogin = async () => {
      if (!validateForm()) {
        return
      }
      
      loading.value = true
      clearErrors()
      
      try {
        const response = await login(formData.username, formData.password)
        
        if (response.success) {
          // 保存令牌和用户信息
          setToken(response.data.token)
          setUser(response.data.user)
          
          // 跳转到首页
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
    
    return {
      formData,
      errors,
      loading,
      handleLogin
    }
  }
}
</script>

<style scoped>
/* 登录容器 - 全屏居中 */
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
}

/* 登录框 */
.login-box {
  width: 400px;
  background-color: #fff;
  border: 1px solid #ddd;
  padding: 0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .login-box {
    width: 90%;
    max-width: 400px;
  }
}

@media (max-width: 480px) {
  .login-box {
    width: 95%;
  }
}

/* 登录头部 */
.login-header {
  padding: 30px 30px 20px;
  border-bottom: 1px solid #ddd;
  text-align: center;
}

.login-header h1 {
  font-size: 24px;
  color: #20a53a;
  margin-bottom: 10px;
  font-weight: 500;
}

.login-header p {
  font-size: 14px;
  color: #666;
}

/* 移动端头部 */
@media (max-width: 480px) {
  .login-header {
    padding: 20px 20px 15px;
  }

  .login-header h1 {
    font-size: 20px;
  }

  .login-header p {
    font-size: 12px;
  }
}

/* 登录表单 */
.login-form {
  padding: 30px;
}

/* 移动端表单 */
@media (max-width: 480px) {
  .login-form {
    padding: 20px;
  }
}

/* 登录底部 */
.login-footer {
  padding: 15px 30px;
  border-top: 1px solid #ddd;
  background-color: #fafafa;
  text-align: center;
}

.login-footer p {
  font-size: 12px;
  color: #999;
}
</style>

