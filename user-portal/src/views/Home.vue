<template>
  <div class="home-wrapper">
    <AppHeader />

    <el-main class="home-main">
      <div class="page-bar">
        <h2 class="page-title">我的设备</h2>
        <el-button type="primary" @click="showBindDialog = true">
          <el-icon style="margin-right: 6px;"><Plus /></el-icon>
          绑定新设备
        </el-button>
      </div>

      <!-- 调试信息（上线前可删除） -->
      <div v-if="debugInfo" class="debug-bar">
        <span>设备数: {{ debugInfo.deviceCount }}</span>
        <span v-if="debugInfo.method">接口: {{ debugInfo.method }}</span>
        <span v-if="debugInfo.hint" style="color:#ff4d4f">{{ debugInfo.hint }}</span>
        <el-button size="small" text @click="showDebug = !showDebug">{{ showDebug ? '隐藏详情' : '查看详情' }}</el-button>
      </div>
      <pre v-if="showDebug && debugRaw" class="debug-pre">{{ JSON.stringify(debugRaw, null, 2) }}</pre>

      <div class="device-grid" v-loading="loading">
        <DeviceCard
          v-for="device in devices"
          :key="device.device_id || device.id"
          :device="device"
          @select-preset="handleSelectPreset"
          @unbind="handleUnbind"
        />

        <el-empty v-if="!loading && devices.length === 0" description="暂无绑定设备，点击上方按钮绑定" />
      </div>
    </el-main>

    <BindDeviceDialog v-model="showBindDialog" :presets="presets" @success="loadDevices" />
    <SelectPresetDialog
      v-model="showPresetDialog"
      :device-id="currentDevice?.macAddress"
      :agent-id="currentAgentId"
      @success="loadDevices"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import AppHeader from '../components/AppHeader.vue'
import DeviceCard from '../components/DeviceCard.vue'
import BindDeviceDialog from '../components/BindDeviceDialog.vue'
import SelectPresetDialog from '../components/SelectPresetDialog.vue'
import api from '../apis'

const devices = ref([])
const presets = ref([])
const loading = ref(false)
const showBindDialog = ref(false)
const showPresetDialog = ref(false)
const currentDevice = ref(null)
const currentAgentId = ref(null)

// 调试用
const debugInfo = ref(null)
const debugRaw = ref(null)
const showDebug = ref(false)

onMounted(() => {
  loadDevices()
})

async function loadDevices() {
  loading.value = true
  debugInfo.value = null
  debugRaw.value = null

  try {
    // === 方式1：优先使用用户级设备接口 ===
    console.log('[用户端] 方式1: 尝试 /user/devices ...')
    try {
      const res = await api.getUserDevices()
      console.log('[用户端] /user/devices 原始返回:', res)

      debugRaw.value = { userDevicesResponse: res }

      let rawData = res
      if (rawData && typeof rawData === 'object' && 'code' in rawData) {
        rawData = rawData.data
      }
      if (Array.isArray(rawData) && rawData.length > 0) {
        const mapped = mapDeviceList(rawData, 'user/devices')
        devices.value = mapped
        debugInfo.value = { deviceCount: mapped.length, method: '/user/devices' }
        return
      }
      console.log('[用户端] /user/devices 返回空或非数组，继续...')
    } catch (e) {
      console.warn('[用户端] /user/devices 失败:', e.message || e)
      debugRaw.value = { userDevicesError: e.message || String(e) }
    }

    // === 方式2：通过智能体列表 + device/bind/{agentId} 获取设备（与管理端一致）===
    console.log('[用户端] 方式2: 尝试 /agent/list + GET /device/bind/{agentId} ...')
    try {
      const agentRes = await api.getAgentList()
      console.log('[用户端] /agent/list 原始返回:', agentRes)

      let rawAgents = agentRes
      if (rawAgents && typeof rawAgents === 'object' && 'code' in rawAgents) {
        rawAgents = rawAgents.data
      }
      const agents = Array.isArray(rawAgents) ? rawAgents : []

      console.log('[用户端] 智能体数量:', agents.length)

      if (!debugRaw.value) debugRaw.value = {}
      debugRaw.value.agentResponse = agentRes

      if (agents.length > 0) {
        const allDevices = []
        for (const agent of agents) {
          const aid = agent.id || agent.agentId
          if (!aid) continue

          try {
            const devRes = await api.getAgentBindDevices(aid)
            console.log(`[用户端] /device/bind/${aid} 返回:`, devRes)

            // 管理端响应格式: { code: 0, data: [{ id, board, appVersion, macAddress, createDate, lastConnectedAt, alias, autoUpdate }] }
            let devData = devRes
            if (devData && typeof devData === 'object' && 'code' in devData) {
              if (devData.code !== 0) continue
              devData = devData.data
            }

            const rawList = Array.isArray(devData) ? devData : []
            if (rawList.length > 0) {
              const mapped = rawList
                .filter(d => d != null)
                .map(d => ({
                  device_id: d.id,
                  model: d.board,
                  firmwareVersion: d.appVersion,
                  macAddress: d.macAddress,
                  bindTime: d.createDate,
                  lastConversation: d.lastConnectedAt,
                  remark: d.alias,
                  autoUpdate: d.autoUpdate === 1,
                  otaSwitch: d.autoUpdate === 1,
                  deviceStatus: 'offline',
                  agentName: agent.name || agent.agentName,
                  agentId: aid,
                  selected: false
                }))
              allDevices.push(...mapped)
            }
          } catch (devErr) {
            console.warn(`[用户端] /device/bind/${aid} 失败:`, devErr.message)
          }
        }

        if (allDevices.length > 0) {
          sortAndSet(allDevices)
          debugInfo.value = { deviceCount: allDevices.length, method: '/device/bind/{agentId}' }
          return
        }
        debugInfo.value = { deviceCount: 0, method: '/device/bind/{agentId}', hint: `智能体${agents.length}个但均无绑定设备` }
        return
      }
      debugInfo.value = { deviceCount: 0, method: 'none', hint: '/agent/list 返回空（普通用户无智能体列表权限）' }
    } catch (e) {
      console.warn('[用户端] agent方式失败:', e.message || e)
      debugRaw.value = { agentError: e.message || String(e) }
      devices.value = []
      debugInfo.value = { deviceCount: 0, method: 'none', hint: '所有API均未返回数据: ' + (e.message || e) }
    }
  } finally {
    loading.value = false
  }
}

function mapDeviceList(rawList, source) {
  return rawList.filter(d => d != null).map(d => ({
    device_id: d.id || d.device_id,
    model: d.model || d.board,
    firmwareVersion: d.firmwareVersion || d.appVersion,
    macAddress: d.macAddress || d.deviceCode,
    bindTime: d.createDate || d.bindTime,
    lastConversation: d.lastConnectedAt || d.lastConversation,
    remark: d.alias || d.remark || d.deviceName,
    autoUpdate: d.autoUpdate === 1,
    otaSwitch: d.autoUpdate === 1,
    deviceStatus: d.deviceStatus || 'offline',
    agentName: d.agentName || d.name,
    agentId: d.agentId || d.id,
    selected: false,
    _source: source
  }))
}

function sortAndSet(list) {
  list.sort((a, b) => {
    const tA = a.bindTime ? new Date(a.bindTime).getTime() : 0
    const tB = b.bindTime ? new Date(b.bindTime).getTime() : 0
    return tB - tA
  })
  devices.value = list
}

function handleSelectPreset(device) {
  currentDevice.value = device
  currentAgentId.value = device.agentId
  showPresetDialog.value = true
}

async function handleUnbind(device) {
  try {
    await ElMessageBox.confirm(
      `确定要解绑设备 "${device.macAddress || device.device_id}" 吗？`,
      '确认解绑',
      { type: 'warning' }
    )
    await api.unbindDevice(device.device_id || device.id)
    loadDevices()
  } catch {
    // cancelled
  }
}
</script>

<style lang="scss" scoped>
.home-wrapper {
  min-height: 100vh;
  background: #f7f8fa;
}

.home-main {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
}

.page-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1d2129;
  margin: 0;
}

.debug-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 12px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  font-size: 12px;
  color: #ad6800;
  margin-bottom: 16px;
}

.debug-pre {
  font-size: 11px;
  background: #f5f5f5;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 16px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  color: #666;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}
</style>