<template>
  <el-card shadow="never" class="ai-card">
    <div class="ai-layout">
      <!-- left: conversation history -->
      <div class="ai-side">
        <el-button type="primary" style="width: 100%" @click="store.newConversation()">
          + 新对话
        </el-button>
        <div class="conv-list">
          <div
            v-for="c in store.conversations"
            :key="c.id"
            class="conv-item"
            :class="{ active: c.id === store.conversationId }"
            @click="store.openConversation(c.id)"
          >
            <span class="conv-title">{{ c.title }}</span>
            <el-popconfirm title="删除该对话？" confirm-button-text="删除" cancel-button-text="取消" @confirm="store.removeConversation(c.id)">
              <template #reference>
                <el-icon class="conv-del" @click.stop><Delete /></el-icon>
              </template>
            </el-popconfirm>
          </div>
          <el-empty v-if="!store.conversations.length" description="暂无历史对话" :image-size="50" />
        </div>
      </div>

      <!-- right: chat -->
      <div class="ai-main">
        <el-alert
          v-if="!store.aiEnabled"
          type="info"
          show-icon
          :closable="false"
          title="AI assistant is not enabled"
          description="Set AI_ENABLED / AI_BASE_URL / AI_API_KEY / AI_MODEL in backend .env and restart."
        />
        <div ref="messageBox" class="messages">
          <template v-if="store.hasMessages">
            <div v-for="(m, i) in store.messages" :key="i" class="msg" :class="m.role">
              <div class="bubble">
                <div class="content">{{ m.content }}</div>
                <div v-if="m.role === 'assistant' && m.sources.length" class="sources">
                  <span class="sources-label">参考来源：</span>
                  <el-tag
                    v-for="s in m.sources"
                    :key="`${s.type}-${s.id}`"
                    size="small"
                    class="source-tag"
                    type="info"
                    @click="gotoSource(s)"
                  >
                    {{ sourceLabel(s) }}
                  </el-tag>
                </div>
              </div>
            </div>
          </template>

          <div v-else class="welcome">
            <h3>LabFlow AI 助手</h3>
            <p style="color: #909399">
              只读助手：回答来自你有权限访问的实验室数据，并附来源链接。
            </p>
            <div class="suggestions">
              <el-button
                v-for="q in store.recommendedQuestions"
                :key="q"
                plain
                size="small"
                @click="ask(q)"
              >
                {{ q }}
              </el-button>
            </div>
          </div>

          <div v-if="store.sending" class="msg assistant">
            <div class="bubble"><el-icon class="is-loading"><Loading /></el-icon> 正在检索本地数据并生成回答…</div>
          </div>
        </div>

        <div class="input-row">
          <el-input
            v-model="draft"
            placeholder="输入问题，例如：我有哪些未完成的任务？"
            :disabled="store.sending || !store.aiEnabled"
            maxlength="4000"
            @keyup.enter="ask()"
          />
          <el-button type="primary" :loading="store.sending" :disabled="!store.aiEnabled" @click="ask()">
            发送
          </el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Delete, Loading } from '@element-plus/icons-vue'
import { useAiStore } from '@/stores/ai'
import { SOURCE_TYPE_LABELS, type AISource } from '@/api/ai'

const store = useAiStore()
const router = useRouter()
const draft = ref('')
const messageBox = ref<HTMLElement>()

function sourceLabel(s: AISource): string {
  return `${SOURCE_TYPE_LABELS[s.type] ?? s.type} · ${s.title}`
}

function gotoSource(s: AISource) {
  if (s.url) router.push(s.url)
}

async function ask(preset?: string) {
  const question = (preset ?? draft.value).trim()
  if (!question) return
  draft.value = ''
  await store.send(question)
  await nextTick()
  messageBox.value?.scrollTo({ top: messageBox.value.scrollHeight, behavior: 'smooth' })
}

onMounted(async () => {
  await store.loadStatus()
  await store.refreshConversations()
})
</script>

<style scoped>
.ai-card :deep(.el-card__body) {
  padding: 0;
}

.ai-layout {
  display: flex;
  height: calc(100vh - 130px);
  min-height: 480px;
}

.ai-side {
  width: 240px;
  border-right: 1px solid #ebeef5;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.conv-list {
  overflow-y: auto;
  flex: 1;
}

.conv-item {
  display: flex;
  align-items: center;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  gap: 6px;
  color: #303133;
  font-size: 13px;
}

.conv-item:hover,
.conv-item.active {
  background: #ecf5ff;
}

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-del {
  color: #c0c4cc;
}

.conv-del:hover {
  color: #f56c6c;
}

.ai-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.msg {
  display: flex;
  margin-bottom: 12px;
}

.msg.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 78%;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f4f4f5;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.msg.user .bubble {
  background: #409eff;
  color: #fff;
}

.content {
  word-break: break-word;
}

.sources {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.sources-label {
  font-size: 12px;
  color: #909399;
}

.source-tag {
  cursor: pointer;
}

.source-tag:hover {
  background: #409eff;
  color: #fff;
}

.welcome {
  text-align: center;
  padding-top: 60px;
}

.suggestions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 320px;
  margin: 20px auto 0;
}

.input-row {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #ebeef5;
}
</style>
