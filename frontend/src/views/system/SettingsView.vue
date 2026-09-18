<template>
  <el-card v-loading="loading" shadow="never">
    <template #header>
      <div class="head-row">
        <span>系统设置</span>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </template>

    <el-tabs v-model="tab">
      <!-- 基础设置 -->
      <el-tab-pane label="基础设置" name="basic">
        <el-form label-width="180px" class="settings-form">
          <el-form-item label="系统名称">
            <el-input v-model="form.APP_NAME" maxlength="100" />
          </el-form-item>
          <el-form-item label="业务时区">
            <el-input v-model="form.APP_TIMEZONE" />
            <div class="hint">修改后需要重启服务生效</div>
          </el-form-item>
          <el-form-item label="对外访问地址">
            <el-input v-model="form.PUBLIC_BASE_URL" placeholder="https://lab.example.edu" />
            <div class="hint">用于生成设备二维码标签（PUBLIC_BASE_URL/q/{token}）；留空则二维码为站内路径</div>
          </el-form-item>
          <el-form-item label="通知中心">
            <el-switch v-model="form.NOTIFICATION_ENABLED" />
            <div class="hint">关闭后系统不再产生站内通知（操作仍会留痕）</div>
          </el-form-item>
          <el-form-item label="周报发布通知对象">
            <el-checkbox-group v-model="form.WEEKLY_REPORT_NOTIFY_ROLES">
              <el-checkbox value="PI">PI</el-checkbox>
              <el-checkbox value="TEACHER">教师</el-checkbox>
              <el-checkbox value="STUDENT">学生</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="学生可创建项目">
            <el-switch v-model="form.STUDENT_CAN_CREATE_PROJECT" />
            <div class="hint">实验室内部协同优先；关闭后仅 PI/教师可创建项目</div>
          </el-form-item>
          <el-form-item label="微信小程序入口">
            <el-switch v-model="form.WECHAT_MINIPROGRAM_ENABLED" />
            <div class="hint">开启后小程序可登录（需在 .env 配置 WECHAT_APPID/WECHAT_SECRET）</div>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- AI 助手 -->
      <el-tab-pane label="AI 助手" name="ai">
        <el-form label-width="180px" class="settings-form">
          <el-form-item label="启用 AI">
            <el-switch v-model="form.AI_ENABLED" />
          </el-form-item>
          <el-form-item label="API Base URL">
            <el-input v-model="form.AI_BASE_URL" placeholder="https://api.example.com/v1" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input
              v-model="apiKeyInput"
              type="password"
              show-password
              :placeholder="aiKeyConfigured ? '已配置（留空保持不变）' : '未配置'"
            />
            <el-tag v-if="aiKeyConfigured" size="small" type="success" style="margin-top: 4px">
              configured
            </el-tag>
            <el-button
              v-if="aiKeyConfigured"
              link
              type="danger"
              size="small"
              style="margin-top: 4px"
              @click="clearKey = true"
            >
              清除已保存的 Key
            </el-button>
          </el-form-item>
          <el-form-item label="模型">
            <el-input v-model="form.AI_MODEL" />
          </el-form-item>
          <el-form-item label="超时（秒）">
            <el-input-number v-model="form.AI_TIMEOUT_SECONDS" :min="5" :max="600" />
          </el-form-item>
          <el-form-item label="最大检索条数">
            <el-input-number v-model="form.AI_MAX_RETRIEVAL_HITS" :min="1" :max="50" />
          </el-form-item>
          <el-form-item label="最大上下文字符">
            <el-input-number v-model="form.AI_MAX_CONTEXT_CHARS" :min="1000" :max="200000" :step="1000" />
          </el-form-item>
          <el-form-item label="每分钟限流">
            <el-input-number v-model="form.AI_RATE_LIMIT_PER_MINUTE" :min="1" :max="1000" />
          </el-form-item>
          <el-form-item label="每天限流">
            <el-input-number v-model="form.AI_RATE_LIMIT_PER_DAY" :min="1" :max="100000" />
          </el-form-item>
          <el-form-item label="审计记录问题原文">
            <el-switch v-model="form.AI_AUDIT_STORE_QUERY" />
          </el-form-item>
          <el-form-item label="检索调试接口">
            <el-switch v-model="form.AI_DEBUG_RETRIEVAL" />
          </el-form-item>
          <el-form-item label="连接测试">
            <el-button :loading="testing" @click="runTest">测试连接</el-button>
            <el-tag
              v-if="testResult"
              size="small"
              :type="testResult.ok ? 'success' : 'danger'"
              style="margin-left: 8px"
            >
              {{ testResult.ok ? `成功 · ${testResult.model} · ${testResult.latency_ms}ms` : `失败 · ${testResult.message}` }}
            </el-tag>
            <div class="hint">测试使用「保存后的配置」，请先保存再测试</div>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 存储 -->
      <el-tab-pane label="存储" name="storage">
        <el-form label-width="180px" class="settings-form">
          <el-form-item label="单文件大小上限（MB）">
            <el-input-number v-model="form.UPLOAD_MAX_MB" :min="1" :max="2048" />
          </el-form-item>
          <el-form-item label="允许的扩展名">
            <el-input
              :model-value="form.ALLOWED_UPLOAD_EXTENSIONS.join(', ')"
              @update:model-value="(v: string) => (form.ALLOWED_UPLOAD_EXTENSIONS = v.split(',').map((s: string) => s.trim()).filter(Boolean))"
            />
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 微信小程序 -->
      <el-tab-pane label="微信绑定码" name="wechat">
        <div class="head-row" style="margin-bottom: 12px">
          <span style="color: #909399; font-size: 13px">
            成员首次绑定微信需要：账号密码 + 一次性绑定码（当面交付，30 分钟内有效，只能用一次）
          </span>
          <el-button type="primary" :loading="codeCreating" @click="newCode">生成绑定码</el-button>
        </div>
        <el-table :data="bindingCodes" size="small" stripe>
          <el-table-column label="绑定码" width="140">
            <template #default="{ row }">
              <span class="mono" style="font-size: 16px; font-weight: 600">{{ row.code }}</span>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="140">
            <template #default="{ row }">{{ row.remark ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="生成时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="过期时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.expires_at) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.state === 'valid' ? 'success' : 'info'">
                {{ { valid: '有效', used: '已使用', expired: '已过期' }[row.state as string] }}
              </el-tag>
            </template>
          </el-table-column>
          <template #empty><el-empty description="还没有生成过绑定码" :image-size="60" /></template>
        </el-table>
      </el-tab-pane>

      <!-- 部署与安全（只读） -->
      <el-tab-pane label="部署与安全" name="deploy">
        <el-alert type="info" show-icon :closable="false" title="以下为部署级配置，只能通过 .env / 环境变量修改，重启后生效" />
        <el-descriptions :column="1" border style="margin-top: 12px">
          <el-descriptions-item v-for="(value, key) in bootstrap" :key="key" :label="String(key)">
            <span class="mono">{{ value }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, testAIConnection, updateSettings } from '@/api/settings'
import { createBindingCode, listBindingCodes, type BindingCode } from '@/api/wechat'
import { formatDateTime } from '@/utils/datetime'

const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const tab = ref('basic')
const aiKeyConfigured = ref(false)
const apiKeyInput = ref('')
const clearKey = ref(false)
const testResult = ref<{ ok: boolean; model?: string; latency_ms?: number; message?: string } | null>(null)
const bootstrap = ref<Record<string, unknown>>({})

const form = reactive({
  APP_NAME: 'LabFlow',
  APP_TIMEZONE: 'Asia/Shanghai',
  PUBLIC_BASE_URL: '',
  NOTIFICATION_ENABLED: true,
  WEEKLY_REPORT_NOTIFY_ROLES: ['PI', 'TEACHER'] as string[],
  STUDENT_CAN_CREATE_PROJECT: true,
  WECHAT_MINIPROGRAM_ENABLED: false,
  AI_ENABLED: false,
  AI_BASE_URL: '',
  AI_MODEL: '',
  AI_TIMEOUT_SECONDS: 60,
  AI_MAX_CONTEXT_CHARS: 30000,
  AI_MAX_RETRIEVAL_HITS: 16,
  AI_AUDIT_STORE_QUERY: false,
  AI_DEBUG_RETRIEVAL: false,
  AI_RATE_LIMIT_PER_MINUTE: 10,
  AI_RATE_LIMIT_PER_DAY: 100,
  UPLOAD_MAX_MB: 100,
  ALLOWED_UPLOAD_EXTENSIONS: [] as string[],
})

const needsKeyClear = computed(() => clearKey.value)

async function load() {
  loading.value = true
  try {
    const { data } = await getSettings()
    Object.assign(form, data.data.runtime)
    aiKeyConfigured.value = data.data.AI_API_KEY_CONFIGURED
    bootstrap.value = data.data.bootstrap
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form }
    if (apiKeyInput.value) payload.AI_API_KEY = apiKeyInput.value
    if (needsKeyClear.value) payload.clear_ai_api_key = true
    const { data } = await updateSettings(payload)
    aiKeyConfigured.value = data.data.AI_API_KEY_CONFIGURED
    apiKeyInput.value = ''
    clearKey.value = false
    ElMessage.success('设置已保存')
    await load()
  } finally {
    saving.value = false
  }
}

async function runTest() {
  testing.value = true
  testResult.value = null
  try {
    const { data } = await testAIConnection()
    testResult.value = data.data
  } finally {
    testing.value = false
  }
}

// ---- wechat binding codes ----
const bindingCodes = ref<BindingCode[]>([])
const codeCreating = ref(false)

async function loadCodes() {
  try {
    const { data } = await listBindingCodes()
    bindingCodes.value = data.data
  } catch {
    bindingCodes.value = []
  }
}

async function newCode() {
  codeCreating.value = true
  try {
    const { data } = await createBindingCode({ ttl_minutes: 30 })
    ElMessage.success(`绑定码 ${data.data.code} 已生成，请当面交付给成员本人`)
    await loadCodes()
  } finally {
    codeCreating.value = false
  }
}

onMounted(() => {
  load()
  loadCodes()
})
</script>

<style scoped>
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.settings-form {
  max-width: 640px;
}

.hint {
  color: var(--lf-muted, #909399);
  font-size: 12px;
  line-height: 1.6;
}

.mono {
  font-family: monospace;
  word-break: break-all;
}
</style>
