<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select
        v-if="auth.canManage"
        v-model="memberId"
        filterable
        clearable
        placeholder="按成员筛选"
        style="width: 220px"
        @change="load"
      >
        <el-option v-for="m in members" :key="m.id" :label="m.user.name" :value="m.id" />
      </el-select>
      <el-select v-model="status" clearable placeholder="状态" style="width: 140px" @change="load">
        <el-option v-for="(label, key) in PLAN_STATUS_LABELS" :key="key" :label="label" :value="key" />
      </el-select>
      <span></span>
    </div>

    <LearningPlanList v-if="targetMemberId" :key="targetMemberId" :member-id="targetMemberId" />
    <el-empty v-else description="请选择成员" />
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import LearningPlanList from '@/components/LearningPlanList.vue'
import { listMembers, type Member } from '@/api/members'
import { listPlans } from '@/api/learning'
import { PLAN_STATUS_LABELS } from '@/utils/constants'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const members = ref<Member[]>([])
const memberId = ref<number>()
const status = ref('')

// students always target their own member id
const ownMemberId = ref<number>()
const targetMemberId = computed(() => (auth.canManage ? memberId.value : ownMemberId.value))

async function load() {
  /* data is loaded inside LearningPlanList; filters are passed via key remount */
}

onMounted(async () => {
  if (auth.canManage) {
    const { data } = await listMembers({ page_size: 100 })
    members.value = data.data.items
  } else {
    const { default: client } = await import('@/api/client')
    const res = await client.get('/members/me')
    ownMemberId.value = res.data.data?.id
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
