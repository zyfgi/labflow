<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="query.status" clearable placeholder="状态" style="width: 140px" @change="load(1)">
        <el-option v-for="(label, key) in BORROW_STATUS_LABELS" :key="key" :label="label" :value="key" />
      </el-select>
      <el-checkbox v-model="query.mine" border @change="load(1)">只看我的</el-checkbox>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="设备" min-width="150">
        <template #default="{ row }">{{ row.equipment_name }}</template>
      </el-table-column>
      <el-table-column label="借用人" width="100">
        <template #default="{ row }">{{ row.borrower_name }}</template>
      </el-table-column>
      <el-table-column label="借出时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.borrow_time) }}</template>
      </el-table-column>
      <el-table-column label="应还时间" width="160">
        <template #default="{ row }">
          <span :style="row.is_overdue ? 'color:#f56c6c;font-weight:600' : ''">{{ formatDateTime(row.expected_return_time) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="归还时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.actual_return_time) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="row.is_overdue ? 'danger' : BORROW_STATUS_TAGS[row.status]">
            {{ row.is_overdue && row.status === 'borrowed' ? '已逾期' : BORROW_STATUS_LABELS[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'borrowed' || row.status === 'overdue'">
            <el-button link type="success" size="small" @click="doReturn(row)">归还</el-button>
            <el-button link size="small" @click="openExtend(row)">延期</el-button>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无借用记录" :image-size="70" />
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

    <!-- extend dialog: push the expected return time, no approval needed -->
    <el-dialog v-model="extend.visible" title="延期归还" width="420px">
      <el-form label-width="90px">
        <el-form-item label="设备">{{ extend.row?.equipment_name }}</el-form-item>
        <el-form-item label="当前应还">{{ formatDateTime(extend.row?.expected_return_time) }}</el-form-item>
        <el-form-item label="新应还时间">
          <el-date-picker
            v-model="extend.time"
            type="datetime"
            placeholder="选择新的归还时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="extend.visible = false">取消</el-button>
        <el-button type="primary" :disabled="!extend.time" @click="submitExtend">确认延期</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { extendBorrow, listBorrows, returnBorrow, type EquipmentBorrow } from '@/api/equipment'
import { BORROW_STATUS_LABELS, BORROW_STATUS_TAGS } from '@/utils/constants'
import { formatDateTime } from '@/utils/datetime'

const loading = ref(false)
const items = ref<EquipmentBorrow[]>([])
const total = ref(0)

const query = reactive({ page: 1, page_size: 20, status: '', mine: false })

const extend = reactive({
  visible: false,
  row: null as EquipmentBorrow | null,
  time: '',
})

function openExtend(row: EquipmentBorrow) {
  extend.row = row
  extend.time = ''
  extend.visible = true
}

async function submitExtend() {
  if (!extend.row || !extend.time) return
  await extendBorrow(extend.row.id, {
    expected_return_time: new Date(extend.time).toISOString().slice(0, 19),
  })
  ElMessage.success('归还时间已更新，设备管理员已收到通知')
  extend.visible = false
  await load()
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listBorrows({
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

async function doReturn(row: EquipmentBorrow) {
  await returnBorrow(row.id)
  ElMessage.success('已归还，设备管理员已收到通知')
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
