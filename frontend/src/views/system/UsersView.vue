<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="用户名/姓名/邮箱"
          clearable
          style="width: 220px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-select v-model="query.role" placeholder="角色" clearable style="width: 150px" @change="load(1)">
          <el-option v-for="(label, role) in ROLE_LABELS" :key="role" :label="label" :value="role" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="load(1)">
          <el-option label="启用" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
        <el-button type="primary" plain @click="load(1)">查询</el-button>
      </div>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe style="width: 100%">
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="email" label="邮箱" min-width="200" />
      <el-table-column prop="phone" label="手机号" width="130">
        <template #default="{ row }">{{ row.phone ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ ROLE_LABELS[row.role] ?? row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="USER_STATUS_LABELS[row.status]">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近登录" width="160">
        <template #default="{ row }">{{ formatDateTime(row.last_login_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
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

    <el-dialog v-model="dialog.visible" :title="dialog.isCreate ? '新建用户' : `编辑用户：${dialog.form.username}`" width="480px">
      <el-form :model="dialog.form" label-width="90px">
        <template v-if="dialog.isCreate">
          <el-form-item label="用户名" required>
            <el-input v-model="dialog.form.username" />
          </el-form-item>
          <el-form-item label="初始密码" required>
            <el-input v-model="dialog.form.password" type="password" show-password />
          </el-form-item>
        </template>
        <el-form-item label="姓名" required>
          <el-input v-model="dialog.form.name" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="dialog.form.email" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="dialog.form.phone" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="dialog.form.role" style="width: 100%">
            <el-option v-for="(label, role) in ROLE_LABELS" :key="role" :label="label" :value="role" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!dialog.isCreate" label="状态">
          <el-switch v-model="dialog.form.active" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item v-if="!dialog.isCreate" label="重置密码">
          <el-input v-model="dialog.form.password" type="password" show-password placeholder="留空则不修改" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createUser, listUsers, updateUser } from '@/api/users'
import { ROLE_LABELS, USER_STATUS_LABELS } from '@/utils/constants'
import { formatDateTime } from '@/utils/datetime'
import type { User } from '@/types'

const loading = ref(false)
const items = ref<User[]>([])
const total = ref(0)

const query = reactive<UserQueryParams>({
  page: 1,
  page_size: 20,
  keyword: '',
  role: '',
  status: '',
})

interface UserQueryParams {
  page: number
  page_size: number
  keyword: string
  role: string
  status: string
}

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listUsers({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      role: query.role || undefined,
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
  isCreate: true,
  editingId: 0,
  form: {
    username: '',
    name: '',
    email: '',
    phone: '',
    role: 'STUDENT',
    password: '',
    active: true,
  },
})

function openCreate() {
  dialog.isCreate = true
  dialog.form = { username: '', name: '', email: '', phone: '', role: 'STUDENT', password: '', active: true }
  dialog.visible = true
}

function openEdit(row: User) {
  dialog.isCreate = false
  dialog.editingId = row.id
  dialog.form = {
    username: row.username,
    name: row.name,
    email: row.email,
    phone: row.phone ?? '',
    role: row.role,
    password: '',
    active: row.status === 'active',
  }
  dialog.visible = true
}

async function save() {
  dialog.saving = true
  try {
    if (dialog.isCreate) {
      await createUser({
        username: dialog.form.username,
        name: dialog.form.name,
        email: dialog.form.email,
        phone: dialog.form.phone || null,
        role: dialog.form.role,
        password: dialog.form.password,
      })
      ElMessage.success('用户创建成功')
    } else {
      const payload: Record<string, unknown> = {
        name: dialog.form.name,
        email: dialog.form.email,
        phone: dialog.form.phone || null,
        role: dialog.form.role,
        status: dialog.form.active ? 'active' : 'inactive',
      }
      if (dialog.form.password) payload.password = dialog.form.password
      await updateUser(dialog.editingId, payload)
      ElMessage.success('用户更新成功')
    }
    dialog.visible = false
    await load()
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
