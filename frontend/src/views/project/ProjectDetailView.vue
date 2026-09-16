<template>
  <div v-if="project">
    <el-page-header style="margin-bottom: 12px" @back="$router.back()">
      <template #content>
        <span style="font-weight: 600">{{ project.name }}</span>
        <el-tag size="small" style="margin-left: 8px" :type="PROJECT_STATUS_TAGS[project.status]">
          {{ PROJECT_STATUS_LABELS[project.status] }}
        </el-tag>
      </template>
    </el-page-header>

    <el-tabs v-model="tab">
      <el-tab-pane label="概览" name="overview">
        <el-row :gutter="16">
          <el-col :span="14">
            <el-card shadow="never">
              <template #header>项目信息</template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="编号">{{ project.code }}</el-descriptions-item>
                <el-descriptions-item label="负责人">{{ project.owner_name ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="优先级">{{ PRIORITY_LABELS[project.priority] }}</el-descriptions-item>
                <el-descriptions-item label="进度">{{ project.progress }}%</el-descriptions-item>
                <el-descriptions-item label="开始日期">{{ formatDate(project.start_date) }}</el-descriptions-item>
                <el-descriptions-item label="预计结束">{{ formatDate(project.expected_end_date) }}</el-descriptions-item>
                <el-descriptions-item label="研究方向" :span="2">{{ project.research_direction ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="描述" :span="2">{{ project.description ?? '-' }}</el-descriptions-item>
              </el-descriptions>
              <div style="margin-top: 12px" v-if="project.my_role === 'owner' || auth.isPI">
                <el-button size="small" @click="progress.visible = true">更新进度</el-button>
              </div>
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card shadow="never">
              <template #header>统计</template>
              <div class="stat-row">
                <el-statistic title="任务总数" :value="project.task_total ?? 0" />
                <el-statistic title="已完成" :value="project.task_done ?? 0" />
                <el-statistic title="逾期" :value="project.task_overdue ?? 0" />
                <el-statistic title="里程碑" :value="project.milestone_count ?? 0" />
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="成员" name="members" lazy>
        <div class="tab-actions">
          <el-button
            v-if="canManage"
            type="primary"
            size="small"
            @click="addMember.visible = true"
          >
            添加成员
          </el-button>
        </div>
        <el-table v-loading="membersLoading" :data="members" stripe>
          <el-table-column prop="name" label="姓名" width="140" />
          <el-table-column prop="username" label="用户名" width="140" />
          <el-table-column label="项目角色" width="140">
            <template #default="{ row }">{{ projectRoleText(row.project_role) }}</template>
          </el-table-column>
          <el-table-column label="加入时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.joined_at) }}</template>
          </el-table-column>
          <el-table-column v-if="canManage" label="操作" width="100">
            <template #default="{ row }">
              <el-button
                v-if="row.user_id !== project.owner_id"
                link
                type="danger"
                size="small"
                @click="removeMember(row)"
              >
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="里程碑" name="milestones" lazy>
        <div class="tab-actions">
          <el-button v-if="canManage" type="primary" size="small" @click="msDialog.visible = true">
            新建里程碑
          </el-button>
        </div>
        <el-table v-loading="msLoading" :data="milestones" stripe>
          <el-table-column prop="title" label="里程碑" min-width="200" />
          <el-table-column label="目标日期" width="120">
            <template #default="{ row }">{{ formatDate(row.due_date) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="MILESTONE_STATUS_TAGS[row.status] ?? 'info'">
                {{ MILESTONE_STATUS_LABELS[row.status] ?? row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" width="150">
            <template #default="{ row }">
              <el-progress :percentage="row.progress" :stroke-width="8" />
            </template>
          </el-table-column>
          <el-table-column v-if="canManage" label="操作" width="150">
            <template #default="{ row }">
              <el-button
                v-if="row.status !== 'completed'"
                link
                type="success"
                size="small"
                @click="completeMilestone(row)"
              >
                完成
              </el-button>
              <el-button link type="danger" size="small" @click="removeMilestone(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="任务" name="tasks" lazy>
        <div class="tab-actions">
          <el-button v-if="canManage" type="primary" size="small" @click="taskDialog.visible = true">
            新建任务
          </el-button>
        </div>
        <el-table v-loading="tasksLoading" :data="tasks" stripe>
          <el-table-column label="任务" min-width="220">
            <template #default="{ row }">
              <el-link type="primary" @click="$router.push(`/tasks/${row.id}`)">{{ row.title }}</el-link>
            </template>
          </el-table-column>
          <el-table-column label="负责人" width="110">
            <template #default="{ row }">{{ row.assignee_name ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="TASK_STATUS_TAGS[row.status]">{{ TASK_STATUS_LABELS[row.status] }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="截止" width="130">
            <template #default="{ row }">
              <span :style="row.is_overdue ? 'color:#f56c6c;font-weight:600' : ''">{{ formatDate(row.due_date) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="进度" width="150">
            <template #default="{ row }">
              <el-progress :percentage="row.progress" :stroke-width="8" />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="实验" name="experiments" disabled>
        <template #label>实验（M5 开放）</template>
      </el-tab-pane>
      <el-tab-pane label="活动" name="activity" disabled>
        <template #label>活动（M8 开放）</template>
      </el-tab-pane>
    </el-tabs>

    <!-- add member -->
    <el-dialog v-model="addMember.visible" title="添加项目成员" width="440px">
      <el-form label-width="80px">
        <el-form-item label="用户" required>
          <el-select v-model="addMember.user_id" filterable style="width: 100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="addMember.project_role" style="width: 100%">
            <el-option label="管理员" value="manager" />
            <el-option label="研究员" value="researcher" />
            <el-option label="学生" value="student" />
            <el-option label="观察者" value="observer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addMember.visible = false">取消</el-button>
        <el-button type="primary" @click="saveMember">添加</el-button>
      </template>
    </el-dialog>

    <!-- new milestone -->
    <el-dialog v-model="msDialog.visible" title="新建里程碑" width="460px">
      <el-form label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="msDialog.form.title" />
        </el-form-item>
        <el-form-item label="目标日期">
          <el-date-picker v-model="msDialog.form.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="msDialog.form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="msDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveMilestone">创建</el-button>
      </template>
    </el-dialog>

    <!-- new task -->
    <TaskFormDialog
      v-model="taskDialog.visible"
      :project-id="projectId"
      :project-fixed="true"
      @saved="loadTasks"
    />

    <!-- update progress -->
    <el-dialog v-model="progress.visible" title="更新项目进度" width="380px">
      <el-slider v-model="progress.value" :max="100" show-input />
      <template #footer>
        <el-button @click="progress.visible = false">取消</el-button>
        <el-button type="primary" @click="saveProgress">保存</el-button>
      </template>
    </el-dialog>
  </div>
  <el-empty v-else-if="!loading" description="项目不存在或没有查看权限" />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addProjectMember,
  createMilestone,
  deleteMilestone,
  getProject,
  listMilestones,
  listProjectMembers,
  removeProjectMember,
  updateMilestone,
  updateProject,
  type Milestone,
  type Project,
  type ProjectMemberRow,
} from '@/api/projects'
import { listTasks, type Task } from '@/api/tasks'
import { userOptions } from '@/api/auth'
import {
  MILESTONE_STATUS_LABELS,
  MILESTONE_STATUS_TAGS,
  PRIORITY_LABELS,
  PROJECT_STATUS_LABELS,
  PROJECT_STATUS_TAGS,
  TASK_STATUS_LABELS,
  TASK_STATUS_TAGS,
} from '@/utils/constants'
import { formatDate, formatDateTime } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'
import TaskFormDialog from '@/components/TaskFormDialog.vue'

const auth = useAuthStore()
const route = useRoute()
const projectId = computed(() => Number(route.params.id))
const loading = ref(true)
const project = ref<Project | null>(null)
const tab = ref('overview')

const canManage = computed(() =>
  project.value?.my_role === 'owner' ||
  project.value?.my_role === 'manager' ||
  auth.isPI,
)

const members = ref<ProjectMemberRow[]>([])
const membersLoading = ref(false)
const milestones = ref<Milestone[]>([])
const msLoading = ref(false)
const tasks = ref<Task[]>([])
const tasksLoading = ref(false)
const userOptionsList = ref<{ id: number; name: string; username: string }[]>([])
const addMember = reactive({ visible: false, user_id: 0, project_role: 'student' })
const msDialog = reactive({ visible: false, form: { title: '', due_date: '', description: '' } })
const taskDialog = reactive({ visible: false })
const progress = reactive({ visible: false, value: 0 })

async function load() {
  loading.value = true
  try {
    const { data } = await getProject(projectId.value)
    project.value = data.data
  } catch {
    project.value = null
  } finally {
    loading.value = false
  }
}

async function loadMembers() {
  membersLoading.value = true
  try {
    members.value = (await listProjectMembers(projectId.value)).data.data
  } finally {
    membersLoading.value = false
  }
}

async function loadMilestones() {
  msLoading.value = true
  try {
    milestones.value = (await listMilestones(projectId.value)).data.data
  } finally {
    msLoading.value = false
  }
}

async function loadTasks() {
  tasksLoading.value = true
  try {
    const { data } = await listTasks({ project_id: projectId.value, page_size: 100 })
    tasks.value = data.data.items
  } finally {
    tasksLoading.value = false
  }
}

function projectRoleText(role: string): string {
  const map: Record<string, string> = { owner: '负责人', manager: '管理员', researcher: '研究员', student: '学生', observer: '观察者' }
  return map[role] ?? role
}

async function saveMember() {
  if (!addMember.user_id) {
    ElMessage.warning('请选择用户')
    return
  }
  await addProjectMember(projectId.value, { user_id: addMember.user_id, project_role: addMember.project_role })
  ElMessage.success('成员已加入')
  addMember.visible = false
  await loadMembers()
}

async function removeMember(row: ProjectMemberRow) {
  await ElMessageBox.confirm(`确认移除成员「${row.name}」？`, '提示', { type: 'warning' })
  await removeProjectMember(projectId.value, row.user_id)
  ElMessage.success('已移除')
  await loadMembers()
}

async function saveMilestone() {
  if (!msDialog.form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  await createMilestone(projectId.value, {
    title: msDialog.form.title,
    due_date: msDialog.form.due_date || null,
    description: msDialog.form.description || null,
  })
  ElMessage.success('里程碑已创建')
  msDialog.visible = false
  msDialog.form = { title: '', due_date: '', description: '' }
  await loadMilestones()
}

async function completeMilestone(row: Milestone) {
  await updateMilestone(row.id, { status: 'completed', progress: 100 })
  ElMessage.success('里程碑已完成')
  await loadMilestones()
}

async function removeMilestone(row: Milestone) {
  await ElMessageBox.confirm(`确认删除里程碑「${row.title}」？`, '提示', { type: 'warning' })
  await deleteMilestone(row.id)
  await loadMilestones()
}

async function saveProgress() {
  await updateProject(projectId.value, { progress: progress.value })
  ElMessage.success('进度已更新')
  progress.visible = false
  await load()
}

watch(projectId, load)
watch(tab, (t) => {
  if (t === 'members') loadMembers()
  else if (t === 'milestones') loadMilestones()
  else if (t === 'tasks') loadTasks()
})

onMounted(async () => {
  await load()
  if (canManage.value) {
    userOptionsList.value = await userOptions()
  }
})
</script>

<style scoped>
.stat-row {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 12px;
}

.tab-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}
</style>
