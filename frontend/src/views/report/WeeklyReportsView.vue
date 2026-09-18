<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-select
          v-if="auth.canManage"
          v-model="query.member_id"
          filterable
          clearable
          placeholder="成员"
          style="width: 160px"
          @change="load(1)"
        >
          <el-option v-for="m in members" :key="m.id" :label="m.user.name" :value="m.id" />
        </el-select>
        <el-select v-model="query.status" clearable placeholder="状态" style="width: 130px" @change="load(1)">
          <el-option v-for="(label, key) in REPORT_STATUS_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
        <ExportButton kind="weekly-reports" />
      </div>
      <el-button
        v-if="!auth.canManage"
        type="primary"
        @click="openForm(currentReport ?? undefined)"
      >
        {{ currentReport ? '编辑本周周报' : '写本周周报' }}
        <el-tag v-if="currentReport" size="small" style="margin-left: 6px" :type="REPORT_STATUS_TAGS[currentReport.status]">
          {{ REPORT_STATUS_LABELS[currentReport.status] }}
        </el-tag>
      </el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="成员" width="110">
        <template #default="{ row }">{{ row.member_name }}</template>
      </el-table-column>
      <el-table-column label="周次" width="130">
        <template #default="{ row }">{{ row.week_start }} ~ {{ row.week_end.slice(5) }}</template>
      </el-table-column>
      <el-table-column prop="work_summary" label="本周工作" min-width="200" show-overflow-tooltip />
      <el-table-column prop="problems" label="问题" min-width="160" show-overflow-tooltip />
      <el-table-column label="自评进度" width="120">
        <template #default="{ row }">
          <el-progress :percentage="row.self_progress" :stroke-width="8" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="REPORT_STATUS_TAGS[row.status]">
            {{ REPORT_STATUS_LABELS[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发布时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.published_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
          <template v-if="isMine(row)">
            <el-button v-if="row.status === 'draft'" link type="primary" size="small" @click="openForm(row)">
              编辑
            </el-button>
            <el-button v-if="row.status === 'draft'" link type="success" size="small" @click="publish(row)">
              发布
            </el-button>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无周报" :image-size="70" />
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

    <!-- form dialog (author) -->
    <el-dialog v-model="form.visible" :title="form.isCreate ? '撰写本周周报' : '编辑周报'" width="680px" top="5vh">
      <el-form label-width="90px">
        <el-form-item label="周次">
          <span>{{ form.weekLabel }}</span>
        </el-form-item>
        <el-form-item label="本周工作">
          <el-input v-model="form.data.work_summary" type="textarea" :rows="3" placeholder="本周完成的主要工作" />
        </el-form-item>
        <el-form-item label="学习情况">
          <el-input v-model="form.data.learning_summary" type="textarea" :rows="2" placeholder="学习了什么理论/工具" />
        </el-form-item>
        <el-form-item label="实验进展">
          <el-input v-model="form.data.experiment_summary" type="textarea" :rows="2" placeholder="仿真/实验结果" />
        </el-form-item>
        <el-form-item label="遇到问题">
          <el-input v-model="form.data.problems" type="textarea" :rows="2" placeholder="卡在哪里、需要什么帮助" />
        </el-form-item>
        <el-form-item label="下周计划">
          <el-input v-model="form.data.next_week_plan" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="需要帮助">
          <el-input v-model="form.data.need_help" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="自评进度">
          <el-slider v-model="form.data.self_progress" :max="100" show-input />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="form.visible = false">取消</el-button>
        <el-button type="primary" :loading="form.saving" @click="save">
          {{ form.wasPublished ? '保存并通知关注人' : '保存草稿' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- detail dialog with comments -->
    <el-dialog v-model="detail.visible" title="周报详情" width="680px" top="5vh">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="成员">{{ detail.row?.member_name }}</el-descriptions-item>
        <el-descriptions-item label="周次">{{ detail.row?.week_start }} ~ {{ detail.row?.week_end }}</el-descriptions-item>
        <el-descriptions-item label="本周工作">{{ detail.row?.work_summary || '-' }}</el-descriptions-item>
        <el-descriptions-item label="学习情况">{{ detail.row?.learning_summary || '-' }}</el-descriptions-item>
        <el-descriptions-item label="实验进展">{{ detail.row?.experiment_summary || '-' }}</el-descriptions-item>
        <el-descriptions-item label="遇到问题">{{ detail.row?.problems || '-' }}</el-descriptions-item>
        <el-descriptions-item label="下周计划">{{ detail.row?.next_week_plan || '-' }}</el-descriptions-item>
        <el-descriptions-item label="需要帮助">{{ detail.row?.need_help || '-' }}</el-descriptions-item>
        <el-descriptions-item label="自评进度">{{ detail.row?.self_progress }}%</el-descriptions-item>
      </el-descriptions>

      <div class="comments">
        <h4>评论</h4>
        <div v-if="!detail.comments.length" class="muted">暂无评论</div>
        <div v-for="c in detail.comments" :key="c.id" class="comment">
          <div class="comment-head">
            <b>{{ c.user_name }}</b>
            <span class="muted">{{ formatDateTime(c.created_at) }}</span>
          </div>
          <div>{{ c.content }}</div>
        </div>
        <div class="comment-input">
          <el-input
            v-model="detail.draft"
            type="textarea"
            :rows="2"
            placeholder="给点建议或提醒（发布后周报作者会收到通知）"
          />
          <el-button type="primary" :disabled="!detail.draft.trim()" :loading="detail.sending" @click="sendComment">
            评论
          </el-button>
        </div>
      </div>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addReportComment,
  createReport,
  getReport,
  listReports,
  myCurrentWeekReport,
  publishReport,
  updateReport,
  type WeeklyReport,
  type WeeklyReportComment,
} from '@/api/reports'
import { REPORT_STATUS_LABELS, REPORT_STATUS_TAGS } from '@/utils/constants'
import ExportButton from '@/components/ExportButton.vue'
import { currentWeekStart, formatDateTime, weekEndOf } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'
import { listMembers, type Member } from '@/api/members'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<WeeklyReport[]>([])
const total = ref(0)
const members = ref<Member[]>([])
const currentReport = ref<WeeklyReport | null>(null)
const myMemberId = ref<number | null>(null)

const query = reactive<{ page: number; page_size: number; member_id?: number; status: string }>({
  page: 1,
  page_size: 20,
  member_id: undefined,
  status: '',
})

function isMine(row: WeeklyReport): boolean {
  return myMemberId.value != null && row.member_id === myMemberId.value
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listReports({
      page: query.page,
      page_size: query.page_size,
      member_id: query.member_id || undefined,
      status: query.status || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

const form = reactive({
  visible: false,
  saving: false,
  isCreate: true,
  wasPublished: false,
  editingId: 0,
  weekLabel: '',
  week: '',
  data: {
    work_summary: '',
    learning_summary: '',
    experiment_summary: '',
    problems: '',
    next_week_plan: '',
    need_help: '',
    self_progress: 0,
  },
})

function fillForm(existing: WeeklyReport) {
  form.isCreate = false
  form.wasPublished = existing.status === 'published'
  form.editingId = existing.id
  form.week = existing.week_start
  form.data = {
    work_summary: existing.work_summary ?? '',
    learning_summary: existing.learning_summary ?? '',
    experiment_summary: existing.experiment_summary ?? '',
    problems: existing.problems ?? '',
    next_week_plan: existing.next_week_plan ?? '',
    need_help: existing.need_help ?? '',
    self_progress: existing.self_progress,
  }
}

async function openForm(existing?: WeeklyReport) {
  if (existing) {
    fillForm(existing)
  } else {
    const cur = await myCurrentWeekReport()
    if (cur.data.data) {
      fillForm(cur.data.data)
    } else {
      form.isCreate = true
      form.wasPublished = false
      form.week = currentWeekStart()
      form.data = { work_summary: '', learning_summary: '', experiment_summary: '', problems: '', next_week_plan: '', need_help: '', self_progress: 0 }
    }
  }
  form.weekLabel = `${form.week} ~ ${weekEndOf(form.week)}`
  form.visible = true
}

async function save() {
  form.saving = true
  try {
    if (form.isCreate) {
      await createReport({ week_start: form.week, ...form.data })
      ElMessage.success('草稿已保存，发布后实验室成员可见')
    } else {
      await updateReport(form.editingId, { ...form.data })
      ElMessage.success(form.wasPublished ? '已更新并通知关注人' : '周报已更新')
    }
    form.visible = false
    await load(1)
    await loadCurrent()
  } finally {
    form.saving = false
  }
}

async function publish(row: WeeklyReport) {
  await ElMessageBox.confirm(
    `发布 ${row.week_start} 周报？发布后实验室成员可见，之后仍可继续修改。`,
    '发布周报',
    { type: 'info', confirmButtonText: '发布', cancelButtonText: '再改改' },
  )
  await publishReport(row.id)
  ElMessage.success('已发布，相关老师会收到通知')
  await load()
  await loadCurrent()
}

const detail = reactive({
  visible: false,
  row: null as WeeklyReport | null,
  comments: [] as WeeklyReportComment[],
  draft: '',
  sending: false,
})

async function viewDetail(row: WeeklyReport) {
  detail.row = row
  detail.draft = ''
  const { data } = await getReport(row.id)
  detail.comments = data.data.comments ?? []
  detail.row = data.data
  detail.visible = true
}

async function sendComment() {
  if (!detail.row || !detail.draft.trim()) return
  detail.sending = true
  try {
    await addReportComment(detail.row.id, detail.draft.trim())
    detail.draft = ''
    const { data } = await getReport(detail.row.id)
    detail.comments = data.data.comments ?? []
    ElMessage.success('评论已添加')
  } finally {
    detail.sending = false
  }
}

async function loadCurrent() {
  if (!auth.canManage) {
    const res = await myCurrentWeekReport()
    currentReport.value = res.data.data
    if (res.data.data) myMemberId.value = res.data.data.member_id
  }
}

onMounted(async () => {
  await load()
  if (auth.canManage) {
    const { data } = await listMembers({ page_size: 100 })
    members.value = data.data.items
  } else {
    await loadCurrent()
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.comments {
  margin-top: 16px;
}

.comments h4 {
  margin: 0 0 8px;
}

.muted {
  color: #909399;
  font-size: 13px;
}

.comment {
  padding: 8px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  font-size: 14px;
}

.comment-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2px;
}

.comment-input {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  margin-top: 12px;
}

.comment-input .el-button {
  flex-shrink: 0;
}
</style>
