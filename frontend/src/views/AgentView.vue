<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue'

import { api } from '../api.js'
import ChatComposer from '../components/ChatComposer.vue'
import MessageBubble from '../components/MessageBubble.vue'
import StatusPill from '../components/StatusPill.vue'

const agentName = ref(
  localStorage.getItem('travel-agent') || '客服小王'
)
const filter = ref('pending')
const requests = ref([])
const selected = ref(null)
const messages = ref([])
const busy = ref(false)
const error = ref('')

const messagesEl = ref(null)
const lastConversationCount = ref(-1)

let listTimer = null
let convoTimer = null
let errorTimer = null

const filters = [
  { value: 'pending', label: '待接入' },
  { value: 'taken', label: '处理中' },
  { value: 'closed', label: '已关闭' },
  { value: '', label: '全部' },
]

const isClosed = computed(
  () => selected.value?.status === 'closed'
)

function showError(message) {
  error.value = message
  clearTimeout(errorTimer)
  errorTimer = setTimeout(() => {
    error.value = ''
  }, 4200)
}

function persistAgent() {
  const value = agentName.value.trim() || '客服'
  agentName.value = value
  localStorage.setItem('travel-agent', value)
}

function scrollToBottom() {
  nextTick(() => {
    const element = messagesEl.value
    if (element) element.scrollTop = element.scrollHeight
  })
}

async function loadRequests({ silent = false } = {}) {
  try {
    const data = await api.handoffList(filter.value || undefined)
    requests.value = data.list

    // 同步当前选中单的状态
    const current = requests.value.find(
      (item) => item.handoff_no === selected.value?.handoff_no
    )
    if (current) selected.value = current

    // 默认选中第一条
    if (!selected.value && requests.value.length) {
      selectRequest(requests.value[0])
    }
  } catch (exception) {
    if (!silent) {
      showError(`加载队列失败：${exception.message}`)
    }
  }
}

async function loadConversation({ silent = false } = {}) {
  const request = selected.value
  if (!request) {
    messages.value = []
    return
  }

  try {
    const data = await api.history(request.sender_id)
    if (data.messages.length !== lastConversationCount.value) {
      messages.value = data.messages
      lastConversationCount.value = data.messages.length
      scrollToBottom()
    }
  } catch (exception) {
    if (!silent) {
      showError(`加载会话失败：${exception.message}`)
    }
  }
}

function selectRequest(request) {
  if (!request) return
  if (selected.value?.handoff_no === request.handoff_no) return

  selected.value = request
  messages.value = []
  lastConversationCount.value = -1
  loadConversation()
}

function setFilter(value) {
  filter.value = value
  selected.value = null
  messages.value = []
  lastConversationCount.value = -1
  loadRequests()
}

async function takeover() {
  if (!selected.value || busy.value) return
  persistAgent()
  busy.value = true

  try {
    const updated = await api.takeover(
      selected.value.handoff_no,
      agentName.value
    )
    selected.value = updated
    await loadRequests({ silent: true })
  } catch (exception) {
    showError(`接单失败：${exception.message}`)
  } finally {
    busy.value = false
  }
}

async function reply(text) {
  if (!selected.value || isClosed.value || busy.value) return
  persistAgent()
  busy.value = true

  try {
    await api.reply(
      selected.value.handoff_no,
      text,
      agentName.value
    )
    await loadConversation({ silent: true })
    await loadRequests({ silent: true })
  } catch (exception) {
    showError(`回复失败：${exception.message}`)
  } finally {
    busy.value = false
  }
}

async function closeRequest() {
  if (!selected.value || busy.value) return
  busy.value = true

  try {
    const updated = await api.closeHandoff(
      selected.value.handoff_no
    )
    selected.value = updated
    await loadRequests({ silent: true })
  } catch (exception) {
    showError(`关闭失败：${exception.message}`)
  } finally {
    busy.value = false
  }
}

function formatTime(value) {
  if (!value) return '-'
  const date = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  loadRequests()
  listTimer = setInterval(
    () => loadRequests({ silent: true }),
    5000
  )
  convoTimer = setInterval(
    () => loadConversation({ silent: true }),
    3000
  )
})

onBeforeUnmount(() => {
  if (listTimer) clearInterval(listTimer)
  if (convoTimer) clearInterval(convoTimer)
  clearTimeout(errorTimer)
})
</script>

<template>
  <div class="workspace agent-workspace">
    <section class="panel list-panel">
      <header class="panel-head">
        <div>
          <div class="title">转人工队列</div>
          <div class="sub">{{ requests.length }} 条记录</div>
        </div>
        <div class="head-actions">
          <button
            class="btn btn-sm icon-btn"
            title="刷新队列"
            @click="loadRequests()"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M21 12a9 9 0 1 1-3-6.7" />
              <path d="M21 3v6h-6" />
            </svg>
          </button>
        </div>
      </header>

      <div class="filter-row">
        <button
          v-for="item in filters"
          :key="item.value"
          class="filter-chip"
          :class="{ active: filter === item.value }"
          @click="setFilter(item.value)"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="panel-body">
        <div
          v-if="!requests.length"
          class="empty"
          style="padding: 30px 16px"
        >
          <div class="glyph">☰</div>
          <h3>暂无转人工</h3>
          <p>用户说“转人工”后，记录会出现在这里。</p>
        </div>

        <button
          v-for="request in requests"
          :key="request.handoff_no"
          class="request-card"
          :class="{
            active:
              request.handoff_no === selected?.handoff_no,
          }"
          @click="selectRequest(request)"
        >
          <div class="request-top">
            <span class="request-no">{{ request.handoff_no }}</span>
            <StatusPill :status="request.status" />
          </div>
          <div class="request-meta">
            <span>会话 {{ request.sender_id }}</span>
            <span>{{ formatTime(request.created_at) }}</span>
          </div>
          <div class="request-reason">
            {{ request.reason || '用户请求人工客服' }}
          </div>
        </button>
      </div>
    </section>

    <section class="panel convo-panel">
      <header class="panel-head">
        <template v-if="selected">
          <div>
            <div class="title">会话 {{ selected.sender_id }}</div>
            <div class="sub">
              {{ selected.handoff_no }} ·
              {{ selected.agent_name || '未接单' }}
            </div>
          </div>
          <div class="convo-head-actions">
            <input
              v-model="agentName"
              class="input"
              style="width: 110px; padding: 6px 9px; font-size: 12px"
              aria-label="客服名称"
              @change="persistAgent"
            />
            <button
              v-if="selected.status === 'pending'"
              class="btn btn-sm btn-primary"
              :disabled="busy"
              @click="takeover"
            >
              接单
            </button>
            <button
              v-if="!isClosed"
              class="btn btn-sm btn-danger"
              :disabled="busy"
              @click="closeRequest"
            >
              关闭
            </button>
            <StatusPill :status="selected.status" />
          </div>
        </template>
        <template v-else>
          <div>
            <div class="title">客服工作台</div>
            <div class="sub">选择左侧转人工单开始处理</div>
          </div>
        </template>
      </header>

      <div ref="messagesEl" class="messages">
        <div v-if="!selected" class="empty">
          <div class="glyph">✦</div>
          <h3>等待选择会话</h3>
          <p>
            从左侧队列选择一条转人工单，查看用户消息并以客服身份回复。
          </p>
        </div>

        <template v-else>
          <div v-if="!messages.length" class="empty">
            <div class="glyph">…</div>
            <h3>暂无消息</h3>
            <p>用户的对话会实时同步到这里。</p>
          </div>

          <MessageBubble
            v-for="(message, index) in messages"
            :key="index"
            :message="message"
            perspective="agent"
          />
        </template>
      </div>

      <ChatComposer
        v-if="selected"
        :disabled="isClosed || busy"
        :placeholder="
          isClosed ? '会话已关闭' : '以客服身份回复…'
        "
        hint-left="Enter 发送 · 回复会实时同步到用户端"
        @send="reply"
      />
    </section>
  </div>

  <div v-if="error" class="toast">{{ error }}</div>
</template>