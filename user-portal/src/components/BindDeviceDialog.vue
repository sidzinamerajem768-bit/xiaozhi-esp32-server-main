<template>
  <el-dialog v-model="visible" title="绑定新设备" width="420px" :close-on-click-modal="false" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="设备编码" prop="deviceCode">
        <el-input v-model="form.deviceCode" placeholder="请输入设备编码（MAC地址或设备SN）" clearable />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleBind">确认绑定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import api from '../apis'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  presets: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = ref(false)
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  deviceCode: ''
})

const rules = {
  deviceCode: [{ required: true, message: '请输入设备编码', trigger: 'blur' }]
}

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    form.deviceCode = ''
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

async function handleBind() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    // 使用默认 agent 或第一个预设进行绑定
    const agentId = props.presets[0]?.id || 0
    await api.bindDevice(agentId, form.deviceCode)
    ElMessage.success('设备绑定成功')
    visible.value = false
    emit('success')
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || '绑定失败，请检查设备编码')
  } finally {
    loading.value = false
  }
}
</script>