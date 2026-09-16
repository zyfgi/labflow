<template>
  <el-dropdown @command="doExport">
    <el-button :size="size">
      导出
      <el-icon class="el-icon--right"><arrow-down /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
        <el-dropdown-item command="xlsx">导出 Excel</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { downloadExport } from '@/api/system'

const props = defineProps<{ kind: string; size?: 'small' | 'default' | 'large' }>()
const busy = ref(false)

async function doExport(format: 'csv' | 'xlsx') {
  busy.value = true
  try {
    await downloadExport(props.kind, format)
    ElMessage.success('导出成功')
  } catch {
    /* error toast already handled by interceptor */
  } finally {
    busy.value = false
  }
}
</script>
