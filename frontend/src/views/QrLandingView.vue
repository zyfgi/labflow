<template>
  <div class="qr-landing">
    <el-card v-loading="loading" shadow="never" class="qr-card">
      <template v-if="equipment">
        <el-result icon="success" :title="equipment.name" :sub-title="`资产编号 ${equipment.asset_no}`">
          <template #extra>
            <el-tag :type="EQUIPMENT_STATUS_TAGS[equipment.status]">
              {{ EQUIPMENT_STATUS_LABELS[equipment.status] }}
            </el-tag>
            <div style="margin-top: 16px; display: flex; gap: 10px; justify-content: center">
              <el-button type="primary" @click="$router.push(`/equipment/${equipment.equipment_id}`)">
                打开设备详情
              </el-button>
            </div>
            <p class="hint">进入后可直接预约 / 借用 / 上报故障</p>
          </template>
        </el-result>
      </template>
      <el-result v-else-if="!loading" icon="warning" title="二维码无效或已失效" sub-title="请联系设备管理员重新生成标签" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { resolveQr } from '@/api/equipment'
import { EQUIPMENT_STATUS_LABELS, EQUIPMENT_STATUS_TAGS } from '@/utils/constants'

const route = useRoute()
const loading = ref(true)
const equipment = ref<{ equipment_id: number; asset_no: string; name: string; status: string } | null>(null)

onMounted(async () => {
  try {
    const { data } = await resolveQr(String(route.params.token))
    equipment.value = data.data
  } catch {
    equipment.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.qr-landing {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  padding: 16px;
}

.qr-card {
  width: 100%;
  max-width: 420px;
}

.hint {
  color: #909399;
  font-size: 13px;
  margin-top: 10px;
}
</style>
