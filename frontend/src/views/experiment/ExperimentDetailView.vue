<template>
  <div v-if="exp">
    <el-page-header style="margin-bottom: 12px" @back="$router.back()">
      <template #content>
        <span style="font-weight: 600; font-family: monospace">{{ exp.experiment_no }}</span>
        <el-tag size="small" style="margin-left: 8px" :type="EXPERIMENT_STATUS_TAGS[exp.status]">
          {{ EXPERIMENT_STATUS_LABELS[exp.status] }}
        </el-tag>
        <el-tag v-if="exp.is_locked" size="small" type="warning" style="margin-left: 6px">
          已锁定{{ exp.locked_at ? ` · ${formatDateTime(exp.locked_at)}` : '' }}
        </el-tag>
      </template>
    </el-page-header>

    <el-row :gutter="16">
      <el-col :span="17">
        <el-card shadow="never">
          <template #header>
            <div class="card-head">
              <b>{{ exp.title }}</b>
              <div>
                <el-button
                  v-if="exp.can_edit && !exp.is_locked"
                  size="small"
                  :type="editing ? 'warning' : 'primary'"
                  plain
                  @click="editing = !editing"
                >
                  {{ editing ? '取消编辑' : '编辑' }}
                </el-button>
                <el-button v-if="exp.can_lock && !exp.is_locked" size="small" type="warning" @click="lock">
                  锁定实验
                </el-button>
                <el-button v-if="exp.can_lock && exp.is_locked" size="small" type="success" @click="unlock">
                  解锁
                </el-button>
              </div>
            </div>
          </template>

          <el-form label-width="90px" :disabled="!editing" label-position="left">
            <el-row :gutter="12">
              <el-col :span="12"><el-form-item label="实验日期"><el-date-picker v-model="form.experiment_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
              <el-col :span="12">
                <el-form-item label="状态">
                  <el-select v-model="form.status" style="width: 100%">
                    <el-option v-for="(label, key) in EXPERIMENT_STATUS_LABELS" :key="key" :label="label" :value="key" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="实验目标"><el-input v-model="form.objective" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="背景"><el-input v-model="form.background" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="环境"><el-input v-model="form.environment" /></el-form-item>
            <el-form-item label="方法"><el-input v-model="form.method" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="参数"><el-input v-model="form.parameters" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="结果"><el-input v-model="form.result_summary" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="结论"><el-input v-model="form.conclusion" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="问题"><el-input v-model="form.problems" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="下一步"><el-input v-model="form.next_step" type="textarea" :rows="2" /></el-form-item>
            <el-divider content-position="left">可追溯信息</el-divider>
            <el-row :gutter="12">
              <el-col :span="12"><el-form-item label="代码仓库"><el-input v-model="form.code_repo_url" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="Git Commit"><el-input v-model="form.git_commit" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="数据位置"><el-input v-model="form.dataset_path" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="软件版本"><el-input v-model="form.software_version" /></el-form-item></el-col>
            </el-row>
            <el-form-item v-if="editing">
              <el-button type="primary" :loading="saving" @click="save">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="7">
        <el-card shadow="never">
          <template #header>信息</template>
          <el-descriptions :column="1">
            <el-descriptions-item label="项目">{{ exp.project_name }}</el-descriptions-item>
            <el-descriptions-item label="负责人">{{ exp.owner_name ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(exp.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="最近更新">{{ formatDateTime(exp.updated_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header>
            <div class="card-head">
              <b>附件</b>
              <el-upload
                v-if="exp.can_edit && !exp.is_locked"
                :show-file-list="false"
                :before-upload="beforeUpload"
                :http-request="doUpload"
              >
                <el-button size="small" type="primary" plain :loading="uploading">上传附件</el-button>
              </el-upload>
            </div>
          </template>
          <div v-for="a in exp.attachments" :key="a.id" class="att-row">
            <el-link type="primary" :href="attachmentDownloadUrl(a.id)" target="_blank">
              {{ a.file_name }}
            </el-link>
            <span class="att-size">{{ formatSize(a.file_size) }}</span>
            <el-button
              v-if="exp.can_edit && !exp.is_locked"
              link
              type="danger"
              size="small"
              @click="removeAttachment(a.id)"
            >
              删除
            </el-button>
          </div>
          <el-empty v-if="!exp.attachments?.length" description="暂无附件" :image-size="60" />
          <div v-if="exp.is_locked" style="color:#909399;font-size:12px;margin-top:8px">
            实验已锁定，附件不可变更（保证可追溯）
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
  <el-empty v-else-if="!loading" description="实验不存在或没有查看权限" />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadRequestOptions } from 'element-plus'
import {
  attachmentDownloadUrl,
  deleteAttachment,
  getExperiment,
  lockExperiment,
  unlockExperiment,
  updateExperiment,
  uploadAttachment,
  type Experiment,
} from '@/api/experiments'
import { EXPERIMENT_STATUS_LABELS, EXPERIMENT_STATUS_TAGS } from '@/utils/constants'
import { formatDate, formatDateTime } from '@/utils/datetime'

const route = useRoute()
const expId = computed(() => Number(route.params.id))
const loading = ref(true)
const exp = ref<Experiment | null>(null)
const editing = ref(false)
const saving = ref(false)
const uploading = ref(false)

const form = reactive<Record<string, string>>({})

function loadForm(e: Experiment) {
  Object.assign(form, {
    experiment_date: e.experiment_date ?? '',
    status: e.status,
    objective: e.objective ?? '',
    background: e.background ?? '',
    environment: e.environment ?? '',
    method: e.method ?? '',
    parameters: e.parameters ?? '',
    result_summary: e.result_summary ?? '',
    conclusion: e.conclusion ?? '',
    problems: e.problems ?? '',
    next_step: e.next_step ?? '',
    code_repo_url: e.code_repo_url ?? '',
    git_commit: e.git_commit ?? '',
    dataset_path: e.dataset_path ?? '',
    software_version: e.software_version ?? '',
  })
}

async function load() {
  loading.value = true
  try {
    const { data } = await getExperiment(expId.value)
    exp.value = data.data
    loadForm(data.data)
  } catch {
    exp.value = null
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const { data } = await updateExperiment(expId.value, { ...form })
    exp.value = data.data
    loadForm(data.data)
    editing.value = false
    ElMessage.success('实验已更新')
  } finally {
    saving.value = false
  }
}

async function lock() {
  await ElMessageBox.confirm('锁定后普通成员不能修改实验内容（保证可追溯）。确认锁定？', '锁定实验', { type: 'warning' })
  const { data } = await lockExperiment(expId.value)
  exp.value = { ...exp.value!, ...data.data }
  ElMessage.success('实验已锁定')
}

async function unlock() {
  await ElMessageBox.confirm('解锁实验将记录操作日志。确认解锁？', '解锁实验', { type: 'warning' })
  const { data } = await unlockExperiment(expId.value)
  exp.value = { ...exp.value!, ...data.data }
  ElMessage.success('实验已解锁')
}

function beforeUpload(file: File) {
  return true
}

async function doUpload(options: UploadRequestOptions) {
  uploading.value = true
  try {
    await uploadAttachment(expId.value, options.file)
    ElMessage.success('附件已上传')
    await load()
  } finally {
    uploading.value = false
  }
}

async function removeAttachment(id: number) {
  await ElMessageBox.confirm('确认删除该附件？', '提示', { type: 'warning' })
  await deleteAttachment(id)
  ElMessage.success('附件已删除')
  await load()
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

watch(expId, load)
onMounted(load)
</script>

<style scoped>
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.att-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.att-size {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
}
</style>
