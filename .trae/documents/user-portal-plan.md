# 用户端重构计划（修订版）

## 一、需求概述

创建一个**独立的用户端应用**（Vue 3 + Element Plus + Vite），与现有管理端分离部署：

* **用户端**（新）：设备绑定 → 选择已发布智能体预设 → 设备管理

* **管理端**（现有）：保持全部功能，仅移除普通用户的权限控制菜单

## 二、架构对比

| 特性   | 管理端（现有）            | 用户端（新建）                         |
| ---- | ------------------ | ------------------------------- |
| 框架   | Vue 2 + Element UI | **Vue 3 + Element Plus + Vite** |
| 状态管理 | Vuex               | **Pinia**                       |
| 路由   | Vue Router 3       | **Vue Router 4**                |
| 首页   | 智能体卡片列表            | 设备卡片列表                          |
| 核心操作 | 创建/编辑智能体           | 绑定设备 → 选预设 → 管理                 |
| 菜单   | 完整管理菜单             | 极简：我的设备                         |
| 定位   | 管理员后台              | 终端用户面板                          |

## 三、目录结构（平级）

```
xiaozhi-esp32-server-main/        # 项目根目录
├── manager-web/                  # 管理端 (Vue 2 + Element UI)
│   ├── src/                      # 保持不变
│   └── ...
│
├── user-portal/                  # 用户端 (Vue 3 + Element Plus + Vite) ★ 新建
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/index.js
│   │   ├── stores/               # Pinia stores
│   │   │   └── auth.js           # 登录态管理
│   │   ├── apis/
│   │   │   ├── httpClient.js     # axios 封装
│   │   │   └── index.js          # API 统一出口
│   │   ├── views/
│   │   │   ├── Login.vue         # 用户端登录页
│   │   │   └── Home.vue          # 用户端首页
│   │   ├── components/
│   │   │   ├── DeviceCard.vue
│   │   │   ├── BindDeviceDialog.vue
│   │   │   ├── SelectPresetDialog.vue
│   │   │   └── AppHeader.vue
│   │   └── styles/
│   │       └── global.scss
│
└── [backend]                     # 后端服务（共用 API）
```

两个前端项目**完全独立**：
- 各自独立的 `node_modules`、`package.json`、构建配置
- 各自独立启动/部署
- 通过访问**同一套后端 API** 共享数据（token、设备、智能体等）

## 四、管理端修改（现有 Vue 2 项目）

### 4.1 登录跳转 — `src/views/login.vue`

登录成功后根据 `userInfo.superAdmin` 判断：

```js
if (userInfo.superAdmin) {
  goToPage('/home')         // 管理端
} else {
  window.location.href = '/user-portal/'  // 重定向到用户端
}
```

### 4.2 HeaderBar — `src/components/HeaderBar.vue`

* 移除普通用户（`!userInfo.superAdmin`）的菜单项

* 只保留"智能管理"导航（对应原有的首页/角色配置/设备管理）

* 如果普通用户不应该登录管理端，可以直接在路由守卫中拦截

### 4.3 路由守卫 — `src/router/index.js`

在 `beforeEach` 中增加角色判断：

```js
if (to.meta.requiresAuth && !store.getters.isSuperAdmin) {
  // 普通用户重定向到用户端
  window.location.href = '/user-portal/'
  return
}
```

## 五、用户端详细设计（新建 Vue 3 项目）

### 5.1 构建配置 — `user-portal/vite.config.js`

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/user-portal/',   // 与管理端分离部署
  server: {
    port: 8081,
    proxy: {
      '/xiaozhi': 'http://localhost:8000'  // 代理后端 API
    }
  }
})
```

### 5.2 路由 — `user-portal/src/router/index.js`

```js
[
  { path: '/', redirect: '/home' },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/home', name: 'Home', component: () => import('../views/Home.vue'), meta: { requiresAuth: true } }
]
```

### 5.3 登录页 — `user-portal/src/views/Login.vue`

* 复用管理端相同的登录 API（`/xiaozhi/login`）

* 简化 UI：只保留用户名+密码登录

* 登录成功后将 token 存入 localStorage（与管理端共享 key 名）

* 同时存储 `userType` 标记为 `user`

### 5.4 首页 — `user-portal/src/views/Home.vue`

**布局**：

```
┌──────────────────────────────────────────────┐
│  Header: 星枢智联 | 用户名 | [退出]           │
├──────────────────────────────────────────────┤
│  我的设备                          [＋绑定设备]│
├──────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │ 📱 ESP32-001     │  │ 📱 ESP32-002     │   │
│  │ 智能体: 小助手    │  │ 智能体: 未绑定    │   │
│  │ 状态: 🟢 在线     │  │ 状态: 🔴 离线     │   │
│  │ [切换智能体]      │  │ [选择智能体]      │   │
│  │ [解绑]           │  │ [解绑]           │   │
│  └──────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────┘
```

**功能流程**：

1. **加载设备列表**：

   * 进入页面调用 `GET /xiaozhi/user/devices` 获取当前用户的所有设备

   * 如果后端没有此接口，降级方案：遍历所有 agents，调用 `getAgentBindDevices` 合并结果

2. **绑定新设备**（`BindDeviceDialog.vue`）：

   * 弹出对话框，输入设备码（MAC 地址或设备编码）

   * 调用 `POST /xiaozhi/device/bind/{agentId}/{deviceCode}`

   * 首次绑定时 agentId 可为空或默认值，绑好后再选预设

   * 或者：先选择预设 → 再输入设备码 → 同时绑定

3. **选择/切换智能体**（`SelectPresetDialog.vue`）：

   * 调用 `GET /xiaozhi/agent/template/list` 获取模板列表

   * 列表项展示：模板名 + 语言模型 + 语音模型

   * 用户单选 → 调用绑定 API 将设备关联到选中的 agent

4. **解绑设备**：

   * 调用 `POST /xiaozhi/device/unbind` 并传入 deviceId

   * 确认后刷新列表

### 5.5 Pinia Store — `user-portal/src/stores/auth.js`

```js
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null
  }),
  getters: {
    isLoggedIn: (state) => !!state.token
  },
  actions: {
    async login(username, password) { /* ... */ },
    logout() {
      localStorage.removeItem('token')
      this.token = ''
      this.userInfo = null
    }
  }
})
```

### 5.6 API 封装 — `user-portal/src/apis/httpClient.js`

使用 axios（或 fetch）封装：

```js
import axios from 'axios'

const client = axios.create({
  baseURL: '/xiaozhi',
  timeout: 30000,
  headers: { 'Accept-Language': 'zh-CN' }
})

client.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${JSON.parse(token).token}`
  return config
})

client.interceptors.response.use(
  res => res.data,
  err => Promise.reject(err)
)

export default client
```

### 5.7 组件清单

| 组件                       | Props            | 功能              |
| ------------------------ | ---------------- | --------------- |
| `AppHeader.vue`          | userInfo         | 顶部栏：logo、用户名、退出 |
| `DeviceCard.vue`         | device           | 设备信息卡片          |
| `BindDeviceDialog.vue`   | visible, agents  | 输入设备码绑定         |
| `SelectPresetDialog.vue` | visible, presets | 预设列表选择          |

## 六、数据流

```
用户登录 → 获取 token + userInfo → 存入 Pinia
  → 进入 Home → 加载设备列表
    → [绑定设备] → 输入设备码 + 选预设 → bindDevice()
    → [切换智能体] → 选新预设 → agentSwitch()
    → [解绑] → unbindDevice() → 刷新列表
```

## 七、后端 API 依赖

假设后端现有以下接口可直接复用：

| 接口                                         | 用途               |
| ------------------------------------------ | ---------------- |
| `POST /login`                              | 用户登录             |
| `GET /agent/template/list`                 | 获取已发布的智能体模板列表    |
| `GET /agent/list`                          | 获取智能体列表（降级方案）    |
| `POST /device/bind/{agentId}/{deviceCode}` | 绑定设备到智能体         |
| `POST /device/unbind`                      | 解绑设备             |
| `GET /device/bind/{agentId}`               | 获取指定智能体下的设备列表    |
| `GET /user/devices`                        | 获取当前用户所有设备（如需新增） |

## 八、实施步骤

1. 创建 `user-portal/` 目录，初始化 Vue 3 + Element Plus + Vite 项目
2. 创建 Pinia store（auth.js）
3. 创建 API 封装层
4. 创建登录页
5. 创建首页 + 设备卡片组件
6. 创建绑定设备弹窗
7. 创建选择预设弹窗
8. 修改管理端：登录后按角色跳转、HeaderBar 简化
9. 联调测试

## 九、验证

* 普通用户登录管理端 → 自动跳转到用户端

* 普通用户直接访问用户端登录 → 正常进入用户端

* 管理员登录管理端 → 正常进入管理端

* 用户端：绑定设备 → 选预设 → 解绑 全流程正常

