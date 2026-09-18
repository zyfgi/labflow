import client from './client'

export interface RuntimeSettings {
  APP_NAME: string
  APP_TIMEZONE: string
  AI_ENABLED: boolean
  AI_BASE_URL: string
  AI_MODEL: string
  AI_TIMEOUT_SECONDS: number
  AI_MAX_CONTEXT_CHARS: number
  AI_MAX_RETRIEVAL_HITS: number
  AI_AUDIT_STORE_QUERY: boolean
  AI_DEBUG_RETRIEVAL: boolean
  AI_RATE_LIMIT_PER_MINUTE: number
  AI_RATE_LIMIT_PER_DAY: number
  UPLOAD_MAX_MB: number
  ALLOWED_UPLOAD_EXTENSIONS: string[]
}

export interface SettingsView {
  runtime: RuntimeSettings
  AI_API_KEY_CONFIGURED: boolean
  bootstrap: Record<string, unknown>
  restart_required: string[]
  updated_at: string | null
}

export interface AITestResult {
  ok: boolean
  model?: string
  latency_ms?: number
  code?: string
  message?: string
}

export function getSettings() {
  return client.get<{ data: SettingsView }>('/system/settings')
}

export function updateSettings(payload: Record<string, unknown>) {
  return client.patch<{ data: SettingsView }>('/system/settings', payload)
}

export function testAIConnection() {
  return client.post<{ data: AITestResult }>('/system/settings/ai/test')
}
