<template>
  <el-dialog v-model="visible" title="选择智能体预设" width="520px" :close-on-click-modal="false" destroy-on-close>
    <div class="preset-list" v-loading="loading">
      <div
        v-for="item in presets"
        :key="item.id"
        class="preset-item"
        :class="{ selected: selectedId === item.id }"
        @click="selectedId = item.id"
      >
        <div class="preset-info">
          <div class="preset-name">{{ item.name || item.agentName }}</div>
          <div class="preset-detail">
            <span v-if="item.llmModelName">LLM: {{ item.llmModelName }}</span>
            <span v-if="item.ttsModelName">TTS: {{ item.ttsModelName }}</span>
            <span v-if="item.mode">模式: {{ item.mode }}</span>
          </div>
        </div>
        <el-icon v-if="selectedId === item.id" color="#4f6ef7" size="20">
          <CircleCheckFilled />
        </el-icon>
      </div>

      <el-empty v-if="!loading && presets.length === 0" description="暂无可用智能体预设，请联系管理员发布" />
    </div>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!selectedId" @click="handleConfirm">
        确认选择
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { CircleCheckFilled } from '@element-plus/icons-vue'
import api from '../apis'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  deviceId: { type: [String, Number], default: null },
  agentId: { type: [String, Number], default: null }
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = ref(false)
const loading = ref(false)
const submitting = ref(false)
const presets = ref([])
const selectedId = ref(null)

watch(() => props.modelValue, async (val) => {
  visible.value = val
  if (val) {
    selectedId.value = props.agentId || null
    await loadPresets()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function handleCancel() {
  visible.value = false
}

async function loadPresets() {
  loading.value = true
  try {
    const res = await api.getPublishedTemplates()
    let rawList = res
    if (rawList && typeof rawList === 'object' && 'code' in rawList) {
      if (rawList.code === 0 || rawList.code === 'success') {
        rawList = rawList.data || []
      } else {
        console.warn('[SelectPreset] 模板接口返回错误:', rawList.msg || rawList.code)
        rawList = []
      }
    }
    presets.value = Array.isArray(rawList) ? rawList : []

    if (presets.value.length > 0) {
      selectedId.value = props.agentId || null
    }
  } catch (e) {
    console.warn('[SelectPreset] 加载智能体模板失败:', e.message || e)
    presets.value = []
  } finally {
    loading.value = false
  }
}

async function handleConfirm() {
  if (!selectedId.value) return

  submitting.value = true
  try {
    await api.bindDevice(selectedId.value, props.deviceId)
    ElMessage.success('智能体绑定成功')
    visible.value = false
    emit('success')
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || '绑定失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
.preset-list {
  max-height: 360px;
  overflow-y: auto;
}

.preset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid #e5e6eb;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 8px;

  &:hover {
    border-color: #4f6ef7;
    background: #eef1ff;
  }

  &.selected {
    border-color: #4f6ef7;
    background: #eef1ff;
  }
}

.preset-name {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
  margin-bottom: 4px;
}

.preset-detail {
  font-size: 12px;
  color: #86909c;

  span {
    margin-right: 12px;
  }
}
</style>
