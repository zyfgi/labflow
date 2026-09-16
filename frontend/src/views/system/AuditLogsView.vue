<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="query.action" clearable filterable placeholder="操作类型" style="width: 220px" @change="load(1)">
        <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="items" stripe size="small">
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作人" width="110">
        <template #default="{ row }">{{ row.user_name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource_type" label="资源类型" width="140" />
      <el-table-column prop="resource_id" label="资源ID" width="90" />
      <el-table-column label="详情" min-width="260">
        <template #default="{ row }">
          <code v-if="row.detail" style="font-size: 12px">{{ JSON.stringify(row.detail) }}</code>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP" width="130">
        <template #default="{ row }">{{ row.ip_address ?? '-' }}</template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无日志" :image-size="70" />
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
import { onMounted, reactive, ref } from 'vue'
import client from '@/api/client'
import { formatDateTime } from '@/utils/datetime'

const loading = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const actions = [
  'login', 'logout', 'create_user', 'change_role', 'create_project', 'update_project',
  'delete_project', 'create_experiment', 'update_experiment', 'lock_experiment',
  'unlock_experiment', 'create_equipment', 'update_equipment', 'approve_booking',
  'reject_booking', 'borrow_equipment', 'return_equipment', 'report_fault', 'export_data',
]

const query = reactive({ page: 1, page_size: 20, action: '' })

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await client.get('/audit-logs', {
      params: { page: query.page, page_size: query.page_size, action: query.action || undefined },
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<style scoped>
.toolbar {
  margin-bottom: 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
