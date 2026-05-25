import { defineStore } from 'pinia'
import api from '../apis'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null')
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.username || ''
  },
  actions: {
    async login(username, password, captchaId) {
      const res = await api.login(username, password, captchaId)
      const data = res.data || res

      if (!data || !data.token) {
        throw new Error('登录响应无token: ' + JSON.stringify(res))
      }

      const tokenObj = JSON.stringify(data)
      console.log('[Auth] 登录成功, 存储token:', tokenObj)

      localStorage.setItem('token', tokenObj)
      this.token = tokenObj

      let userInfo = null
      try {
        const userRes = await api.getUserInfo()
        userInfo = userRes.data || userRes || {}
      } catch {
        userInfo = { username }
      }

      localStorage.setItem('userInfo', JSON.stringify(userInfo))
      this.userInfo = userInfo

      return userInfo
    },

    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      this.token = ''
      this.userInfo = null
    }
  }
})
