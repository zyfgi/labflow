<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="任务标题"
          clearable
          style="width: 180px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-select
          v-if="auth.canManage"
          v-model="query.project_id"
          filterable
          clearable
          placeholder="项目"
          style="width: 200px"
          @change="load(1)"
        >
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.status" clearable placeholder="状态" style="width: 120px" @change="load(1)">
          <el-option v-for="(label, key) in TASK_STATUS_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
        <el-checkbox v-model="query.mine" border @change="load(1)">只看我的</el-checkbox>
      </div>
      <div>
        <el-button
          v-if="auth.isPI || auth.isTeacher"
          type="primary"
          @click="createVisible = true"
        >
          新建任务
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="任务" min-width="220">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/tasks/${row.id}`)">{{ row.title }}</el-link>
          <span v-if="row.is_overdue" class="overdue-badge">逾期</span>
        </template>
      </el-table-column>
      <el-table-column label="项目" min-width="160">
        <template #default="{ row }">{{ row.project_name }}</template>
      </el-table-column>
      <el-table-column label="负责人" width="100">
        <template #default="{ row }">{{ row.assignee_name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="TASK_STATUS_TAGS[row.status]">{{ TASK_STATUS_LABELS[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="PRIORITY_TAGS[row.priority]" effect="plain">{{ PRIORITY_LABELS[row.priority] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="截止" width="120">
        <template #default="{ row }">
          <span :style="row.is_overdue ? 'color:#f56c6c;font-weight:600' : ''">{{ formatDate(row.due_date) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="150">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" :stroke-width="8" />
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无任务" :image-size="70" />
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

    <TaskFormDialog v-model="createVisible" @saved="load()" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { listTasks, type Task } from '@/api/tasks'
import { listProjects, type Project } from '@/api/projects'
import { PRIORITY_LABELS, PRIORITY_TAGS, TASK_STATUS_LABELS, TASK_STATUS_TAGS } from '@/utils/constants'
import { formatDate } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'
import TaskFormDialog from '@/components/TaskFormDialog.vue'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<Task[]>([])
const total = ref(0)
const projects = ref<Project[]>([])
const createVisible = ref(false)

const query = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  project_id: undefined as number | undefined,
  status: '',
  mine: false,
})

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listTasks({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      project_id: query.project_id || undefined,
      status: query.status || undefined,
      mine: query.mine || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await load()
  if (auth.canManage) {
    const { data } = await listProjects({ page_size: 100 })
    projects.value = data.data.items
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
  align-items: center;
  flex-wrap: wrap;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.overdue-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 0 6px;
  border-radius: 3px;
  background: #f56c6c;
  color: #fff;
  font-size: 12px;
}
</style>
