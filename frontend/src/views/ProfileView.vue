<template>
  <el-row :gutter="16">
    <el-col :span="10">
      <el-card shadow="never">
        <template #header>个人信息</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户名">{{ auth.user?.username }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ auth.user?.name }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ ROLE_LABELS[auth.user?.role ?? ''] }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ auth.user?.email }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ auth.user?.phone ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="最近登录">{{ formatDateTime(auth.user?.last_login_at) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-col>
    <el-col :span="14">
      <el-card shadow="never">
        <template #header>修改密码</template>
        <el-alert
          v-if="auth.user?.must_change_password"
          type="warning"
          show-icon
          :closable="false"
          style="margin-bottom: 16px"
        >
          检测到您仍在使用初始密码，请修改。
        </el-alert>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" style="max-width: 420px">
          <el-form-item label="原密码" prop="oldPassword">
            <el-input v-model="form.oldPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码" prop="newPassword">
            <el-input v-model="form.newPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm">
            <el-input v-model="form.confirm" type="password" show-password />
          </el-form-item>
          <el-button type="primary" :loading="saving" @click="submit">修改密码</el-button>
        </el-form>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS } from '@/utils/constants'
import { formatDateTime } from '@/utils/datetime'

const auth = useAuthStore()
const router = useRouter()

const formRef = ref<FormInstance>()
const saving = ref(false)
const form = reactive({ oldPassword: '', newPassword: '', confirm: '' })

const rules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    {
      validator: (_rule, value, callback) => {
        if (value !== form.newPassword) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await auth.resetPassword(form.oldPassword, form.newPassword)
    ElMessage.success('密码修改成功')
    form.oldPassword = form.newPassword = form.confirm = ''
    if (router.currentRoute.value.path === '/profile') {
      // stay; user info refreshed in store
    }
  } finally {
    saving.value = false
  }
}
</script>
