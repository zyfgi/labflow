<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="query.status" clearable placeholder="状态" style="width: 140px" @change="load(1)">
        <el-option v-for="(label, key) in MAINTENANCE_STATUS_LABELS" :key="key" :label="label" :value="key" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="设备" min-width="150">
        <template #default="{ row }">{{ row.equipment_name }}</template>
      </el-table-column>
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ MAINTENANCE_TYPE_LABELS[row.type] ?? row.type }}</template>
      </el-table-column>
      <el-table-column label="描述" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="上报人" width="100">
        <template #default="{ row }">{{ row.reporter_name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="上报时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.reported_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="MAINTENANCE_STATUS_TAGS[row.status]">{{ MAINTENANCE_STATUS_LABELS[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="处理方" width="110">
        <template #default="{ row }">{{ row.vendor ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <template v-if="canManage">
            <el-button
              v-if="row.status === 'reported'"
              link
              type="primary"
              size="small"
              @click="advance(row, 'processing')"
            >
              开始处理
            </el-button>
            <el-button
              v-if="row.status === 'processing'"
              link
              type="success"
              size="small"
              @click="complete(row)"
            >
              完成维修
            </el-button>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无维修记录" :image-size="70" />
      </template>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load()"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { listMaintenance, updateMaintenance, type EquipmentMaintenance } from '@/api/equipment'
import {
  MAINTENANCE_STATUS_LABELS,
  MAINTENANCE_STATUS_TAGS,
  MAINTENANCE_TYPE_LABELS,
} from '@/utils/constants'
import { formatDateTime } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canManage = computed(() => auth.isPI || auth.isEquipmentAdmin)
const loading = ref(false)
const items = ref<EquipmentMaintenance[]>([])
const total = ref(0)

const query = reactive({ page: 1, page_size: 20, status: '' })

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listMaintenance({
      page: query.page,
      page_size: query.page_size,
      status: query.status || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

async function advance(row: EquipmentMaintenance, status: string) {
  await updateMaintenance(row.id, { status })
  await load()
}

async function complete(row: EquipmentMaintenance) {
  const { value } = await ElMessageBox.prompt('维修结果', '完成维修', {
    inputType: 'textarea',
    confirmButtonText: '确认完成',
  }).catch(() => ({ value: undefined }))
  if (value === undefined) return
  await updateMaintenance(row.id, { status: 'completed', result: value || null })
  await load()
}

onMounted(() => load())
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
