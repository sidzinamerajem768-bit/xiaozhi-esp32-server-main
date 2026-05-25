/**
 * 现代 Promise-based HTTP 客户端
 * 基于 flyio，提供 async/await 风格的 API
 */
import Fly from 'flyio/dist/npm/fly'
import store from '../store/index'
import Constant from '../utils/constant'
import { goToPage, showDanger } from '../utils/index'

const fly = new Fly()
fly.config.timeout = 30000

// --- 请求 / 响应拦截器 ---

fly.interceptors.request.use((config) => {
  // 语言头
  config.headers['Accept-Language'] = 'zh-CN'

  // Token
  const token = store.getters.getToken
  if (token) {
    try {
      config.headers['Authorization'] = 'Bearer ' + JSON.parse(token).token
    } catch {
      // ignore
    }
  }
  return config
})

fly.interceptors.response.use(
  (response) => {
    const { data, status } = response
    if (status === 200) {
      if (data.code === 'success' || data.code === 0 || data.code === undefined) {
        return response
      }
      if (data.code === 401) {
        store.commit('clearAuth')
        goToPage(Constant.PAGE.LOGIN, true)
        return Promise.reject(new Error('Unauthorized'))
      }
      // 业务错误
      return Promise.reject(new Error(data.msg || '请求失败'))
    }
    return Promise.reject(new Error(`网络错误 [${status}]`))
  },
  (error) => {
    return Promise.reject(error)
  }
)

// --- 导出简洁 API ---

const httpClient = {
  get(url, params) {
    return fly.get(url, params).then(res => res.data)
  },

  post(url, data) {
    return fly.post(url, data).then(res => res.data)
  },

  put(url, data) {
    return fly.put(url, data).then(res => res.data)
  },

  delete(url) {
    return fly.delete(url).then(res => res.data)
  },

  /**
   * 通用请求
   */
  request({ url, method = 'GET', data, headers, responseType } = {}) {
    return fly.request(url, data, { method, headers, responseType }).then(res => res.data)
  }
}

export default httpClient