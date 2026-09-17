<template>
  <div>
    <div class="toolbar">
      <span style="color: #909399; font-size: 13px">0 未接触 · 1 学习中 · 2 可在指导下完成 · 3 可独立完成 · 4 可指导他人</span>
      <el-button v-if="canEdit" type="primary" size="small" @click="editing = !editing">
        {{ editing ? '取消编辑' : '编辑技能' }}
      </el-button>
    </div>

    <el-table v-loading="loading" :data="allSkills" stripe>
      <el-table-column prop="name" label="技能" width="160" />
      <el-table-column prop="category" label="分类" width="120" />
      <el-table-column label="掌握等级" min-width="300">
        <template #default="{ row }">
          <template v-if="editing">
            <el-radio-group v-model="draft[row.id]" size="small">
              <el-radio-button v-for="lv in [0, 1, 2, 3, 4]" :key="lv" :value="lv">{{ lv }}</el-radio-button>
            </el-radio-group>
          </template>
          <template v-else>
            <el-rate
              :model-value="levels[row.id] ?? 0"
              :max="4"
              disabled
              :colors="['#c6d1de', '#409eff']"
              :texts="['未接触', '学习中', '指导下完成', '独立完成', '可指导他人']"
              show-text
              text-color="#606266"
              style="--el-rate-icon-margin: 1px"
            />
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="editing" label="备注" min-width="180">
        <template #default="{ row }">
          <el-input v-model="draftNotes[row.id]" size="small" placeholder="备注" />
        </template>
      </el-table-column>
    </el-table>

    <div v-if="editing" style="margin-top: 12px; text-align: right">
      <el-button type="primary" :loading="saving" @click="save">保存技能</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getMemberSkills, listSkills, setMemberSkills, type MemberSkill, type Skill } from '@/api/learning'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ memberId: number }>()

const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const editing = ref(false)
const allSkills = ref<Skill[]>([])
const memberSkills = ref<MemberSkill[]>([])

const canEdit = auth.isPI || auth.isTeacher || props.memberId === auth.user?.id

const draft = reactive<Record<number, number>>({})
const draftNotes = reactive<Record<number, string>>({})

const levels = computed<Record<number, number>>(() => {
  const map: Record<number, number> = {}
  for (const ms of memberSkills.value) map[ms.skill_id] = ms.level
  return map
})

async function load() {
  loading.value = true
  try {
    allSkills.value = await listSkills()
    memberSkills.value = await getMemberSkills(props.memberId)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const items = allSkills.value
      .filter((s) => (draft[s.id] ?? 0) > 0)
      .map((s) => ({ skill_id: s.id, level: draft[s.id] ?? 0, note: draftNotes[s.id] || undefined }))
    memberSkills.value = (await setMemberSkills(props.memberId, items)).data.data
    editing.value = false
    ElMessage.success('技能已更新')
  } finally {
    saving.value = false
  }
}

watch(editing, (on) => {
  if (!on) return
  for (const s of allSkills.value) {
    draft[s.id] = levels.value[s.id] ?? 0
    draftNotes[s.id] = memberSkills.value.find((m) => m.skill_id === s.id)?.note ?? ''
  }
})

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
</style>
