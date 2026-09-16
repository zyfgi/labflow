<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="query.status" clearable placeholder="状态" style="width: 140px" @change="load(1)">
        <el-option v-for="(label, key) in BOOKING_STATUS_LABELS" :key="key" :label="label" :value="key" />
      </el-select>
      <el-checkbox v-model="query.mine" border @change="load(1)">只看我的</el-checkbox>
      <ExportButton kind="equipment-bookings" />
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="设备" min-width="150">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/equipment/${row.equipment_id}`)">{{ row.equipment_name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column label="预约人" width="100">
        <template #default="{ row }">{{ row.user_name }}</template>
      </el-table-column>
      <el-table-column label="时间" min-width="240">
        <template #default="{ row }">{{ formatDateTime(row.start_time) }} ~ {{ formatDateTime(row.end_time) }}</template>
      </el-table-column>
      <el-table-column label="用途" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.purpose ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="BOOKING_STATUS_TAGS[row.status]">{{ BOOKING_STATUS_LABELS[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <template v-if="canApprove && row.status === 'pending'">
            <el-button link type="success" size="small" @click="act(row, 'approve')">批准</el-button>
            <el-button link type="danger" size="small" @click="act(row, 'reject')">拒绝</el-button>
          </template>
          <el-button
            v-if="row.status === 'pending' || row.status === 'approved'"
            link
            size="small"
            @click="act(row, 'cancel')"
          >
            取消
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无预约" :image-size="70" />
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
import { bookingAction, listBookings, type EquipmentBooking } from '@/api/equipment'
import { BOOKING_STATUS_LABELS, BOOKING_STATUS_TAGS } from '@/utils/constants'
import ExportButton from '@/components/ExportButton.vue'
import { formatDateTime } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canApprove = computed(() => auth.isPI || auth.isEquipmentAdmin)
const loading = ref(false)
const items = ref<EquipmentBooking[]>([])
const total = ref(0)

const query = reactive({ page: 1, page_size: 20, status: '', mine: false })

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listBookings({
      page: query.page,
      page_size: query.page_size,
      status: query.status || undefined,
      mine: query.mine || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

async function act(row: EquipmentBooking, action: 'approve' | 'reject' | 'cancel') {
  await bookingAction(row.id, action)
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
