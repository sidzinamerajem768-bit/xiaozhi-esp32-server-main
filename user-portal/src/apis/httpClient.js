import axios from 'axios'

const client = axios.create({
  baseURL: '/xiaozhi',
  timeout: 30000,
  headers: { 'Accept-Language': 'zh-CN' }
})

function extractTokenValue(rawToken) {
  if (!rawToken) return null
  try {
    const parsed = JSON.parse(rawToken)
    if (parsed && parsed.token) return parsed.token
    if (parsed && parsed.code !== undefined) {
      console.error('[HTTP] 检测到坏token(是错误响应JSON)，自动清除:', rawToken.substring(0, 80))
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      window.location.href = '/user-portal/login'
      return null
    }
    return rawToken
  } catch {
    if (!rawToken.startsWith('{') && !rawToken.startsWith('[')) return rawToken
    console.error('[HTTP] 检测到坏token(无法解析的JSON)，自动清除:', rawToken.substring(0, 80))
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    window.location.href = '/user-portal/login'
    return null
  }
}

client.interceptors.request.use(config => {
  const rawToken = localStorage.getItem('token')
  const tokenValue = extractTokenValue(rawToken)
  if (tokenValue) {
    config.headers.Authorization = 'Bearer ' + tokenValue
    if (config.url !== '/user/info') {
      console.log('[HTTP]请求:', config.method?.toUpperCase(), config.url, '| token前20字符:', tokenValue.substring(0, 20))
    }
  }
  return config
})

client.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      console.error('[HTTP] 401未授权 URL:', err.config?.url)
      console.error('[HTTP] 当前localStorage[token]:', localStorage.getItem('token')?.substring(0, 100))
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      window.location.href = '/user-portal/login'
    }
    return Promise.reject(err)
  }
)

export default client
