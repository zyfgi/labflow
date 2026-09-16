<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="名称/资产编号/型号"
          clearable
          style="width: 220px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-select v-model="query.status" clearable placeholder="状态" style="width: 130px" @change="load(1)">
          <el-option v-for="(label, key) in EQUIPMENT_STATUS_LABELS" :key="key" :label="label" :value="key" />
        </el-select>
        <el-button type="primary" plain @click="load(1)">查询</el-button>
      </div>
      <el-button v-if="canManage" type="primary" @click="openCreate">新增设备</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="资产编号" width="130">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/equipment/${row.id}`)">{{ row.asset_no }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="category" label="分类" width="110" />
      <el-table-column label="型号" min-width="140">
        <template #default="{ row }">{{ row.manufacturer }} {{ row.model }}</template>
      </el-table-column>
      <el-table-column prop="location" label="位置" width="130">
        <template #default="{ row }">{{ row.location ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="管理员" width="100">
        <template #default="{ row }">{{ row.manager_name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="EQUIPMENT_STATUS_TAGS[row.status]">
            {{ EQUIPMENT_STATUS_LABELS[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无设备" :image-size="70" />
      </template>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load()"
      />
    </div>

    <el-dialog v-model="dialog.visible" title="新增设备" width="560px">
      <el-form label-width="90px">
        <el-form-item label="资产编号" required>
          <el-input v-model="dialog.form.asset_no" placeholder="如 EQ-XXX-001" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="dialog.form.name" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-input v-model="dialog.form.category" placeholder="如：测量仪器" />
        </el-form-item>
        <el-form-item label="厂商/型号">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-input v-model="dialog.form.manufacturer" placeholder="厂商" />
            <el-input v-model="dialog.form.model" placeholder="型号" />
          </div>
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="dialog.form.location" />
        </el-form-item>
        <el-form-item label="需要预约">
          <el-switch v-model="dialog.form.booking_required" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dialog.form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createEquipment, listEquipment, type Equipment } from '@/api/equipment'
import { EQUIPMENT_STATUS_LABELS, EQUIPMENT_STATUS_TAGS } from '@/utils/constants'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canManage = computed(() => auth.isPI || auth.isEquipmentAdmin)
const loading = ref(false)
const items = ref<Equipment[]>([])
const total = ref(0)

const query = reactive({ page: 1, page_size: 20, keyword: '', status: '' })

async function load(page?: number) {
  if (page) query.page = page
  loading.value = true
  try {
    const { data } = await listEquipment({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status || undefined,
    })
    items.value = data.data.items
    total.value = data.data.total
  } finally {
    loading.value = false
  }
}

const dialog = reactive({
  visible: false,
  saving: false,
  form: { asset_no: '', name: '', category: '', manufacturer: '', model: '', location: '', booking_required: true, description: '' },
})

function openCreate() {
  dialog.form = { asset_no: '', name: '', category: '', manufacturer: '', model: '', location: '', booking_required: true, description: '' }
  dialog.visible = true
}

async function save() {
  dialog.saving = true
  try {
    await createEquipment({
      ...dialog.form,
      manufacturer: dialog.form.manufacturer || null,
      model: dialog.form.model || null,
      location: dialog.form.location || null,
      description: dialog.form.description || null,
    })
    dialog.visible = false
    await load(1)
  } finally {
    dialog.saving = false
  }
}

onMounted(() => load())
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
