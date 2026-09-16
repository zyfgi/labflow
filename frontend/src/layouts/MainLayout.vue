<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <span class="logo-badge">LF</span>
        <span class="logo-text">LabFlow</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
        :collapse="false"
        background-color="#1f2d3d"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="dashboard" route="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>

        <template v-if="auth.canManage">
          <el-sub-menu index="member">
            <template #title>
              <el-icon><User /></el-icon>
              <span>成员</span>
            </template>
            <el-menu-item index="member-list" route="/members">成员列表</el-menu-item>
            <el-menu-item index="member-plans" route="/learning-plans">学习计划</el-menu-item>
            <el-menu-item index="member-skills" route="/skills-matrix">技能矩阵</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="research">
            <template #title>
              <el-icon><DataAnalysis /></el-icon>
              <span>科研</span>
            </template>
            <el-menu-item index="projects" route="/projects">项目</el-menu-item>
            <el-menu-item index="tasks" route="/tasks">任务</el-menu-item>
            <el-menu-item index="experiments" route="/experiments">实验记录</el-menu-item>
            <el-menu-item index="reports" route="/weekly-reports">周报</el-menu-item>
          </el-sub-menu>
        </template>

        <template v-if="auth.isStudent">
          <el-sub-menu index="research">
            <template #title>
              <el-icon><DataAnalysis /></el-icon>
              <span>科研</span>
            </template>
            <el-menu-item index="projects" route="/projects">项目</el-menu-item>
            <el-menu-item index="my-tasks" route="/tasks">我的任务</el-menu-item>
            <el-menu-item index="experiments" route="/experiments">实验记录</el-menu-item>
            <el-menu-item index="reports" route="/weekly-reports">我的周报</el-menu-item>
            <el-menu-item index="member-plans" route="/learning-plans">学习计划</el-menu-item>
          </el-sub-menu>
        </template>

        <el-sub-menu index="equipment">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>设备</span>
          </template>
          <el-menu-item index="equipment" route="/equipment">设备台账</el-menu-item>
          <el-menu-item index="bookings" route="/equipment-bookings">设备预约</el-menu-item>
          <el-menu-item index="borrows" route="/equipment-borrows">借用记录</el-menu-item>
          <el-menu-item index="maintenance" route="/equipment-maintenance">故障维修</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="notifications" route="/notifications">
          <el-icon><Bell /></el-icon>
          <span>通知</span>
        </el-menu-item>

        <el-sub-menu v-if="auth.isPI" index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="system-users" route="/system/users">用户与角色</el-menu-item>
          <el-menu-item index="system-audit" route="/system/audit-logs">操作日志</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header" height="50px">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="header-right">
          <el-popover width="380" trigger="focus" :visible="searchVisible">
            <template #reference>
              <el-input
                v-model="searchKw"
                placeholder="搜索 成员/项目/任务/实验/设备"
                size="small"
                style="width: 250px; margin-right: 10px"
                clearable
                @input="onSearch"
                @blur="closeSearchSoon"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
            </template>
            <div style="max-height: 320px; overflow-y: auto">
              <template v-if="searchResults">
                <div v-if="searchResults.projects.length" class="sec">项目</div>
                <div v-for="p in searchResults.projects" :key="`p${p.id}`" class="hit" @mousedown="go(`/projects/${p.id}`)">
                  {{ p.name }} <span class="dim">{{ p.code }}</span>
                </div>
                <div v-if="searchResults.tasks.length" class="sec">任务</div>
                <div v-for="t in searchResults.tasks" :key="`t${t.id}`" class="hit" @mousedown="go(`/tasks/${t.id}`)">
                  {{ t.title }}
                </div>
                <div v-if="searchResults.experiments.length" class="sec">实验</div>
                <div v-for="e in searchResults.experiments" :key="`e${e.id}`" class="hit" @mousedown="go(`/experiments/${e.id}`)">
                  <span style="font-family: monospace">{{ e.experiment_no }}</span> {{ e.title }}
                </div>
                <div v-if="searchResults.equipment.length" class="sec">设备</div>
                <div v-for="q in searchResults.equipment" :key="`q${q.id}`" class="hit" @mousedown="go(`/equipment/${q.id}`)">
                  {{ q.name }} <span class="dim">{{ q.asset_no }}</span>
                </div>
                <div v-if="searchResults.members.length" class="sec">成员</div>
                <div v-for="m in searchResults.members" :key="`m${m.id}`" class="hit" @mousedown="go(`/members/${m.id}`)">
                  {{ m.name }}
                </div>
                <el-empty v-if="!hasAny" description="无匹配结果" :image-size="40" />
              </template>
            </div>
          </el-popover>

          <el-popover width="420" trigger="click" @show="loadBell">
            <template #reference>
              <el-badge :value="bellUnread" :hidden="!bellUnread" :max="99" class="bell">
                <el-icon :size="18"><BellFilled /></el-icon>
              </el-badge>
            </template>
            <div style="max-height: 360px; overflow-y: auto">
              <div
                v-for="n in bellItems"
                :key="n.id"
                class="bell-item"
                :class="{ unread: !n.is_read }"
                @click="goNotifications"
              >
                <div class="bell-title">{{ n.title }}</div>
                <div class="bell-content">{{ n.content }}</div>
                <div class="bell-time">{{ formatDateTime(n.created_at) }}</div>
              </div>
              <el-empty v-if="!bellItems.length" description="暂无通知" :image-size="50" />
            </div>
          </el-popover>

          <el-dropdown @command="onCommand">
            <span class="user-chip">
              <el-icon><UserFilled /></el-icon>
              {{ auth.user?.name }}
              <el-tag size="small" type="info" style="margin-left: 6px">
                {{ ROLE_LABELS[auth.user?.role ?? ''] ?? auth.user?.role }}
              </el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bell,
  BellFilled,
  DataAnalysis,
  Monitor,
  Odometer,
  Search,
  Setting,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { globalSearch, listNotifications } from '@/api/system'
import { ROLE_LABELS } from '@/utils/constants'
import { formatDateTime } from '@/utils/datetime'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => (route.meta.menu as string) ?? 'dashboard')

const bellItems = ref<any[]>([])
const bellUnread = ref(0)

const searchKw = ref('')
const searchVisible = ref(false)
const searchResults = ref<any>(null)
const hasAny = computed(() =>
  searchResults.value
    ? Object.values(searchResults.value).some((list: any) => list.length > 0)
    : false,
)

let searchTimer: ReturnType<typeof setTimeout> | null = null

async function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  const kw = searchKw.value.trim()
  if (!kw) {
    searchVisible.value = false
    searchResults.value = null
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const { data } = await globalSearch(kw)
      searchResults.value = data.data
      searchVisible.value = true
    } catch {
      /* ignore */
    }
  }, 250)
}

function closeSearchSoon() {
  setTimeout(() => (searchVisible.value = false), 200)
}

function go(path: string) {
  searchVisible.value = false
  searchKw.value = ''
  searchResults.value = null
  router.push(path)
}

async function loadBell() {
  try {
    const { data } = await listNotifications({ page: 1, page_size: 8 })
    bellItems.value = data.data.items
    bellUnread.value = data.data.unread
  } catch {
    /* ignore */
  }
}

function goNotifications() {
  router.push('/notifications')
}

async function onCommand(command: string) {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    await auth.logout()
    router.push('/login')
  }
}

onMounted(loadBell)
</script>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  background-color: #1f2d3d;
  overflow-x: hidden;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
}

.logo-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: #409eff;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}

.logo-text {
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.menu {
  border-right: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.bell {
  cursor: pointer;
  display: flex;
  align-items: center;
}

.bell-item {
  padding: 6px 4px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}

.bell-item.unread .bell-title {
  font-weight: 600;
}

.bell-title {
  font-size: 13px;
}

.bell-content {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bell-time {
  font-size: 11px;
  color: #c0c4cc;
}

.sec {
  font-size: 12px;
  color: #909399;
  padding: 4px 4px 2px;
}

.hit {
  padding: 5px 6px;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
}

.hit:hover {
  background: #f5f7fa;
}

.dim {
  color: #909399;
  font-size: 12px;
  margin-left: 4px;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #303133;
  font-size: 14px;
}

.main {
  padding: 16px;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  overflow-y: auto;
}
</style>
