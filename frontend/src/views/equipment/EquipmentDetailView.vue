<template>
  <div v-if="eq">
    <el-page-header style="margin-bottom: 12px" @back="$router.back()">
      <template #content>
        <span style="font-weight: 600">{{ eq.name }}</span>
        <el-tag size="small" style="margin-left: 8px" :type="EQUIPMENT_STATUS_TAGS[eq.status]">
          {{ EQUIPMENT_STATUS_LABELS[eq.status] }}
        </el-tag>
      </template>
      <template #extra>
        <el-button v-if="canManage" size="small" @click="ensureQr">{{ eq.qr_token ? '重新生成二维码' : '生成二维码' }}</el-button>
        <template v-if="eq.qr_token">
          <el-button size="small" @click="showQr = true">显示二维码</el-button>
          <el-button size="small" type="primary" plain @click="downloadQr">下载二维码 PNG</el-button>
        </template>
      </template>
    </el-page-header>

    <el-row :gutter="16">
      <el-col :md="10" :xs="24">
        <el-card shadow="never">
          <template #header>设备信息</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="资产编号">{{ eq.asset_no }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ eq.category }}</el-descriptions-item>
            <el-descriptions-item label="厂商/型号">{{ eq.manufacturer ?? '-' }} {{ eq.model ?? '' }}</el-descriptions-item>
            <el-descriptions-item label="当前位置">{{ eq.location ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="设备管理员">{{ eq.manager_name ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag size="small" :type="EQUIPMENT_STATUS_TAGS[eq.status]">{{ EQUIPMENT_STATUS_LABELS[eq.status] }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="当前使用">
              <span v-if="eq.current_booking">
                {{ formatDateTime(eq.current_booking.start_time) }} ~
                {{ formatDateTime(eq.current_booking.end_time).slice(11) }}
                （{{ eq.current_booking.user_name }}）
              </span>
              <span v-else style="color: #909399">空闲</span>
            </el-descriptions-item>
            <el-descriptions-item label="下一次预约">
              <span v-if="eq.next_booking">
                {{ formatDateTime(eq.next_booking.start_time) }} ~
                {{ formatDateTime(eq.next_booking.end_time).slice(11) }}
                （{{ eq.next_booking.user_name }}）
              </span>
              <span v-else style="color: #909399">暂无</span>
            </el-descriptions-item>
            <el-descriptions-item label="最近维护">
              <span v-if="eq.latest_maintenance">
                {{ MAINTENANCE_TYPE_LABELS[eq.latest_maintenance.type] }}
                · {{ MAINTENANCE_STATUS_LABELS[eq.latest_maintenance.status] }}
                · {{ formatDate(eq.latest_maintenance.reported_at) }}
              </span>
              <span v-else style="color: #909399">无记录</span>
            </el-descriptions-item>
            <el-descriptions-item label="描述">{{ eq.description ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :md="14" :xs="24">
        <el-card shadow="never">
          <template #header>
            <div class="head-row">
              <b>预约记录</b>
              <el-button size="small" type="primary" @click="book.visible = true">预约设备</el-button>
            </div>
          </template>
          <el-table v-loading="bookingsLoading" :data="bookings" size="small" stripe>
            <el-table-column label="时间" min-width="200">
              <template #default="{ row }">
                {{ formatDateTime(row.start_time) }} ~ {{ formatDateTime(row.end_time) }}
              </template>
            </el-table-column>
            <el-table-column label="预约人" width="90">
              <template #default="{ row }">{{ row.user_name }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="BOOKING_STATUS_TAGS[row.status]">{{ BOOKING_STATUS_LABELS[row.status] }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'reserved' && (row.user_id === auth.user?.id || canManage)"
                  link
                  size="small"
                  @click="cancel(row)"
                >
                  取消
                </el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无预约" :image-size="60" /></template>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="book.visible" title="预约设备" width="460px">
      <el-form label-width="80px">
        <el-form-item label="开始时间" required>
          <el-date-picker v-model="book.start" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" required>
          <el-date-picker v-model="book.end" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用途">
          <el-input v-model="book.purpose" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="book.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBooking">预约</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showQr" title="设备二维码" width="340px" align-center>
      <div style="text-align: center">
        <img v-if="qrDataUrl" :src="qrDataUrl" alt="设备二维码" style="width: 260px; height: 260px" />
        <p style="color: #909399; font-size: 13px">扫码直达设备详情页<br />{{ qrTarget }}</p>
        <p v-if="!eq.qr_url" style="color: #e6a23c; font-size: 12px">
          未配置 PUBLIC_BASE_URL，当前二维码为站内路径，仅本系统页面可解析
        </p>
      </div>
    </el-dialog>
  </div>
  <el-empty v-else-if="!loading" description="设备不存在" />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import QRCode from 'qrcode'
import {
  cancelBooking,
  createBooking,
  generateQr,
  getEquipment,
  listBookings,
  type Equipment,
  type EquipmentBooking,
} from '@/api/equipment'
import {
  BOOKING_STATUS_LABELS,
  BOOKING_STATUS_TAGS,
  EQUIPMENT_STATUS_LABELS,
  EQUIPMENT_STATUS_TAGS,
  MAINTENANCE_STATUS_LABELS,
  MAINTENANCE_TYPE_LABELS,
} from '@/utils/constants'
import { formatDate, formatDateTime } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const eqId = computed(() => Number(route.params.id))
const canManage = computed(() => auth.isPI || auth.isEquipmentAdmin)

const loading = ref(true)
const eq = ref<Equipment | null>(null)
const bookings = ref<EquipmentBooking[]>([])
const bookingsLoading = ref(false)

const showQr = ref(false)
const qrDataUrl = ref('')
const qrTarget = ref('')

const book = reactive({ visible: false, start: '', end: '', purpose: '' })

async function renderQr() {
  if (!eq.value) return
  // printable tag uses the server token URL when PUBLIC_BASE_URL is set,
  // otherwise the in-app route (still resolvable after login)
  qrTarget.value = eq.value.qr_url ?? `${window.location.origin}/equipment/${eqId.value}`
  qrDataUrl.value = await QRCode.toDataURL(qrTarget.value, { width: 320, margin: 1 })
}

async function load() {
  loading.value = true
  try {
    const { data } = await getEquipment(eqId.value)
    eq.value = data.data
    await renderQr()
    bookingsLoading.value = true
    try {
      const res = await listBookings({ equipment_id: eqId.value, page_size: 50 })
      bookings.value = res.data.data.items
    } finally {
      bookingsLoading.value = false
    }
  } catch {
    eq.value = null
  } finally {
    loading.value = false
  }
}

async function ensureQr() {
  const rotating = Boolean(eq.value?.qr_token)
  if (rotating) {
    await ElMessageBox.confirm(
      '重新生成后旧二维码标签将立即失效，已打印的旧标签作废。继续？',
      '重新生成二维码',
      { type: 'warning', confirmButtonText: '重新生成', cancelButtonText: '取消' },
    )
  }
  await generateQr(eqId.value, rotating)
  ElMessage.success(rotating ? '已生成新二维码，旧标签已失效' : '二维码已生成')
  await load()
}

function downloadQr() {
  const link = document.createElement('a')
  link.download = `qrcode-${eq.value?.asset_no ?? eqId.value}.png`
  link.href = qrDataUrl.value
  link.click()
  ElMessage.success('二维码已下载，可打印后贴在设备上')
}

async function cancel(row: EquipmentBooking) {
  await cancelBooking(row.id)
  ElMessage.success('预约已取消，相关人员已收到通知')
  await load()
}

async function submitBooking() {
  if (!book.start || !book.end) {
    ElMessage.warning('请选择预约时间')
    return
  }
  await createBooking({
    equipment_id: eqId.value,
    start_time: book.start,
    end_time: book.end,
    purpose: book.purpose || null,
  })
  ElMessage.success('预约成功，已生效（设备管理员已收到通知）')
  book.visible = false
  await load()
}

watch(eqId, load)
onMounted(load)
</script>

<style scoped>
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
