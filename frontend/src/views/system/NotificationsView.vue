<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-checkbox v-model="unreadOnly" border @change="load(1)">只看未读</el-checkbox>
      <span></span>
      <el-button @click="markAll">全部已读</el-button>
    </div>

    <div v-loading="loading">
      <div
        v-for="n in items"
        :key="n.id"
        class="notice-row"
        :class="{ unread: !n.is_read }"
        @click="openNotice(n)"
      >
        <el-badge is-dot :hidden="n.is_read" type="danger">
          <el-tag size="small" :type="typeTag(n.type)">{{ typeLabel(n.type) }}</el-tag>
        </el-badge>
        <div class="notice-body">
          <div class="notice-title">{{ n.title }}</div>
          <div class="notice-content">{{ n.content }}</div>
        </div>
        <span class="notice-time">{{ formatDateTime(n.created_at) }}</span>
      </div>
      <el-empty v-if="!loading && !items.length" description="暂无通知" :image-size="80" />
    </div>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load()"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listNotifications, markRead, readAll, type AppNotification } from '@/api/system'
import { formatDateTime } from '@/utils/datetime'

const loading = ref(false)
const items = ref<AppNotification[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const unreadOnly = ref(false)

const TYPE_LABELS: Record<string, string> = {
  report_submitted: '周报',
  report_reviewed: '周报',
  report_returned: '周报',
  task_assigned: '任务',
  task_due_soon: '任务',
  task_overdue: '任务',
  booking_approved: '设备',
  booking_rejected: '设备',
  borrow_overdue: '设备',
  equipment_fault: '设备',
  project_added: '项目',
}

function typeLabel(type: string): string {
  return TYPE_LABELS[type] ?? '通知'
}

function typeTag(type: string): string {
  if (type.startsWith('task')) return 'primary'
  if (type.startsWith('report')) return 'success'
  if (type.startsWith('borrow') || type === 'equipment_fault' || type === 'booking_rejected') return 'danger'
  return 'info'
}

async function load(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const { data } = await listNotifications({
      page: page.value,
      page_size: pageSize,
      unread_only: unreadOnly.value || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

async function openNotice(n: AppNotification) {
  if (!n.is_read) {
    await markRead(n.id)
    n.is_read = true
  }
}

async function markAll() {
  await readAll()
  ElMessage.success('已全部标记为已读')
  await load()
}

onMounted(() => load())
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  justify-content: space-between;
}

.notice-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}

.notice-row.unread .notice-title {
  font-weight: 600;
}

.notice-row:hover {
  background: #f5f7fa;
}

.notice-body {
  flex: 1;
  min-width: 0;
}

.notice-title {
  font-size: 14px;
}

.notice-content {
  color: #909399;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notice-time {
  color: #c0c4cc;
  font-size: 12px;
  flex-shrink: 0;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
