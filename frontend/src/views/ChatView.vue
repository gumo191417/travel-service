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

const senderId = ref(
  localStorage.getItem('travel-sender') || 'demo-001'
)
const userId = ref(
  localStorage.getItem('travel-user') || '10001'
)

const messages = ref([])
const busy = ref(false)
const humanMode = ref(false)
const handoffNo = ref('')
const stateInfo = ref(null)
const showContext = ref(true)
const error = ref('')

const messagesEl = ref(null)
const lastCount = ref(-1)

let pollTimer = null
let errorTimer = null

const quickPrompts = [
  { text: '三亚有哪些五星酒店？', hint: '产品搜索' },
  { text: '帮我查订单 TR_DEMO_0001', hint: '订单状态' },
  { text: '这个订单哪天入住？', hint: '行程信息' },
  { text: '我要退款', hint: '退款申请' },
  { text: '退款政策是什么？', hint: '政策咨询' },
  { text: '我要转人工客服', hint: '人工接管' },
]

const objectShortcuts = [
  {
    label: '发送当前订单',
    object: {
      type: 'order',
      id: 'TR_DEMO_0001',
      title: '三亚酒店订单',
    },
  },
]

const activeTask = computed(
  () => stateInfo.value?.active_task || null
)
const slotEntries = computed(() =>
  Object.entries(stateInfo.value?.slots || {}).slice(0, 10)
)
const isHuman = computed(() => humanMode.value)

function identity() {
  const sender = senderId.value.trim() || 'demo-001'
  const user = Number(userId.value)
  return {
    senderId: sender,
    userId:
      Number.isFinite(user) && user > 0 ? user : undefined,
  }
}

function showError(message) {
  error.value = message
  clearTimeout(errorTimer)
  errorTimer = setTimeout(() => {
    error.value = ''
  }, 4200)
}

function scrollToBottom() {
  nextTick(() => {
    const element = messagesEl.value
    if (element) element.scrollTop = element.scrollHeight
  })
}

function setHumanMode(value) {
  const next = Boolean(value)
  humanMode.value = next

  if (next && !pollTimer) {
    // 人工模式下机器人不回复，改为轮询客服消息
    pollTimer = setInterval(
      () => loadHistory({ silent: true }),
      3000
    )
  }
  if (!next && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadHistory({
  silent = false,
  force = false,
} = {}) {
  try {
    const { senderId: sender } = identity()
    const data = await api.history(sender)
    setHumanMode(Boolean(data.human_mode))
    if (data.human_mode) {
      handoffNo.value = stateInfo.value?.handoff_no || handoffNo.value
    }

    if (force || data.messages.length !== lastCount.value) {
      messages.value = data.messages
      lastCount.value = data.messages.length
      scrollToBottom()
    }
  } catch (exception) {
    if (!silent) {
      showError(`加载历史失败：${exception.message}`)
    }
  }
}

async function refreshState({ silent = false } = {}) {
  try {
    const { senderId: sender } = identity()
    stateInfo.value = await api.state(sender)
    handoffNo.value = stateInfo.value.handoff_no || ''
    setHumanMode(Boolean(stateInfo.value.human_mode))
  } catch (exception) {
    if (!silent) {
      showError(`加载状态失败：${exception.message}`)
    }
  }
}

function pushLocalMessage(message) {
  messages.value = [...messages.value, message]
  scrollToBottom()
}

async function send(text) {
  const value = (text || '').trim()
  if (!value || busy.value) return

  const { senderId: sender, userId: user } = identity()
  pushLocalMessage({ role: 'user', text: value })
  busy.value = true

  try {
    const data = await api.chat({
      senderId: sender,
      userId: user,
      text: value,
    })
    setHumanMode(Boolean(data.human_mode))
    await loadHistory({ silent: true, force: true })
    if (showContext.value) await refreshState({ silent: true })
  } catch (exception) {
    showError(`发送失败：${exception.message}`)
    await loadHistory({ silent: true, force: true })
  } finally {
    busy.value = false
  }
}

async function sendObject(object) {
  if (busy.value) return

  const { senderId: sender, userId: user } = identity()
  pushLocalMessage({ role: 'user', object })
  busy.value = true

  try {
    const data = await api.chat({
      senderId: sender,
      userId: user,
      object,
    })
    setHumanMode(Boolean(data.human_mode))
    await loadHistory({ silent: true, force: true })
    if (showContext.value) await refreshState({ silent: true })
  } catch (exception) {
    showError(`发送失败：${exception.message}`)
    await loadHistory({ silent: true, force: true })
  } finally {
    busy.value = false
  }
}

async function newSession() {
  try {
    const { senderId: sender, userId: user } = identity()
    await api.newSession(sender, user)
    messages.value = []
    lastCount.value = -1
    stateInfo.value = null
    handoffNo.value = ''
    setHumanMode(false)
    await loadHistory({ silent: true, force: true })
    if (showContext.value) await refreshState({ silent: true })
  } catch (exception) {
    showError(`新建会话失败：${exception.message}`)
  }
}

function toggleContext() {
  showContext.value = !showContext.value
  if (showContext.value && !stateInfo.value) refreshState()
}

function formatSlot(value) {
  const text =
    typeof value === 'object' && value !== null
      ? JSON.stringify(value)
      : String(value)
  return text.length > 64 ? `${text.slice(0, 64)}…` : text
}

onMounted(() => {
  loadHistory()
  if (showContext.value) refreshState({ silent: true })
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  clearTimeout(errorTimer)
})
</script>

<template>
  <div
    class="workspace chat-workspace"
    :class="{ 'with-context': showContext }"
  >
    <aside class="rail">
      <div class="rail-card">
        <h2 class="rail-title">快速开始</h2>
        <div class="quick-list">
          <button
            v-for="prompt in quickPrompts"
            :key="prompt.text"
            class="quick-item"
            :disabled="busy"
            @click="send(prompt.text)"
          >
            {{ prompt.text }}
            <span>{{ prompt.hint }}</span>
          </button>
        </div>
      </div>

      <div class="rail-card">
        <h2 class="rail-title">对象卡片</h2>
        <div class="quick-list">
          <button
            v-for="item in objectShortcuts"
            :key="item.label"
            class="quick-item"
            :disabled="busy"
            @click="sendObject(item.object)"
          >
            {{ item.label }}
            <span>{{ item.object.id }}</span>
          </button>
        </div>
      </div>
    </aside>

    <main class="panel">
      <header class="panel-head">
        <div class="avatar bot">AI</div>
        <div>
          <div class="title">旅游客服助手</div>
          <div class="sub">酒店 · 景点 · 交通 · 订单 · 退款</div>
        </div>
        <div class="head-actions">
          <StatusPill :status="isHuman ? 'human' : 'online'" />
          <button class="btn btn-sm" @click="newSession">新会话</button>
          <button class="btn btn-sm" @click="loadHistory()">
            刷新
          </button>
          <button class="btn btn-sm" @click="toggleContext">
            {{ showContext ? '隐藏状态' : '会话状态' }}
          </button>
        </div>
      </header>

      <div ref="messagesEl" class="messages">
        <div v-if="isHuman" class="human-banner">
          <span class="dot" />
          人工客服已接管，消息会直接发送给客服
          <template v-if="handoffNo">· {{ handoffNo }}</template>
        </div>

        <div v-if="!messages.length && !busy" class="empty">
          <div class="glyph">✳</div>
          <h3>开始一段旅行咨询</h3>
          <p>
            可以按城市和日期搜索酒店、景点与交通，也可以直接查询订单、申请退款或转人工客服。
          </p>
        </div>

        <MessageBubble
          v-for="(message, index) in messages"
          :key="index"
          :message="message"
        />

        <div v-if="busy" class="typing">
          <span /><span /><span />
        </div>
      </div>

      <ChatComposer
        :disabled="busy"
        :placeholder="isHuman ? '消息将发送给人工客服…' : '输入消息，Enter 发送'"
        :hint-right="isHuman ? '人工模式下不会有机器人回复' : ''"
        @send="send"
      />
    </main>

    <aside v-if="showContext" class="panel context-panel">
      <header class="panel-head">
        <div>
          <div class="title">会话状态</div>
          <div class="sub">任务与槽位实时视图</div>
        </div>
        <div class="head-actions">
          <button class="btn btn-sm" @click="refreshState()">
            刷新
          </button>
        </div>
      </header>

      <div class="panel-body">
        <div class="kv">
          <span class="k">模式</span>
          <span class="v">{{ isHuman ? '人工接管' : '自动应答' }}</span>
        </div>
        <div v-if="handoffNo" class="kv">
          <span class="k">工单号</span>
          <span class="v">{{ handoffNo }}</span>
        </div>
        <div class="kv">
          <span class="k">活动任务</span>
          <span class="v">{{ activeTask ? activeTask.flow_id : '无' }}</span>
        </div>
        <div v-if="activeTask" class="kv">
          <span class="k">当前步骤</span>
          <span class="v">{{ activeTask.step_id }}</span>
        </div>

        <template v-if="slotEntries.length">
          <h2 class="rail-title" style="margin-top: 16px">槽位</h2>
          <div
            v-for="[key, value] in slotEntries"
            :key="key"
            class="kv"
          >
            <span class="k">{{ key }}</span>
            <span class="v">{{ formatSlot(value) }}</span>
          </div>
        </template>
      </div>
    </aside>
  </div>

  <div v-if="error" class="toast">{{ error }}</div>
</template>