<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">星枢智联</h1>
        <p class="login-subtitle">用户端登录</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            clearable
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item prop="captcha">
          <div class="captcha-row">
            <el-input
              v-model="form.captcha"
              placeholder="图形验证码"
              clearable
              @keyup.enter="handleLogin"
            />
            <img v-if="captchaUrl" :src="captchaUrl" alt="验证码" class="captcha-img" @click="refreshCaptcha" />
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" class="login-btn" @click="handleLogin">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <p class="login-error" v-if="errorMsg">{{ errorMsg }}</p>

      <div class="register-link">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../apis'
import { sm2Encrypt } from '../utils/crypto'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const errorMsg = ref('')
const formRef = ref(null)
const captchaUrl = ref('')
const sm2PublicKey = ref('')

const form = reactive({
  username: '',
  password: '',
  captcha: '',
  captchaId: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
}

onMounted(async () => {
  await fetchPubConfig()
  refreshCaptcha()
})

async function fetchPubConfig() {
  try {
    const res = await api.getPubConfig()
    const data = res.data || res
    sm2PublicKey.value = data.sm2PublicKey || ''
  } catch {
    // ignore
  }
}

function getUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    return (c === 'x' ? (Math.random() * 16 | 0) : ('r&0x3' | '0x8')).toString(16)
  })
}

async function refreshCaptcha() {
  form.captchaId = getUUID()
  try {
    const response = await fetch(`/xiaozhi/user/captcha?uuid=${form.captchaId}`)
    if (!response.ok) throw new Error('验证码加载失败')
    const blob = await response.blob()
    captchaUrl.value = URL.createObjectURL(blob)
  } catch {
    captchaUrl.value = ''
  }
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''

  try {
    let encryptedPassword
    if (sm2PublicKey.value) {
      const captchaAndPassword = form.captcha + form.password
      encryptedPassword = sm2Encrypt(sm2PublicKey.value, captchaAndPassword)
    } else {
      encryptedPassword = form.password
    }

    await authStore.login(form.username, encryptedPassword, form.captchaId)
    router.replace('/home')
  } catch (err) {
    errorMsg.value = err.response?.data?.msg || err.message || '登录失败，请重试'
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f3ff 0%, #f5f0ff 100%);
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: #4f6ef7;
  margin: 0 0 8px 0;
}

.login-subtitle {
  font-size: 14px;
  color: #86909c;
  margin: 0;
}

.captcha-row {
  display: flex;
  gap: 12px;
  width: 100%;
  align-items: center;
}

.captcha-img {
  height: 40px;
  width: 120px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid #e5e6eb;
  flex-shrink: 0;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4f6ef7 0%, #7b93fa 100%);
  border: none;

  &:hover {
    opacity: 0.9;
  }
}

.login-error {
  text-align: center;
  color: #ff4d4f;
  font-size: 13px;
  margin: 0 0 16px 0;
}

.register-link {
  text-align: center;
  font-size: 14px;
  color: #86909c;

  a {
    color: #4f6ef7;
    text-decoration: none;
  }
}
</style>
