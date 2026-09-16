<template>
  <div v-loading="loading">
    <!-- PI / Teacher dashboard -->
    <template v-if="pi">
      <el-row :gutter="12" class="kpi-row">
        <el-col v-for="k in piKpis" :key="k.label" :xs="12" :sm="8" :md="6" :lg="3">
          <el-card shadow="never" class="kpi-card">
            <div class="kpi-value" :class="k.danger ? 'kpi-danger' : ''">{{ k.value }}</div>
            <div class="kpi-label">{{ k.label }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 4px">
        <el-col :md="14">
          <el-card shadow="never">
            <template #header>项目进度</template>
            <el-table :data="pi.projects" size="small" stripe>
              <el-table-column label="项目" min-width="160">
                <template #default="{ row }">
                  <el-link type="primary" @click="$router.push(`/projects/${row.id}`)">{{ row.name }}</el-link>
                </template>
              </el-table-column>
              <el-table-column label="负责人" width="90">
                <template #default="{ row }">{{ row.owner_name ?? '-' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="PROJECT_STATUS_TAGS[row.status]">{{ PROJECT_STATUS_LABELS[row.status] }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="140">
                <template #default="{ row }"><el-progress :percentage="row.progress" :stroke-width="8" /></template>
              </el-table-column>
              <el-table-column label="逾期" width="60">
                <template #default="{ row }">
                  <span :style="row.overdue_tasks ? 'color:#f56c6c;font-weight:600' : ''">{{ row.overdue_tasks }}</span>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无进行中项目" :image-size="60" /></template>
            </el-table>
            <div ref="projectChart" style="height: 220px; margin-top: 8px" />
          </el-card>
        </el-col>
        <el-col :md="10">
          <el-card shadow="never">
            <template #header>待处理事项</template>
            <div class="todo-grid">
              <div class="todo-item" @click="$router.push('/weekly-reports?status=submitted')">
                <span class="todo-num" :class="{ 'todo-hot': pi.todo.pending_reports > 0 }">{{ pi.todo.pending_reports }}</span>
                <span>待审核周报</span>
              </div>
              <div class="todo-item" @click="$router.push('/equipment-bookings?status=pending')">
                <span class="todo-num" :class="{ 'todo-hot': pi.todo.pending_bookings > 0 }">{{ pi.todo.pending_bookings }}</span>
                <span>待审批预约</span>
              </div>
              <div class="todo-item" @click="$router.push('/tasks')">
                <span class="todo-num" :class="{ 'todo-hot': pi.todo.overdue_tasks.length > 0 }">{{ pi.todo.overdue_tasks.length }}</span>
                <span>逾期任务</span>
              </div>
              <div class="todo-item" @click="$router.push('/equipment-maintenance')">
                <span class="todo-num" :class="{ 'todo-hot': pi.todo.fault_equipment.length > 0 }">{{ pi.todo.fault_equipment.length }}</span>
                <span>故障设备</span>
              </div>
            </div>
            <el-divider content-position="left">即将到期里程碑（14 天内）</el-divider>
            <div v-for="m in pi.todo.due_milestones" :key="m.id" class="milestone-row">
              <span>{{ m.title }} <span style="color:#909399">· {{ m.project_name }}</span></span>
              <el-tag size="small" type="warning">{{ m.due_date }}</el-tag>
            </div>
            <el-empty v-if="!pi.todo.due_milestones.length" description="暂无到期里程碑" :image-size="50" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :md="15">
          <el-card shadow="never">
            <template #header>成员动态</template>
            <el-table :data="pi.members" size="small" stripe>
              <el-table-column label="姓名" width="90">
                <template #default="{ row }">
                  <el-link type="primary" @click="$router.push(`/members/${row.member_id}`)">{{ row.name }}</el-link>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="80">
                <template #default="{ row }">{{ MEMBER_TYPE_LABELS[row.member_type] }}</template>
              </el-table-column>
              <el-table-column prop="research_direction" label="研究方向" min-width="130" show-overflow-tooltip />
              <el-table-column label="当前项目" min-width="130" show-overflow-tooltip>
                <template #default="{ row }">{{ row.projects.join('、') || '-' }}</template>
              </el-table-column>
              <el-table-column label="任务" width="70" align="center">
                <template #default="{ row }">{{ row.in_progress_tasks }}</template>
              </el-table-column>
              <el-table-column label="逾期" width="60" align="center">
                <template #default="{ row }">
                  <span :style="row.overdue_tasks ? 'color:#f56c6c;font-weight:600' : ''">{{ row.overdue_tasks }}</span>
                </template>
              </el-table-column>
              <el-table-column label="本周周报" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.this_week_report === 'none' ? 'info' : REPORT_STATUS_TAGS[row.this_week_report]">
                    {{ row.this_week_report === 'none' ? '未提交' : REPORT_STATUS_LABELS[row.this_week_report] }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :md="9">
          <el-card shadow="never">
            <template #header>最近动态</template>
            <el-timeline>
              <el-timeline-item
                v-for="(a, i) in pi.activity"
                :key="i"
                :timestamp="formatDateTime(a.time)"
                :type="activityDot(a.type)"
              >
                {{ a.text }}
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="!pi.activity.length" description="暂无动态" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- Student dashboard -->
    <template v-else-if="stu">
      <el-row :gutter="12" class="kpi-row">
        <el-col :xs="12" :sm="8" :md="4" v-for="k in stuKpis" :key="k.label">
          <el-card shadow="never" class="kpi-card">
            <div class="kpi-value" :class="k.danger ? 'kpi-danger' : ''">{{ k.value }}</div>
            <div class="kpi-label">{{ k.label }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 4px">
        <el-col :md="14">
          <el-card shadow="never">
            <template #header>
              <div class="head-row"><b>我的任务</b><el-button size="small" link type="primary" @click="$router.push('/tasks')">全部任务</el-button></div>
            </template>
            <el-table :data="stu.tasks" size="small" stripe>
              <el-table-column label="任务" min-width="180">
                <template #default="{ row }">
                  <el-link type="primary" @click="$router.push(`/tasks/${row.id}`)">{{ row.title }}</el-link>
                </template>
              </el-table-column>
              <el-table-column label="项目" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ row.project_name }}</template>
              </el-table-column>
              <el-table-column label="截止" width="110">
                <template #default="{ row }">
                  <span :style="row.is_overdue ? 'color:#f56c6c;font-weight:600' : ''">{{ row.due_date ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="130">
                <template #default="{ row }"><el-progress :percentage="row.progress" :stroke-width="8" /></template>
              </el-table-column>
              <template #empty><el-empty description="暂无进行中任务" :image-size="60" /></template>
            </el-table>
          </el-card>

          <el-card shadow="never" style="margin-top: 16px">
            <template #header>我的项目</template>
            <div v-for="p in stu.projects" :key="p.id" class="proj-row">
              <el-link type="primary" @click="$router.push(`/projects/${p.id}`)">{{ p.name }}</el-link>
              <el-tag size="small" :type="PROJECT_STATUS_TAGS[p.status]" style="margin: 0 10px">{{ PROJECT_STATUS_LABELS[p.status] }}</el-tag>
              <el-progress :percentage="p.progress" :stroke-width="8" style="flex: 1" />
            </div>
            <el-empty v-if="!stu.projects.length" description="暂无参与项目" :image-size="60" />
          </el-card>
        </el-col>
        <el-col :md="10">
          <el-card shadow="never">
            <template #header>最近实验</template>
            <div v-for="e in stu.experiments" :key="e.id" class="proj-row">
              <el-link type="primary" @click="$router.push(`/experiments/${e.id}`)">
                <span style="font-family: monospace">{{ e.experiment_no }}</span> {{ e.title }}
              </el-link>
              <el-tag size="small" :type="EXPERIMENT_STATUS_TAGS[e.status]" style="margin-left: 8px">
                {{ EXPERIMENT_STATUS_LABELS[e.status] }}
              </el-tag>
            </div>
            <el-empty v-if="!stu.experiments.length" description="暂无实验记录" :image-size="60" />
          </el-card>
          <el-card shadow="never" style="margin-top: 16px">
            <template #header>近期设备预约</template>
            <div v-for="b in stu.bookings" :key="b.id" class="proj-row">
              <span>{{ b.equipment_name }}</span>
              <span style="color: #909399; margin-left: auto; font-size: 12px">
                {{ formatDateTime(b.start_time) }}
              </span>
            </div>
            <el-empty v-if="!stu.bookings.length" description="暂无预约" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useAuthStore } from '@/stores/auth'
import client from '@/api/client'
import {
  EQUIPMENT_STATUS_LABELS,
  EXPERIMENT_STATUS_LABELS,
  EXPERIMENT_STATUS_TAGS,
  MEMBER_TYPE_LABELS,
  PROJECT_STATUS_LABELS,
  PROJECT_STATUS_TAGS,
  REPORT_STATUS_LABELS,
  REPORT_STATUS_TAGS,
} from '@/utils/constants'
import { formatDateTime } from '@/utils/datetime'

const auth = useAuthStore()
const loading = ref(true)
const pi = ref<any>(null)
const stu = ref<any>(null)
const projectChart = ref<HTMLElement>()

const isStaffView = computed(() => auth.isPI || auth.isTeacher)
const piKpis = computed(() =>
  pi.value
    ? [
        { label: '实验室成员', value: pi.value.kpis.member_total },
        { label: '活跃项目', value: pi.value.kpis.active_projects },
        { label: '本周周报提交率', value: `${pi.value.kpis.weekly_report_rate}%` },
        { label: '进行中任务', value: pi.value.kpis.tasks_open },
        { label: '逾期任务', value: pi.value.kpis.tasks_overdue, danger: pi.value.kpis.tasks_overdue > 0 },
        { label: '本周实验', value: pi.value.kpis.experiments_this_week },
        { label: '设备故障', value: pi.value.kpis.equipment_fault, danger: pi.value.kpis.equipment_fault > 0 },
        { label: '今日预约', value: pi.value.kpis.bookings_today },
      ]
    : [],
)

const stuKpis = computed(() =>
  stu.value
    ? [
        { label: '进行中任务', value: stu.value.kpis.tasks_in_progress },
        { label: '逾期任务', value: stu.value.kpis.tasks_overdue, danger: stu.value.kpis.tasks_overdue > 0 },
        { label: '本周周报', value: stu.value.kpis.this_week_report === 'none' ? '未提交' : REPORT_STATUS_LABELS[stu.value.kpis.this_week_report] },
        { label: '我的实验', value: stu.value.kpis.experiment_count },
        { label: '未读通知', value: stu.value.kpis.unread_notifications, danger: stu.value.kpis.unread_notifications > 0 },
      ]
    : [],
)

function activityDot(type: string) {
  const map: Record<string, string> = { experiment: 'primary', report: 'success', task: 'warning', equipment: 'danger' }
  return map[type] ?? 'info'
}

function renderChart() {
  if (!projectChart.value || !pi.value) return
  const chart = echarts.init(projectChart.value)
  const names = pi.value.projects.map((p: any) => p.name)
  const manual = pi.value.projects.map((p: any) => p.progress)
  const derived = pi.value.projects.map((p: any) =>
    p.task_total ? Math.round((p.task_done / p.task_total) * 100) : 0,
  )
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['负责人设定进度', '任务完成率（参考）'], bottom: 0 },
    grid: { left: 8, right: 8, top: 10, bottom: 40, containLabel: true },
    xAxis: { type: 'value', max: 100 },
    yAxis: { type: 'category', data: names, axisLabel: { width: 110, overflow: 'truncate' } },
    series: [
      { name: '负责人设定进度', type: 'bar', data: manual, itemStyle: { color: '#409eff' }, barWidth: 12 },
      { name: '任务完成率（参考）', type: 'bar', data: derived, itemStyle: { color: '#95d475' }, barWidth: 12 },
    ],
  })
  window.addEventListener('resize', () => chart.resize())
}

onMounted(async () => {
  try {
    if (isStaffView.value) {
      const { data } = await client.get('/dashboard/pi')
      pi.value = data.data
      await nextTick()
      renderChart()
    } else {
      const { data } = await client.get('/dashboard/student')
      stu.value = data.data
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.kpi-row {
  margin-bottom: 12px;
}

.kpi-card {
  text-align: center;
}

.kpi-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
}

.kpi-danger {
  color: #f56c6c;
}

.kpi-label {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.todo-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  cursor: pointer;
  color: #606266;
}

.todo-item:hover {
  background: #ecf5ff;
}

.todo-num {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.todo-hot {
  color: #f56c6c;
}

.milestone-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  font-size: 13px;
}

.proj-row {
  display: flex;
  align-items: center;
  padding: 5px 0;
}

.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
