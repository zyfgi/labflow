<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑任务' : '新建任务'"
    width="560px"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <el-form label-width="80px">
      <el-form-item label="所属项目" required>
        <el-select v-if="!projectFixed" v-model="form.project_id" filterable style="width: 100%">
          <el-option v-for="p in projects" :key="p.id" :label="`${p.name} (${p.code})`" :value="p.id" />
        </el-select>
        <span v-else>{{ project?.name }}</span>
      </el-form-item>
      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="200" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="负责人">
        <el-select v-model="form.assignee_id" filterable clearable style="width: 100%">
          <el-option v-for="u in options" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级">
        <el-select v-model="form.priority" style="width: 100%">
          <el-option v-for="(label, key) in PRIORITY_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="form.status" style="width: 100%">
          <el-option v-for="(label, key) in TASK_STATUS_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
      </el-form-item>
      <el-form-item label="截止日期">
        <el-date-picker v-model="form.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="进度">
        <el-slider v-model="form.progress" :max="100" show-input />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createTask, updateTask } from '@/api/tasks'
import { listProjects, type Project } from '@/api/projects'
import { userOptions } from '@/api/auth'
import { PRIORITY_LABELS, TASK_STATUS_LABELS } from '@/utils/constants'
import type { UserOption } from '@/types'

const props = defineProps<{
  modelValue: boolean
  projectId?: number
  projectFixed?: boolean
  task?: Task | null
}>()

interface Task {
  id: number
  title: string
  description: string | null
  assignee_id: number | null
  priority: string
  status: string
  due_date: string | null
  progress: number
}

const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>()

const options = ref<UserOption[]>([])
const projects = ref<Project[]>([])
const saving = ref(false)

const form = reactive({
  project_id: 0,
  title: '',
  description: '',
  assignee_id: undefined as number | undefined,
  priority: 'medium',
  status: 'todo',
  due_date: '',
  progress: 0,
})

const isEdit = computed(() => !!props.task?.id)
const project = computed(() => projects.value.find((p) => p.id === props.projectId))

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    if (!options.value.length) {
      options.value = await userOptions()
    }
    if (props.projectFixed && props.projectId) {
      form.project_id = props.projectId
    } else if (!projects.value.length) {
      const { data } = await listProjects({ page_size: 100 })
      projects.value = data.data.items
    }
    if (props.task) {
      Object.assign(form, {
        project_id: props.task.project_id ?? props.projectId ?? 0,
        title: props.task.title,
        description: props.task.description ?? '',
        assignee_id: props.task.assignee_id ?? undefined,
        priority: props.task.priority,
        status: props.task.status,
        due_date: props.task.due_date ?? '',
        progress: props.task.progress,
      })
    } else {
      Object.assign(form, {
        project_id: props.projectId ?? 0,
        title: '',
        description: '',
        assignee_id: undefined,
        priority: 'medium',
        status: 'todo',
        due_date: '',
        progress: 0,
      })
    }
  },
)

async function save() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入任务标题')
    return
  }
  if (!form.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title,
      description: form.description || null,
      assignee_id: form.assignee_id ?? null,
      priority: form.priority,
      status: form.status,
      due_date: form.due_date || null,
      progress: form.progress,
    }
    if (isEdit.value && props.task) {
      await updateTask(props.task.id, payload)
    } else {
      await createTask({ project_id: form.project_id, ...payload })
    }
    ElMessage.success('任务已保存')
    emit('update:modelValue', false)
    emit('saved')
  } finally {
    saving.value = false
  }
}
</script>
