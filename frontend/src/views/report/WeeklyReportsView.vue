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
      <el-table-column v-if="auth.canManage" label="成员" width="110">
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
      <el-table-column label="提交时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.submitted_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
          <template v-if="!auth.canManage && isMine(row)">
            <el-button
              v-if="row.status === 'draft' || row.status === 'returned'"
              link
              type="primary"
              size="small"
              @click="openForm(row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="row.status === 'draft' || row.status === 'returned'"
              link
              type="success"
              size="small"
              @click="submit(row)"
            >
              提交
            </el-button>
          </template>
          <template v-if="auth.canManage && row.status === 'submitted'">
            <el-button link type="success" size="small" @click="review(row, 'review')">通过</el-button>
            <el-button link type="danger" size="small" @click="review(row, 'return')">退回</el-button>
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

    <!-- form dialog (student) -->
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
        <el-button type="primary" :loading="form.saving" @click="save">保存草稿</el-button>
      </template>
    </el-dialog>

    <!-- detail dialog -->
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
        <el-descriptions-item label="导师意见">
          <span v-if="detail.row?.review_comment">{{ detail.row.review_comment }}</span>
          <span v-else style="color: #909399">暂无</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createReport,
  listReports,
  myCurrentWeekReport,
  returnReport,
  reviewReport,
  submitReport,
  updateReport,
  type WeeklyReport,
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

const query = reactive<{ page: number; page_size: number; member_id?: number; status: string }>({
  page: 1,
  page_size: 20,
  member_id: undefined,
  status: '',
})

function isMine(row: WeeklyReport): boolean {
  return !auth.canManage
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

async function openForm(existing?: WeeklyReport) {
  if (existing) {
    form.isCreate = false
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
  } else {
    const cur = await myCurrentWeekReport()
    if (cur.data.data) {
      existing = cur.data.data
      form.isCreate = false
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
    } else {
      form.isCreate = true
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
      ElMessage.success('草稿已保存，请点击提交')
    } else {
      await updateReport(form.editingId, { ...form.data })
      ElMessage.success('周报已更新')
    }
    form.visible = false
    await load(1)
    await loadCurrent()
  } finally {
    form.saving = false
  }
}

async function submit(row: WeeklyReport) {
  await ElMessageBox.confirm(`确认提交 ${row.week_start} 周报？提交后需老师退回才能修改。`, '提示', { type: 'info' })
  await submitReport(row.id)
  ElMessage.success('已提交')
  await load()
  await loadCurrent()
}

async function review(row: WeeklyReport, action: 'review' | 'return') {
  const { value } = await ElMessageBox.prompt(
    action === 'review' ? '审核意见（可选）' : '退回原因（将通知学生）',
    action === 'review' ? '通过周报' : '退回周报',
    { inputType: 'textarea', inputValue: '', confirmButtonText: '确认', cancelButtonText: '取消' },
  ).catch(() => ({ value: undefined }))
  if (value === undefined) return
  if (action === 'review') {
    await reviewReport(row.id, value || undefined)
    ElMessage.success('已审核')
  } else {
    await returnReport(row.id, value || undefined)
    ElMessage.success('已退回')
  }
  await load()
}

const detail = reactive({ visible: false, row: null as WeeklyReport | null })

function viewDetail(row: WeeklyReport) {
  detail.row = row
  detail.visible = true
}

async function loadCurrent() {
  if (!auth.canManage) {
    const res = await myCurrentWeekReport()
    currentReport.value = res.data.data
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
</style>
