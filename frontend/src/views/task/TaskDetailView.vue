<template>
  <div v-if="task">
    <el-page-header style="margin-bottom: 12px" @back="$router.back()">
      <template #content>
        <span style="font-weight: 600">{{ task.title }}</span>
        <el-tag size="small" style="margin-left: 8px" :type="TASK_STATUS_TAGS[task.status]">
          {{ TASK_STATUS_LABELS[task.status] }}
        </el-tag>
        <el-tag v-if="task.is_overdue" size="small" type="danger" style="margin-left: 6px">已逾期</el-tag>
      </template>
    </el-page-header>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>任务详情</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="项目">
              <el-link type="primary" @click="$router.push(`/projects/${task.project_id}`)">
                {{ task.project_name }}
              </el-link>
            </el-descriptions-item>
            <el-descriptions-item label="负责人">{{ task.assignee_name ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="优先级">{{ PRIORITY_LABELS[task.priority] }}</el-descriptions-item>
            <el-descriptions-item label="截止日期">
              <span :style="task.is_overdue ? 'color:#f56c6c;font-weight:600' : ''">{{ formatDate(task.due_date) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="进度">{{ task.progress }}%</el-descriptions-item>
            <el-descriptions-item label="最近更新">{{ formatDateTime(task.updated_at) }}</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ task.description ?? '-' }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="task.can_edit" class="actions">
            <el-dropdown @command="setStatus" style="margin-right: 8px">
              <el-button size="small" type="primary" plain>
                更新状态 <el-icon><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="(label, key) in TASK_STATUS_LABELS" :key="key" :command="key">
                    {{ label }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <span style="color: #909399; margin-right: 8px">进度</span>
            <el-slider v-model="progress" style="width: 220px; margin-right: 8px" @change="saveProgress" />
          </div>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header>评论 / 活动记录</template>
          <div class="comments">
            <div v-for="c in comments" :key="c.id" class="comment">
              <div class="comment-meta">
                <b>{{ c.user_name ?? '用户' }}</b>
                <span>{{ formatDateTime(c.created_at) }}</span>
              </div>
              <div class="comment-body">{{ c.content }}</div>
            </div>
            <el-empty v-if="!comments.length" description="暂无评论" :image-size="60" />
          </div>
          <div class="comment-input">
            <el-input v-model="newComment" placeholder="添加评论..." @keyup.enter="sendComment" />
            <el-button type="primary" :loading="sending" @click="sendComment">发送</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
  <el-empty v-else-if="!loading" description="任务不存在或没有查看权限" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { addTaskComment, getTask, listTaskComments, setTaskStatus, updateTask, type Task, type TaskComment } from '@/api/tasks'
import { PRIORITY_LABELS, TASK_STATUS_LABELS, TASK_STATUS_TAGS } from '@/utils/constants'
import { formatDate, formatDateTime } from '@/utils/datetime'

const route = useRoute()
const taskId = computed(() => Number(route.params.id))
const loading = ref(true)
const task = ref<Task | null>(null)
const comments = ref<TaskComment[]>([])
const newComment = ref('')
const sending = ref(false)
const progress = ref(0)

async function load() {
  loading.value = true
  try {
    const { data } = await getTask(taskId.value)
    task.value = data.data
    progress.value = data.data.progress
    comments.value = (await listTaskComments(taskId.value)).data.data
  } catch {
    task.value = null
  } finally {
    loading.value = false
  }
}

async function setStatus(status: string) {
  if (!task.value) return
  const { data } = await setTaskStatus(taskId.value, status)
  task.value = data.data
  progress.value = data.data.progress
  ElMessage.success(`状态已更新为「${TASK_STATUS_LABELS[status]}」`)
}

async function saveProgress() {
  if (!task.value) return
  const { data } = await updateTask(taskId.value, { progress: progress.value })
  task.value = data.data
  ElMessage.success('进度已更新')
}

async function sendComment() {
  if (!newComment.value.trim()) return
  sending.value = true
  try {
    await addTaskComment(taskId.value, newComment.value.trim())
    newComment.value = ''
    comments.value = (await listTaskComments(taskId.value)).data.data
    ElMessage.success('评论已添加')
  } finally {
    sending.value = false
  }
}

watch(taskId, load)
onMounted(load)
</script>

<style scoped>
.actions {
  margin-top: 14px;
  display: flex;
  align-items: center;
}

.comments {
  max-height: 320px;
  overflow-y: auto;
}

.comment {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.comment-meta {
  display: flex;
  gap: 10px;
  color: #909399;
  font-size: 12px;
  margin-bottom: 4px;
}

.comment-body {
  font-size: 14px;
}

.comment-input {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
