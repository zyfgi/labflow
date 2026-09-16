<template>
  <div class="home">
    <h1>LabFlow — 高校科研实验室管理系统</h1>
    <p>后端健康状态：<el-tag :type="health.status === 'ok' ? 'success' : 'danger'">{{ healthText }}</el-tag></p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const health = ref<{ status?: string; app?: string; env?: string }>({})

const healthText = computed(() => health.value.status ?? '检查中...')

onMounted(async () => {
  try {
    const res = await axios.get('/api/health')
    health.value = res.data
  } catch {
    health.value = { status: 'unreachable' }
  }
})
</script>

<style scoped>
.home {
  max-width: 1600px;
  margin: 80px auto;
  text-align: center;
}
</style>
