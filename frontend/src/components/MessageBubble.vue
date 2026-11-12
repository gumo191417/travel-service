<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
  // user：站在用户视角（用户消息靠右）
  // agent：站在客服视角（客服回复靠右）
  perspective: {
    type: String,
    default: 'user',
  },
})

const role = computed(() => props.message.role || 'bot')
const isAgentPerspective = computed(
  () => props.perspective === 'agent'
)

const displayRole = computed(() => {
  if (!isAgentPerspective.value) return role.value
  if (role.value === 'agent') return 'own'
  if (role.value === 'user') return 'incoming'
  return 'bot'
})

const avatarText = computed(() => {
  if (displayRole.value === 'bot') return 'AI'
  if (
    displayRole.value === 'incoming'
    || displayRole.value === 'agent'
  ) {
    return '客'
  }
  return ''
})

const showAvatar = computed(() => Boolean(avatarText.value))
const showAgentLabel = computed(
  () => role.value === 'agent' && !isAgentPerspective.value
)

const object = computed(() => props.message.object || null)
const text = computed(() => props.message.text || '')
</script>

<template>
  <div class="message" :class="displayRole">
    <div
      v-if="showAvatar"
      class="avatar"
      :class="avatarText === 'AI' ? 'bot' : 'agent'"
    >
      {{ avatarText }}
    </div>

    <div class="bubble-wrap">
      <span v-if="showAgentLabel" class="agent-label">人工客服</span>
      <div class="bubble">
        <div v-if="object" class="object-chip">
          <span class="type">{{ object.type }}</span>
          <span>{{ object.title || object.id }}</span>
          <span v-if="object.title">{{ object.id }}</span>
        </div>
        <template v-else>{{ text }}</template>
      </div>
    </div>
  </div>
</template>