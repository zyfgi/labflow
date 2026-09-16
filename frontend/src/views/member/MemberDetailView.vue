<template>
  <div v-if="member">
    <el-page-header style="margin-bottom: 12px" @back="$router.back()">
      <template #content>
        <span style="font-weight: 600">{{ member.user.name }}</span>
        <el-tag size="small" style="margin-left: 8px">{{ MEMBER_TYPE_LABELS[member.member_type] }}</el-tag>
      </template>
    </el-page-header>

    <el-tabs v-model="tab">
      <el-tab-pane label="概览" name="overview">
        <el-row :gutter="16">
          <el-col :span="10">
            <el-card shadow="never">
              <template #header>基本信息</template>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="姓名">{{ member.user.name }}</el-descriptions-item>
                <el-descriptions-item label="身份">{{ MEMBER_TYPE_LABELS[member.member_type] }}</el-descriptions-item>
                <el-descriptions-item label="年级">{{ member.grade_year ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="学号">{{ member.student_no ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="研究方向">{{ member.research_direction ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="入组时间">{{ formatDate(member.join_date) }}</el-descriptions-item>
                <el-descriptions-item label="预计毕业">{{ formatDate(member.expected_leave_date) }}</el-descriptions-item>
                <el-descriptions-item label="邮箱">{{ member.user.email }}</el-descriptions-item>
                <el-descriptions-item label="简介">{{ member.bio ?? '-' }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          <el-col :span="14">
            <el-card shadow="never">
              <template #header>科研状态</template>
              <div class="stat-row">
                <el-statistic title="进行中任务" :value="overview?.in_progress_tasks ?? 0" />
                <el-statistic title="逾期任务" :value="overview?.overdue_tasks ?? 0" />
                <el-statistic title="当前项目" :value="overview?.current_projects.length ?? 0" />
                <el-statistic title="最近实验" :value="overview?.latest_experiment_date ?? '-'" />
              </div>
              <el-divider />
              <p style="margin: 0 0 6px">
                本周周报：
                <el-tag v-if="overview?.this_week_report_status" size="small" :type="REPORT_STATUS_TAGS[overview.this_week_report_status]">
                  {{ REPORT_STATUS_LABELS[overview.this_week_report_status] }}
                </el-tag>
                <el-tag v-else size="small" type="info">未提交</el-tag>
              </p>
              <p style="margin: 0 0 6px; color: #606266; font-weight: 600">参与项目</p>
              <el-empty v-if="!overview?.current_projects.length" description="暂无项目" :image-size="60" />
              <ul v-else class="project-list">
                <li v-for="p in overview.current_projects" :key="p.id">
                  <el-link type="primary" @click="$router.push(`/projects/${p.id}`)">{{ p.name }}</el-link>
                  <el-tag size="small" :type="PROJECT_STATUS_TAGS[p.status]" style="margin: 0 8px">
                    {{ PROJECT_STATUS_LABELS[p.status] }}
                  </el-tag>
                  <span style="color: #909399">{{ p.progress }}%</span>
                </li>
              </ul>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="学习计划" name="plans" lazy>
        <LearningPlanList :member-id="memberId" />
      </el-tab-pane>

      <el-tab-pane label="技能" name="skills" lazy>
        <MemberSkillPanel :member-id="memberId" />
      </el-tab-pane>

      <el-tab-pane label="周报" name="reports" disabled>
        <template #label>周报（M3 开放）</template>
      </el-tab-pane>
      <el-tab-pane label="参与项目" name="projects" disabled>
        <template #label>参与项目（M4 开放）</template>
      </el-tab-pane>
      <el-tab-pane label="任务" name="tasks" disabled>
        <template #label>任务（M4 开放）</template>
      </el-tab-pane>
      <el-tab-pane label="实验记录" name="experiments" disabled>
        <template #label>实验记录（M5 开放）</template>
      </el-tab-pane>
    </el-tabs>
  </div>
  <el-empty v-else-if="!loading" description="成员不存在或没有查看权限" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getMember, getMemberOverview, type Member, type MemberOverview } from '@/api/members'
import { MEMBER_TYPE_LABELS, MEMBER_STATUS_LABELS, PROJECT_STATUS_LABELS, PROJECT_STATUS_TAGS, REPORT_STATUS_LABELS, REPORT_STATUS_TAGS } from '@/utils/constants'
import { formatDate } from '@/utils/datetime'
import LearningPlanList from '@/components/LearningPlanList.vue'
import MemberSkillPanel from '@/components/MemberSkillPanel.vue'

const route = useRoute()
const memberId = computed(() => Number(route.params.id))
const loading = ref(true)
const member = ref<Member | null>(null)
const overview = ref<MemberOverview | null>(null)
const tab = ref('overview')

async function load() {
  loading.value = true
  try {
    const { data } = await getMember(memberId.value)
    member.value = data.data
    const res = await getMemberOverview(memberId.value)
    overview.value = res.data.data
  } catch {
    member.value = null
  } finally {
    loading.value = false
  }
}

watch(memberId, load)
onMounted(load)
</script>

<style scoped>
.stat-row {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 12px;
}

.project-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.project-list li {
  padding: 4px 0;
}
</style>
