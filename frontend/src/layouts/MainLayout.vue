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
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bell,
  DataAnalysis,
  Monitor,
  Odometer,
  Setting,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS } from '@/utils/constants'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => (route.meta.menu as string) ?? 'dashboard')

async function onCommand(command: string) {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    await auth.logout()
    router.push('/login')
  }
}
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
