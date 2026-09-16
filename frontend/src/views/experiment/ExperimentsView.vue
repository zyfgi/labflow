<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="实验名称/编号"
          clearable
          style="width: 200px"
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
          <el-option v-for="(label, key) in EXPERIMENT_STATUS_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
        <el-checkbox v-model="query.mine" border @change="load(1)">只看我的</el-checkbox>
      </div>
      <el-button type="primary" @click="createVisible = true">新建实验</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="实验编号" width="170">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/experiments/${row.id}`)">{{ row.experiment_no }}</el-link>
          <el-tag v-if="row.is_locked" size="small" type="warning" style="margin-left: 4px">已锁定</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="实验名称" min-width="200" show-overflow-tooltip />
      <el-table-column label="项目" min-width="150">
        <template #default="{ row }">{{ row.project_name }}</template>
      </el-table-column>
      <el-table-column label="负责人" width="100">
        <template #default="{ row }">{{ row.owner_name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="日期" width="110">
        <template #default="{ row }">{{ formatDate(row.experiment_date) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="EXPERIMENT_STATUS_TAGS[row.status]">
            {{ EXPERIMENT_STATUS_LABELS[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无实验记录" :image-size="70" />
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

    <ExperimentFormDialog v-model="createVisible" @saved="load(1)" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { listExperiments, type Experiment } from '@/api/experiments'
import { listProjects, type Project } from '@/api/projects'
import { EXPERIMENT_STATUS_LABELS, EXPERIMENT_STATUS_TAGS } from '@/utils/constants'
import { formatDate } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'
import ExperimentFormDialog from '@/components/ExperimentFormDialog.vue'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<Experiment[]>([])
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
    const { data } = await listExperiments({
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
</style>
