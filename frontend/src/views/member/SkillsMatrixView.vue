<template>
  <el-card shadow="never">
    <template #header>
      <div class="header-row">
        <span>技能矩阵</span>
        <el-button v-if="auth.isPI" size="small" type="primary" plain @click="skillDialog = true">新增技能项</el-button>
      </div>
    </template>
    <p style="margin-top: 0; color: #909399; font-size: 13px">
      0 未接触 · 1 学习中 · 2 可在指导下完成 · 3 可独立完成 · 4 可指导他人（点击单元格可编辑，仅自己/PI/教师）
    </p>

    <el-table v-loading="loading" :data="matrix.rows" border stripe size="small">
      <el-table-column fixed prop="name" label="姓名" width="110" />
      <el-table-column
        v-for="col in matrix.skills"
        :key="col.id"
        :label="col.name"
        :min-width="90"
        align="center"
      >
        <template #default="{ row }">
          <span
            class="cell-level"
            :class="{ editable: canEditRow(row) }"
            @click="canEditRow(row) && openCell(row, col)"
          >
            {{ row.levels[col.id] ?? '-' }}
          </span>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无成员数据" :image-size="70" />
      </template>
    </el-table>

    <el-dialog v-model="skillDialog" title="新增技能项" width="420px">
      <el-form label-width="70px">
        <el-form-item label="名称" required>
          <el-input v-model="newSkill.name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="newSkill.category" placeholder="如：编程语言/仿真工具" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="newSkill.description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="skillDialog = false">取消</el-button>
        <el-button type="primary" :loading="skillSaving" @click="saveSkill">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cellDialog.visible" :title="`设置技能：${cellDialog.memberName} / ${cellDialog.skillName}`" width="420px">
      <el-radio-group v-model="cellDialog.level">
        <el-radio-button v-for="lv in [0, 1, 2, 3, 4]" :key="lv" :value="lv">{{ lv }}</el-radio-button>
      </el-radio-group>
      <el-input v-model="cellDialog.note" placeholder="备注（可选）" style="margin-top: 12px" />
      <template #footer>
        <el-button @click="cellDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="cellDialog.saving" @click="saveCell">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getMemberSkills, listSkills, setMemberSkills, type Skill } from '@/api/learning'
import { listMembers, type Member } from '@/api/members'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const members = ref<Member[]>([])
const skillList = ref<Skill[]>([])
const skillMap = ref<Record<number, Record<number, number>>>({})

const skillDialog = ref(false)
const skillSaving = ref(false)
const newSkill = reactive({ name: '', category: '', description: '' })

const cellDialog = reactive({
  visible: false,
  saving: false,
  memberId: 0,
  memberName: '',
  skillId: 0,
  skillName: '',
  level: 0,
  note: '',
})

interface MatrixRow {
  id: number
  name: string
  levels: Record<number, number>
}

const matrix = computed(() => {
  const activeSkills = skillList.value
  const rows: MatrixRow[] = members.value.map((m) => ({
    id: m.id,
    name: m.user.name,
    levels: skillMap.value[m.id] ?? {},
  }))
  return { skills: activeSkills, rows }
})

function canEditRow(row: MatrixRow): boolean {
  return auth.canManage || row.id === auth.user?.id
}

async function load() {
  loading.value = true
  try {
    skillList.value = await listSkills()
    const { data } = await listMembers({ page_size: 100, status: 'active' })
    members.value = data.data.items
    const maps: Record<number, Record<number, number>> = {}
    await Promise.all(
      members.value.map(async (m) => {
        const skills = await getMemberSkills(m.id)
        maps[m.id] = Object.fromEntries(skills.map((s) => [s.skill_id, s.level]))
      }),
    )
    skillMap.value = maps
  } finally {
    loading.value = false
  }
}

async function saveSkill() {
  if (!newSkill.name.trim()) {
    ElMessage.warning('请输入技能名称')
    return
  }
  skillSaving.value = true
  try {
    const { createSkill } = await import('@/api/learning')
    await createSkill({ ...newSkill })
    ElMessage.success('技能项已添加')
    skillDialog.value = false
    newSkill.name = newSkill.category = newSkill.description = ''
    await load()
  } finally {
    skillSaving.value = false
  }
}

function openCell(row: MatrixRow, skill: Skill) {
  cellDialog.memberId = row.id
  cellDialog.memberName = row.name
  cellDialog.skillId = skill.id
  cellDialog.skillName = skill.name
  cellDialog.level = row.levels[skill.id] ?? 0
  cellDialog.note = ''
  cellDialog.visible = true
}

async function saveCell() {
  cellDialog.saving = true
  try {
    const current = await getMemberSkills(cellDialog.memberId)
    const kept = current.filter((s) => s.skill_id !== cellDialog.skillId && s.level > 0)
    const items = [
      ...kept.map((s) => ({ skill_id: s.skill_id, level: s.level })),
      ...(cellDialog.level > 0 ? [{ skill_id: cellDialog.skillId, level: cellDialog.level }] : []),
    ]
    await setMemberSkills(cellDialog.memberId, items)
    skillMap.value[cellDialog.memberId] = Object.fromEntries(items.map((i) => [i.skill_id, i.level]))
    cellDialog.visible = false
    ElMessage.success('已更新')
  } finally {
    cellDialog.saving = false
  }
}

onMounted(load)
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cell-level {
  display: inline-block;
  min-width: 24px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f0f2f5;
  font-weight: 600;
}

.cell-level.editable {
  cursor: pointer;
}

.cell-level.editable:hover {
  background: #d9ecff;
  color: #409eff;
}
</style>
