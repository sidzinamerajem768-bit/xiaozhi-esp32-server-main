import client from './httpClient'

export default {
  // 登录（后端路径：POST /user/login）
  login(username, password, captchaId) {
    return client.post('/user/login', { username, password, captchaId })
  },

  // 获取用户信息
  getUserInfo() {
    return client.get('/user/info')
  },

  // 获取当前用户所有设备
  getUserDevices() {
    return client.get('/user/devices')
  },

  // 获取已发布的智能体模板列表（普通用户可访问：GET /agent/template）
  getPublishedTemplates() {
    return client.get('/agent/template')
  },

  // 获取智能体列表（降级方案）
  getAgentList() {
    return client.get('/agent/list')
  },

  // 获取智能体下已绑定的设备列表（与管理端一致：GET /device/bind/{agentId}）
  getAgentBindDevices(agentId) {
    return client.get(`/device/bind/${agentId}`)
  },

  // 绑定设备到智能体
  bindDevice(agentId, deviceCode) {
    return client.post(`/device/bind/${agentId}/${deviceCode}`)
  },

  // 解绑设备
  unbindDevice(deviceId) {
    return client.post('/device/unbind', { deviceId })
  },

  // 获取图形验证码 (后端路径：GET /user/captcha?uuid=xxx)
  getCaptcha(captchaId) {
    return client.get(`/user/captcha?uuid=${captchaId}`, { responseType: 'blob' })
  },

  // 发送短信验证码
  sendSmsVerification(data) {
    return client.post('/user/smsVerification', data)
  },

  // 用户注册
  register(registerData) {
    return client.post('/user/register', registerData)
  },

  // 获取公共配置（SM2公钥等）
  getPubConfig() {
    return client.get('/user/pub-config')
  }
}
