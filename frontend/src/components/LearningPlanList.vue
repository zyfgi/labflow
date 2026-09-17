<template>
  <div>
    <div class="toolbar">
      <span></span>
      <el-button v-if="canEdit" type="primary" size="small" @click="openCreate">新建计划</el-button>
    </div>

    <el-table v-loading="loading" :data="plans" stripe>
      <el-table-column prop="title" label="计划" min-width="200" />
      <el-table-column label="分类" width="110">
        <template #default="{ row }">{{ row.category }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="PLAN_STATUS_TAGS[row.status]">
            {{ PLAN_STATUS_LABELS[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="160">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" :stroke-width="8" />
        </template>
      </el-table-column>
      <el-table-column label="开始" width="110">
        <template #default="{ row }">{{ formatDate(row.start_date) }}</template>
      </el-table-column>
      <el-table-column label="目标" width="110">
        <template #default="{ row }">{{ formatDate(row.target_date) }}</template>
      </el-table-column>
      <el-table-column v-if="canEdit" label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无学习计划" :image-size="70" />
      </template>
    </el-table>

    <el-dialog v-model="dialog.visible" :title="dialog.isCreate ? '新建学习计划' : '编辑学习计划'" width="520px">
      <el-form label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="dialog.form.title" maxlength="200" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dialog.form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="dialog.form.category" placeholder="如：理论学习/仿真实验" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="dialog.form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="目标日期">
          <el-date-picker v-model="dialog.form.target_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dialog.form.status" style="width: 100%">
            <el-option v-for="(label, key) in PLAN_STATUS_LABELS" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="进度">
          <el-slider v-model="dialog.form.progress" :max="100" show-input />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createPlan, deletePlan, listPlans, updatePlan, type LearningPlan } from '@/api/learning'
import { PLAN_STATUS_LABELS, PLAN_STATUS_TAGS } from '@/utils/constants'
import { formatDate } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ memberId: number }>()

const auth = useAuthStore()
const loading = ref(false)
const plans = ref<LearningPlan[]>([])

const canEdit = auth.isPI || auth.isTeacher || props.memberId === auth.user?.id

async function load() {
  loading.value = true
  try {
    plans.value = (await listPlans({ member_id: props.memberId })).data.data
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
    title: '',
    description: '',
    category: '',
    start_date: '',
    target_date: '',
    status: 'not_started',
    progress: 0,
  },
})

function openCreate() {
  dialog.isCreate = true
  dialog.form = { title: '', description: '', category: '', start_date: '', target_date: '', status: 'not_started', progress: 0 }
  dialog.visible = true
}

function openEdit(row: LearningPlan) {
  dialog.isCreate = false
  dialog.editingId = row.id
  dialog.form = {
    title: row.title,
    description: row.description ?? '',
    category: row.category,
    start_date: row.start_date ?? '',
    target_date: row.target_date ?? '',
    status: row.status,
    progress: row.progress,
  }
  dialog.visible = true
}

async function save() {
  if (!dialog.form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  dialog.saving = true
  try {
    const payload = {
      title: dialog.form.title,
      description: dialog.form.description || null,
      category: dialog.form.category || 'general',
      start_date: dialog.form.start_date || null,
      target_date: dialog.form.target_date || null,
      status: dialog.form.status,
      progress: dialog.form.progress,
    }
    if (dialog.isCreate) {
      await createPlan({ ...payload, member_id: props.memberId })
    } else {
      await updatePlan(dialog.editingId, payload)
    }
    ElMessage.success('已保存')
    dialog.visible = false
    await load()
  } finally {
    dialog.saving = false
  }
}

async function remove(row: LearningPlan) {
  await ElMessageBox.confirm(`确认删除计划「${row.title}」？`, '提示', { type: 'warning' })
  await deletePlan(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}
</style>
