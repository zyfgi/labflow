<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="姓名/学号/研究方向"
          clearable
          style="width: 220px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-select v-model="query.member_type" placeholder="身份" clearable style="width: 130px" @change="load(1)">
          <el-option v-for="(label, key) in MEMBER_TYPE_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="load(1)">
          <el-option label="在组" value="active" />
          <el-option label="已毕业" value="graduated" />
          <el-option label="已离组" value="left" />
        </el-select>
        <el-button type="primary" plain @click="load(1)">查询</el-button>
      </div>
      <el-button v-if="auth.isPI" type="primary" @click="dialog.visible = true">添加成员档案</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="姓名" width="110">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/members/${row.id}`)">{{ row.user.name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column label="用户名" width="110">
        <template #default="{ row }">{{ row.user.username }}</template>
      </el-table-column>
      <el-table-column label="身份" width="100">
        <template #default="{ row }">{{ MEMBER_TYPE_LABELS[row.member_type] ?? row.member_type }}</template>
      </el-table-column>
      <el-table-column prop="grade_year" label="年级" width="90">
        <template #default="{ row }">{{ row.grade_year ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="student_no" label="学号" width="120">
        <template #default="{ row }">{{ row.student_no ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="research_direction" label="研究方向" min-width="180">
        <template #default="{ row }">{{ row.research_direction ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="MEMBER_STATUS_LABELS[row.status]">
            {{ { active: '在组', graduated: '已毕业', left: '已离组' }[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="入组时间" width="110">
        <template #default="{ row }">{{ formatDate(row.join_date) }}</template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="load()"
        @size-change="load(1)"
      />
    </div>

    <el-dialog v-model="dialog.visible" title="添加成员档案（选择已有用户）" width="480px">
      <el-form label-width="90px">
        <el-form-item label="用户" required>
          <el-select v-model="dialog.form.user_id" filterable style="width: 100%" placeholder="选择用户">
            <el-option
              v-for="u in options"
              :key="u.id"
              :label="`${u.name} (${u.username})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="身份" required>
          <el-select v-model="dialog.form.member_type" style="width: 100%">
            <el-option v-for="(label, key) in MEMBER_TYPE_LABELS" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="研究方向">
          <el-input v-model="dialog.form.research_direction" />
        </el-form-item>
        <el-form-item label="入组日期">
          <el-date-picker v-model="dialog.form.join_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="saveMember">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listMembers, type Member } from '@/api/members'
import { userOptions } from '@/api/auth'
import { MEMBER_STATUS_LABELS, MEMBER_TYPE_LABELS } from '@/utils/constants'
import { formatDate } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'
import type { UserOption } from '@/types'

const auth = useAuthStore()
const loading = ref(false)
const items = ref<Member[]>([])
const total = ref(0)
const options = ref<UserOption[]>([])

const query = reactive({ page: 1, page_size: 20, keyword: '', member_type: '', status: '' })

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listMembers({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      member_type: (query.member_type as string) || undefined,
      status: query.status || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

const dialog = reactive({
  visible: false,
  saving: false,
  form: { user_id: 0, member_type: 'master', research_direction: '', join_date: '' },
})

async function saveMember() {
  if (!dialog.form.user_id) {
    ElMessage.warning('请选择用户')
    return
  }
  dialog.saving = true
  try {
    const { default: client } = await import('@/api/client')
    await client.post('/members', {
      user_id: dialog.form.user_id,
      member_type: dialog.form.member_type,
      research_direction: dialog.form.research_direction || null,
      join_date: dialog.form.join_date || null,
    })
    ElMessage.success('成员档案已创建')
    dialog.visible = false
    await load(1)
  } finally {
    dialog.saving = false
  }
}

onMounted(async () => {
  await load()
  if (auth.isPI) {
    options.value = await userOptions()
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
