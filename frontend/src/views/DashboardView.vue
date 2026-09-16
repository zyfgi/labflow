<template>
  <div>
    <el-alert
      v-if="auth.user?.must_change_password"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    >
      您仍在使用初始密码，请尽快到
      <router-link to="/profile">个人设置</router-link>
      修改密码。
    </el-alert>
    <el-card shadow="never">
      <el-empty description="Dashboard 将在 Milestone 7 完成真实数据接入" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>
