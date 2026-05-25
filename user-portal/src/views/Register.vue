<template>
  <div class="register-wrapper">
    <div class="register-card">
      <div class="register-header">
        <h1 class="register-title">星枢智联</h1>
        <p class="register-subtitle">用户注册</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleRegister">
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
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请确认密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item prop="captcha">
          <div class="captcha-row">
            <el-input
              v-model="form.captcha"
              placeholder="图形验证码"
              clearable
            />
            <img v-if="captchaUrl" :src="captchaUrl" alt="验证码" class="captcha-img" @click="refreshCaptcha" />
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" class="register-btn" @click="handleRegister">
            {{ loading ? '注册中...' : '注 册' }}
          </el-button>
        </el-form-item>
      </el-form>

      <p class="register-error" v-if="errorMsg">{{ errorMsg }}</p>

      <div class="login-link">
        已有账号？
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../apis'
import { sm2Encrypt } from '../utils/crypto'

const router = useRouter()

const loading = ref(false)
const errorMsg = ref('')
const formRef = ref(null)
const captchaUrl = ref('')
const sm2PublicKey = ref('')

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  captcha: '',
  captchaId: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
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
    // 如果没有 pub config API，使用默认公钥或降级处理
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
    // 使用 fetch 直接获取验证码图片，避免 axios 拦截器干扰
    const response = await fetch(`/xiaozhi/user/captcha?uuid=${form.captchaId}`)
    if (!response.ok) throw new Error('验证码加载失败')
    const blob = await response.blob()
    captchaUrl.value = URL.createObjectURL(blob)
  } catch {
    captchaUrl.value = ''
  }
}

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''

  try {
    // SM2 加密密码
    let encryptedPassword
    if (sm2PublicKey.value) {
      const captchaAndPassword = form.captcha + form.password
      encryptedPassword = sm2Encrypt(sm2PublicKey.value, captchaAndPassword)
    } else {
      // 如果没有 SM2 公钥，使用明文（后端可能不需要加密）
      encryptedPassword = form.password
    }

    const registerData = {
      username: form.username,
      password: encryptedPassword,
      captchaId: form.captchaId
    }

    await api.register(registerData)
    ElMessage.success('注册成功，请登录')
    router.replace('/login')
  } catch (err) {
    errorMsg.value = err.response?.data?.msg || err.message || '注册失败，请重试'
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.register-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f3ff 0%, #f5f0ff 100%);
}

.register-card {
  width: 420px;
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.register-header {
  text-align: center;
  margin-bottom: 32px;
}

.register-title {
  font-size: 28px;
  font-weight: 700;
  color: #4f6ef7;
  margin: 0 0 8px 0;
}

.register-subtitle {
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

.register-btn {
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

.register-error {
  text-align: center;
  color: #ff4d4f;
  font-size: 13px;
  margin: 0 0 16px 0;
}

.login-link {
  text-align: center;
  font-size: 14px;
  color: #86909c;

  a {
    color: #4f6ef7;
    text-decoration: none;
  }
}
</style>