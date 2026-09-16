<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="项目名/编号"
          clearable
          style="width: 180px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-select v-model="query.status" clearable placeholder="状态" style="width: 120px" @change="load(1)">
          <el-option v-for="(label, key) in PROJECT_STATUS_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
        <el-select v-model="query.priority" clearable placeholder="优先级" style="width: 120px" @change="load(1)">
          <el-option v-for="(label, key) in PRIORITY_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
        <el-button type="primary" plain @click="load(1)">查询</el-button>
      </div>
      <el-button
        v-if="auth.isPI || auth.isTeacher"
        type="primary"
        @click="openCreate"
      >
        新建项目
      </el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="项目" min-width="220">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/projects/${row.id}`)">
            <span style="font-weight: 600">{{ row.name }}</span>
          </el-link>
          <span style="color:#909399; font-size:12px; margin-left:6px">{{ row.code }}</span>
        </template>
      </el-table-column>
      <el-table-column label="负责人" width="100">
        <template #default="{ row }">{{ row.owner_name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="PROJECT_STATUS_TAGS[row.status]">
            {{ PROJECT_STATUS_LABELS[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="PRIORITY_TAGS[row.priority]" effect="plain">
            {{ PRIORITY_LABELS[row.priority] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="150">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" :stroke-width="8" />
        </template>
      </el-table-column>
      <el-table-column label="任务" width="120">
        <template #default="{ row }">
          <span>{{ row.task_done ?? 0 }}/{{ row.task_total ?? 0 }}</span>
          <el-tag v-if="row.task_overdue" size="small" type="danger" style="margin-left: 6px">
            逾期 {{ row.task_overdue }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="我的角色" width="100">
        <template #default="{ row }">{{ roleText(row.my_role) }}</template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无项目" :image-size="70" />
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

    <el-dialog v-model="dialog.visible" title="新建项目" width="560px">
      <el-form label-width="90px">
        <el-form-item label="项目名称" required>
          <el-input v-model="dialog.form.name" maxlength="200" />
        </el-form-item>
        <el-form-item label="项目编号" required>
          <el-input v-model="dialog.form.code" maxlength="50" placeholder="如 LAB-P004" />
        </el-form-item>
        <el-form-item label="研究方向">
          <el-input v-model="dialog.form.research_direction" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dialog.form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="dialog.form.priority" style="width: 100%">
            <el-option v-for="(label, key) in PRIORITY_LABELS" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="可见性">
          <el-radio-group v-model="dialog.form.visibility">
            <el-radio value="lab">全实验室可见</el-radio>
            <el-radio value="project_members">仅项目成员</el-radio>
            <el-radio value="private">仅负责人</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker
            v-model="dialog.form.range"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始"
            end-placeholder="预计结束"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">创建</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { createProject, listProjects, type Project } from '@/api/projects'
import { PRIORITY_LABELS, PRIORITY_TAGS, PROJECT_STATUS_LABELS, PROJECT_STATUS_TAGS } from '@/utils/constants'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<Project[]>([])
const total = ref(0)

const query = reactive({ page: 1, page_size: 20, keyword: '', status: '', priority: '' })

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listProjects({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status || undefined,
      priority: query.priority || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

function roleText(role?: string): string {
  const map: Record<string, string> = {
    owner: '负责人',
    manager: '管理员',
    researcher: '研究员',
    student: '学生',
    observer: '观察者',
    lab: '实验室可见',
    none: '-',
  }
  return map[role ?? 'none'] ?? role ?? '-'
}

const dialog = reactive({
  visible: false,
  saving: false,
  form: { name: '', code: '', research_direction: '', description: '', priority: 'medium', visibility: 'project_members', range: [] as string[] },
})

function openCreate() {
  dialog.form = { name: '', code: '', research_direction: '', description: '', priority: 'medium', visibility: 'project_members', range: [] }
  dialog.visible = true
}

async function save() {
  dialog.saving = true
  try {
    await createProject({
      name: dialog.form.name,
      code: dialog.form.code,
      research_direction: dialog.form.research_direction || null,
      description: dialog.form.description || null,
      priority: dialog.form.priority,
      visibility: dialog.form.visibility,
      start_date: dialog.form.range?.[0] ?? null,
      expected_end_date: dialog.form.range?.[1] ?? null,
    })
    dialog.visible = false
    await load(1)
  } finally {
    dialog.saving = false
  }
}

onMounted(() => load())
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
