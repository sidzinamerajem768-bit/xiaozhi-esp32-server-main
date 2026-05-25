<template>
  <div class="device-card">
    <div class="card-top">
      <div class="device-name">
        <el-icon class="device-icon"><Monitor /></el-icon>
        {{ device.macAddress || '未知设备' }}
      </div>
      <el-tag :type="device.deviceStatus === 'online' ? 'success' : 'info'" size="small" effect="light">
        {{ device.deviceStatus === 'online' ? '在线' : '离线' }}
      </el-tag>
    </div>

    <div class="card-body">
      <div class="info-row">
        <span class="info-label">型号</span>
        <span class="info-value">{{ device.model || '-' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">固件版本</span>
        <span class="info-value">{{ device.firmwareVersion || '-' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">绑定智能体</span>
        <span class="info-value agent-name">{{ device.agentName || '未绑定' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">绑定时间</span>
        <span class="info-value">{{ formatTime(device.bindTime) }}</span>
      </div>
      <div class="info-row" v-if="device.lastConversation">
        <span class="info-label">最后连接</span>
        <span class="info-value">{{ formatRelative(device.lastConversation) }}</span>
      </div>
      <div class="info-row" v-if="device.remark">
        <span class="info-label">备注</span>
        <span class="info-value remark-text">{{ device.remark }}</span>
      </div>
    </div>

    <div class="card-actions">
      <el-button type="primary" size="small" @click="$emit('select-preset', device)">
        {{ device.agentName ? '切换智能体' : '选择智能体' }}
      </el-button>
      <el-button type="danger" size="small" plain @click="$emit('unbind', device)">
        解绑
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { Monitor } from '@element-plus/icons-vue'

defineProps({
  device: { type: Object, required: true }
})

defineEmits(['select-preset', 'unbind'])

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

function formatRelative(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const now = new Date()
  const diffMin = Math.floor((now - d) / 60000)

  if (diffMin <= 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}小时前`
  if (diffMin < 43200) return `${Math.floor(diffMin / 1440)}天前`
  return formatTime(dateStr)
}
</script>

<style lang="scss" scoped>
.device-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  }
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.device-name {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
  display: flex;
  align-items: center;
  gap: 6px;
}

.device-icon {
  color: #4f6ef7;
}

.card-body {
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 13px;
}

.info-label {
  color: #86909c;
  flex-shrink: 0;
}

.info-value {
  color: #4e5969;
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}

.agent-name {
  color: #4f6ef7;
}

.remark-text {
  color: #86909c;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  gap: 8px;
}
</style>