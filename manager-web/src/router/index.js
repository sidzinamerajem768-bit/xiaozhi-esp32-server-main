import Vue from 'vue'
import VueRouter from 'vue-router'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'welcome',
    meta: { title: '登录' },
    component: () => import(/* webpackChunkName: "auth" */ '../views/login.vue')
  },
  {
    path: '/login',
    name: 'login',
    meta: { title: '登录' },
    component: () => import(/* webpackChunkName: "auth" */ '../views/login.vue')
  },
  {
    path: '/register',
    name: 'Register',
    meta: { title: '注册' },
    component: () => import(/* webpackChunkName: "auth" */ '../views/register.vue')
  },
  {
    path: '/retrieve-password',
    name: 'RetrievePassword',
    meta: { title: '找回密码' },
    component: () => import(/* webpackChunkName: "auth" */ '../views/retrievePassword.vue')
  },

  // ===== 需要登录的路由 =====
  {
    path: '/home',
    name: 'home',
    meta: { requiresAuth: true, title: '首页' },
    component: () => import(/* webpackChunkName: "home" */ '../views/home.vue')
  },
  {
    path: '/role-config',
    name: 'RoleConfig',
    meta: { requiresAuth: true, title: '角色配置' },
    component: () => import(/* webpackChunkName: "agent" */ '../views/roleConfig.vue')
  },
  {
    path: '/voice-print',
    name: 'VoicePrint',
    meta: { requiresAuth: true, title: '声纹管理' },
    component: () => import(/* webpackChunkName: "agent" */ '../views/VoicePrint.vue')
  },
  {
    path: '/device-management',
    name: 'DeviceManagement',
    meta: { requiresAuth: true, title: '设备管理' },
    component: () => import(/* webpackChunkName: "device" */ '../views/DeviceManagement.vue')
  },
  {
    path: '/user-management',
    name: 'UserManagement',
    meta: { requiresAuth: true, title: '用户管理' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/UserManagement.vue')
  },
  {
    path: '/model-config',
    name: 'ModelConfig',
    meta: { requiresAuth: true, title: '模型配置' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/ModelConfig.vue')
  },
  {
    path: '/params-management',
    name: 'ParamsManagement',
    meta: { requiresAuth: true, title: '参数管理' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/ParamsManagement.vue')
  },
  {
    path: '/dict-management',
    name: 'DictManagement',
    meta: { requiresAuth: true, title: '字典管理' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/DictManagement.vue')
  },
  {
    path: '/provider-management',
    name: 'ProviderManagement',
    meta: { requiresAuth: true, title: '提供商管理' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/ProviderManagement.vue')
  },
  {
    path: '/knowledge-base-management',
    name: 'KnowledgeBaseManagement',
    meta: { requiresAuth: true, title: '知识库管理' },
    component: () => import(/* webpackChunkName: "knowledge" */ '../views/KnowledgeBaseManagement.vue')
  },
  {
    path: '/knowledge-file-upload',
    name: 'KnowledgeFileUpload',
    meta: { requiresAuth: true, title: '文档上传管理' },
    component: () => import(/* webpackChunkName: "knowledge" */ '../views/KnowledgeFileUpload.vue')
  },
  {
    path: '/server-side-management',
    name: 'ServerSideManager',
    meta: { requiresAuth: true, title: '服务端管理' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/ServerSideManager.vue')
  },
  {
    path: '/ota-management',
    name: 'OtaManagement',
    meta: { requiresAuth: true, title: 'OTA管理' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/OtaManagement.vue')
  },
  {
    path: '/voice-resource-management',
    name: 'VoiceResourceManagement',
    meta: { requiresAuth: true, title: '音色资源开通' },
    component: () => import(/* webpackChunkName: "voice" */ '../views/VoiceResourceManagement.vue')
  },
  {
    path: '/voice-clone-management',
    name: 'VoiceCloneManagement',
    meta: { requiresAuth: true, title: '音色克隆管理' },
    component: () => import(/* webpackChunkName: "voice" */ '../views/VoiceCloneManagement.vue')
  },
  {
    path: '/agent-template-management',
    name: 'AgentTemplateManagement',
    meta: { requiresAuth: true, title: '智能体模板管理' },
    component: () => import(/* webpackChunkName: "agent" */ '../views/AgentTemplateManagement.vue')
  },
  {
    path: '/template-quick-config',
    name: 'TemplateQuickConfig',
    meta: { requiresAuth: true, title: '模板快速配置' },
    component: () => import(/* webpackChunkName: "agent" */ '../views/TemplateQuickConfig.vue')
  },
  {
    path: '/feature-management',
    name: 'FeatureManagement',
    meta: { requiresAuth: true, title: '功能配置' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/FeatureManagement.vue')
  },
  {
    path: '/replacement-word-management',
    name: 'ReplacementWordManagement',
    meta: { requiresAuth: true, title: '替换词管理' },
    component: () => import(/* webpackChunkName: "admin" */ '../views/ReplacementWordManagement.vue')
  }
]

const router = new VueRouter({
  base: process.env.VUE_APP_PUBLIC_PATH || '/',
  routes
})

// 处理重复导航
const originalPush = VueRouter.prototype.push
VueRouter.prototype.push = function push(location) {
  return originalPush.call(this, location).catch(err => {
    if (err.name === 'NavigationDuplicated') {
      window.location.reload()
    } else {
      throw err
    }
  })
}

// 路由守卫：基于 meta.requiresAuth 进行鉴权
router.beforeEach((to, from, next) => {
  if (to.meta && to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      return next({ name: 'login', query: { redirect: to.fullPath } })
    }
  }
  next()
})

export default router