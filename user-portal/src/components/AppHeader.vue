<template>
  <el-header class="app-header">
    <div class="header-left">
      <img src="@/assets/logo.png" alt="logo" class="logo-img" />
      <h1 class="brand">星枢智联</h1>
      <span class="brand-tag">用户端</span>
    </div>
    <div class="header-right">
      <span class="username">{{ authStore.username }}</span>
      <el-button type="danger" size="small" plain @click="handleLogout">退出</el-button>
    </div>
  </el-header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.replace('/login')
}
</script>

<style lang="scss" scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #e5e6eb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-img {
  width: 36px;
  height: 36px;
}

.brand {
  font-size: 20px;
  font-weight: 700;
  color: #4f6ef7;
  margin: 0;
}

.brand-tag {
  font-size: 12px;
  color: #86909c;
  background: #f2f3f5;
  padding: 2px 8px;
  border-radius: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.username {
  font-size: 14px;
  color: #4e5969;
  font-weight: 500;
}
</style>