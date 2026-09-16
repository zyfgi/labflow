<template>
  <el-dialog :model-value="modelValue" title="新建实验记录" width="600px" @update:model-value="(v: boolean) => emit('update:modelValue', v)">
    <el-form label-width="80px">
      <el-form-item label="所属项目" required>
        <el-select v-model="form.project_id" filterable style="width: 100%">
          <el-option v-for="p in projects" :key="p.id" :label="`${p.name} (${p.code})`" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="实验名称" required>
        <el-input v-model="form.title" maxlength="200" />
      </el-form-item>
      <el-form-item label="实验目标">
        <el-input v-model="form.objective" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="实验环境">
        <el-input v-model="form.environment" placeholder="台架/仿真平台/实车" />
      </el-form-item>
      <el-form-item label="方法">
        <el-input v-model="form.method" />
      </el-form-item>
      <el-form-item label="实验日期">
        <el-date-picker v-model="form.experiment_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createExperiment } from '@/api/experiments'
import { listProjects, type Project } from '@/api/projects'
import { today } from '@/utils/datetime'

const props = defineProps<{ modelValue: boolean; projectId?: number }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>()

const projects = ref<Project[]>([])
const saving = ref(false)

const form = reactive({
  project_id: 0,
  title: '',
  objective: '',
  environment: '',
  method: '',
  experiment_date: today(),
})

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    if (!projects.value.length) {
      const { data } = await listProjects({ page_size: 100 })
      projects.value = data.data.items
    }
    form.project_id = props.projectId ?? 0
    form.title = ''
    form.objective = ''
    form.environment = ''
    form.method = ''
    form.experiment_date = today()
  },
)

async function save() {
  if (!form.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请输入实验名称')
    return
  }
  saving.value = true
  try {
    await createExperiment({
      project_id: form.project_id,
      title: form.title,
      objective: form.objective || null,
      environment: form.environment || null,
      method: form.method || null,
      experiment_date: form.experiment_date || null,
    })
    ElMessage.success('实验已创建')
    emit('update:modelValue', false)
    emit('saved')
  } finally {
    saving.value = false
  }
}
</script>
