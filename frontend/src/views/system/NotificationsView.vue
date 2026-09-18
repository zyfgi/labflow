<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-checkbox v-model="unreadOnly" border @change="load(1)">只看未读</el-checkbox>
        <el-select v-model="typeFilter" clearable placeholder="按类型筛选" style="width: 140px" @change="load(1)">
          <el-option v-for="g in NOTIFICATION_GROUPS" :key="g.label" :label="g.label" :value="g.types[0]">
            {{ g.label }}
          </el-option>
        </el-select>
      </div>
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listNotifications, markRead, readAll, type AppNotification } from '@/api/system'
import { NOTIFICATION_GROUPS, NOTIFICATION_TYPE_LABELS } from '@/utils/constants'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()
const loading = ref(false)
const items = ref<AppNotification[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const unreadOnly = ref(false)
const typeFilter = ref('')

function typeLabel(type: string): string {
  return NOTIFICATION_TYPE_LABELS[type] ?? '通知'
}

function typeTag(type: string): string {
  if (type.startsWith('task')) return 'primary'
  if (type.startsWith('weekly_report')) return 'success'
  if (type.endsWith('_overdue') || type === 'equipment_fault') return 'danger'
  if (type.startsWith('equipment') || type.startsWith('maintenance')) return 'warning'
  return 'info'
}

function filterTypes(): string[] | undefined {
  if (!typeFilter.value) return undefined
  const group = NOTIFICATION_GROUPS.find((g) => g.types.includes(typeFilter.value))
  return group?.types
}

async function load(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const types = filterTypes()
    // the API takes a single type; page through with the first type of the group
    const { data } = await listNotifications({
      page: page.value,
      page_size: pageSize,
      unread_only: unreadOnly.value || undefined,
      type: typeFilter.value || undefined,
    })
    let rows = data.data.items
    if (types && types.length > 1) {
      rows = rows.filter((n: AppNotification) => types.includes(n.type))
    }
    items.value = rows
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

function jumpTo(n: AppNotification) {
  switch (n.related_type) {
    case 'project':
      router.push(`/projects/${n.related_id}`)
      break
    case 'task':
      router.push(`/tasks/${n.related_id}`)
      break
    case 'experiment':
      router.push(`/experiments/${n.related_id}`)
      break
    case 'weekly_report':
      router.push('/weekly-reports')
      break
    case 'equipment':
    case 'equipment_maintenance':
      router.push(`/equipment/${n.related_id}`)
      break
    case 'equipment_borrow':
      router.push('/equipment-borrows')
      break
    default:
      break
  }
}

async function openNotice(n: AppNotification) {
  if (!n.is_read) {
    await markRead(n.id)
    n.is_read = true
  }
  jumpTo(n)
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

.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
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
